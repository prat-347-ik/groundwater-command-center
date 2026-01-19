from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime
from src.config.mongo_client import mongo_client
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/forecasts", tags=["Forecasts"])

# Response Schema
class ForecastResponse(BaseModel):
    region_id: str
    forecast_date: datetime
    predicted_level: float
    model_version: str
    horizon_step: int

@router.get("/{region_id}", response_model=List[ForecastResponse])
def get_forecasts(region_id: str):
    """
    Get the latest 7-day forecast for a region.
    """
    db = mongo_client.get_olap_db()
    collection = db.daily_forecasts
    
    # Fetch futures
    cursor = collection.find(
        {"region_id": region_id}
    ).sort("forecast_date", 1).limit(30)
    
    results = []
    for doc in cursor:
        results.append(ForecastResponse(
            region_id=doc["region_id"],
            forecast_date=doc["forecast_date"],
            predicted_level=doc["predicted_level"],
            model_version=doc["model_version"],
            horizon_step=doc["horizon_step"]
        ))
    
    if not results:
        # Fallback: If no forecast exists, return empty list (Frontend handles this)
        return []
        
    return results