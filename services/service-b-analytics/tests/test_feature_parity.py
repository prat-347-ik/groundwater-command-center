import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error
from src.modelling.linear_regression.model import LinearRegressionModel

def run_parity():
    np.random.seed(42)
    n_rows = 100
    dates = pd.date_range('2025-01-01', periods=n_rows, freq='D')

    # --- 1. MAIN's REAL 5-FEATURE DATASET ---
    rain = np.random.uniform(0, 10, n_rows)
    water = 12.0 + 0.3 * pd.Series(rain).shift(1).fillna(0) + np.random.normal(0, 0.05, n_rows)
    df_main = pd.DataFrame({
        'date': dates,
        'region_id': 'region-001',
        'target_water_level': water,
        'feat_rainfall_1d_lag': pd.Series(rain).shift(1).fillna(0),
        'feat_rainfall_7d_sum': pd.Series(rain).shift(1).rolling(7, min_periods=1).sum(),
        'feat_water_trend_7d': pd.Series(water).diff(7).fillna(0),
        'feat_sin_day': np.sin(2 * np.pi * np.arange(n_rows) / 365.0),
        'feat_cos_day': np.cos(2 * np.pi * np.arange(n_rows) / 365.0)
    })

    df_main = df_main.dropna().reset_index(drop=True)
    features_5 = ['feat_rainfall_1d_lag', 'feat_rainfall_7d_sum', 'feat_water_trend_7d', 'feat_sin_day', 'feat_cos_day']
    train_5 = df_main.iloc[:int(len(df_main)*0.8)]
    test_5 = df_main.iloc[int(len(df_main)*0.8):]
    ols_5 = LinearRegression().fit(train_5[features_5], train_5['target_water_level'])
    preds_5 = ols_5.predict(test_5[features_5])
    mae_5 = mean_absolute_error(test_5['target_water_level'], preds_5)
    rmse_5 = np.sqrt(mean_squared_error(test_5['target_water_level'], preds_5))

    model_5 = LinearRegressionModel(region_id='region-001', features=features_5)
    meta_5 = model_5.fit(df_main)

    print("=== 1. MAIN'S ORIGINAL 5-FEATURE COMPARISON ===")
    print(f"Original main OLS MAE:   {mae_5:.6f}")
    print(f"LinearRegressionModel:   {meta_5['metrics']['mae']:.6f}")
    print(f"Original main OLS RMSE:  {rmse_5:.6f}")
    print(f"LinearRegressionModel:   {meta_5['metrics']['rmse']:.6f}")
    print(f"Coefficients identical:  {np.allclose(ols_5.coef_, model_5.model.coef_)}")
    print(f"Intercept identical:     {np.isclose(ols_5.intercept_, model_5.model.intercept_)}")

    # --- 2. UPGRADED 8-FEATURE PHYSICS PIPELINE ---
    eff_rain = np.random.uniform(0, 10, n_rows)
    ext = np.random.uniform(100, 1000, n_rows)
    log_ext = np.log1p(ext)
    flux = eff_rain - (log_ext * 0.1)
    water_phys = 15.0 + 0.3 * eff_rain - 0.5 * log_ext + np.random.normal(0, 0.05, n_rows)

    df_8 = pd.DataFrame({
        'date': dates,
        'region_id': 'region-001',
        'target_water_level': water_phys,
        'effective_rainfall': eff_rain,
        'log_extraction': log_ext,
        'feat_net_flux_1d_lag': pd.Series(flux).shift(1).fillna(0),
        'feat_net_flux_window_sum': pd.Series(flux).shift(1).rolling(7, min_periods=1).sum(),
        'feat_water_trend_7d': pd.Series(water_phys).diff(7).fillna(0),
        'feat_soil_permeability': 0.15,
        'feat_sin_day': np.sin(2 * np.pi * np.arange(n_rows) / 365.0),
        'feat_cos_day': np.cos(2 * np.pi * np.arange(n_rows) / 365.0)
    })

    model_8 = LinearRegressionModel(region_id='region-001')
    meta_8 = model_8.fit(df_8)
    print("\n=== 2. UPGRADED 8-FEATURE PHYSICS COMPARISON ===")
    print(f"LinearRegressionModel (8-feat) MAE:  {meta_8['metrics']['mae']:.4f}")
    print(f"LinearRegressionModel (8-feat) RMSE: {meta_8['metrics']['rmse']:.4f}")
    print(f"Active Features: {model_8.features}")

if __name__ == "__main__":
    run_parity()
