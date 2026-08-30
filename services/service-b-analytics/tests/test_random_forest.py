import pytest
import numpy as np
import pandas as pd
import tempfile
import os
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

from src.modelling.random_forest.model import RandomForestModel, DEFAULT_FEATURES

@pytest.fixture
def sample_feature_data():
    np.random.seed(42)
    n_days = 100
    base_date = datetime(2026, 1, 1)
    dates = [base_date + timedelta(days=i) for i in range(n_days)]
    
    rain = np.random.uniform(0, 10, n_days)
    ext = np.random.uniform(100, 1000, n_days)
    log_ext = np.log1p(ext)
    net_flux_lag = rain - (log_ext * 0.1)
    water_level = 15.0 + 0.3 * rain - 0.5 * log_ext + np.random.normal(0, 0.05, n_days)

    df = pd.DataFrame({
        'date': dates,
        'region_id': 'region-001',
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

def test_numeric_parity_against_original_rf_train(sample_feature_data):
    """
    Direct before/after numerical parity test against rf_train.py lines 38-70.
    """
    df = sample_feature_data.sort_values('date').reset_index(drop=True)
    
    # 1. Original rf_train.py logic:
    X = df[DEFAULT_FEATURES]
    y = df['target_water_level']
    split_idx = int(len(df) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

    val_rf = RandomForestRegressor(n_estimators=100, max_depth=15, random_state=42, n_jobs=-1)
    val_rf.fit(X_train, y_train)
    orig_val_preds = val_rf.predict(X_test)
    orig_mae = mean_absolute_error(y_test, orig_val_preds)
    orig_rmse = np.sqrt(mean_squared_error(y_test, orig_val_preds))

    # Production full refit
    full_rf = RandomForestRegressor(n_estimators=100, max_depth=15, random_state=42, n_jobs=-1)
    full_rf.fit(X, y)
    orig_full_preds = full_rf.predict(X_test)
    orig_importances = full_rf.feature_importances_

    # 2. New RandomForestModel class:
    model = RandomForestModel(region_id='region-001')
    meta = model.fit(df)
    new_full_preds = model.model.predict(X_test)
    new_importances = model.model.feature_importances_

    # 3. Assert exact mathematical equivalence:
    assert abs(meta["metrics"]["mae"] - orig_mae) < 1e-3
    assert abs(meta["metrics"]["rmse"] - orig_rmse) < 1e-3
    assert np.allclose(orig_full_preds, new_full_preds, atol=1e-7)
    assert np.allclose(orig_importances, new_importances, atol=1e-7)

def test_predict_horizon_batch(sample_feature_data):
    model = RandomForestModel(region_id='region-001')
    model.fit(sample_feature_data)
    
    forecasts = model.predict_horizon(sample_feature_data, horizon_days=7)
    assert len(forecasts) == 7
    for idx, f in enumerate(forecasts, 1):
        assert f["region_id"] == "region-001"
        assert f["horizon_step"] == idx
        assert isinstance(f["predicted_level"], float)
        assert f["scenario_extraction"] == 0.0

def test_predict_horizon_scenario(sample_feature_data):
    model = RandomForestModel(region_id='region-001')
    model.fit(sample_feature_data)
    
    schedule = [500.0, 600.0, 700.0, 800.0, 900.0, 1000.0, 1100.0]
    forecasts = model.predict_horizon(sample_feature_data, horizon_days=7, planned_extraction_schedule=schedule)
    assert len(forecasts) == 7
    for idx, f in enumerate(forecasts):
        assert f["scenario_extraction"] == schedule[idx]

def test_predict_scenario_sanity(sample_feature_data):
    model = RandomForestModel(region_id='region-001')
    model.fit(sample_feature_data)
    
    res = model.predict_scenario(sample_feature_data, rainfall_mod=1.0, extraction_mod=2.0)
    assert "baseline_level" in res
    assert "simulated_level" in res
    assert "delta" in res
    assert abs(res["simulated_level"] - res["baseline_level"] - res["delta"]) < 1e-4

def test_feature_importance(sample_feature_data):
    model = RandomForestModel(region_id='region-001')
    model.fit(sample_feature_data)
    
    importances = model.get_feature_importance()
    assert len(importances) == len(DEFAULT_FEATURES)
    assert all(item["importance"] >= 0 for item in importances)
    for i in range(len(importances) - 1):
        assert importances[i]["importance"] >= importances[i + 1]["importance"]

def test_save_and_load(sample_feature_data):
    model = RandomForestModel(region_id='region-001')
    model.fit(sample_feature_data)
    pred_orig = model.predict_horizon(sample_feature_data, horizon_days=3)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        save_path = os.path.join(tmpdir, "rf_test.pkl")
        model.save(save_path)
        
        loaded_model = RandomForestModel(region_id='region-001')
        loaded_model.load(save_path)
        pred_loaded = loaded_model.predict_horizon(sample_feature_data, horizon_days=3)
        
        for o, l in zip(pred_orig, pred_loaded):
            assert o["predicted_level"] == l["predicted_level"]
