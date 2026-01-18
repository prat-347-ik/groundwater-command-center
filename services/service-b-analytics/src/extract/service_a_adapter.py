from datetime import datetime
from typing import Iterator, Dict, Any, List
from src.extract.base_extractor import MongoExtractor
import logging
import requests

logger = logging.getLogger(__name__)

class ServiceAAdapter:
    """
    Domain-specific adapter for Service A (Operational Layer).
    """
    
    def __init__(self, extractor: MongoExtractor = None):
        # Allow optional extractor for API-only calls
        self.extractor = extractor
        # Base URL for API calls 
        self.base_url = "http://localhost:4000/api/v1" 

    def fetch_water_readings(self, start_date: datetime, end_date: datetime) -> Iterator[Dict[str, Any]]:
        if not self.extractor:
            raise ValueError("MongoExtractor required for direct DB fetching")

        query = {
            "timestamp": {
                "$gte": start_date,
                "$lt": end_date
            }
        }
        projection = {
            "_id": 0, "well_id": 1, "region_id": 1, 
            "timestamp": 1, "water_level": 1, "source": 1
        }
        
        # 🔴 CORRECTED COLLECTION NAME: waterreadings
        return self.extractor.fetch_batch("waterreadings", query, projection)

    def fetch_rainfall(self, start_date: datetime, end_date: datetime) -> Iterator[Dict[str, Any]]:
        if not self.extractor:
            raise ValueError("MongoExtractor required for direct DB fetching")

        query = {"timestamp": {"$gte": start_date, "$lt": end_date}}
        projection = {"_id": 0, "region_id": 1, "timestamp": 1, "amount_mm": 1, "source": 1}
        
        return self.extractor.fetch_batch("rainfall", query, projection)

    def fetch_regions(self, active_only: bool = False) -> Iterator[Dict[str, Any]]:
        if not self.extractor:
             pass

        query = {}
        if active_only:
            query["is_active"] = True
            
        projection = {
            "_id": 0, "region_id": 1, "name": 1, "state": 1, 
            "critical_level": 1, "is_active": 1,
            "soil_type": 1, "aquifer_depth": 1, "permeability_index": 1
        }
        
        return self.extractor.fetch_batch("regions", query, projection)
    
    def fetch_extraction_history(self, region_id: str) -> List[Dict[str, Any]]:
        try:
            url = f"{self.base_url}/extraction/{region_id}"
            response = requests.get(url)
            if response.status_code == 404:
                return [] 
            response.raise_for_status()
            return response.json().get('data', [])
        except Exception as e:
            logger.warning(f"Failed to fetch extraction logs for {region_id}: {e}")
            return []