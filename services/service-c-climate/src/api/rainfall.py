import shutil
import uuid
import os
from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Query, BackgroundTasks
from pymongo import DESCENDING

from config.database import db
from models.rainfall import RainfallRecord, RainfallResponse
from services.ingestion import IngestionService

router = APIRouter(prefix="/api/v1/rainfall", tags=["Rainfall"])

# Ensure a temp directory exists
UPLOAD_DIR = "/tmp/ingestion_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/", status_code=201)
def create_rainfall_record(record: RainfallRecord):
    """
    Manual Ingestion: Adds a single rainfall record.
    """
    collection = db.get_rainfall_collection()
    # Pydantic v2 uses model_dump(), v1 used dict()
    result = collection.insert_one(record.model_dump())
    
    return {
        "message": "Rainfall record created successfully",
        "id": str(result.inserted_id)
    }

@router.post("/ingest/csv", status_code=202)
async def ingest_rainfall_csv(
    background_tasks: BackgroundTasks, 
    file: UploadFile = File(...)
):
    """
    Bulk Ingestion (Async Streaming):
    1. Streams file to disk immediately (prevents RAM OOM).
    2. Returns 202 Accepted.
    3. Processes data in background thread.
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Invalid file type. Only CSV allowed.")

    # 1. Generate unique temp path
    file_id = f"{uuid.uuid4()}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, file_id)

    try:
        # 2. Stream upload to disk (Blocking I/O but efficient for large files)
        # shutil.copyfileobj reads in chunks, so it won't load the whole file into RAM.
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")
    finally:
        file.file.close()

    # 3. Trigger Background Processing
    # This runs IngestionService.process_csv_background in a separate thread
    background_tasks.add_task(IngestionService.process_csv_background, file_path)

    return {
        "message": "File accepted for processing.",
        "job_id": file_id,
        "status": "Processing in background"
    }

@router.get("/", response_model=RainfallResponse)
def get_rainfall_history(
    region_id: Optional[str] = Query(None, description="Filter by Region ID"),
    limit: int = Query(100, ge=1, le=1000)
):
    """
    Data Serving: Fetch rainfall history.
    """
    collection = db.get_rainfall_collection()
    query = {}
    
    if region_id:
        query["region_id"] = region_id

    # Fetch and Sort
    cursor = collection.find(query).sort("timestamp", DESCENDING).limit(limit)
    
    results = []
    for doc in cursor:
        doc["_id"] = str(doc["_id"])
        results.append(doc)

    return {"count": len(results), "data": results}