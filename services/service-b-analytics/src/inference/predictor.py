import os
import json
import joblib
import logging
import pandas as pd
import numpy as np
from datetime import timedelta
from typing import List, Dict, Any

from src.config.mongo_client import mongo_client

# Configure Logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Configuration ---
ARTIFACTS_DIR = "models/v1"
REGISTRY_PATH = os.path.join(ARTIFACTS_DIR, "model_registry.json")
FORECAST_COLLECTION = "daily_forecasts"
FORECAST_HORIZON_DAYS = 7
HISTORY_WINDOW = 30  # Needed to calculate rolling trends

# Exact same features used in training
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
            # Load Scikit-Learn model via Joblib
            model = joblib.load(path)
            loaded_models[region_id] = model
        except Exception as e:
            logger.error(f"❌ Failed to load RF model for {region_id}: {e}")

    logger.info(f"✅ Loaded {len(loaded_models)} active RF models.")
    return loaded_models

def get_recent_history(region_ids: List[str]) -> pd.DataFrame:
    """Fetches enough history to calculate rolling features (trends/flux sums)."""
    db = mongo_client.get_olap_db()
    all_data = []
    
    for rid in region_ids:
        # We need the last N days to calculate trends for tomorrow
        cursor = db.region_feature_store.find({"region_id": rid}).sort("date", -1).limit(HISTORY_WINDOW)
        docs = list(cursor)
        if not docs: continue
        docs.reverse() # Oldest first
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

def run_inference():
    """
    Main Random Forest Recursive Forecasting Routine.
    """
    try:
        models = load_active_models()
        if not models: return

        history_df = get_recent_history(list(models.keys()))
        if history_df.empty: return

        forecasts = []
        logger.info(f"🌲 Generating {FORECAST_HORIZON_DAYS}-day RF forecasts...")

        for region_id, region_df in history_df.groupby('region_id'):
            model = models.get(region_id)
            if not model: continue

            # Create a local buffer to simulate time passing
            # We copy the relevant columns to a list of dicts for easy appending
            sim_buffer = region_df.to_dict('records')
            
            # Static values
            permeability = region_df['feat_soil_permeability'].iloc[-1]
            last_date = region_df['date'].iloc[-1]

            for i in range(1, FORECAST_HORIZON_DAYS + 1):
                next_date = last_date + timedelta(days=i)
                
                # --- 1. PREPARE FEATURES FOR T+i ---
                
                # A. External Forcings (Assumption: Neutral/Zero for future)
                eff_rain = 0.0
                log_ext = 0.0
                
                # B. Calculate Derived Physics (Flux)
                # Formula matches feature_engineering.py: Rain - (LogExt * 0.1)
                current_net_flux = eff_rain - (log_ext * 0.1)
                
                # C. Retrieve Lags from Simulation Buffer
                # Lag 1 Day
                prev_day_row = sim_buffer[-1]
                # Note: If 'net_flux_proxy' isn't in history, we calculate it or fallback to lag features
                feat_flux_lag_1 = prev_day_row.get('net_flux_proxy', 
                                    prev_day_row.get('effective_rainfall', 0) - (prev_day_row.get('log_extraction', 0) * 0.1))

                # Window Sum (Last 7 days approx)
                # Extract last 7 fluxes from buffer
                recent_fluxes = []
                for row in sim_buffer[-7:]:
                    f = row.get('net_flux_proxy', row.get('effective_rainfall', 0) - (row.get('log_extraction', 0) * 0.1))
                    recent_fluxes.append(f)
                feat_flux_window = sum(recent_fluxes)

                # D. Water Trend (T-1 vs T-8)
                # We need the water level from 1 day ago and 8 days ago
                val_t_minus_1 = sim_buffer[-1].get('target_water_level', sim_buffer[-1].get('avg_water_level', 0))
                
                if len(sim_buffer) >= 8:
                    val_t_minus_8 = sim_buffer[-8].get('target_water_level', sim_buffer[-8].get('avg_water_level', 0))
                else:
                    val_t_minus_8 = val_t_minus_1 # Fallback if buffer too short
                
                feat_trend_7d = val_t_minus_1 - val_t_minus_8

                # E. Seasonality
                seas = generate_seasonality_features(next_date)

                # Construct Feature Vector (Must match training order!)
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

                # --- 2. PREDICT ---
                prediction = model.predict(input_row)[0]
                
                # --- 3. UPDATE BUFFER ---
                # Add this prediction to buffer so next iteration can calculate trends
                sim_buffer.append({
                    'date': next_date,
                    'region_id': region_id,
                    'target_water_level': prediction, # This becomes history for next step
                    'net_flux_proxy': current_net_flux,
                    'effective_rainfall': eff_rain,
                    'log_extraction': log_ext
                })

                # --- 4. SAVE RESULT ---
                forecasts.append({
                    "region_id": region_id,
                    "forecast_date": next_date.normalize().to_pydatetime(),
                    "predicted_level": float(round(prediction, 4)),
                    "model_version": "v3.0-rf-sklearn",
                    "created_at": pd.Timestamp.utcnow().to_pydatetime(),
                    "horizon_step": i
                })

        # Save to DB (Identical to previous implementation)
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

    except Exception as e:
        logger.exception(f"❌ Inference Failed: {e}")
        raise e

if __name__ == "__main__":
    run_inference()