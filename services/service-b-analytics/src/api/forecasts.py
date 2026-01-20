from fastapi import APIRouter, HTTPException
from typing import List, Optional, Any, Dict
from datetime import datetime
from src.config.mongo_client import mongo_client
from pydantic import BaseModel

# Import the updated inference engine
from src.inference.predictor import run_inference

router = APIRouter(prefix="/api/v1/forecasts", tags=["Forecasts"])

# --- Request/Response Schemas ---
class ForecastResponse(BaseModel):
    region_id: str
    forecast_date: datetime
    predicted_level: float
    model_version: str
    horizon_step: int
    scenario_extraction: Optional[float] = 0.0

class GenerateRequest(BaseModel):
    region_id: str
    # 🆕 CHANGED: Now accepts a list of daily extraction values for the 7-day horizon
    planned_extraction: Optional[List[float]] = None 

# --- Routes ---

@router.post("/generate")
def generate_forecast(payload: GenerateRequest):
    """
    Triggers the Random Forest inference.
    If 'planned_extraction' is provided (as a list), runs a simulation and returns the data (What-If Mode).
    If not provided, runs standard batch inference and saves to DB (Production Mode).
    """
    try:
        if payload.planned_extraction is not None:
            # --- SCENARIO MODE ---
            # 🆕 UPDATED: Pass the list as 'planned_extraction_schedule'
            # We log the schedule to verify what the user sent
            print(f"🧪 Running scenario for {payload.region_id} | Schedule: {payload.planned_extraction}")
            
            results = run_inference(
                region_id_filter=payload.region_id, 
                planned_extraction_schedule=payload.planned_extraction
            )
            return {
                "status": "success",
                "mode": "scenario",
                "data": results
            }
        else:
            # --- BATCH MODE ---
            # Run for specific region or all (defaulting to specific here based on payload)
            run_inference(region_id_filter=payload.region_id)
            return {
                "status": "success", 
                "mode": "batch_save",
                "message": f"Forecast generated and saved for {payload.region_id}."
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{region_id}", response_model=List[ForecastResponse])
def get_forecasts(region_id: str):
    """
    Get the latest stored 7-day forecast for a region.
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
            horizon_step=doc["horizon_step"],
            scenario_extraction=doc.get("scenario_extraction", 0.0)
        ))
    
    if not results:
        return []
        
    return results