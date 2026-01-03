from datetime import datetime
from typing import Iterator, Dict, Any
from src.extract.base_extractor import MongoExtractor

class ServiceAAdapter:
    """
    Domain-specific adapter for Service A (Operational Layer).
    Wraps the generic extractor with specific business queries.
    """
    
    def __init__(self, extractor: MongoExtractor):
        self.extractor = extractor

    def fetch_water_readings(self, start_date: datetime, end_date: datetime) -> Iterator[Dict[str, Any]]:
        """
        Fetches raw water readings within a date range.
        
        Reflects Schema:
        - well_id, region_id, timestamp, water_level, source
        """
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
        """
        query = {}
        if active_only:
            query["is_active"] = True
            
        projection = {
            "_id": 0,
            "region_id": 1,
            "name": 1,
            "state": 1,
            "critical_level": 1,
            "is_active": 1
        }
        
        return self.extractor.fetch_batch("regions", query, projection)