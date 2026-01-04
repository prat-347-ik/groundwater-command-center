import os
import pickle
import json
import logging
import subprocess
from datetime import datetime,timezone
import numpy as np  # Added for RMSE calculation
from typing import Dict, Any, List

import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error  # Added mean_squared_error

from src.config.mongo_client import mongo_client

# Configure Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configuration ---
# Root directory for the model versioning system
ARTIFACTS_ROOT = "models/v1"
FEATURES = [
    'feat_rainfall_1d_lag', 
    'feat_rainfall_7d_sum', 
    'feat_water_trend_7d', 
    'feat_sin_day', 
    'feat_cos_day'
]
TARGET = 'target_water_level'
MIN_HISTORY_DAYS = 90
TRAIN_SPLIT_RATIO = 0.80

def fetch_training_data() -> pd.DataFrame:
    """
    Fetches the complete feature store from the OLAP database.
    """
    db = mongo_client.get_olap_db()
    # Fetch only necessary fields to optimize I/O
    projection = {f: 1 for f in FEATURES}
    projection[TARGET] = 1
    projection['region_id'] = 1
    projection['date'] = 1
    projection['_id'] = 0
    
    logger.info("📡 Fetching data from region_feature_store...")
    cursor = db.region_feature_store.find({}, projection)
    
    df = pd.DataFrame(list(cursor))
    
    if df.empty:
        raise ValueError("No training data found in region_feature_store.")
        
    # Ensure date is datetime for sorting
    df['date'] = pd.to_datetime(df['date'])
    return df

def train_region_model(region_id: str, df_region: pd.DataFrame) -> Dict[str, Any]:
    """
    Trains a Linear Regression model for a single region using time-based split.
    
    Args:
        region_id: Unique identifier for the region.
        df_region: DataFrame containing data ONLY for this region.
        
    Returns:
        Metadata dictionary if successful, None otherwise.
    """
    # 1. Sort by Date (CRITICAL for time-series)
    # Strict chronological order prevents future leakage
    df_region = df_region.sort_values('date').reset_index(drop=True)
    
    # 2. Check Minimum History
    if len(df_region) < MIN_HISTORY_DAYS:
        logger.warning(f"⚠️ Region {region_id}: Skipped (Insufficient history: {len(df_region)} days)")
        return None

    # 3. Time-Based Split
    # No random shuffling!
    split_idx = int(len(df_region) * TRAIN_SPLIT_RATIO)
    
    train_df = df_region.iloc[:split_idx]
    test_df = df_region.iloc[split_idx:]
    
    X_train = train_df[FEATURES]
    y_train = train_df[TARGET]
    X_test = test_df[FEATURES]
    y_test = test_df[TARGET]

    # 4. Train Model (Linear Regression)
    # We use OLS (Ordinary Least Squares) as defined in the baseline contract
    model = LinearRegression()
    model.fit(X_train, y_train)

    # 5. Evaluate (MAE)
    # Validate using the "future" (test set)
    predictions = model.predict(X_test)
    mae = mean_absolute_error(y_test, predictions)
    # UPDATED: Calculate RMSE for richer metrics
    rmse = np.sqrt(mean_squared_error(y_test, predictions))
    
    # 6. Sanity Check: Baseline Comparison (Persistence)
    # Predict t = t-1
    persistence_pred = test_df[TARGET].shift(1)
    # Drop first row of test set for fair comparison (due to shift NaNs)
    valid_indices = persistence_pred.dropna().index
    persistence_mae = mean_absolute_error(test_df.loc[valid_indices, TARGET], persistence_pred.loc[valid_indices])
    
    logger.info(f"✅ Region {region_id}: MAE={mae:.4f} (Baseline={persistence_mae:.4f})")

    # 7. Save Artifacts & Metadata (Versioning Logic)
    # ---------------------------------------------------------
    # Define sub-directories
    artifacts_dir = os.path.join(ARTIFACTS_ROOT, "artifacts")
    metadata_dir = os.path.join(ARTIFACTS_ROOT, "metadata")
    os.makedirs(artifacts_dir, exist_ok=True)
    os.makedirs(metadata_dir, exist_ok=True)

    # Retrieve Git Hash for Lineage
    # This binds the code version to the binary artifact
    try:
        git_hash = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).decode('ascii').strip()
    except Exception:
        git_hash = "nohash"

    # Generate Naming: {region_id}_{YYYYMMDD_HHMMSS}_{git_hash}
    # Timestamp is UTC to ensure global consistency
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    base_filename = f"{region_id}_{timestamp}_{git_hash}"
    
    artifact_filename = f"{base_filename}.pkl"
    metadata_filename = f"{base_filename}.json"
    
    artifact_path = os.path.join(artifacts_dir, artifact_filename)
    metadata_path = os.path.join(metadata_dir, metadata_filename)
    
    # Safety Check: Never overwrite existing files (Immutability)
    if os.path.exists(artifact_path):
        logger.error(f"⛔ Artifact collision detected: {artifact_path}")
        raise FileExistsError(f"Artifact {artifact_path} already exists. Aborting to maintain immutability.")
    
    # Save Binary Artifact
    with open(artifact_path, 'wb') as f:
        pickle.dump(model, f)

    # 8. Prepare & Save Metadata
    # This file provides the audit trail for the binary
    metadata = {
        "region_id": region_id,
        "model_type": "LinearRegression",
        "features": FEATURES,
        "training_rows": len(train_df),
        "test_rows": len(test_df),
        "mae": round(mae, 4),
        "rmse": round(rmse, 4), # UPDATED: Included in metadata
        "baseline_mae": round(persistence_mae, 4),
        "artifact_path": artifact_path,
        "metadata_path": metadata_path,
        "trained_at": timestamp,
        "git_hash": git_hash,
        "coefficients": {feat: round(coef, 4) for feat, coef in zip(FEATURES, model.coef_)},
        "intercept": round(model.intercept_, 4)
    }

    # Save Metadata JSON
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)

    logger.info(f"💾 Artifact saved: {artifact_path}")
    logger.info(f"📄 Metadata saved: {metadata_path}")

    return metadata

def save_evaluation_summary(results: List[Dict[str, Any]]):
    """
    Writes a transient summary of the latest training run to disk.
    This file is overwritten every run and allows quick inspection of model health.
    """
    summary_path = os.path.join(ARTIFACTS_ROOT, "evaluation_summary.json")
    
    summary_data = [
        {
            "region_id": r["region_id"],
            "mae": r["mae"],
            "rmse": r["rmse"],
            "baseline_mae": r["baseline_mae"],
            "trained_at": r["trained_at"],
            "artifact_path": r["artifact_path"],
            "metadata_path": r["metadata_path"]
        }
        for r in results
    ]
    
    with open(summary_path, 'w') as f:
        json.dump(summary_data, f, indent=2)
        
    logger.info(f"📊 Evaluation summary overwritten: {summary_path}")

def run_training_pipeline():
    """
    Orchestrates the training for all regions.
    """
    try:
        # Setup output directory
        os.makedirs(ARTIFACTS_ROOT, exist_ok=True)
        
        # Load Data
        df = fetch_training_data()
        
        # Group by Region (Split-Apply-Combine strategy)
        regions = df['region_id'].unique()
        logger.info(f"🔄 Starting training for {len(regions)} regions...")
        
        results = []
        for region_id in regions:
            region_data = df[df['region_id'] == region_id]
            metadata = train_region_model(region_id, region_data)
            if metadata:
                results.append(metadata)
        
        # UPDATED: Save Transient Summary (CRITICAL for Gating)
        if results:
            save_evaluation_summary(results)
        
        # Save Run Manifest
        # NOTE: We do NOT overwrite 'registry.json' here. 
        # Promotion to registry is a separate gated process.
        manifest_path = os.path.join(ARTIFACTS_ROOT, "latest_run_manifest.json")
        with open(manifest_path, 'w') as f:
            json.dump(results, f, indent=2)
            
        logger.info(f"🎉 Training Complete. Run manifest saved to {manifest_path}")
        
    except Exception as e:
        logger.exception(f"❌ Training Pipeline Failed: {e}")
        raise e
    finally:
        mongo_client.close()

if __name__ == "__main__":
    run_training_pipeline()