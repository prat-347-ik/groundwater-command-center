from fastapi import APIRouter, BackgroundTasks, Query
from datetime import datetime, timezone
from typing import Optional

from services.satellite_fetcher import SatelliteService

router = APIRouter(prefix="/api/v1/satellite", tags=["Satellite"])

@router.post("/fetch-trigger", status_code=202)
def trigger_satellite_fetch(
    background_tasks: BackgroundTasks,
    region_id: str,
    date_str: Optional[str] = Query(None, description="YYYY-MM-DD")
):
    """
    Triggers an async job to fetch/simulate satellite data for a region.
    """
    if date_str:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    else:
        target_date = datetime.now(timezone.utc)
        
    background_tasks.add_task(SatelliteService.fetch_mock_satellite_data, region_id, target_date)
    
    return {"message": "Satellite fetch job started", "region": region_id}

@router.get("/{region_id}")
def get_satellite_data(region_id: str, limit: int = 30):
    """
    Get historical GRACE/InSAR data.
    """
    data = SatelliteService.get_history(region_id, limit)
    return {"count": len(data), "data": data}