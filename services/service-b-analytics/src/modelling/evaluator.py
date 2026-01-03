import os
import json
import pickle
import logging
import math
import pandas as pd
from typing import Dict, List, Any
from sklearn.metrics import mean_absolute_error, mean_squared_error

from src.config.mongo_client import mongo_client

# Configure Logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Configuration ---
ARTIFACTS_DIR = "models/v1"
REGISTRY_PATH = os.path.join(ARTIFACTS_DIR, "model_registry.json")
REPORT_PATH = os.path.join(ARTIFACTS_DIR, "evaluation_summary.json")

# Must match training config exactly to replicate the split
FEATURES = [
    'feat_rainfall_1d_lag', 
    'feat_rainfall_7d_sum', 
    'feat_water_trend_7d', 
    'feat_sin_day', 
    'feat_cos_day'
]
TARGET = 'target_water_level'
TRAIN_SPLIT_RATIO = 0.80

def load_data_for_region(region_id: str) -> pd.DataFrame:
    """
    Fetches data for a specific region from OLAP.
    """
    db = mongo_client.get_olap_db()
    
    # Projection to minimize bandwidth
    projection = {f: 1 for f in FEATURES}
    projection[TARGET] = 1
    projection['date'] = 1
    projection['_id'] = 0
    
    cursor = db.region_feature_store.find({"region_id": region_id}, projection)
    df = pd.DataFrame(list(cursor))
    
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
        
    return df

def calculate_metrics(y_true, y_pred) -> Dict[str, float]:
    """
    Computes standard regression metrics.
    """
    mae = mean_absolute_error(y_true, y_pred)
    mse = mean_squared_error(y_true, y_pred)
    rmse = math.sqrt(mse)
    
    return {
        "mae": round(mae, 4),
        "rmse": round(rmse, 4)
    }

def evaluate_region(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates a single region's model on its Test Set.
    
    Steps:
    1. Load Data
    2. Replicate Time-Split (Critical!)
    3. Load Model Artifact
    4. Predict & Score
    """
    region_id = metadata['region_id']
    artifact_path = metadata['artifact_path']
    
    # 1. Load Data
    df = load_data_for_region(region_id)
    if df.empty:
        logger.warning(f"⚠️ Region {region_id}: No data found for evaluation.")
        return None

    # 2. Replicate Time-Based Split
    # We must sort and split exactly as the trainer did to isolate the Validation Set.
    df = df.sort_values('date').reset_index(drop=True)
    split_idx = int(len(df) * TRAIN_SPLIT_RATIO)
    
    # We ONLY evaluate on the Test set (Future)
    test_df = df.iloc[split_idx:].copy()
    
    if test_df.empty:
        logger.warning(f"⚠️ Region {region_id}: Test set is empty.")
        return None
    
    X_test = test_df[FEATURES]
    y_test = test_df[TARGET]

    # 3. Load Model
    if not os.path.exists(artifact_path):
        logger.error(f"❌ Artifact not found: {artifact_path}")
        return None
        
    with open(artifact_path, 'rb') as f:
        model = pickle.load(f)

    # 4. Generate Predictions
    y_pred = model.predict(X_test)
    
    # 5. Calculate Metrics (Model)
    model_metrics = calculate_metrics(y_test, y_pred)
    
    # 6. Calculate Metrics (Baseline / Persistence)
    # Predict t = t-1
    persistence_pred = test_df[TARGET].shift(1)
    # Drop first row to align (shift creates a NaN)
    valid_idx = persistence_pred.dropna().index
    
    if len(valid_idx) == 0:
         return None

    baseline_metrics = calculate_metrics(
        test_df.loc[valid_idx, TARGET], 
        persistence_pred.loc[valid_idx]
    )
    
    # 7. Verdict
    # Does the model beat the naive baseline?
    is_passing = model_metrics['mae'] < baseline_metrics['mae']
    
    return {
        "region_id": region_id,
        "test_rows": len(test_df),
        "model_mae": model_metrics['mae'],
        "model_rmse": model_metrics['rmse'],
        "baseline_mae": baseline_metrics['mae'],
        "improvement_pct": round((1 - model_metrics['mae'] / baseline_metrics['mae']) * 100, 2),
        "status": "PASS" if is_passing else "FAIL"
    }

def run_evaluation():
    """
    Main entry point for batch evaluation.
    """
    if not os.path.exists(REGISTRY_PATH):
        logger.error("❌ Model registry not found. Run training first.")
        return

    # Load Registry
    with open(REGISTRY_PATH, 'r') as f:
        registry = json.load(f)
        
    logger.info(f"📉 Starting Evaluation for {len(registry)} models...")
    
    results = []
    passed_count = 0
    
    print(f"\n{'REGION ID':<20} | {'MAE':<8} | {'BASE MAE':<8} | {'RMSE':<8} | {'STATUS'}")
    print("-" * 65)
    
    for meta in registry:
        res = evaluate_region(meta)
        if res:
            results.append(res)
            if res['status'] == "PASS":
                passed_count += 1
            
            # Human-Readable Output
            print(f"{res['region_id']:<20} | {res['model_mae']:<8} | {res['baseline_mae']:<8} | {res['model_rmse']:<8} | {res['status']}")

    # Summary
    print("-" * 65)
    logger.info(f"✅ Evaluation Complete. Passed: {passed_count}/{len(results)}")
    
    # Save Report
    with open(REPORT_PATH, 'w') as f:
        json.dump({
            "generated_at": str(pd.Timestamp.now()),
            "total_regions": len(results),
            "passed_regions": passed_count,
            "details": results
        }, f, indent=2)
        
    logger.info(f"📄 Detailed report saved to {REPORT_PATH}")
    mongo_client.close()

if __name__ == "__main__":
    run_evaluation()