import pytest
import os
import json
import tempfile
import numpy as np
import pandas as pd
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app import app
from src.modelling.training import train_region_candidates, run_training_pipeline
from src.modelling.update_registry import promote_models
from src.modelling.registry import get_model, load_raw_registry

client = TestClient(app)

@pytest.fixture
def sample_feature_data():
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
        'region_id': 'region-gate-test',
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
    return df

def test_train_candidates_and_promotion_gate(sample_feature_data):
    with tempfile.TemporaryDirectory() as tmpdir:
        reg_path = os.path.join(tmpdir, "model_registry.json")
        eval_path = os.path.join(tmpdir, "evaluation_summary.json")

        # Start with empty registry
        with open(reg_path, 'w') as f:
            json.dump([], f)

        # Patch ARTIFACTS_ROOT / paths
        with patch("src.modelling.training.ARTIFACTS_ROOT", tmpdir), \
             patch("src.modelling.update_registry.ARTIFACTS_DIR", tmpdir), \
             patch("src.modelling.training.fetch_training_data", return_value=sample_feature_data):

            # 1. Run training pipeline
            candidates = run_training_pipeline()
            assert len(candidates) >= 2  # LR and RF
            assert os.path.exists(eval_path)

            # Check candidate schema
            for c in candidates:
                assert c["region_id"] == "region-gate-test"
                assert c["model_type"] in ("linear-regression", "random-forest")
                assert "metrics" in c
                assert "mae" in c["metrics"]
                assert "baseline_mae" in c["metrics"]
                assert os.path.exists(c["artifact_path"])

            # 2. Run promotion gate
            summary = promote_models(registry_path=reg_path, evaluation_path=eval_path)
            assert summary["promoted"] == 1
            assert summary["total_entries"] == 1

            # 3. Verify registry content and locked schema
            registry_entries = load_raw_registry(reg_path)
            assert len(registry_entries) == 1
            entry = registry_entries[0]
            assert entry["region_id"] == "region-gate-test"
            assert entry["status"] == "active"
            assert entry["promoted_at"] is not None
            assert entry["metrics"]["mae"] < entry["metrics"]["baseline_mae"]

            # 4. Verify registry can load promoted model
            model = get_model("region-gate-test", registry_path=reg_path)
            assert model.is_fitted
            assert model.region_id == "region-gate-test"

def test_jobs_api_endpoints_via_testclient():
    with patch("app.run_training_pipeline", return_value=[]), \
         patch("app.promote_models", return_value={"promoted": 1}), \
         patch("app.run_inference", return_value=[]):

        # 1. Test POST /jobs/train
        resp_train = client.post("/jobs/train", json={"model_type": "all"})
        assert resp_train.status_code == 200
        assert resp_train.json() == {"status": "queued", "job": "training", "model_type": "all"}

        # 2. Test POST /jobs/promote
        resp_promote = client.post("/jobs/promote")
        assert resp_promote.status_code == 200
        assert resp_promote.json() == {"status": "queued", "job": "promotion"}

        # 3. Test POST /jobs/forecast
        resp_forecast = client.post("/jobs/forecast")
        assert resp_forecast.status_code == 200
        assert resp_forecast.json() == {"status": "queued", "job": "forecast"}
