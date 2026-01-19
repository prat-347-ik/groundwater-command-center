import os
import json
import torch
import logging
import pandas as pd
import numpy as np
from datetime import timedelta
from typing import List, Dict, Any

from src.config.mongo_client import mongo_client
from src.modelling.lstm_arch import GroundwaterLSTM  # Must match the architecture definition

# Configure Logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Configuration ---
ARTIFACTS_DIR = "models/v1"
REGISTRY_PATH = os.path.join(ARTIFACTS_DIR, "model_registry.json")
FORECAST_COLLECTION = "daily_forecasts"
FORECAST_HORIZON_DAYS = 7
SEQUENCE_LENGTH = 30  # LSTM requires 30 days of history

# Features expected by the LSTM model (Order Matters!)
FEATURES = [
    'effective_rainfall', 
    'log_extraction', 
    'feat_net_flux_1d_lag', 
    'feat_soil_permeability', 
    'feat_sin_day', 
    'feat_cos_day'
]

def load_active_models() -> Dict[str, Any]:
    """
    Loads active PyTorch models from the registry.
    Returns: Dict[region_id, loaded_model_object]
    """
    if not os.path.exists(REGISTRY_PATH):
        raise FileNotFoundError(f"🚨 CRITICAL: Registry not found at {REGISTRY_PATH}.")
        
    try:
        with open(REGISTRY_PATH, 'r') as f:
            registry = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"🚨 CRITICAL: Corrupted registry file. {e}")

    active_entries = [entry for entry in registry if entry.get('status') == 'active']
    
    if not active_entries:
        logger.warning("⚠️ No active models found in registry.")
        return {}

    loaded_models = {}
    for entry in active_entries:
        region_id = entry['region_id']
        path = entry['artifact_path']
        
        if not os.path.exists(path):
            logger.error(f"❌ Artifact missing for {region_id}: {path}")
            continue
            
        try:
            # Initialize Architecture
            model = GroundwaterLSTM(input_dim=len(FEATURES), hidden_dim=50)
            # Load Weights
            model.load_state_dict(torch.load(path))
            model.eval() # Set to inference mode
            loaded_models[region_id] = model
        except Exception as e:
            logger.error(f"❌ Failed to load PyTorch model for {region_id}: {e}")

    logger.info(f"✅ Loaded {len(loaded_models)} active LSTM models.")
    return loaded_models

def get_recent_history(region_ids: List[str]) -> pd.DataFrame:
    """
    Fetches the last 30 days of features for each active region.
    Returns a DataFrame containing history for all requested regions.
    """
    db = mongo_client.get_olap_db()
    
    # Aggregation to get last N docs per group is complex, so we iterate for simplicity
    # (In high-scale, use $window or $sort+$group+$slice)
    all_data = []
    
    for rid in region_ids:
        cursor = db.region_feature_store.find(
            {"region_id": rid}
        ).sort("date", -1).limit(SEQUENCE_LENGTH)
        
        docs = list(cursor)
        if len(docs) < SEQUENCE_LENGTH:
            logger.warning(f"⚠️ Insufficient history for {rid} (Found {len(docs)}, Need {SEQUENCE_LENGTH}). Skipping.")
            continue
            
        # Sort back to ascending time for the LSTM (Oldest -> Newest)
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

def run_inference():
    """
    Main LSTM Forecasting Routine.
    """
    try:
        # 1. Load Models
        models = load_active_models()
        if not models:
            return

        # 2. Fetch History (30 Days)
        history_df = get_recent_history(list(models.keys()))
        if history_df.empty:
            return

        forecasts = []
        logger.info(f"🔮 Generating {FORECAST_HORIZON_DAYS}-day LSTM forecasts...")

        # Group by region to process sequences
        for region_id, region_df in history_df.groupby('region_id'):
            model = models.get(region_id)
            if not model: continue

            # Prepare Input Tensor (1, 30, 6)
            # Fill NaNs with 0 to prevent crash
            input_data = region_df[FEATURES].fillna(0).values
            
            # Start Recursive Forecasting
            current_seq = torch.tensor(input_data, dtype=torch.float32).unsqueeze(0) # Add batch dim
            last_date = region_df['date'].max()
            
            # We need static features (like permeability) to carry forward
            permeability = region_df['feat_soil_permeability'].iloc[-1]

            for i in range(1, FORECAST_HORIZON_DAYS + 1):
                # Predict next step
                with torch.no_grad():
                    pred_tensor = model(current_seq) # Output shape (1, 1)
                    prediction = pred_tensor.item()
                
                # Create Next Input Row (Recursive Step)
                next_date = last_date + timedelta(days=i)
                seasonality = generate_seasonality_features(next_date)
                
                # Assumption: Future Rain/Extraction = 0 (Conservative)
                # Net Flux Lag: In a real system, we'd calculate this from the predicted level.
                # For now, we assume neutral flux for future steps to stabilize prediction.
                next_row = np.array([[
                    0.0, # effective_rainfall
                    0.0, # log_extraction
                    0.0, # feat_net_flux_1d_lag (Neutral)
                    permeability,
                    seasonality['feat_sin_day'],
                    seasonality['feat_cos_day']
                ]])
                
                # Update Sequence: Drop oldest, add new prediction context
                # Note: We append the 'next_row' features, NOT the predicted water level directly.
                # The LSTM predicts water level, but takes features as input.
                next_tensor = torch.tensor(next_row, dtype=torch.float32).unsqueeze(0)
                current_seq = torch.cat((current_seq[:, 1:, :], next_tensor), dim=1)
                
                # Append to results
                forecasts.append({
                    "region_id": region_id,
                    "forecast_date": next_date.normalize().to_pydatetime(),
                    "predicted_level": float(round(prediction, 4)),
                    "model_version": "v2.0-lstm-pytorch",
                    "created_at": pd.Timestamp.utcnow().to_pydatetime(),
                    "horizon_step": i
                })

        # 4. Save to OLAP
        if forecasts:
            db = mongo_client.get_olap_db()
            collection = db[FORECAST_COLLECTION]
            
            # Idempotency: Clean old forecasts for these dates
            region_ids = list(set(f['region_id'] for f in forecasts))
            dates = list(set(f['forecast_date'] for f in forecasts))
            
            collection.delete_many({
                "region_id": {"$in": region_ids},
                "forecast_date": {"$in": dates}
            })
            
            result = collection.insert_many(forecasts)
            logger.info(f"✅ Saved {len(result.inserted_ids)} LSTM forecast records.")
            
    except Exception as e:
        logger.exception(f"❌ Inference Failed: {e}")
        raise e

if __name__ == "__main__":
    run_inference()