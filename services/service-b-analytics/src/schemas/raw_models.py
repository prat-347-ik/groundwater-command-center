from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Literal

class RegionRaw(BaseModel):
    """Reflects Service A 'Region' collection."""
    region_id: str
    name: str
    state: str
    critical_level: float
    is_active: bool
    created_at: datetime

class WellRaw(BaseModel):
    """Reflects Service A 'Well' collection."""
    well_id: str
    region_id: str
    depth: float
    status: Literal['active', 'inactive', 'maintenance']

class WaterReadingRaw(BaseModel):
    """Reflects Service A 'WaterReading' collection."""
    well_id: str
    region_id: str
    timestamp: datetime
    water_level: float
    source: str

class RainfallRaw(BaseModel):
    """Reflects Service A 'Rainfall' collection."""
    region_id: str
    timestamp: datetime
    amount_mm: float
    source: str