import pandas as pd
import numpy as np
from typing import List, Dict, Any

def generate_region_features(
    groundwater_data: List[Dict[str, Any]], 
    rainfall_data: List[Dict[str, Any]],
    static_critical_levels: Dict[str, float]
) -> List[Dict[str, Any]]:
    """
    Combines daily aggregations into a ML-ready feature set.
    
    Operations:
    1. Merge Groundwater (Target) and Rainfall (Features).
    2. Sort by Date.
    3. Generate Rolling/Lagged Features (Strictly Validated to avoid Leakage).
    4. Generate Seasonality Features.
    5. Drop rows with NaN (insufficient history).
    
    Args:
        groundwater_data: List of DailyRegionGroundwater dicts.
        rainfall_data: List of DailyRegionRainfall dicts.
        static_critical_levels: Dict mapping region_id -> critical_level (from Metadata).
        
    Returns:
        List of RegionFeatureStore dicts ready for insertion.
    """
    if not groundwater_data or not rainfall_data:
        return []

    # 1. Convert to DataFrames
    gw_df = pd.DataFrame(groundwater_data)
    rf_df = pd.DataFrame(rainfall_data)
    
    # Ensure Dates are Datetime objects
    gw_df['date'] = pd.to_datetime(gw_df['date'])
    rf_df['date'] = pd.to_datetime(rf_df['date'])

    # 2. Merge DataFrames on (region_id, date)
    # Using Inner Join: We need both Water (Target) and Rain (Features) to train
    merged_df = pd.merge(
        gw_df[['date', 'region_id', 'avg_water_level']],
        rf_df[['date', 'region_id', 'total_rainfall_mm']],
        on=['date', 'region_id'],
        how='inner'
    )

    # 3. Apply Feature Engineering per Region
    # We use groupby().apply() to ensure lags don't cross region boundaries
    def apply_transformations(group):
        # Sort by date asc to ensure correct rolling/shifting
        group = group.sort_values('date')
        
        # --- Target ---
        # The value we want to predict for this Date
        group['target_water_level'] = group['avg_water_level']

        # --- Rainfall Lags (No Target Leakage) ---
        # feat_rainfall_1d_lag: Rain yesterday (T-1)
        group['feat_rainfall_1d_lag'] = group['total_rainfall_mm'].shift(1)
        
        # feat_rainfall_3d_sum: Sum of rain from T-3 to T-1
        # Shift(1) first ensures we only look at yesterday backwards
        group['feat_rainfall_3d_sum'] = group['total_rainfall_mm'].shift(1).rolling(window=3).sum()
        
        # feat_rainfall_7d_sum: Sum of rain from T-7 to T-1
        group['feat_rainfall_7d_sum'] = group['total_rainfall_mm'].shift(1).rolling(window=7).sum()

        # --- Water Level Trend (No Target Leakage) ---
        # feat_water_trend_7d: Difference between T-1 and T-8
        # This represents the trend leading UP TO the prediction day, without seeing the prediction day.
        # Safe for ML.
        prev_day = group['avg_water_level'].shift(1)
        prev_week = group['avg_water_level'].shift(8)
        group['feat_water_trend_7d'] = prev_day - prev_week

        # --- Seasonality ---
        # Extract Day of Year (1-366)
        day_of_year = group['date'].dt.dayofyear
        group['day_of_year'] = day_of_year
        
        # Cyclical Encoding (Sin/Cos)
        # 365.25 accounts for leap years roughly, but 365.0 is standard for simple robust features
        group['feat_sin_day'] = np.sin(2 * np.pi * day_of_year / 365.0)
        group['feat_cos_day'] = np.cos(2 * np.pi * day_of_year / 365.0)

        return group

    # Apply logic group-wise
    features_df = merged_df.groupby('region_id', include_groups=False).apply(apply_transformations)
    features_df = features_df.reset_index()
    
    # 4. Enforce Metadata Features (Denormalization)
    # Map critical levels. If missing, use a safe default or drop (here we drop to be safe)
    # In production, you might load this from a DB lookup.
    features_df['static_critical_level'] = features_df['region_id'].map(static_critical_levels)
    
    # 5. Clean Up
    # Drop rows with NaN (caused by shifting/rolling at the start of history)
    # Drop rows where critical_level mapping failed
    features_df = features_df.dropna()

    # 6. Formatting Output
    output_cols = [
        'date', 'region_id', 'target_water_level',
        'feat_rainfall_1d_lag', 'feat_rainfall_3d_sum', 'feat_rainfall_7d_sum',
        'feat_water_trend_7d', 'static_critical_level',
        'day_of_year', 'feat_sin_day', 'feat_cos_day'
    ]
    
    # Ensure types match Pydantic models (float rounding)
    float_cols = [
        'target_water_level', 'feat_rainfall_1d_lag', 'feat_rainfall_3d_sum', 
        'feat_rainfall_7d_sum', 'feat_water_trend_7d', 'feat_sin_day', 'feat_cos_day'
    ]
    features_df[float_cols] = features_df[float_cols].round(4)
    
    return features_df[output_cols].to_dict('records')