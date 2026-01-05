from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List

class RainfallRecord(BaseModel):
    """
    Represents a single rainfall entry.
    """
    region_id: str = Field(..., description="The ID of the region (e.g., 'region-001')")
    amount_mm: float = Field(..., ge=0, description="Rainfall amount in millimeters")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Time of observation")
    source: str = Field(default="manual", description="Source of data (sensor, manual, csv)")

    class Config:
        json_schema_extra = {
            "example": {
                "region_id": "region-001",
                "amount_mm": 15.4,
                "timestamp": "2025-01-01T12:00:00Z",
                "source": "manual_entry"
            }
        }

class RainfallResponse(BaseModel):
    """
    Standard response format for lists of rainfall data.
    """
    count: int
    data: List[dict]