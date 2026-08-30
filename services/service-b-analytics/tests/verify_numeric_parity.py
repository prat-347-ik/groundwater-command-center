import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error

from src.modelling.linear_regression.model import LinearRegressionModel

# 1. Create a fixed, deterministic historical dataset
np.random.seed(42)
n_rows = 100
dates = pd.date_range('2025-01-01', periods=n_rows, freq='D')
features = [
    'effective_rainfall', 'log_extraction', 'feat_net_flux_1d_lag',
    'feat_net_flux_window_sum', 'feat_water_trend_7d',
    'feat_soil_permeability', 'feat_sin_day', 'feat_cos_day'
]

X_mat = np.random.uniform(0, 10, size=(n_rows, len(features)))
true_weights = np.array([0.4, -0.7, 0.2, 0.1, 0.5, 0.3, 0.15, -0.15])
y_vec = 12.0 + X_mat @ true_weights + np.random.normal(0, 0.05, size=n_rows)

df = pd.DataFrame(X_mat, columns=features)
df['date'] = dates
df['region_id'] = 'region-001'
df['target_water_level'] = y_vec

# 2. RUN EXACT 'MAIN' ORIGINAL CODE LOGIC
# From main: training.py lines 60-98:
df_region = df.sort_values('date').reset_index(drop=True)
split_idx = int(len(df_region) * 0.80)
train_df = df_region.iloc[:split_idx]
test_df = df_region.iloc[split_idx:]
X_train_orig = train_df[features]
y_train_orig = train_df['target_water_level']
X_test_orig = test_df[features]
y_test_orig = test_df['target_water_level']

orig_model = LinearRegression()
orig_model.fit(X_train_orig, y_train_orig)
orig_preds = orig_model.predict(X_test_orig)
orig_mae = mean_absolute_error(y_test_orig, orig_preds)
orig_rmse = np.sqrt(mean_squared_error(y_test_orig, orig_preds))

# 3. RUN NEW LinearRegressionModel CLASS
new_model = LinearRegressionModel(region_id='region-001', features=features)
new_meta = new_model.fit(df, train_split_ratio=0.80, min_history_days=30)
new_preds = new_model.model.predict(X_test_orig)

# 4. PRINT SIDE-BY-SIDE NUMERICAL COMPARISON
print("=== NUMERICAL COMPARISON: MAIN CODE vs NEW LinearRegressionModel ===\n")
header = f"{'Metric / Parameter':<26} | {'Original (main)':<21} | {'New LinearRegressionModel':<25} | {'Difference'}"
print(header)
print("-" * len(header))
print(f"{'Train Sample Size':<26} | {len(train_df):<21} | {new_meta['metrics']['train_size']:^25} | 0")
print(f"{'Test Sample Size':<26} | {len(test_df):<21} | {new_meta['metrics']['test_size']:^25} | 0")
print(f"{'Intercept':<26} | {orig_model.intercept_:<21.8f} | {new_model.model.intercept_:^25.8f} | {abs(orig_model.intercept_ - new_model.model.intercept_):.2e}")
print(f"{'Evaluation MAE':<26} | {orig_mae:<21.8f} | {new_meta['metrics']['mae']:^25.8f} | {abs(orig_mae - new_meta['metrics']['mae']):.2e}")
print(f"{'Evaluation RMSE':<26} | {orig_rmse:<21.8f} | {new_meta['metrics']['rmse']:^25.8f} | {abs(orig_rmse - new_meta['metrics']['rmse']):.2e}")

print("\nCoefficients Comparison:")
for f, c_orig, c_new in zip(features, orig_model.coef_, new_model.model.coef_):
    print(f"  {f:<24} | {c_orig:<21.8f} | {c_new:^25.8f} | {abs(c_orig - c_new):.2e}")

print("\nFirst 5 Test Predictions:")
for i in range(5):
    print(f"  Test sample #{i+1:<13} | {orig_preds[i]:<21.8f} | {new_preds[i]:^25.8f} | {abs(orig_preds[i] - new_preds[i]):.2e}")
