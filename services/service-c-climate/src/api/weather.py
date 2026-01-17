import shutil
import uuid
import os
from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Query, BackgroundTasks
from pymongo import DESCENDING

from config.database import db
from models.weather import WeatherRecord
from services.ingestion import IngestionService

router = APIRouter(prefix="/api/v1/weather", tags=["Weather"])

UPLOAD_DIR = "/tmp/ingestion_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/", status_code=201)
def create_weather_record(record: WeatherRecord):
    """
    Manual Ingestion: Adds a single weather snapshot.
    """
    collection = db.get_weather_collection()
    result = collection.insert_one(record.model_dump())
    
    return {
        "message": "Weather record created successfully",
        "id": str(result.inserted_id)
    }

@router.post("/ingest/csv", status_code=202)
async def ingest_weather_csv(
    background_tasks: BackgroundTasks, 
    file: UploadFile = File(...)
):
    """
    Bulk Ingestion for Weather Data (Async).
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Invalid file type. Only CSV allowed.")

    file_id = f"{uuid.uuid4()}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, file_id)

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")
    finally:
        file.file.close()

    # Trigger the specific Weather worker
    background_tasks.add_task(IngestionService.process_weather_csv_background, file_path)

    return {
        "message": "Weather CSV accepted for processing.",
        "job_id": file_id,
        "status": "Processing in background"
    }

@router.get("/", status_code=200)
def get_weather_history(
    region_id: Optional[str] = Query(None, description="Filter by Region ID"),
    limit: int = Query(100, ge=1, le=1000)
):
    """
    Fetch historical weather data (Temperature/Humidity).
    """
    collection = db.get_weather_collection()
    query = {}
    
    if region_id:
        query["region_id"] = region_id

    cursor = collection.find(query).sort("timestamp", DESCENDING).limit(limit)
    
    results = []
    for doc in cursor:
        doc["_id"] = str(doc["_id"])
        results.append(doc)

    return {"count": len(results), "data": results}

@router.post("/fetch-external", status_code=202)
def trigger_external_fetch(
    background_tasks: BackgroundTasks,
    region_id: str,
    lat: float,
    lon: float
):
    """
    Manually trigger an external API fetch (e.g., OpenMeteo) for a region.
    """
    background_tasks.add_task(IngestionService.fetch_external_weather, region_id, lat, lon)
    return {"message": f"External fetch triggered for {region_id}"}