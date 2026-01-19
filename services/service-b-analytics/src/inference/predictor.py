import os
import json
import joblib
import logging
import pandas as pd
import numpy as np
from datetime import timedelta
from typing import List, Dict, Any, Optional

from src.config.mongo_client import mongo_client

# Configure Logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Configuration ---
ARTIFACTS_DIR = "models/v1"
REGISTRY_PATH = os.path.join(ARTIFACTS_DIR, "model_registry.json")
FORECAST_COLLECTION = "daily_forecasts"
FORECAST_HORIZON_DAYS = 7
HISTORY_WINDOW = 30 

# Features (Must match training order)
FEATURES = [
    'effective_rainfall', 
    'log_extraction', 
    'feat_net_flux_1d_lag', 
    'feat_net_flux_window_sum', 
    'feat_water_trend_7d', 
    'feat_soil_permeability', 
    'feat_sin_day', 
    'feat_cos_day'
]

def load_active_models() -> Dict[str, Any]:
    """Loads active .pkl models (Random Forest)."""
    if not os.path.exists(REGISTRY_PATH):
        return {}
        
    try:
        with open(REGISTRY_PATH, 'r') as f:
            registry = json.load(f)
    except Exception:
        return {}

    active_entries = [e for e in registry if e.get('status') == 'active']
    loaded_models = {}

    for entry in active_entries:
        region_id = entry['region_id']
        path = entry['artifact_path']
        
        if not os.path.exists(path):
            continue
            
        try:
            model = joblib.load(path)
            loaded_models[region_id] = model
        except Exception as e:
            logger.error(f"❌ Failed to load RF model for {region_id}: {e}")

    return loaded_models

def get_recent_history(region_ids: List[str]) -> pd.DataFrame:
    """Fetches enough history to calculate rolling features."""
    db = mongo_client.get_olap_db()
    all_data = []
    
    for rid in region_ids:
        cursor = db.region_feature_store.find({"region_id": rid}).sort("date", -1).limit(HISTORY_WINDOW)
        docs = list(cursor)
        if not docs: continue
        docs.reverse()
        all_data.extend(docs)
        
    if not all_data:
        return pd.DataFrame()
        
    df = pd.DataFrame(all_data)
    df['date'] = pd.to_datetime(df['date'])
    return df

def generate_seasonality_features(date: pd.Timestamp) -> Dict[str, float]:
    day_of_year = date.dayofyear
    return {
        "feat_sin_day": np.sin(2 * np.pi * day_of_year / 365.0),
        "feat_cos_day": np.cos(2 * np.pi * day_of_year / 365.0)
    }

def run_inference(region_id_filter: Optional[str] = None, planned_extraction_liters: Optional[float] = None) -> List[Dict[str, Any]]:
    """
    Main Forecasting Routine.
    
    Args:
        region_id_filter: If provided, only runs for this specific region.
        planned_extraction_liters: If provided, runs a 'What-If' scenario using this daily extraction volume 
                                   instead of the default 0.0. (Does NOT save to DB).
    """
    try:
        # 1. Load Models
        models = load_active_models()
        
        # Apply filter if requested
        if region_id_filter:
            if region_id_filter not in models:
                logger.warning(f"⚠️ Model for {region_id_filter} not active or not found.")
                return []
            models = {region_id_filter: models[region_id_filter]}
            
        if not models: 
            return []

        # 2. Fetch History
        history_df = get_recent_history(list(models.keys()))
        if history_df.empty: 
            return []

        forecasts = []
        mode_label = "SCENARIO" if planned_extraction_liters is not None else "BATCH"
        logger.info(f"🌲 Generating {FORECAST_HORIZON_DAYS}-day RF forecasts ({mode_label} MODE)...")

        # 3. Inference Loop
        for region_id, region_df in history_df.groupby('region_id'):
            model = models.get(region_id)
            if not model: continue

            sim_buffer = region_df.to_dict('records')
            permeability = region_df['feat_soil_permeability'].iloc[-1]
            last_date = region_df['date'].iloc[-1]

            for i in range(1, FORECAST_HORIZON_DAYS + 1):
                next_date = last_date + timedelta(days=i)
                
                # --- A. External Forcings ---
                eff_rain = 0.0
                
                # Check for Scenario Input
                if planned_extraction_liters is not None:
                    # Apply user's planned extraction for the scenario
                    log_ext = np.log1p(planned_extraction_liters)
                else:
                    # Default assumption: Zero extraction for future
                    log_ext = 0.0
                
                # --- B. Calculate Derived Physics ---
                current_net_flux = eff_rain - (log_ext * 0.1)
                
                # --- C. Retrieve Lags ---
                prev_day_row = sim_buffer[-1]
                feat_flux_lag_1 = prev_day_row.get('net_flux_proxy', 
                                    prev_day_row.get('effective_rainfall', 0) - (prev_day_row.get('log_extraction', 0) * 0.1))

                recent_fluxes = []
                for row in sim_buffer[-7:]:
                    f = row.get('net_flux_proxy', row.get('effective_rainfall', 0) - (row.get('log_extraction', 0) * 0.1))
                    recent_fluxes.append(f)
                feat_flux_window = sum(recent_fluxes)

                # --- D. Water Trend ---
                val_t_minus_1 = sim_buffer[-1].get('target_water_level', sim_buffer[-1].get('avg_water_level', 0))
                
                if len(sim_buffer) >= 8:
                    val_t_minus_8 = sim_buffer[-8].get('target_water_level', sim_buffer[-8].get('avg_water_level', 0))
                else:
                    val_t_minus_8 = val_t_minus_1
                
                feat_trend_7d = val_t_minus_1 - val_t_minus_8

                # --- E. Seasonality ---
                seas = generate_seasonality_features(next_date)

                # Construct Feature Vector
                input_row = pd.DataFrame([{
                    'effective_rainfall': eff_rain,
                    'log_extraction': log_ext,
                    'feat_net_flux_1d_lag': feat_flux_lag_1,
                    'feat_net_flux_window_sum': feat_flux_window,
                    'feat_water_trend_7d': feat_trend_7d,
                    'feat_soil_permeability': permeability,
                    'feat_sin_day': seas['feat_sin_day'],
                    'feat_cos_day': seas['feat_cos_day']
                }])

                # Predict
                prediction = model.predict(input_row)[0]
                
                # Update Buffer
                sim_buffer.append({
                    'date': next_date,
                    'region_id': region_id,
                    'target_water_level': prediction,
                    'net_flux_proxy': current_net_flux,
                    'effective_rainfall': eff_rain,
                    'log_extraction': log_ext
                })

                # Append Result
                forecasts.append({
                    "region_id": region_id,
                    "forecast_date": next_date.normalize().to_pydatetime(),
                    "predicted_level": float(round(prediction, 4)),
                    "model_version": "v3.0-rf-sklearn",
                    "created_at": pd.Timestamp.utcnow().to_pydatetime(),
                    "horizon_step": i,
                    "scenario_extraction": planned_extraction_liters if planned_extraction_liters is not None else 0
                })

        # 4. Handle Output
        if planned_extraction_liters is not None:
            # SCENARIO MODE: Return results directly, DO NOT SAVE
            logger.info(f"🧪 Generated scenario forecast for {region_id_filter} | Extraction: {planned_extraction_liters}L")
            return forecasts

        # BATCH MODE: Save to DB
        if forecasts:
            db = mongo_client.get_olap_db()
            collection = db[FORECAST_COLLECTION]
            
            region_ids = list(set(f['region_id'] for f in forecasts))
            dates = list(set(f['forecast_date'] for f in forecasts))
            
            collection.delete_many({
                "region_id": {"$in": region_ids},
                "forecast_date": {"$in": dates}
            })
            
            result = collection.insert_many(forecasts)
            logger.info(f"✅ Saved {len(result.inserted_ids)} RF forecast records.")
            
        return forecasts

    except Exception as e:
        logger.exception(f"❌ Inference Failed: {e}")
        raise e

if __name__ == "__main__":
    run_inference()