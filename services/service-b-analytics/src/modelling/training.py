import os
import pickle
import json
import logging
from datetime import datetime
from typing import Dict, Any, List

import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error

from src.config.mongo_client import mongo_client

# Configure Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configuration ---
ARTIFACTS_DIR = "models/v1"
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
    
    # 6. Sanity Check: Baseline Comparison (Persistence)
    # Predict t = t-1
    persistence_pred = test_df[TARGET].shift(1)
    # Drop first row of test set for fair comparison (due to shift NaNs)
    valid_indices = persistence_pred.dropna().index
    persistence_mae = mean_absolute_error(test_df.loc[valid_indices, TARGET], persistence_pred.loc[valid_indices])
    
    logger.info(f"✅ Region {region_id}: MAE={mae:.4f} (Baseline={persistence_mae:.4f})")

    # 7. Save Artifacts
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    model_filename = f"{region_id}_{timestamp}.pkl"
    save_path = os.path.join(ARTIFACTS_DIR, model_filename)
    
    with open(save_path, 'wb') as f:
        pickle.dump(model, f)
        
    # 8. Return Metadata
    return {
        "region_id": region_id,
        "model_type": "LinearRegression",
        "features": FEATURES,
        "training_rows": len(train_df),
        "test_rows": len(test_df),
        "mae": round(mae, 4),
        "baseline_mae": round(persistence_mae, 4),
        "artifact_path": save_path,
        "trained_at": timestamp,
        "coefficients": {feat: round(coef, 4) for feat, coef in zip(FEATURES, model.coef_)},
        "intercept": round(model.intercept_, 4)
    }

def run_training_pipeline():
    """
    Orchestrates the training for all regions.
    """
    try:
        # Setup output directory
        os.makedirs(ARTIFACTS_DIR, exist_ok=True)
        
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
        
        # Save Registry (Model Catalog)
        registry_path = os.path.join(ARTIFACTS_DIR, "model_registry.json")
        with open(registry_path, 'w') as f:
            json.dump(results, f, indent=2)
            
        logger.info(f"🎉 Training Complete. Models saved to {ARTIFACTS_DIR}")
        
    except Exception as e:
        logger.exception(f"❌ Training Pipeline Failed: {e}")
        raise e
    finally:
        mongo_client.close()

if __name__ == "__main__":
    run_training_pipeline()