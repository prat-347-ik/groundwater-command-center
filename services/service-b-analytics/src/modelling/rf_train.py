import os
import sys
import logging
import joblib
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from src.config.mongo_client import mongo_client

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
ARTIFACTS_DIR = "models/v1"
FEATURES = [
    'effective_rainfall', 
    'log_extraction', 
    'feat_net_flux_1d_lag', 
    'feat_net_flux_window_sum', # RF can leverage this accumulated history better than raw LSTM lags
    'feat_water_trend_7d', 
    'feat_soil_permeability', 
    'feat_sin_day', 
    'feat_cos_day'
]
TARGET = 'target_water_level'

def train_rf_for_region(region_id: str):
    logger.info(f"🌲 Starting Random Forest Training for {region_id}...")

    # 1. Fetch Data
    db = mongo_client.get_olap_db()
    cursor = db.region_feature_store.find({"region_id": region_id}).sort("date", 1)
    df = pd.DataFrame(list(cursor))

    if df.empty:
        logger.error(f"❌ No data found for region {region_id}")
        return

    # 2. Preprocessing
    # Drop rows where targets or lags might be NaN (common in first few rows of time series)
    df = df.dropna(subset=FEATURES + [TARGET])
    
    X = df[FEATURES]
    y = df[TARGET]

    logger.info(f"   Training on {len(df)} records...")

    # 3. Initialize Random Forest
    # n_estimators=100 is standard. max_depth=15 prevents overfitting and keeps model size small.
    # n_jobs=-1 uses all CPU cores for faster training.
    model = RandomForestRegressor(
        n_estimators=100,
        max_depth=15, 
        random_state=42,
        n_jobs=-1
    )

    # 4. Train
    model.fit(X, y)

    # 5. Save Artifact
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    save_path = os.path.join(ARTIFACTS_DIR, f"rf_{region_id}.pkl")
    
    # Compress=3 reduces file size significantly
    joblib.dump(model, save_path, compress=3)
    
    logger.info(f"✅ Random Forest Model Saved: {save_path}")
    logger.info(f"   Feature Importances: {dict(zip(FEATURES, model.feature_importances_.round(4)))}")

if __name__ == "__main__":
    # Replace with your actual Region ID
    train_rf_for_region("65f4fc28-a5f9-47e0-b326-962b20bb35b1")