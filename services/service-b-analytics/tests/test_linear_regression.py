import pytest
import numpy as np
import pandas as pd
import tempfile
import os
from datetime import datetime, timedelta

from src.modelling.linear_regression.model import LinearRegressionModel, DEFAULT_FEATURES

@pytest.fixture
def sample_feature_data():
    """Generates synthetic historical feature dataframe for testing."""
    np.random.seed(42)
    n_days = 60
    base_date = datetime(2026, 1, 1)
    dates = [base_date + timedelta(days=i) for i in range(n_days)]
    
    # Synthetic physical process: water_level = 10.0 + 0.5 * rain - 0.8 * log_extraction + noise
    rain = np.random.uniform(0, 10, n_days)
    ext = np.random.uniform(100, 1000, n_days)
    log_ext = np.log1p(ext)
    net_flux_lag = rain - (log_ext * 0.1)
    water_level = 15.0 + 0.3 * rain - 0.5 * log_ext + np.random.normal(0, 0.1, n_days)

    df = pd.DataFrame({
        'date': dates,
        'region_id': 'test-region-001',
        'target_water_level': water_level,
        'effective_rainfall': rain,
        'log_extraction': log_ext,
        'feat_net_flux_1d_lag': net_flux_lag,
        'feat_net_flux_window_sum': pd.Series(net_flux_lag).rolling(7, min_periods=1).sum(),
        'feat_water_trend_7d': pd.Series(water_level).diff(7).fillna(0),
        'feat_soil_permeability': 0.15,
        'feat_sin_day': np.sin(2 * np.pi * np.arange(n_days) / 365.0),
        'feat_cos_day': np.cos(2 * np.pi * np.arange(n_days) / 365.0)
    })
    return df

def test_fit_and_metrics(sample_feature_data):
    model = LinearRegressionModel(region_id='test-region-001')
    meta = model.fit(sample_feature_data)
    
    assert model.is_fitted
    assert "mae" in model.metrics
    assert "rmse" in model.metrics
    assert model.metrics["mae"] >= 0.0
    assert model.metrics["rmse"] >= 0.0
    assert model.metrics["train_size"] > 0
    assert model.metrics["test_size"] > 0

def test_predict_horizon_batch(sample_feature_data):
    model = LinearRegressionModel(region_id='test-region-001')
    model.fit(sample_feature_data)
    
    forecasts = model.predict_horizon(sample_feature_data, horizon_days=7)
    assert len(forecasts) == 7
    for idx, f in enumerate(forecasts, 1):
        assert f["region_id"] == "test-region-001"
        assert f["horizon_step"] == idx
        assert isinstance(f["predicted_level"], float)
        assert not np.isnan(f["predicted_level"])
        assert f["scenario_extraction"] == 0.0

def test_predict_horizon_scenario(sample_feature_data):
    model = LinearRegressionModel(region_id='test-region-001')
    model.fit(sample_feature_data)
    
    schedule = [500.0, 600.0, 700.0, 800.0, 900.0, 1000.0, 1100.0]
    forecasts = model.predict_horizon(sample_feature_data, horizon_days=7, planned_extraction_schedule=schedule)
    
    assert len(forecasts) == 7
    for idx, f in enumerate(forecasts):
        assert f["scenario_extraction"] == schedule[idx]

def test_predict_scenario_hydrological_sanity(sample_feature_data):
    model = LinearRegressionModel(region_id='test-region-001')
    model.fit(sample_feature_data)
    
    # 1. Increased extraction should lower (or maintain) groundwater level
    res_ext = model.predict_scenario(sample_feature_data, rainfall_mod=1.0, extraction_mod=2.0)
    assert "baseline_level" in res_ext
    assert "simulated_level" in res_ext
    assert "delta" in res_ext
    assert abs(res_ext["simulated_level"] - res_ext["baseline_level"] - res_ext["delta"]) < 1e-4
    assert res_ext["delta"] <= 0.0, f"Expected extraction increase to decrease water level, got delta={res_ext['delta']}"

    # 2. Increased rainfall should increase (or maintain) groundwater level
    res_rain = model.predict_scenario(sample_feature_data, rainfall_mod=2.0, extraction_mod=1.0)
    assert res_rain["delta"] >= 0.0, f"Expected rain increase to increase water level, got delta={res_rain['delta']}"

def test_feature_importance_sanity(sample_feature_data):
    model = LinearRegressionModel(region_id='test-region-001')
    model.fit(sample_feature_data)
    
    importances = model.get_feature_importance()
    assert len(importances) == len(DEFAULT_FEATURES)
    assert all(item["importance"] >= 0 for item in importances)
    assert abs(sum(item["importance"] for item in importances) - 1.0) < 1e-3
    for i in range(len(importances) - 1):
        assert importances[i]["importance"] >= importances[i + 1]["importance"]

def test_save_and_load(sample_feature_data):
    model = LinearRegressionModel(region_id='test-region-001')
    model.fit(sample_feature_data)
    pred_orig = model.predict_horizon(sample_feature_data, horizon_days=3)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        save_path = os.path.join(tmpdir, "linreg_test.pkl")
        model.save(save_path)
        
        loaded_model = LinearRegressionModel(region_id='test-region-001')
        loaded_model.load(save_path)
        pred_loaded = loaded_model.predict_horizon(sample_feature_data, horizon_days=3)
        
        for o, l in zip(pred_orig, pred_loaded):
            assert o["predicted_level"] == l["predicted_level"]
