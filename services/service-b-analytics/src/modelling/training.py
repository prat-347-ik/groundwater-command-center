import os
import json
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from src.config.mongo_client import mongo_client
from src.modelling.linear_regression.model import LinearRegressionModel
from src.modelling.random_forest.model import RandomForestModel
from src.modelling.lstm.model import LSTMModel

# Configure Logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Configuration ---
ARTIFACTS_ROOT = "models/v1"
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
TARGET = 'target_water_level'
MIN_HISTORY_DAYS = 30
TRAIN_SPLIT_RATIO = 0.80

def fetch_training_data() -> pd.DataFrame:
    """Fetches the complete feature store from MongoDB OLAP database."""
    db = mongo_client.get_olap_db()
    
    projection = {f: 1 for f in FEATURES}
    projection[TARGET] = 1
    projection['region_id'] = 1
    projection['date'] = 1
    
    logger.info("📡 Fetching feature data from region_feature_store...")
    cursor = db.region_feature_store.find({}, projection)
    
    df = pd.DataFrame(list(cursor))
    if df.empty:
        logger.warning("⚠️ No training data found in OLAP feature store.")
        return pd.DataFrame()
        
    df['date'] = pd.to_datetime(df['date'])
    return df

def calculate_baseline_mae(train_df: pd.DataFrame, test_df: pd.DataFrame) -> float:
    """Calculates persistence baseline MAE (predicting last known training value)."""
    if train_df.empty or test_df.empty:
        return 999.0
    last_val = train_df[TARGET].iloc[-1]
    baseline_preds = np.full(len(test_df), last_val)
    return float(np.mean(np.abs(test_df[TARGET].values - baseline_preds)))

def train_region_candidates(region_id: str, df: pd.DataFrame, model_type: str = "all") -> List[Dict[str, Any]]:
    """
    Trains candidate models (LinearRegression and RandomForest) for a given region.
    Returns metadata list of candidates for evaluation and promotion gating.
    """
    df = df.sort_values('date').reset_index(drop=True)
    if len(df) < MIN_HISTORY_DAYS:
        logger.warning(f"⚠️ Skipping {region_id}: Insufficient data ({len(df)} rows < {MIN_HISTORY_DAYS})")
        return []

    split_idx = int(len(df) * TRAIN_SPLIT_RATIO)
    train_df = df.iloc[:split_idx].copy()
    test_df = df.iloc[split_idx:].copy()

    if test_df.empty:
        logger.warning(f"⚠️ Skipping {region_id}: Test slice is empty.")
        return []

    baseline_mae = calculate_baseline_mae(train_df, test_df)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    os.makedirs(os.path.join(ARTIFACTS_ROOT, "artifacts"), exist_ok=True)
    os.makedirs(os.path.join(ARTIFACTS_ROOT, "metadata"), exist_ok=True)

    candidates: List[Dict[str, Any]] = []
    target_type = model_type.strip().lower()

    # 1. Train Linear Regression Candidate
    if target_type in ("all", "linear-regression", "linear_regression", "lr"):
        try:
            lr_model = LinearRegressionModel(region_id=region_id)
            lr_model.fit(train_df)
            
            # Evaluate on validation slice
            X_test_lr = test_df[lr_model.features]
            lr_preds = lr_model.model.predict(X_test_lr)
            lr_mae = float(np.mean(np.abs(test_df[TARGET].values - lr_preds)))
            lr_rmse = float(np.sqrt(np.mean((test_df[TARGET].values - lr_preds) ** 2)))

            lr_filename = f"{region_id}_{timestamp}_lr.pkl"
            lr_artifact_path = os.path.join(ARTIFACTS_ROOT, "artifacts", lr_filename)
            lr_model.save(lr_artifact_path)

            lr_meta_filename = f"{region_id}_{timestamp}_lr.json"
            lr_meta_path = os.path.join(ARTIFACTS_ROOT, "metadata", lr_meta_filename)
            lr_meta = {
                "region_id": region_id,
                "model_type": "linear-regression",
                "version": f"1.0-lr-{timestamp}",
                "status": "candidate",
                "artifact_path": lr_artifact_path,
                "metadata_path": lr_meta_path,
                "registered_at": datetime.now(timezone.utc).isoformat(),
                "promoted_at": None,
                "metrics": {
                    "mae": round(lr_mae, 4),
                    "rmse": round(lr_rmse, 4),
                    "baseline_mae": round(baseline_mae, 4)
                }
            }
            with open(lr_meta_path, 'w') as f:
                json.dump(lr_meta, f, indent=2)
            candidates.append(lr_meta)
            logger.info(f"✅ Trained LinearRegression [{region_id}] | MAE: {lr_mae:.4f} | Baseline: {baseline_mae:.4f}")
        except Exception as e:
            logger.error(f"❌ Failed to train LinearRegression for {region_id}: {e}")

    # 2. Train Random Forest Candidate
    if target_type in ("all", "random-forest", "random_forest", "rf"):
        try:
            rf_model = RandomForestModel(region_id=region_id, random_state=42)
            rf_model.fit(train_df)

            X_test_rf = test_df[rf_model.features]
            rf_preds = rf_model.model.predict(X_test_rf)
            rf_mae = float(np.mean(np.abs(test_df[TARGET].values - rf_preds)))
            rf_rmse = float(np.sqrt(np.mean((test_df[TARGET].values - rf_preds) ** 2)))

            rf_filename = f"{region_id}_{timestamp}_rf.pkl"
            rf_artifact_path = os.path.join(ARTIFACTS_ROOT, "artifacts", rf_filename)
            rf_model.save(rf_artifact_path)

            rf_meta_filename = f"{region_id}_{timestamp}_rf.json"
            rf_meta_path = os.path.join(ARTIFACTS_ROOT, "metadata", rf_meta_filename)
            rf_meta = {
                "region_id": region_id,
                "model_type": "random-forest",
                "version": f"1.0-rf-{timestamp}",
                "status": "candidate",
                "artifact_path": rf_artifact_path,
                "metadata_path": rf_meta_path,
                "registered_at": datetime.now(timezone.utc).isoformat(),
                "promoted_at": None,
                "metrics": {
                    "mae": round(rf_mae, 4),
                    "rmse": round(rf_rmse, 4),
                    "baseline_mae": round(baseline_mae, 4)
                }
            }
            with open(rf_meta_path, 'w') as f:
                json.dump(rf_meta, f, indent=2)
            candidates.append(rf_meta)
            logger.info(f"✅ Trained RandomForest [{region_id}] | MAE: {rf_mae:.4f} | Baseline: {baseline_mae:.4f}")
        except Exception as e:
            logger.error(f"❌ Failed to train RandomForest for {region_id}: {e}")

    return candidates

def run_training_pipeline(model_type: str = "all") -> List[Dict[str, Any]]:
    """
    Orchestrates the candidate training pipeline across all regions.
    Saves candidate summaries to evaluation_summary.json for the promotion gate.
    """
    try:
        os.makedirs(ARTIFACTS_ROOT, exist_ok=True)
        df = fetch_training_data()
        
        if df.empty:
            logger.warning("❌ Aborting training: No data available in feature store.")
            return []

        regions = df['region_id'].unique()
        logger.info(f"🔄 Starting multi-model candidate training ({model_type}) for {len(regions)} regions...")
        
        all_candidates: List[Dict[str, Any]] = []
        for region_id in regions:
            region_data = df[df['region_id'] == region_id]
            candidates = train_region_candidates(region_id, region_data, model_type=model_type)
            all_candidates.extend(candidates)
            
        summary_path = os.path.join(ARTIFACTS_ROOT, "evaluation_summary.json")
        with open(summary_path, 'w') as f:
            json.dump(all_candidates, f, indent=2)
            
        logger.info(f"🎉 Candidate training completed. {len(all_candidates)} candidates saved to {summary_path}")
        return all_candidates
        
    except Exception as e:
        logger.exception(f"❌ Training Pipeline Failed: {e}")
        raise e

if __name__ == "__main__":
    run_training_pipeline()