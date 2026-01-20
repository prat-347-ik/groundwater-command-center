import os
import sys
import logging
import joblib
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split # 🆕
from sklearn.metrics import mean_absolute_error # 🆕
from src.config.mongo_client import mongo_client

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

ARTIFACTS_DIR = "models/v1"
FEATURES = [
    'effective_rainfall', 'log_extraction', 'feat_net_flux_1d_lag', 
    'feat_net_flux_window_sum', 'feat_water_trend_7d', 
    'feat_soil_permeability', 'feat_sin_day', 'feat_cos_day'
]
TARGET = 'target_water_level'
MAX_ALLOWED_MAE = 2.0 # 🆕 Threshold: Average error must be < 2 meters

def train_rf_for_region(region_id: str):
    logger.info(f"🌲 Starting Random Forest Training for {region_id}...")

    # 1. Fetch & Clean Data
    db = mongo_client.get_olap_db()
    cursor = db.region_feature_store.find({"region_id": region_id}).sort("date", 1)
    df = pd.DataFrame(list(cursor))

    if df.empty:
        logger.error(f"❌ No data found for region {region_id}")
        return
    
    df = df.dropna(subset=FEATURES + [TARGET])
    
    # 2. 🆕 Train/Test Split (Time Series Aware: No Shuffling)
    # We validate on the most recent 20% of data to mimic forecasting
    X = df[FEATURES]
    y = df[TARGET]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)

    logger.info(f"   Training on {len(X_train)} rows, Validating on {len(X_test)} rows...")

    # 3. Train
    model = RandomForestRegressor(n_estimators=100, max_depth=15, random_state=42, n_jobs=-1)
    model.fit(X_train, y_train)

    # 4. 🆕 Evaluation Gate
    predictions = model.predict(X_test)
    mae = mean_absolute_error(y_test, predictions)
    logger.info(f"   📊 Model Performance (MAE): {mae:.4f} meters")

    if mae > MAX_ALLOWED_MAE:
        logger.error(f"❌ TRAIN FAILED: MAE {mae:.4f} exceeds threshold {MAX_ALLOWED_MAE}. Model discarded.")
        # Optional: Send Alert to Admin here
        return

    # 5. Save Artifact (Only if good)
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    save_path = os.path.join(ARTIFACTS_DIR, f"rf_{region_id}.pkl")
    
    # Retrain on FULL dataset before saving for production usage? 
    # Usually yes, but for safety, we often save the validated model.
    # Let's refit on full data for maximum recency.
    model.fit(X, y) 
    
    joblib.dump(model, save_path, compress=3)
    logger.info(f"✅ Quality Assurance Passed. Model Saved: {save_path}")

if __name__ == "__main__":
    train_rf_for_region("65f4fc28-a5f9-47e0-b326-962b20bb35b1")