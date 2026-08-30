import os
import logging
import pandas as pd
from typing import List, Dict, Any, Optional

from src.config.mongo_client import mongo_client
from src.modelling.registry import (
    get_model,
    load_active_models,
    ModelNotFoundError,
    ModelArtifactNotFoundError,
)
from src.modelling.base import BaseGroundwaterModel

# Configure Logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Configuration ---
FORECAST_COLLECTION = "daily_forecasts"
FORECAST_HORIZON_DAYS = 7
HISTORY_WINDOW = 35  # Ensures sufficient history for 30-day LSTM sequence length

def get_recent_history(region_ids: List[str]) -> pd.DataFrame:
    """Fetches recent history from OLAP feature store to drive recursive inference."""
    try:
        db = mongo_client.get_olap_db()
        all_data = []
        
        for rid in region_ids:
            cursor = db.region_feature_store.find({"region_id": rid}).sort("date", -1).limit(HISTORY_WINDOW)
            docs = list(cursor)
            if not docs:
                continue
            docs.reverse()
            all_data.extend(docs)
            
        if not all_data:
            return pd.DataFrame()
            
        df = pd.DataFrame(all_data)
        df['date'] = pd.to_datetime(df['date'])
        return df
    except Exception as e:
        logger.error(f"❌ Failed to fetch recent history for regions {region_ids}: {e}")
        return pd.DataFrame()

def get_feature_importance(region_id: str) -> List[Dict[str, Any]]:
    """
    Extracts feature drivers from the active model for a region.
    Raises ModelNotFoundError or ModelArtifactNotFoundError if model is missing.
    """
    model = get_model(region_id)
    return model.get_feature_importance()

def predict_scenario(region_id: str, rainfall_mod: float, extraction_mod: float) -> Dict[str, Any]:
    """
    Runs a single-step simulation with modified inputs using the region's active model.
    """
    model = get_model(region_id)
    history_df = get_recent_history([region_id])
    
    if history_df.empty:
        raise ValueError(f"No history data found in feature store for region '{region_id}'")
        
    return model.predict_scenario(
        history_df=history_df,
        rainfall_mod=rainfall_mod,
        extraction_mod=extraction_mod
    )

def run_inference(
    region_id_filter: Optional[str] = None, 
    planned_extraction_schedule: Optional[List[float]] = None
) -> List[Dict[str, Any]]:
    """
    Main Forecasting Routine (7-Day Horizon).
    Dispatches polymorphic inference to active model implementations.
    """
    try:
        # 1. Resolve target models
        if region_id_filter:
            model = get_model(region_id_filter)
            models: Dict[str, BaseGroundwaterModel] = {region_id_filter: model}
        else:
            models = load_active_models()
            
        if not models:
            logger.warning("⚠️ No active models available for inference.")
            return []

        # 2. Fetch history for all active regions
        history_df = get_recent_history(list(models.keys()))
        if history_df.empty:
            logger.warning("⚠️ No recent history data available for active regions.")
            return []

        forecasts: List[Dict[str, Any]] = []
        mode_label = "SCENARIO" if planned_extraction_schedule is not None else "BATCH"
        logger.info(f"🔮 Generating {FORECAST_HORIZON_DAYS}-day forecasts for {len(models)} regions ({mode_label} MODE)...")

        # 3. Polymorphic Inference Execution
        for region_id, model in models.items():
            region_df = history_df[history_df['region_id'] == region_id].copy()
            if region_df.empty:
                logger.warning(f"⚠️ No history found for region {region_id}, skipping.")
                continue

            region_forecasts = model.predict_horizon(
                history_df=region_df,
                horizon_days=FORECAST_HORIZON_DAYS,
                planned_extraction_schedule=planned_extraction_schedule
            )
            forecasts.extend(region_forecasts)

        # 4. Handle Output
        if planned_extraction_schedule is not None:
            # Scenario Mode: Return ephemeral simulation results, do not persist to database
            logger.info(f"🧪 Generated scenario forecasts for {region_id_filter or 'all'} ({len(forecasts)} steps)")
            return forecasts

        # Batch Mode: Persist forecast horizons to MongoDB
        if forecasts:
            try:
                db = mongo_client.get_olap_db()
                collection = db[FORECAST_COLLECTION]
                
                region_ids = list(set(f['region_id'] for f in forecasts))
                dates = list(set(f['forecast_date'] for f in forecasts))
                
                collection.delete_many({
                    "region_id": {"$in": region_ids},
                    "forecast_date": {"$in": dates}
                })
                
                result = collection.insert_many(forecasts)
                logger.info(f"✅ Saved {len(result.inserted_ids)} forecast records to MongoDB.")
            except Exception as e:
                logger.error(f"❌ Failed to persist forecasts to MongoDB: {e}")
                
        return forecasts

    except Exception as e:
        logger.exception(f"❌ Inference Failed: {e}")
        raise e

if __name__ == "__main__":
    run_inference()