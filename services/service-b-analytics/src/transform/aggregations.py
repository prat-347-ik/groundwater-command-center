import pandas as pd
from typing import List, Dict, Any

# --- [NEW] Streaming Aggregator Class ---
class GroundwaterStreamAggregator:
    """
    Stateful aggregator to process water readings row-by-row.
    Eliminates the need to hold all raw rows in memory.
    """
    def __init__(self):
        # Key: (region_id, date)
        # Value: {sum, count, min, max, wells (set)}
        self.groups = {}

    def consume(self, row: Dict[str, Any]):
        """Ingest a single cleaned row and update running stats."""
        key = (row['region_id'], row['date'])
        val = row['water_level']
        well_id = row['well_id']

        if key not in self.groups:
            self.groups[key] = {
                'sum': 0.0,
                'count': 0,
                'min': val,
                'max': val,
                'wells': {well_id} # Set for unique counting
            }
        else:
            stats = self.groups[key]
            stats['sum'] += val
            stats['count'] += 1
            if val < stats['min']: stats['min'] = val
            if val > stats['max']: stats['max'] = val
            stats['wells'].add(well_id)

    def get_results(self) -> List[Dict[str, Any]]:
        """Finalize aggregations and return the schema-compliant list."""
        results = []
        for (region_id, date), stats in self.groups.items():
            results.append({
                'region_id': region_id,
                'date': date,
                'avg_water_level': round(stats['sum'] / stats['count'], 2),
                'min_water_level': round(stats['min'], 2),
                'max_water_level': round(stats['max'], 2),
                'reading_count': stats['count'],
                'reporting_wells_count': len(stats['wells'])
            })
        return results

# --- Existing Function (Kept for Rainfall or small batches) ---
def aggregate_daily_rainfall(cleaned_rainfall: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Aggregates cleaned rainfall data into daily regional totals.
    """
    if not cleaned_rainfall:
        return []

    df = pd.DataFrame(cleaned_rainfall)

    # Custom aggregation for primary_source (Mode)
    def get_primary_source(series):
        mode = series.mode()
        return mode.iloc[0] if not mode.empty else "unknown"

    grouped = df.groupby(['region_id', 'date'], as_index=False).agg(
        total_rainfall_mm=('amount_mm', 'sum'),
        max_single_reading_mm=('amount_mm', 'max'),
        reading_count=('amount_mm', 'count'),
        unique_source_count=('source', 'nunique'),
        primary_source=('source', get_primary_source),
        data_sources=('source', lambda x: list(set(x)))
    )

    grouped['rainfall_intensity_mm'] = (
        grouped['total_rainfall_mm'] / grouped['reading_count']
    ).round(2)
    
    grouped['total_rainfall_mm'] = grouped['total_rainfall_mm'].round(2)
    grouped['max_single_reading_mm'] = grouped['max_single_reading_mm'].round(2)

    output_cols = [
        'region_id', 'date', 'total_rainfall_mm', 
        'max_single_reading_mm', 'rainfall_intensity_mm', 
        'unique_source_count', 'primary_source', 'data_sources'
    ]
    
    return grouped[output_cols].to_dict('records')