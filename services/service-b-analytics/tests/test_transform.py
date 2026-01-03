import unittest
from datetime import datetime, timezone
import pandas as pd
import numpy as np

# Import transformations
from src.transform.cleaning import clean_water_reading_row, normalize_utc_midnight
from src.transform.aggregations import aggregate_daily_groundwater, aggregate_daily_rainfall
from src.transform.feature_engineering import generate_region_features

class TestTransformations(unittest.TestCase):

    # --- Cleaning Tests ---

    def test_normalize_utc_midnight(self):
        # Case 1: String ISO
        res = normalize_utc_midnight("2024-01-01T15:30:00Z")
        self.assertEqual(res, datetime(2024, 1, 1, tzinfo=timezone.utc))
        
        # Case 2: Datetime object
        dt = datetime(2024, 1, 1, 12, 0, 0) # Naive
        res = normalize_utc_midnight(dt)
        self.assertEqual(res, datetime(2024, 1, 1, tzinfo=timezone.utc))
        
        # Case 3: None
        self.assertIsNone(normalize_utc_midnight(None))

    def test_clean_water_reading_row(self):
        # Valid Row
        raw = {
            "well_id": "w1", "region_id": "r1", 
            "timestamp": "2024-01-01T10:00:00Z", 
            "water_level": 15.5, "source": "sensor"
        }
        clean = clean_water_reading_row(raw)
        self.assertIsNotNone(clean)
        self.assertEqual(clean['water_level'], 15.5)
        
        # Invalid Row (Missing well_id)
        raw_bad = {"region_id": "r1", "water_level": 15.5}
        self.assertIsNone(clean_water_reading_row(raw_bad))

    # --- Aggregation Tests ---

    def test_aggregate_groundwater_determinism(self):
        """
        Test that aggregation computes stats correctly and is deterministic.
        """
        date_1 = datetime(2024, 1, 1, tzinfo=timezone.utc)
        
        # Input: 3 readings for Region A, 1 for Region B
        inputs = [
            {"date": date_1, "region_id": "A", "well_id": "w1", "water_level": 10.0},
            {"date": date_1, "region_id": "A", "well_id": "w1", "water_level": 20.0}, # Same well
            {"date": date_1, "region_id": "A", "well_id": "w2", "water_level": 30.0}, # Diff well
            {"date": date_1, "region_id": "B", "well_id": "w3", "water_level": 5.0},
        ]
        
        results = aggregate_daily_groundwater(inputs)
        
        # Convert to dict for easier lookup
        res_map = {r['region_id']: r for r in results}
        
        # Checks for Region A
        stats_a = res_map["A"]
        self.assertEqual(stats_a["avg_water_level"], 20.0) # (10+20+30)/3
        self.assertEqual(stats_a["min_water_level"], 10.0)
        self.assertEqual(stats_a["max_water_level"], 30.0)
        self.assertEqual(stats_a["reading_count"], 3)
        self.assertEqual(stats_a["reporting_wells_count"], 2) # w1 and w2 (w1 appears twice)

    def test_aggregate_rainfall_intensity(self):
        """
        Test rainfall intensity logic (Total / Count).
        """
        date_1 = datetime(2024, 1, 1, tzinfo=timezone.utc)
        inputs = [
            {"date": date_1, "region_id": "A", "amount_mm": 10.0, "source": "s1"},
            {"date": date_1, "region_id": "A", "amount_mm": 50.0, "source": "s2"},
        ]
        
        results = aggregate_daily_rainfall(inputs)
        stats = results[0]
        
        self.assertEqual(stats["total_rainfall_mm"], 60.0)
        self.assertEqual(stats["max_single_reading_mm"], 50.0)
        # Intensity = 60 / 2 = 30.0
        self.assertEqual(stats["rainfall_intensity_mm"], 30.0)

    # --- Feature Engineering Tests ---

    def test_feature_engineering_no_leakage(self):
        """
        Verify that feature engineering does not leak target data 
        and drops rows with insufficient history (NaNs).
        """
        # Create a 10-day history for one region
        dates = [
            datetime(2024, 1, i, tzinfo=timezone.utc) 
            for i in range(1, 11)
        ]
        
        gw_data = [{"date": d, "region_id": "A", "avg_water_level": 10.0 + i} for i, d in enumerate(dates)]
        rf_data = [{"date": d, "region_id": "A", "total_rainfall_mm": 5.0} for d in dates]
        meta = {"A": 50.0} # Critical level

        features = generate_region_features(gw_data, rf_data, meta)
        
        # We expect rows to be dropped due to 7-day lags.
        # Inputs: 10 days. 
        # T-7 requires 7 previous days.
        # Valid output starts from index 7 (Day 8).
        # Expected outputs: Day 8, 9, 10 (Total 3 rows)
        self.assertGreater(len(features), 0)
        self.assertLess(len(features), 10)
        
        # Check first valid row
        first_feat = features[0]
        
        # Ensure no NaNs exist in output
        self.assertFalse(np.isnan(first_feat["feat_water_trend_7d"]))
        
        # Check Seasonality
        self.assertIn("feat_sin_day", first_feat)
        self.assertIn("feat_cos_day", first_feat)

if __name__ == '__main__':
    unittest.main()