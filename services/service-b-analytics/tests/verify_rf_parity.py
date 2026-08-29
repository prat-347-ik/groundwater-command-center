import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import train_test_split
from src.modelling.random_forest.model import RandomForestModel, DEFAULT_FEATURES

np.random.seed(42)
n_rows = 100
dates = pd.date_range('2025-01-01', periods=n_rows, freq='D')

rain = np.random.uniform(0, 10, n_rows)
ext = np.random.uniform(100, 1000, n_rows)
log_ext = np.log1p(ext)
flux = rain - (log_ext * 0.1)
water = 15.0 + 0.3 * rain - 0.5 * log_ext + np.random.normal(0, 0.05, n_rows)

df = pd.DataFrame({
    'date': dates,
    'region_id': 'region-001',
    'target_water_level': water,
    'effective_rainfall': rain,
    'log_extraction': log_ext,
    'feat_net_flux_1d_lag': pd.Series(flux).shift(1),
    'feat_net_flux_window_sum': pd.Series(flux).shift(1).rolling(7, min_periods=1).sum(),
    'feat_water_trend_7d': pd.Series(water).diff(7),
    'feat_soil_permeability': 0.15,
    'feat_sin_day': np.sin(2 * np.pi * np.arange(n_rows) / 365.0),
    'feat_cos_day': np.cos(2 * np.pi * np.arange(n_rows) / 365.0)
})

# 1. EXACT rf_train.py logic (lines 30-68):
# 1.1 df = df.dropna(subset=FEATURES + [TARGET])
df_clean = df.dropna(subset=DEFAULT_FEATURES + ['target_water_level']).copy()

# 1.2 Train/Test Split (Time Series Aware: No Shuffling)
X = df_clean[DEFAULT_FEATURES]
y = df_clean['target_water_level']
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)

# 1.3 Train
val_rf = RandomForestRegressor(n_estimators=100, max_depth=15, random_state=42, n_jobs=-1)
val_rf.fit(X_train, y_train)
orig_val_preds = val_rf.predict(X_test)
orig_mae = mean_absolute_error(y_test, orig_val_preds)
orig_rmse = np.sqrt(mean_squared_error(y_test, orig_val_preds))

# 1.4 Refit full
full_rf = RandomForestRegressor(n_estimators=100, max_depth=15, random_state=42, n_jobs=-1)
full_rf.fit(X, y)
orig_full_preds = full_rf.predict(X_test)
orig_importances = full_rf.feature_importances_

# 2. New RandomForestModel class:
model = RandomForestModel(region_id='region-001')
meta = model.fit(df)
new_full_preds = model.model.predict(X_test)
new_importances = model.model.feature_importances_

print("=== NUMERICAL COMPARISON: rf_train.py vs RandomForestModel ===\n")
header = f"{'Metric / Parameter':<26} | {'Original (rf_train.py)':<22} | {'New RandomForestModel':<23} | {'Difference'}"
print(header)
print("-" * len(header))
print(f"{'Train Sample Size':<26} | {len(X_train):<22} | {meta['metrics']['train_size']:^23} | 0")
print(f"{'Test Sample Size':<26} | {len(X_test):<22} | {meta['metrics']['test_size']:^23} | 0")
print(f"{'Evaluation MAE':<26} | {orig_mae:<22.8f} | {meta['metrics']['mae']:^23.8f} | {abs(orig_mae - meta['metrics']['mae']):.2e}")
print(f"{'Evaluation RMSE':<26} | {orig_rmse:<22.8f} | {meta['metrics']['rmse']:^23.8f} | {abs(orig_rmse - meta['metrics']['rmse']):.2e}")

print("\nFeature Importances Comparison:")
for f, imp_orig, imp_new in zip(DEFAULT_FEATURES, orig_importances, new_importances):
    print(f"  {f:<24} | {imp_orig:<22.8f} | {imp_new:^23.8f} | {abs(imp_orig - imp_new):.2e}")

print("\nFirst 5 Test Sample Predictions:")
for i in range(5):
    print(f"  Test sample #{i+1:<13} | {orig_full_preds[i]:<22.8f} | {new_full_preds[i]:^23.8f} | {abs(orig_full_preds[i] - new_full_preds[i]):.2e}")
