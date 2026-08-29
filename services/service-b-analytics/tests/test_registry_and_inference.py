import pytest
import os
import json
import tempfile
import numpy as np
import pandas as pd
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

from src.modelling.linear_regression.model import LinearRegressionModel
from src.modelling.random_forest.model import RandomForestModel
from src.modelling.lstm.model import LSTMModel
from src.modelling.registry import (
    get_model,
    load_active_models,
    ModelNotFoundError,
    ModelArtifactNotFoundError,
)
from src.inference.predictor import (
    get_feature_importance,
    predict_scenario,
    run_inference,
)
from src.api.forecasts import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)

@pytest.fixture
def test_environment():
    """Sets up a temporary directory with trained LR, RF, and LSTM artifacts and a model_registry.json."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create synthetic training dataset
        np.random.seed(42)
        n_days = 60
        dates = pd.date_range('2025-01-01', periods=n_days, freq='D')
        rain = np.random.exponential(scale=2.0, size=n_days)
        ext = np.random.uniform(500, 1000, size=n_days)
        log_ext = np.log1p(ext)
        flux = rain - (log_ext * 0.1)
        water = 15.0 + 0.3 * rain - 0.4 * log_ext + np.random.normal(0, 0.05, n_days)

        df = pd.DataFrame({
            'date': dates,
            'region_id': 'reg-lr',
            'target_water_level': water,
            'effective_rainfall': rain,
            'log_extraction': log_ext,
            'feat_net_flux_1d_lag': pd.Series(flux).shift(1).fillna(0),
            'feat_net_flux_window_sum': pd.Series(flux).shift(1).rolling(7, min_periods=1).sum(),
            'feat_water_trend_7d': pd.Series(water).diff(7).bfill().fillna(0),
            'feat_soil_permeability': 0.15,
            'feat_sin_day': np.sin(2 * np.pi * np.arange(n_days) / 365.0),
            'feat_cos_day': np.cos(2 * np.pi * np.arange(n_days) / 365.0)
        })

        # Train LR
        lr = LinearRegressionModel(region_id='reg-lr')
        lr.fit(df)
        lr_path = os.path.join(tmpdir, "lr_model.pkl")
        lr.save(lr_path)

        # Train RF
        rf = RandomForestModel(region_id='reg-rf', random_state=42)
        rf.fit(df)
        rf_path = os.path.join(tmpdir, "rf_model.pkl")
        rf.save(rf_path)

        # Train LSTM
        lstm = LSTMModel(region_id='reg-lstm', epochs=10, random_seed=42)
        lstm.fit(df)
        lstm_path = os.path.join(tmpdir, "lstm_model.pth")
        lstm.save(lstm_path)

        # Build Registry
        registry_data = [
            {
                "region_id": "reg-lr",
                "model_type": "linear-regression",
                "status": "active",
                "artifact_path": lr_path
            },
            {
                "region_id": "reg-rf",
                "model_type": "random-forest-sklearn",
                "status": "active",
                "artifact_path": rf_path
            },
            {
                "region_id": "reg-lstm",
                "model_type": "lstm-pytorch",
                "status": "active",
                "artifact_path": lstm_path
            },
            {
                "region_id": "reg-missing-file",
                "model_type": "random-forest",
                "status": "active",
                "artifact_path": os.path.join(tmpdir, "nonexistent.pkl")
            }
        ]
        registry_path = os.path.join(tmpdir, "model_registry.json")
        with open(registry_path, 'w') as f:
            json.dump(registry_data, f, indent=2)

        yield {
            "tmpdir": tmpdir,
            "registry_path": registry_path,
            "df": df,
            "lr_path": lr_path,
            "rf_path": rf_path,
            "lstm_path": lstm_path
        }

def test_registry_factory_polymorphic_loading(test_environment):
    reg_path = test_environment["registry_path"]
    
    # 1. Load LR
    model_lr = get_model("reg-lr", registry_path=reg_path)
    assert isinstance(model_lr, LinearRegressionModel)
    assert model_lr.region_id == "reg-lr"
    assert model_lr.is_fitted

    # 2. Load RF
    model_rf = get_model("reg-rf", registry_path=reg_path)
    assert isinstance(model_rf, RandomForestModel)
    assert model_rf.region_id == "reg-rf"
    assert model_rf.is_fitted

    # 3. Load LSTM
    model_lstm = get_model("reg-lstm", registry_path=reg_path)
    assert isinstance(model_lstm, LSTMModel)
    assert model_lstm.region_id == "reg-lstm"
    assert model_lstm.is_fitted

def test_registry_error_handling(test_environment):
    reg_path = test_environment["registry_path"]

    # Unknown region raises ModelNotFoundError
    with pytest.raises(ModelNotFoundError):
        get_model("unknown-region-999", registry_path=reg_path)

    # Missing artifact file raises ModelArtifactNotFoundError (subclass of FileNotFoundError)
    with pytest.raises(ModelArtifactNotFoundError):
        get_model("reg-missing-file", registry_path=reg_path)

def test_load_all_active_models(test_environment):
    reg_path = test_environment["registry_path"]
    models = load_active_models(registry_path=reg_path)
    assert "reg-lr" in models
    assert "reg-rf" in models
    assert "reg-lstm" in models
    assert "reg-missing-file" not in models  # Gracefully skipped with warning

@patch("src.inference.predictor.get_recent_history")
def test_predictor_polymorphic_execution(mock_history, test_environment):
    df = test_environment["df"]
    mock_history.side_effect = lambda rids: pd.concat([df.assign(region_id=rid) for rid in rids], ignore_index=True)
    reg_path = test_environment["registry_path"]

    with patch("src.inference.predictor.get_model", side_effect=lambda rid: get_model(rid, registry_path=reg_path)), \
         patch("src.inference.predictor.load_active_models", side_effect=lambda: load_active_models(registry_path=reg_path)):
        
        # Test feature importance for all three
        for rid in ["reg-lr", "reg-rf", "reg-lstm"]:
            imps = get_feature_importance(rid)
            assert len(imps) > 0
            assert "feature" in imps[0] and "importance" in imps[0]

        # Test predict_scenario for all three
        for rid in ["reg-lr", "reg-rf", "reg-lstm"]:
            res = predict_scenario(rid, rainfall_mod=0.8, extraction_mod=1.2)
            assert res["region_id"] == rid
            assert "baseline_level" in res
            assert "simulated_level" in res
            assert "delta" in res

        # Test scenario horizon inference
        schedule = [500.0, 600.0, 700.0, 800.0, 900.0, 1000.0, 1100.0]
        results = run_inference(region_id_filter="reg-rf", planned_extraction_schedule=schedule)
        assert len(results) == 7
        assert results[0]["scenario_extraction"] == 500.0

@patch("src.inference.predictor.get_recent_history")
def test_forecasts_api_endpoints_and_404_handling(mock_history, test_environment):
    df = test_environment["df"]
    mock_history.side_effect = lambda rids: pd.concat([df.assign(region_id=rid) for rid in rids], ignore_index=True)
    reg_path = test_environment["registry_path"]

    with patch("src.inference.predictor.get_model", side_effect=lambda rid: get_model(rid, registry_path=reg_path)), \
         patch("src.inference.predictor.load_active_models", side_effect=lambda: load_active_models(registry_path=reg_path)):

        # 1. Successful simulation (HTTP 200)
        resp_sim = client.post("/api/v1/forecasts/simulate", json={
            "region_id": "reg-rf",
            "rainfall_modifier": 0.8,
            "extraction_modifier": 1.2
        })
        assert resp_sim.status_code == 200
        data = resp_sim.json()
        assert data["region_id"] == "reg-rf"
        assert "delta" in data

        # 2. Successful scenario forecast (HTTP 200)
        resp_gen = client.post("/api/v1/forecasts/generate", json={
            "region_id": "reg-lstm",
            "planned_extraction": [500.0, 600.0, 700.0, 800.0, 900.0, 1000.0, 1100.0]
        })
        assert resp_gen.status_code == 200
        assert resp_gen.json()["status"] == "success"
        assert len(resp_gen.json()["data"]) == 7

        # 3. Successful importance query (HTTP 200)
        resp_imp = client.get("/api/v1/forecasts/importance/reg-lr")
        assert resp_imp.status_code == 200
        assert "importance" in resp_imp.json()

        # 4. Unknown region returns HTTP 404 (ModelNotFoundError)
        resp_unknown = client.post("/api/v1/forecasts/simulate", json={
            "region_id": "unknown-region-123",
            "rainfall_modifier": 1.0,
            "extraction_modifier": 1.0
        })
        assert resp_unknown.status_code == 404
        assert "No registered model found" in resp_unknown.json()["detail"]

        # 5. Missing artifact file on disk returns HTTP 404 (ModelArtifactNotFoundError)
        resp_missing = client.post("/api/v1/forecasts/simulate", json={
            "region_id": "reg-missing-file",
            "rainfall_modifier": 1.0,
            "extraction_modifier": 1.0
        })
        assert resp_missing.status_code == 404
        assert "Model artifact for region 'reg-missing-file' not found" in resp_missing.json()["detail"]
