from datetime import datetime
from typing import Iterator, Dict, Any, List
from src.extract.base_extractor import MongoExtractor
import logging
import requests

logger = logging.getLogger(__name__)

class ServiceAAdapter:
    """
    Domain-specific adapter for Service A (Operational Layer).
    Wraps the generic extractor with specific business queries.
    """
    
    def __init__(self, extractor: MongoExtractor = None):
        # Allow optional extractor for API-only calls
        self.extractor = extractor
        # Base URL for API calls (fallback if direct DB access isn't used for new modules)
        self.base_url = "http://localhost:4000/api/v1" 

    def fetch_water_readings(self, start_date: datetime, end_date: datetime) -> Iterator[Dict[str, Any]]:
        """
        Fetches raw water readings within a date range.
        
        Reflects Schema:
        - well_id, region_id, timestamp, water_level, source
        """
        if not self.extractor:
            raise ValueError("MongoExtractor required for direct DB fetching")

        query = {
            "timestamp": {
                "$gte": start_date,
                "$lt": end_date
            }
        }
        # Exclude MongoDB internal _id, include only schema fields
        projection = {
            "_id": 0,
            "well_id": 1,
            "region_id": 1,
            "timestamp": 1,
            "water_level": 1,
            "source": 1
        }
        
        return self.extractor.fetch_batch("water_readings", query, projection)

    def fetch_rainfall(self, start_date: datetime, end_date: datetime) -> Iterator[Dict[str, Any]]:
        """
        Fetches raw rainfall data within a date range.
        
        Reflects Schema:
        - region_id, timestamp, amount_mm, source
        """
        if not self.extractor:
            raise ValueError("MongoExtractor required for direct DB fetching")

        query = {
            "timestamp": {
                "$gte": start_date,
                "$lt": end_date
            }
        }
        projection = {
            "_id": 0,
            "region_id": 1,
            "timestamp": 1,
            "amount_mm": 1,
            "source": 1
        }
        
        return self.extractor.fetch_batch("rainfall", query, projection)

    def fetch_regions(self, active_only: bool = False) -> Iterator[Dict[str, Any]]:
        """
        Fetches region metadata (Dimensional Data).
        
        Reflects Schema:
        - region_id, name, state, critical_level, is_active
        - 🆕 Phase 3: soil_type, aquifer_depth, permeability_index
        """
        if not self.extractor:
             # Fallback to API if extractor not provided (though aggregation job uses DB)
             # For the aggregation job, we usually pass the extractor.
             pass

        query = {}
        if active_only:
            query["is_active"] = True
            
        projection = {
            "_id": 0,
            "region_id": 1,
            "name": 1,
            "state": 1,
            "critical_level": 1,
            "is_active": 1,
            # 🆕 Phase 3 Fields
            "soil_type": 1,
            "aquifer_depth": 1,
            "permeability_index": 1
        }
        
        return self.extractor.fetch_batch("regions", query, projection)
    
    # 🆕 Phase 3: Fetch Extraction Data
    def fetch_extraction_history(self, region_id: str) -> List[Dict[str, Any]]:
        """
        Fetches water pumping logs (Discharge) for a specific region.
        Uses HTTP API as this is a new module potentially on a different service/shard.
        """
        try:
            url = f"{self.base_url}/extraction/{region_id}"
            response = requests.get(url)
            
            if response.status_code == 404:
                return [] # No extraction data is fine
                
            response.raise_for_status()
            return response.json().get('data', [])
        except Exception as e:
            logger.warning(f"Failed to fetch extraction logs for {region_id}: {e}")
            return []