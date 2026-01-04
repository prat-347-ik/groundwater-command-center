import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.config.mongo_client import mongo_client

def seed_database():
    print("🌱 Seeding 'region_feature_store' with dummy data...")
    db = mongo_client.get_olap_db()
    
    # 1. Clear existing trash
    db.region_feature_store.delete_many({})
    
    # 2. Generate 100 days of dummy data for 'region-001'
    # This ensures we pass the MIN_HISTORY_DAYS = 90 check in training.py
    data = []
    base_date = datetime.now(datetime.timezone.utc) - timedelta(days=120)
    
    for i in range(120):
        row_date = base_date + timedelta(days=i)
        data.append({
            "region_id": "region-001",
            "date": row_date,
            "feat_rainfall_1d_lag": np.random.uniform(0, 50),
            "feat_rainfall_7d_sum": np.random.uniform(0, 200),
            "feat_water_trend_7d": np.random.uniform(-1, 1),
            "feat_sin_day": np.sin(2 * np.pi * row_date.timetuple().tm_yday / 365.0),
            "feat_cos_day": np.cos(2 * np.pi * row_date.timetuple().tm_yday / 365.0),
            "target_water_level": 15.0 + np.random.normal(0, 0.5)
        })

    # 3. Insert
    db.region_feature_store.insert_many(data)
    print(f"✅ Inserted {len(data)} records for region-001.")
    print("🚀 You can now run the training pipeline.")

if __name__ == "__main__":
    seed_database()