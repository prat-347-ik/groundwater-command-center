import pandas as pd
from typing import List, Dict, Any

def aggregate_daily_groundwater(cleaned_readings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Aggregates cleaned water readings into daily regional statistics.
    
    Logic:
    - Group by (region_id, date)
    - Calculate arithmetic mean, min, max for water_level
    - Count total readings
    - Count unique reporting wells
    
    Args:
        cleaned_readings: List of dicts with keys ['date', 'region_id', 'well_id', 'water_level']
        
    Returns:
        List of dicts matching the partial DailyRegionGroundwater schema.
    """
    if not cleaned_readings:
        return []

    df = pd.DataFrame(cleaned_readings)

    # Grouping
    # As_index=False ensures columns are preserved in the output DataFrame
    grouped = df.groupby(['region_id', 'date'], as_index=False).agg(
        avg_water_level=('water_level', 'mean'),
        min_water_level=('water_level', 'min'),
        max_water_level=('water_level', 'max'),
        reading_count=('water_level', 'count'),
        reporting_wells_count=('well_id', 'nunique')
    )

    # Rounding for precision consistency (optional but recommended for floats)
    grouped['avg_water_level'] = grouped['avg_water_level'].round(2)
    grouped['min_water_level'] = grouped['min_water_level'].round(2)
    grouped['max_water_level'] = grouped['max_water_level'].round(2)

    return grouped.to_dict('records')

def aggregate_daily_rainfall(cleaned_rainfall: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Aggregates cleaned rainfall data into daily regional totals.
    
    Logic:
    - Group by (region_id, date)
    - Sum total rainfall
    - Identify max single reading (storm detection)
    - Calculate intensity (total / count)
    - Determine primary source (mode) and source diversity
    
    Args:
        cleaned_rainfall: List of dicts with keys ['date', 'region_id', 'amount_mm', 'source']
        
    Returns:
        List of dicts matching the partial DailyRegionRainfall schema.
    """
    if not cleaned_rainfall:
        return []

    df = pd.DataFrame(cleaned_rainfall)

    # Custom aggregation for primary_source (Mode)
    def get_primary_source(series):
        mode = series.mode()
        return mode.iloc[0] if not mode.empty else "unknown"

    # Grouping
    grouped = df.groupby(['region_id', 'date'], as_index=False).agg(
        total_rainfall_mm=('amount_mm', 'sum'),
        max_single_reading_mm=('amount_mm', 'max'),
        reading_count=('amount_mm', 'count'),
        unique_source_count=('source', 'nunique'),
        primary_source=('source', get_primary_source),
        data_sources=('source', lambda x: list(set(x))) # Capture unique list for audit
    )

    # Derived Feature: Rainfall Intensity
    # Avoid division by zero (though reading_count >= 1 due to groupby)
    grouped['rainfall_intensity_mm'] = (
        grouped['total_rainfall_mm'] / grouped['reading_count']
    ).round(2)
    
    grouped['total_rainfall_mm'] = grouped['total_rainfall_mm'].round(2)
    grouped['max_single_reading_mm'] = grouped['max_single_reading_mm'].round(2)

    # Cleanup intermediate field if not needed in final schema (reading_count is used for intensity)
    # The schema 'DailyRegionRainfall' does not strictly require 'reading_count' 
    # but uses 'rainfall_intensity_mm'. We keep the dict clean.
    output_cols = [
        'region_id', 'date', 'total_rainfall_mm', 
        'max_single_reading_mm', 'rainfall_intensity_mm', 
        'unique_source_count', 'primary_source', 'data_sources'
    ]
    
    return grouped[output_cols].to_dict('records')