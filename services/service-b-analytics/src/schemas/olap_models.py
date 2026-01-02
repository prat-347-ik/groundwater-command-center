from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import List

class AnalyticsBaseModel(BaseModel):
    """Base configuration for immutable analytics models."""
    model_config = ConfigDict(frozen=True)  # Enforce immutability in code

class DailyRegionGroundwater(AnalyticsBaseModel):
    """
    Collection: daily_region_groundwater
    Purpose: Aggregated daily snapshot of groundwater levels per region.
    """
    date: datetime = Field(..., description="UTC Midnight reference date")
    region_id: str
    region_name: str
    state: str
    
    # Aggregations
    avg_water_level: float
    min_water_level: float
    max_water_level: float
    
    # Trust Metrics
    reading_count: int
    reporting_wells_count: int
    data_completeness_score: float = Field(
        ..., 
        description="Ratio of reporting wells to total active wells (0.0 to 1.0)"
    )
    
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DailyRegionRainfall(AnalyticsBaseModel):
    """
    Collection: daily_region_rainfall
    Purpose: Normalized daily rainfall totals from mixed sources.
    """
    date: datetime = Field(..., description="UTC Midnight reference date")
    region_id: str
    
    # Metrics
    total_rainfall_mm: float
    max_single_reading_mm: float = Field(..., description="Storm intensity signal")
    rainfall_intensity_mm: float = Field(..., description="Avg mm per event")
    
    # Provenance
    unique_source_count: int
    primary_source: str = Field(..., description="Dominant source type (sensor/manual)")
    data_sources: List[str] = Field(..., description="Audit trail of source types")
    
    created_at: datetime = Field(default_factory=datetime.utcnow)


class RegionFeatureStore(AnalyticsBaseModel):
    """
    Collection: region_feature_store
    Purpose: The 'Gold Layer' for ML training. Joins Groundwater + Rainfall + Engineered Features.
    """
    date: datetime = Field(..., description="UTC Midnight reference date")
    region_id: str
    
    # Target (Label)
    target_water_level: float
    
    # Lagged Rainfall Features
    feat_rainfall_1d_lag: float
    feat_rainfall_3d_sum: float
    feat_rainfall_7d_sum: float
    
    # Trend Features
    feat_water_trend_7d: float
    
    # Static Features (Denormalized)
    static_critical_level: float
    
    # Seasonality Features
    day_of_year: int = Field(..., ge=1, le=366)
    feat_sin_day: float = Field(..., description="Cyclical encoding: sin(2*pi*d/365)")
    feat_cos_day: float = Field(..., description="Cyclical encoding: cos(2*pi*d/365)")