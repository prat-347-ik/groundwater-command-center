import pandas as pd
import numpy as np
from typing import List, Dict, Any

def calculate_evapotranspiration(temp_c, humidity):
    """
    Simplified Hargreaves/PM estimation.
    Higher temp & lower humidity = Higher loss.
    """
    if pd.isna(temp_c) or pd.isna(humidity):
        return 0.0
    
    # 100% Humidity = 0 Deficit (No evaporation)
    # 0% Humidity = 1.0 Deficit (Max evaporation)
    saturation_deficit = (100 - humidity) / 100.0
    
    # 0.05 is a calibration constant for daily mm loss per degree C
    return max(0, 0.05 * temp_c * saturation_deficit)

def generate_region_features(
    groundwater_data: List[Dict[str, Any]], 
    rainfall_data: List[Dict[str, Any]],
    weather_data: List[Dict[str, Any]],     # 🆕
    extraction_data: List[Dict[str, Any]],  # 🆕
    region_metadata: Dict[str, Any]         # 🆕 Needs full metadata now
) -> List[Dict[str, Any]]:
    """
    Combines daily aggregations into a Physics-Informed ML feature set.
    """
    if not groundwater_data:
        return []

    # 1. Convert to DataFrames & Standardize Dates
    # 🛑 CRITICAL FIX: .dt.tz_localize(None) ensures all dates are Naive (No UTC mismatch)
    
    # Groundwater
    gw_df = pd.DataFrame(groundwater_data)
    gw_df['date'] = pd.to_datetime(gw_df['date']).dt.tz_localize(None).dt.normalize()
    
    # Rainfall
    rf_df = pd.DataFrame(rainfall_data) if rainfall_data else pd.DataFrame(columns=['timestamp', 'amount_mm'])
    if not rf_df.empty:
        col = 'timestamp' if 'timestamp' in rf_df.columns else 'date'
        rf_df['date'] = pd.to_datetime(rf_df[col]).dt.tz_localize(None).dt.normalize()
        
        # Aggregate hourly rain to daily
        if 'amount_mm' in rf_df.columns:
            rf_df = rf_df.groupby('date')['amount_mm'].sum().reset_index()
        elif 'rainfall_mm' in rf_df.columns:
             rf_df = rf_df.groupby('date')['rainfall_mm'].sum().reset_index()
             rf_df.rename(columns={'rainfall_mm': 'amount_mm'}, inplace=True)

    # Weather (Temp/Humidity)
    wx_df = pd.DataFrame(weather_data) if weather_data else pd.DataFrame(columns=['timestamp', 'temperature_c', 'humidity_percent'])
    if not wx_df.empty:
        wx_df['date'] = pd.to_datetime(wx_df['timestamp']).dt.tz_localize(None).dt.normalize()
        # Average daily weather
        wx_df = wx_df.groupby('date')[['temperature_c', 'humidity_percent']].mean().reset_index()

    # Extraction (Pumping)
    ex_df = pd.DataFrame(extraction_data) if extraction_data else pd.DataFrame(columns=['timestamp', 'volume_liters'])
    if not ex_df.empty:
        ex_df['date'] = pd.to_datetime(ex_df['timestamp']).dt.tz_localize(None).dt.normalize()
        # Sum daily extraction
        ex_df = ex_df.groupby('date')['volume_liters'].sum().reset_index()

    # 2. Merge All Inputs (Master Table)
    # Start with Target (Water Level) - We need the date backbone
    df = gw_df[['date', 'region_id', 'avg_water_level']].sort_values('date')
    
    # Left join features (fill missing days with 0 for rain/extraction)
    df = pd.merge(df, rf_df, on='date', how='left').fillna({'amount_mm': 0})
    df = pd.merge(df, wx_df, on='date', how='left') 
    df = pd.merge(df, ex_df, on='date', how='left').fillna({'volume_liters': 0})
    
    # Forward fill weather data (temp doesn't change wildly overnight if missing)
    if 'temperature_c' in df.columns:
        df[['temperature_c', 'humidity_percent']] = df[['temperature_c', 'humidity_percent']].ffill().bfill()
    else:
        df['temperature_c'] = 25.0 
        df['humidity_percent'] = 50.0

    # 3. Apply Physics Calculations
    
    # A. Evapotranspiration (ET)
    df['evap_loss_mm'] = df.apply(
        lambda row: calculate_evapotranspiration(row.get('temperature_c'), row.get('humidity_percent')), axis=1
    )
    
    # B. Effective Rainfall
    df['effective_rainfall'] = (df['amount_mm'] - df['evap_loss_mm']).clip(lower=0)
    
    # C. Normalize Extraction (Log)
    df['log_extraction'] = np.log1p(df['volume_liters'])
    
    # D. Net Flux Proxy
    df['net_flux_proxy'] = df['effective_rainfall'] - (df['log_extraction'] * 0.1)

    # 4. Feature Engineering (Lags & Rolling)
    
    soil_type = region_metadata.get('soil_type', 'sandy_loam')
    permeability = region_metadata.get('permeability_index', 0.5)
    
    if soil_type == 'clay':
        window = 30 
    elif soil_type == 'rock':
        window = 60
    else:
        window = 7  
        
    df = df.sort_values('date')
    
    df['target_water_level'] = df['avg_water_level']
    
    # History Features (Shift 1 to avoid leakage)
    df['feat_net_flux_1d_lag'] = df['net_flux_proxy'].shift(1)
    df['feat_net_flux_window_sum'] = df['net_flux_proxy'].shift(1).rolling(window=window, min_periods=1).sum()
    df['feat_water_trend_7d'] = df['avg_water_level'].shift(1) - df['avg_water_level'].shift(8)
    
    df['feat_soil_permeability'] = permeability
    
    day_of_year = df['date'].dt.dayofyear
    df['feat_sin_day'] = np.sin(2 * np.pi * day_of_year / 365.0)
    df['feat_cos_day'] = np.cos(2 * np.pi * day_of_year / 365.0)

    # 5. Clean & Format
    df = df.dropna()
    
    # 🔴 UPDATED: Include raw physics inputs needed for LSTM
    output_cols = [
        'date', 'region_id', 'target_water_level',
        'effective_rainfall', 'log_extraction',  # <--- NEWLY ADDED
        'feat_net_flux_1d_lag', 'feat_net_flux_window_sum',
        'feat_water_trend_7d', 'feat_soil_permeability',
        'feat_sin_day', 'feat_cos_day'
    ]
    
    float_cols = [c for c in output_cols if c not in ['date', 'region_id']]
    df[float_cols] = df[float_cols].round(4)
    
    return df[output_cols].to_dict('records')