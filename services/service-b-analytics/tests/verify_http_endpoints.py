import json
import os
import sys
import tempfile
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath("."))
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from unittest.mock import patch
from fastapi.testclient import TestClient

from main import app
from src.modelling.linear_regression.model import LinearRegressionModel
from src.modelling.random_forest.model import RandomForestModel
from src.modelling.lstm.model import LSTMModel
from src.modelling.registry import get_model, load_active_models

client = TestClient(app)

def run_e2e_verification():
    print("=" * 70)
    print("🚀 FASTAPI TESTCLIENT END-TO-END HTTP VERIFICATION")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create dataset
        np.random.seed(42)
        n = 60
        dates = pd.date_range('2025-01-01', periods=n, freq='D')
        rain = np.random.exponential(scale=2.0, size=n)
        ext = np.random.uniform(500, 1000, size=n)
        log_ext = np.log1p(ext)
        flux = rain - (log_ext * 0.1)
        water = 25.0 + 0.3 * rain - 0.4 * log_ext + np.random.normal(0, 0.05, n)

        df = pd.DataFrame({
            'date': dates,
            'region_id': '65f4fc28-a5f9-47e0-b326-962b20bb35b1',
            'target_water_level': water,
            'effective_rainfall': rain,
            'log_extraction': log_ext,
            'feat_net_flux_1d_lag': pd.Series(flux).shift(1).fillna(0),
            'feat_net_flux_window_sum': pd.Series(flux).shift(1).rolling(7, min_periods=1).sum(),
            'feat_water_trend_7d': pd.Series(water).diff(7).bfill().fillna(0),
            'feat_soil_permeability': 0.15,
            'feat_sin_day': np.sin(2 * np.pi * np.arange(n) / 365.0),
            'feat_cos_day': np.cos(2 * np.pi * np.arange(n) / 365.0)
        })

        # Train & save RF
        rf = RandomForestModel(region_id='65f4fc28-a5f9-47e0-b326-962b20bb35b1', random_state=42)
        rf.fit(df)
        rf_path = os.path.join(tmpdir, "rf_active.pkl")
        rf.save(rf_path)

        # Build clean canonical registry
        registry_data = [
            {
                "region_id": "65f4fc28-a5f9-47e0-b326-962b20bb35b1",
                "model_type": "random-forest",
                "version": "1.0-rf",
                "status": "active",
                "artifact_path": rf_path,
                "registered_at": "2026-01-19T16:15:20.870691+00:00"
            },
            {
                "region_id": "missing-artifact-region",
                "model_type": "random-forest",
                "status": "active",
                "artifact_path": os.path.join(tmpdir, "does_not_exist.pkl")
            }
        ]
        reg_path = os.path.join(tmpdir, "model_registry.json")
        with open(reg_path, 'w') as f:
            json.dump(registry_data, f, indent=2)

        with patch("src.inference.predictor.get_recent_history", side_effect=lambda rids: pd.concat([df.assign(region_id=rid) for rid in rids], ignore_index=True)), \
             patch("src.inference.predictor.get_model", side_effect=lambda rid: get_model(rid, registry_path=reg_path)), \
             patch("src.inference.predictor.load_active_models", side_effect=lambda: load_active_models(registry_path=reg_path)):

            # TEST 1: POST /api/v1/forecasts/simulate (Success - 200 OK)
            print("\n--- [HTTP TEST 1] POST /api/v1/forecasts/simulate ---")
            payload_sim = {
                "region_id": "65f4fc28-a5f9-47e0-b326-962b20bb35b1",
                "rainfall_modifier": 0.8,
                "extraction_modifier": 1.2
            }
            print(f"Request Payload:\n{json.dumps(payload_sim, indent=2)}")
            resp_sim = client.post("/api/v1/forecasts/simulate", json=payload_sim)
            print(f"HTTP Status Code: {resp_sim.status_code}")
            print(f"Response Body:\n{json.dumps(resp_sim.json(), indent=2)}")
            assert resp_sim.status_code == 200
            assert "baseline_level" in resp_sim.json()
            assert "simulated_level" in resp_sim.json()
            assert "delta" in resp_sim.json()

            # TEST 2: POST /api/v1/forecasts/generate (What-If Scenario Mode - 200 OK)
            print("\n--- [HTTP TEST 2] POST /api/v1/forecasts/generate (Scenario Mode) ---")
            payload_gen = {
                "region_id": "65f4fc28-a5f9-47e0-b326-962b20bb35b1",
                "planned_extraction": [600.0, 650.0, 700.0, 750.0, 800.0, 850.0, 900.0]
            }
            print(f"Request Payload:\n{json.dumps(payload_gen, indent=2)}")
            resp_gen = client.post("/api/v1/forecasts/generate", json=payload_gen)
            print(f"HTTP Status Code: {resp_gen.status_code}")
            print(f"Response Body (sample 2 of 7 steps):\n{json.dumps(resp_gen.json()['data'][:2], indent=2)}")
            assert resp_gen.status_code == 200
            assert resp_gen.json()["status"] == "success"
            assert len(resp_gen.json()["data"]) == 7

            # TEST 3: GET /api/v1/forecasts/importance/{region_id} (Success - 200 OK)
            print("\n--- [HTTP TEST 3] GET /api/v1/forecasts/importance/65f4fc28-a5f9-47e0-b326-962b20bb35b1 ---")
            resp_imp = client.get("/api/v1/forecasts/importance/65f4fc28-a5f9-47e0-b326-962b20bb35b1")
            print(f"HTTP Status Code: {resp_imp.status_code}")
            print(f"Response Body (all {len(resp_imp.json()['importance'])} features):\n{json.dumps(resp_imp.json()['importance'], indent=2)}")
            assert resp_imp.status_code == 200
            assert len(resp_imp.json()["importance"]) == 8

            # TEST 4: POST /api/v1/forecasts/simulate (Missing Region - 404 Not Found)
            print("\n--- [HTTP TEST 4] POST /api/v1/forecasts/simulate (Unknown Region 404) ---")
            resp_404_unreg = client.post("/api/v1/forecasts/simulate", json={
                "region_id": "nonexistent-region-id",
                "rainfall_modifier": 1.0,
                "extraction_modifier": 1.0
            })
            print(f"HTTP Status Code: {resp_404_unreg.status_code}")
            print(f"Response Body:\n{json.dumps(resp_404_unreg.json(), indent=2)}")
            assert resp_404_unreg.status_code == 404

            # TEST 5: POST /api/v1/forecasts/simulate (Missing Artifact on Disk - 404 Not Found)
            print("\n--- [HTTP TEST 5] POST /api/v1/forecasts/simulate (ModelArtifactNotFoundError 404) ---")
            resp_404_missing = client.post("/api/v1/forecasts/simulate", json={
                "region_id": "missing-artifact-region",
                "rainfall_modifier": 1.0,
                "extraction_modifier": 1.0
            })
            print(f"HTTP Status Code: {resp_404_missing.status_code}")
            print(f"Response Body:\n{json.dumps(resp_404_missing.json(), indent=2)}")
            assert resp_404_missing.status_code == 404

    print("\n" + "=" * 70)
    print("✅ ALL FASTAPI ENDPOINTS VERIFIED END-TO-END VIA HTTP TESTCLIENT")
    print("=" * 70)

if __name__ == "__main__":
    run_e2e_verification()
