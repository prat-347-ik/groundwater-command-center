from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class WeatherRecord(BaseModel):
    """
    Represents a snapshot of weather conditions for a region.
    """
    region_id: str = Field(..., description="Target Region ID")
    temperature_c: float = Field(..., description="Average Temperature in Celsius")
    humidity_percent: float = Field(..., ge=0, le=100, description="Relative Humidity (0-100%)")
    solar_radiation: Optional[float] = Field(default=0.0, description="Solar Radiation in W/m^2")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source: str = Field(default="api_fetch", description="Source: 'api_fetch', 'csv_ingest'")

    class Config:
        json_schema_extra = {
            "example": {
                "region_id": "region-001",
                "temperature_c": 32.5,
                "humidity_percent": 45.0,
                "solar_radiation": 850.2,
                "timestamp": "2026-05-20T14:00:00Z"
            }
        }