from fastapi import APIRouter, HTTPException
from typing import List
from datetime import datetime
from src.config.mongo_client import mongo_client
from pydantic import BaseModel

# 1. Import the inference engine we created
from src.inference.predictor import run_inference

router = APIRouter(prefix="/api/v1/forecasts", tags=["Forecasts"])

# --- Request/Response Schemas ---
class ForecastResponse(BaseModel):
    region_id: str
    forecast_date: datetime
    predicted_level: float
    model_version: str
    horizon_step: int

class GenerateRequest(BaseModel):
    region_id: str

# --- Routes ---

# 2. Add this POST endpoint BEFORE the GET endpoint
@router.post("/generate")
def generate_forecast(payload: GenerateRequest):
    """
    Manually triggers the Random Forest inference pipeline.
    """
    try:
        # Note: In a production system, we might filter by payload.region_id here.
        # For now, we run the optimized batch inference we wrote in predictor.py.
        run_inference()
        return {
            "status": "success", 
            "message": f"Forecast generated successfully for active regions (including {payload.region_id})."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
        return []
        
    return results