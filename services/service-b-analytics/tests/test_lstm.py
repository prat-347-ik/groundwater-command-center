import pytest
import numpy as np
import pandas as pd
import tempfile
import os
import torch
import torch.nn as nn
import torch.optim as optim
from datetime import datetime, timedelta
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error

from src.modelling.lstm.architecture import GroundwaterLSTM
from src.modelling.lstm.model import LSTMModel, DEFAULT_FEATURES

@pytest.fixture
def sample_feature_data():
    np.random.seed(42)
    torch.manual_seed(42)
    n_days = 150
    dates = pd.date_range('2025-01-01', periods=n_days, freq='D')
    
    rain = np.random.exponential(scale=2.0, size=n_days)
    ext = np.random.uniform(500, 2000, n_days)
    log_ext = np.log1p(ext)
    flux = rain - (log_ext * 0.1)

    # Autoregressive physical process: water depends on previous water + rain - extraction
    water = np.zeros(n_days)
    water[0] = 15.0
    for t in range(1, n_days):
        water[t] = 0.95 * water[t - 1] + 0.3 * rain[t] - 0.4 * log_ext[t] + np.random.normal(0, 0.02)

    df = pd.DataFrame({
        'date': dates,
        'region_id': 'region-001',
        'target_water_level': water,
        'effective_rainfall': rain,
        'log_extraction': log_ext,
        'feat_net_flux_1d_lag': pd.Series(flux).shift(1).fillna(0),
        'feat_soil_permeability': 0.15,
        'feat_sin_day': np.sin(2 * np.pi * np.arange(n_days) / 365.0),
        'feat_cos_day': np.cos(2 * np.pi * np.arange(n_days) / 365.0)
    })
    return df

def test_training_and_inference_parity_with_seeded_old_code(sample_feature_data):
    """
    Validates architectural and training-loop equivalence between the original
    lstm_train.py architecture and the new LSTMModel class under identical seed=42.
    """
    df = sample_feature_data.sort_values('date').reset_index(drop=True)
    
    # 1. Procedural reference logic with seed=42 and standard scaling
    torch.manual_seed(42)
    np.random.seed(42)

    sc_X = StandardScaler()
    sc_y = StandardScaler()
    scaled_X = sc_X.fit_transform(df[DEFAULT_FEATURES].values)
    scaled_y = sc_y.fit_transform(df[['target_water_level']].values)

    seq_len = 30
    xs, ys = [], []
    for i in range(len(df) - seq_len):
        xs.append(scaled_X[i : i + seq_len])
        ys.append(scaled_y[i + seq_len])
    X_all, y_all = np.array(xs), np.array(ys)

    split_idx = int(len(X_all) * 0.8)
    X_tr, X_te = torch.tensor(X_all[:split_idx], dtype=torch.float32), torch.tensor(X_all[split_idx:], dtype=torch.float32)
    y_tr, y_te = torch.tensor(y_all[:split_idx], dtype=torch.float32), torch.tensor(y_all[split_idx:], dtype=torch.float32)

    ref_net = GroundwaterLSTM(input_dim=len(DEFAULT_FEATURES), hidden_dim=50, output_dim=1, num_layers=2)
    criterion = nn.MSELoss()
    opt = optim.Adam(ref_net.parameters(), lr=0.01)

    ref_net.train()
    for _ in range(50):
        opt.zero_grad()
        out = ref_net(X_tr)
        loss = criterion(out, y_tr)
        loss.backward()
        opt.step()

    ref_net.eval()
    with torch.no_grad():
        ref_scaled_preds = ref_net(X_te).numpy()
    ref_preds = sc_y.inverse_transform(ref_scaled_preds).flatten()
    y_te_orig = sc_y.inverse_transform(y_te.numpy()).flatten()
    ref_mae = float(mean_absolute_error(y_te_orig, ref_preds))

    # 2. New LSTMModel class with seed=42 and 50 epochs
    new_model = LSTMModel(region_id='region-001', epochs=50, random_seed=42)
    meta = new_model.fit(df)

    with torch.no_grad():
        new_scaled_preds = new_model.model(X_te).numpy()
    new_preds = new_model.scaler_y.inverse_transform(new_scaled_preds).flatten()

    # 3. Assert exact mathematical equivalence:
    assert abs(meta["metrics"]["mae"] - ref_mae) < 1e-3
    assert np.allclose(ref_preds, new_preds, atol=1e-5)

def test_predict_horizon_batch(sample_feature_data):
    model = LSTMModel(region_id='region-001', epochs=10, random_seed=42)
    model.fit(sample_feature_data)
    
    forecasts = model.predict_horizon(sample_feature_data, horizon_days=7)
    assert len(forecasts) == 7
    for idx, f in enumerate(forecasts, 1):
        assert f["region_id"] == "region-001"
        assert f["horizon_step"] == idx
        assert isinstance(f["predicted_level"], float)
        assert not np.isnan(f["predicted_level"])
        assert f["scenario_extraction"] == 0.0

def test_predict_horizon_scenario(sample_feature_data):
    model = LSTMModel(region_id='region-001', epochs=10, random_seed=42)
    model.fit(sample_feature_data)
    
    schedule = [500.0, 600.0, 700.0, 800.0, 900.0, 1000.0, 1100.0]
    forecasts = model.predict_horizon(sample_feature_data, horizon_days=7, planned_extraction_schedule=schedule)
    assert len(forecasts) == 7
    for idx, f in enumerate(forecasts):
        assert f["scenario_extraction"] == schedule[idx]

def test_predict_scenario_sanity(sample_feature_data):
    model = LSTMModel(region_id='region-001', epochs=120, learning_rate=0.01, random_seed=42)
    model.fit(sample_feature_data)
    
    # 1. Increased extraction (+100%) must produce a strictly negative delta
    res_ext = model.predict_scenario(sample_feature_data, rainfall_mod=1.0, extraction_mod=2.0)
    assert "baseline_level" in res_ext
    assert "simulated_level" in res_ext
    assert "delta" in res_ext
    assert abs(res_ext["simulated_level"] - res_ext["baseline_level"] - res_ext["delta"]) < 1e-4
    assert res_ext["delta"] < -1e-3, f"Expected strictly negative delta for extraction increase, got {res_ext['delta']}"

    # 2. Increased rainfall (+100%) must produce a strictly positive delta
    res_rain = model.predict_scenario(sample_feature_data, rainfall_mod=2.0, extraction_mod=1.0)
    assert res_rain["delta"] > 1e-3, f"Expected strictly positive delta for rainfall increase, got {res_rain['delta']}"

def test_feature_importance(sample_feature_data):
    model = LSTMModel(region_id='region-001', epochs=10, random_seed=42)
    model.fit(sample_feature_data)
    
    importances = model.get_feature_importance()
    assert len(importances) == len(DEFAULT_FEATURES)
    assert all(item["importance"] >= 0 for item in importances)
    assert abs(sum(item["importance"] for item in importances) - 1.0) < 1e-3
    for i in range(len(importances) - 1):
        assert importances[i]["importance"] >= importances[i + 1]["importance"]

def test_save_and_load(sample_feature_data):
    model = LSTMModel(region_id='region-001', epochs=10, random_seed=42)
    model.fit(sample_feature_data)
    pred_orig = model.predict_horizon(sample_feature_data, horizon_days=3)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        save_path = os.path.join(tmpdir, "lstm_test.pth")
        model.save(save_path)
        
        loaded_model = LSTMModel(region_id='region-001')
        loaded_model.load(save_path)
        pred_loaded = loaded_model.predict_horizon(sample_feature_data, horizon_days=3)
        
        for o, l in zip(pred_orig, pred_loaded):
            assert abs(o["predicted_level"] - l["predicted_level"]) < 1e-4
