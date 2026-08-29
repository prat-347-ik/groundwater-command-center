from fastapi import APIRouter, HTTPException
from typing import List, Optional, Any, Dict
from datetime import datetime
from pydantic import BaseModel

from src.config.mongo_client import mongo_client
from src.inference.predictor import run_inference, predict_scenario, get_feature_importance
from src.modelling.registry import ModelNotFoundError, ModelArtifactNotFoundError

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
    planned_extraction: Optional[List[float]] = None 

class SimulationRequest(BaseModel):
    region_id: str
    rainfall_modifier: float   # 1.0 = 100%
    extraction_modifier: float # 1.0 = 100%

# --- Routes ---

@router.post("/generate")
def generate_forecast(payload: GenerateRequest):
    """
    Triggers model inference for a region.
    If 'planned_extraction' is provided (as a list), runs a simulation and returns ephemeral horizon data (Scenario Mode).
    If not provided, runs standard batch inference and persists to DB (Production Mode).
    """
    try:
        if payload.planned_extraction is not None:
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
            run_inference(region_id_filter=payload.region_id)
            return {
                "status": "success", 
                "mode": "batch_save",
                "message": f"Forecast generated and saved for region {payload.region_id}."
            }

    except (ModelNotFoundError, ModelArtifactNotFoundError) as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/simulate")
def run_simulation(req: SimulationRequest):
    """
    Runs a single-step What-If sensitivity simulation using the active model for the region.
    """
    try:
        result = predict_scenario(
            req.region_id, 
            req.rainfall_modifier, 
            req.extraction_modifier
        )
        return result
    except (ModelNotFoundError, ModelArtifactNotFoundError) as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/importance/{region_id}")
def get_feature_drivers(region_id: str):
    """Get top driving feature importances for the region's active model."""
    try:
        data = get_feature_importance(region_id)
        return {"region_id": region_id, "importance": data}
    except (ModelNotFoundError, ModelArtifactNotFoundError) as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{region_id}", response_model=List[ForecastResponse])
def get_forecasts(region_id: str):
    """
    Get the latest stored 7-day forecast for a region from MongoDB.
    """
    try:
        db = mongo_client.get_olap_db()
        collection = db.daily_forecasts
        
        cursor = collection.find(
            {"region_id": region_id}
        ).sort("forecast_date", 1).limit(30)
        
        results = []
        for doc in cursor:
            results.append(ForecastResponse(
                region_id=doc["region_id"],
                forecast_date=doc["forecast_date"],
                predicted_level=doc["predicted_level"],
                model_version=doc.get("model_version", "unknown"),
                horizon_step=doc["horizon_step"],
                scenario_extraction=doc.get("scenario_extraction", 0.0)
            ))
        
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))