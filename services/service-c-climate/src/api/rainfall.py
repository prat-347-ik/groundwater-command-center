from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from pymongo import DESCENDING

from config.database import db
from models.rainfall import RainfallRecord, RainfallResponse
from services.ingestion import IngestionService  # <--- Import the new service

router = APIRouter(prefix="/api/v1/rainfall", tags=["Rainfall"])

@router.post("/", status_code=201)
def create_rainfall_record(record: RainfallRecord):
    """
    Manual Ingestion: Adds a single rainfall record.
    """
    collection = db.get_rainfall_collection()
    result = collection.insert_one(record.model_dump())
    
    return {
        "message": "Rainfall record created successfully",
        "id": str(result.inserted_id)
    }

@router.post("/ingest/csv")
async def ingest_rainfall_csv(file: UploadFile = File(...)):
    """
    Bulk Ingestion: Upload a CSV file.
    Delegates processing to IngestionService.
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Invalid file type. Only CSV allowed.")

    # Delegate to Service Layer
    result = await IngestionService.process_csv(file)

    return {
        "message": "CSV Processing Complete",
        "details": result
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