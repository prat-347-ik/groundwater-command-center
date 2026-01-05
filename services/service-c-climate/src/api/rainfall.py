import csv
import io
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from pymongo import DESCENDING

from config.database import db
from models.rainfall import RainfallRecord, RainfallResponse

router = APIRouter(prefix="/api/v1/rainfall", tags=["Rainfall"])

@router.post("/", status_code=201)
def create_rainfall_record(record: RainfallRecord):
    """
    Manual Ingestion: Adds a single rainfall record.
    """
    collection = db.get_rainfall_collection()
    
    # 1. Insert Data
    result = collection.insert_one(record.model_dump())
    
    return {
        "message": "Rainfall record created successfully",
        "id": str(result.inserted_id)
    }

@router.post("/ingest/csv")
async def ingest_rainfall_csv(file: UploadFile = File(...)):
    """
    Bulk Ingestion: Upload a CSV file with columns 'region_id', 'amount_mm'.
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Invalid file type. Only CSV allowed.")

    content = await file.read()
    decoded_content = content.decode('utf-8')
    csv_reader = csv.DictReader(io.StringIO(decoded_content))

    batch = []
    errors = []
    row_count = 0

    for row in csv_reader:
        row_count += 1
        try:
            # Basic Validation
            if 'region_id' not in row or 'amount_mm' not in row:
                raise ValueError("Missing required columns: region_id, amount_mm")

            # Parse Timestamp (Default to Now if missing)
            ts = datetime.utcnow()
            if row.get('timestamp'):
                ts = datetime.fromisoformat(row['timestamp'].replace('Z', '+00:00'))

            record = {
                "region_id": row['region_id'].strip(),
                "amount_mm": float(row['amount_mm']),
                "timestamp": ts,
                "source": "csv_upload"
            }
            batch.append(record)

        except Exception as e:
            errors.append(f"Row {row_count}: {str(e)}")

    # Bulk Insert
    if batch:
        collection = db.get_rainfall_collection()
        collection.insert_many(batch)

    return {
        "message": "CSV Processing Complete",
        "total_rows_scanned": row_count,
        "successfully_inserted": len(batch),
        "errors": errors[:10]  # Return top 10 errors to avoid payload bloat
    }

@router.get("/", response_model=RainfallResponse)
def get_rainfall_history(
    region_id: Optional[str] = Query(None, description="Filter by Region ID"),
    limit: int = Query(100, ge=1, le=1000)
):
    """
    Data Serving: Fetch rainfall history (Used by Service B for Analytics).
    """
    collection = db.get_rainfall_collection()
    query = {}
    
    if region_id:
        query["region_id"] = region_id

    # Fetch and Sort
    cursor = collection.find(query).sort("timestamp", DESCENDING).limit(limit)
    
    results = []
    for doc in cursor:
        doc["_id"] = str(doc["_id"])  # Convert ObjectId to string
        results.append(doc)

    return {"count": len(results), "data": results}