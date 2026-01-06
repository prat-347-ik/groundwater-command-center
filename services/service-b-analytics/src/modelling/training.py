import os
import pickle
import json
import logging
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, Any, List

# Machine Learning Imports
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error
import numpy as np

# Database
from src.config.mongo_client import mongo_client

# Configure Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configuration ---
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
    # ✅ FIX: Get DB reference inside the function
    db = mongo_client.get_olap_db()
    
    # Fetch only necessary fields to optimize I/O
    projection = {f: 1 for f in FEATURES}
    projection[TARGET] = 1
    projection['region_id'] = 1
    projection['date'] = 1
    
    logger.info("📡 Fetching data from region_feature_store...")
    cursor = db.region_feature_store.find({}, projection)
    
    df = pd.DataFrame(list(cursor))
    
    if df.empty:
        logger.warning("⚠️ No training data found in OLAP.")
        return pd.DataFrame()
        
    return df

def train_region_model(region_id: str, df: pd.DataFrame) -> Dict[str, Any]:
    """
    Trains a Linear Regression model for a specific region.
    Returns metadata dict if successful, None otherwise.
    """
    # 1. Sort & Preprocess
    df = df.sort_values('date').dropna()
    
    if len(df) < MIN_HISTORY_DAYS:
        logger.warning(f"⚠️ Skipping {region_id}: Insufficient data ({len(df)} rows)")
        return None
        
    # 2. Split Data (Chronological Split)
    split_idx = int(len(df) * TRAIN_SPLIT_RATIO)
    train_df = df.iloc[:split_idx]
    test_df = df.iloc[split_idx:]
    
    X_train = train_df[FEATURES]
    y_train = train_df[TARGET]
    X_test = test_df[FEATURES]
    y_test = test_df[TARGET]
    
    # 3. Train Model
    model = LinearRegression()
    model.fit(X_train, y_train)
    
    # 4. Evaluate (Validation)
    predictions = model.predict(X_test)
    mae = mean_absolute_error(y_test, predictions)
    rmse = np.sqrt(mean_squared_error(y_test, predictions))
    
    logger.info(f"✅ Trained {region_id} | MAE: {mae:.4f} | RMSE: {rmse:.4f}")
    
    # 5. Save Artifact
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"{region_id}_{timestamp}.pkl"
    filepath = os.path.join(ARTIFACTS_ROOT, filename)
    
    with open(filepath, 'wb') as f:
        pickle.dump(model, f)
        
    # 6. Return Metadata
    return {
        "region_id": region_id,
        "model_type": "LinearRegression",
        "artifact_path": filepath,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "metrics": {
            "mae": mae,
            "rmse": rmse,
            "train_size": len(train_df),
            "test_size": len(test_df)
        },
        "features": FEATURES,
        "status": "candidate" # Needs to pass gating to become active
    }

def save_evaluation_summary(results: List[Dict]):
    """Saves a summary of the training run for the Gating process."""
    summary_path = os.path.join(ARTIFACTS_ROOT, "training_summary.json")
    with open(summary_path, 'w') as f:
        json.dump(results, f, indent=2)

def run_training_pipeline():
    """
    Orchestrates the training for all regions.
    """
    try:
        # Setup output directory
        os.makedirs(ARTIFACTS_ROOT, exist_ok=True)
        
        # Load Data
        df = fetch_training_data()
        
        if df.empty:
            logger.warning("❌ Aborting training: No data available.")
            return

        # Group by Region (Split-Apply-Combine strategy)
        regions = df['region_id'].unique()
        logger.info(f"🔄 Starting training for {len(regions)} regions...")
        
        results = []
        for region_id in regions:
            region_data = df[df['region_id'] == region_id]
            metadata = train_region_model(region_id, region_data)
            if metadata:
                results.append(metadata)
        
        # Save Transient Summary (CRITICAL for Gating)
        if results:
            save_evaluation_summary(results)
        
        # Save Run Manifest
        manifest_path = os.path.join(ARTIFACTS_ROOT, "latest_run_manifest.json")
        with open(manifest_path, 'w') as f:
            json.dump(results, f, indent=2)
            
        logger.info(f"🎉 Training Complete. Run manifest saved to {manifest_path}")
        
    except Exception as e:
        logger.exception(f"❌ Training Pipeline Failed: {e}")
        # Note: Do NOT raise e here if you want the API to continue running other tasks,
        # but raising it helps the API wrapper know it failed.
        raise e
    
    # ✅ FIX: REMOVED THE 'finally: mongo_client.close()' BLOCK
    # The connection must remain open for the next API call.