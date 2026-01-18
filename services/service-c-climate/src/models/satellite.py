from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class SatelliteRecord(BaseModel):
    """
    Stores Remote Sensing data for Ground Truth verification.
    """
    region_id: str = Field(..., description="Target Region ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # GRACE-FO (Gravity Recovery and Climate Experiment)
    # Measures Liquid Water Equivalent Thickness (LWE) in cm
    # Positive = Mass Surplus, Negative = Mass Deficit (Drought)
    grace_lwe_thickness_cm: float = Field(..., description="Liquid Water Equivalent (Gravity Anomaly)")
    
    # InSAR (Interferometric Synthetic Aperture Radar)
    # Measures ground deformation in mm
    # Negative = Subsidence (Ground sinking due to over-extraction)
    insar_subsidence_mm: float = Field(default=0.0, description="Ground vertical displacement")
    
    source: str = Field(default="nasa_earthdata", description="Source Satellite/Mission")

    class Config:
        json_schema_extra = {
            "example": {
                "region_id": "region-delta",
                "timestamp": "2026-06-15T00:00:00Z",
                "grace_lwe_thickness_cm": -2.5,
                "insar_subsidence_mm": -12.0
            }
        }