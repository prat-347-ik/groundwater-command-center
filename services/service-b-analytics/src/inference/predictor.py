import os
import json
import pickle
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

# Features expected by the model (Must match training!)
FEATURES = [
    'feat_rainfall_1d_lag', 
    'feat_rainfall_7d_sum', 
    'feat_water_trend_7d', 
    'feat_sin_day', 
    'feat_cos_day'
]

def load_active_models() -> Dict[str, str]:
    """
    Loads the registry and maps region_id -> artifact_path strictly for ACTIVE models.
    
    Constraints:
    - Must load from registry.json (Single Source of Truth)
    - Must filter by status="active"
    - Must fail fast if no models are available
    """
    if not os.path.exists(REGISTRY_PATH):
        # Fail Fast: If registry is missing, the system is in an invalid state.
        raise FileNotFoundError(f"🚨 CRITICAL: Registry not found at {REGISTRY_PATH}. Cannot perform inference.")
        
    try:
        with open(REGISTRY_PATH, 'r') as f:
            registry = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"🚨 CRITICAL: Corrupted registry file. {e}")

    # Filter: Select ONLY active models
    # This prevents loading 'staged', 'archived', or 'rejected' models
    active_models = [
        entry for entry in registry 
        if entry.get('status') == 'active'
    ]
    
    if not active_models:
        # Fail Fast: Running inference with 0 models is likely a pipeline error
        raise RuntimeError("🚨 CRITICAL: Registry exists but contains NO 'active' models. Aborting.")

    # Create optimized lookup map
    model_map = {entry['region_id']: entry['artifact_path'] for entry in active_models}
    
    logging.info(f"✅ Loaded {len(model_map)} active models from registry.")
    return model_map

def load_model_registry() -> Dict[str, str]:
    """
    Loads the registry and maps region_id -> artifact_path.
    """
    if not os.path.exists(REGISTRY_PATH):
        logger.error("❌ Model registry not found. Cannot perform inference.")
        return {}
        
    with open(REGISTRY_PATH, 'r') as f:
        registry = json.load(f)
        
    # Create a map for quick lookup: region_id -> full_artifact_path
    return {entry['region_id']: entry['artifact_path'] for entry in registry}

def get_latest_features(region_ids: List[str]) -> pd.DataFrame:
    """
    Fetches the most recent feature row for each requested region.
    """
    db = mongo_client.get_olap_db()
    
    # We use an aggregation to get the 'max' date document per region
    pipeline = [
        {"$match": {"region_id": {"$in": region_ids}}},
        {"$sort": {"date": -1}},
        {"$group": {
            "_id": "$region_id",
            "latest_doc": {"$first": "$$ROOT"}
        }},
        {"$replaceRoot": {"newRoot": "$latest_doc"}}
    ]
    
    docs = list(db.region_feature_store.aggregate(pipeline))
    
    if not docs:
        return pd.DataFrame()
        
    df = pd.DataFrame(docs)
    df['date'] = pd.to_datetime(df['date'])
    return df

def generate_seasonality_features(date: pd.Timestamp) -> Dict[str, float]:
    """
    Calculates deterministic seasonality features for a given date.
    """
    day_of_year = date.dayofyear
    return {
        "feat_sin_day": np.sin(2 * np.pi * day_of_year / 365.0),
        "feat_cos_day": np.cos(2 * np.pi * day_of_year / 365.0)
    }

def run_inference():
    """
    Main Forecasting Routine.
    1. Load Models
    2. Fetch Latest State
    3. Generate 7-Day Forecast (Recursive)
    4. Save to OLAP
    """
    try:
        # 1. Load Model Map
        model_map = load_model_registry()
        if not model_map:
            return

        # 2. Fetch Latest Features for all trained regions
        active_regions = list(model_map.keys())
        latest_df = get_latest_features(active_regions)
        
        if latest_df.empty:
            logger.warning("⚠️ No feature data found. Skipping inference.")
            return

        forecasts = []
        
        logger.info(f"🔮 Generating {FORECAST_HORIZON_DAYS}-day forecasts for {len(latest_df)} regions...")

        for _, row in latest_df.iterrows():
            region_id = row['region_id']
            artifact_path = model_map.get(region_id)
            
            # Load Region Model
            if not artifact_path or not os.path.exists(artifact_path):
                logger.warning(f"  Skipping {region_id}: Model artifact missing.")
                continue
                
            with open(artifact_path, 'rb') as f:
                model = pickle.load(f)

            # --- Recursive Forecasting Loop ---
            # We start with the known 'current' state
            current_date = row['date']
            
            # Initialize dynamic features with the latest known values
            current_trend = row['feat_water_trend_7d']
            
            # Rainfall assumptions for future: 0 (Conservative / No-Rain Scenario)
            # In v2, this would be replaced by a weather service API input.
            future_rain_1d = 0.0
            future_rain_7d = 0.0 # Decaying old rain would be better, but 0 is safe baseline

            for i in range(1, FORECAST_HORIZON_DAYS + 1):
                forecast_date = current_date + timedelta(days=i)
                
                # 1. Build Feature Vector
                seasonality = generate_seasonality_features(forecast_date)
                
                # Construct Input (Order must match FEATURES list exactly)
                # Note: For T+1, we could strictly use T's lags if we had them.
                # Here we simplify: T+1 uses actuals (if i==1), T+n uses assumptions.
                if i == 1:
                    # Day 1: Use the actual Lag/Sum from the feature store (which are technically T-1 lags)
                    # This represents the prediction for "Tomorrow" based on "Today's" known data.
                    input_vector = np.array([[
                        row['feat_rainfall_1d_lag'],
                        row['feat_rainfall_7d_sum'],
                        row['feat_water_trend_7d'],
                        seasonality['feat_sin_day'],
                        seasonality['feat_cos_day']
                    ]])
                else:
                    # Day 2+: Recursive / Assumed inputs
                    input_vector = np.array([[
                        future_rain_1d,    # Assume Dry
                        future_rain_7d,    # Assume Dry
                        current_trend,     # Assume Momentum Persists (Constant Trend)
                        seasonality['feat_sin_day'],
                        seasonality['feat_cos_day']
                    ]])
                
                # 2. Predict
                # Use DataFrame to pass feature names and avoid sklearn warnings
                input_df = pd.DataFrame(input_vector, columns=FEATURES)
                prediction = model.predict(input_df)[0]
                
                # 3. Append to Results
                forecasts.append({
                    "region_id": region_id,
                    "forecast_date": forecast_date,
                    "predicted_level": round(prediction, 4),
                    "model_version": "v1.0-linear-baseline",
                    "created_at": pd.Timestamp.utcnow(),
                    "horizon_step": i
                })

        # 4. Save to OLAP
        if forecasts:
            db = mongo_client.get_olap_db()
            collection = db[FORECAST_COLLECTION]
            
            # Idempotency: Delete existing forecasts for these dates/regions before inserting?
            # For simplicity in v1, we just insert. A production job might clear overlap.
            result = collection.insert_many(forecasts)
            logger.info(f"✅ Saved {len(result.inserted_ids)} forecast records to '{FORECAST_COLLECTION}'.")
        else:
            logger.info("No forecasts generated.")

    except Exception as e:
        logger.exception(f"❌ Inference Failed: {e}")
        raise e
    finally:
        mongo_client.close()

if __name__ == "__main__":
    run_inference()