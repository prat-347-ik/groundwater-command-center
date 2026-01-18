import logging
import random
from datetime import datetime, timezone
from config.database import db
from models.satellite import SatelliteRecord

logger = logging.getLogger("service-c-satellite")
logger.setLevel(logging.INFO)

class SatelliteService:
    """
    Handles fetching and storage of Satellite Data.
    """

    @staticmethod
    def fetch_mock_satellite_data(region_id: str, date: datetime):
        """
        Simulates fetching data from NASA Earthdata / Google Earth Engine.
        In a real prod environment, this would call the GEE API.
        """
        try:
            # 1. Simulate Physics
            # If it's summer (June), GRACE usually shows mass loss (negative LWE)
            month = date.month
            
            if 4 <= month <= 9: # Summer/Monsoon transition
                lwe = random.uniform(-5.0, -1.0) # Deficit
                subsidence = random.uniform(-15.0, -5.0) # Sinking
            else:
                lwe = random.uniform(-1.0, 3.0) # Recovery
                subsidence = random.uniform(-2.0, 0.0) # Stable
                
            record = SatelliteRecord(
                region_id=region_id,
                timestamp=date,
                grace_lwe_thickness_cm=round(lwe, 3),
                insar_subsidence_mm=round(subsidence, 2),
                source="simulated_grace_fo"
            )
            
            # 2. Store in MongoDB
            collection = db.get_satellite_collection()
            
            # Idempotent Upsert (One record per region per day)
            collection.update_one(
                {"region_id": region_id, "timestamp": date},
                {"$set": record.model_dump()},
                upsert=True
            )
            
            logger.info(f"🛰️ Satellite Data Ingested for {region_id}: LWE={lwe:.2f}cm")
            return record

        except Exception as e:
            logger.error(f"❌ Satellite Fetch Failed: {e}")
            return None

    @staticmethod
    def get_history(region_id: str, limit: int = 30):
        collection = db.get_satellite_collection()
        cursor = collection.find({"region_id": region_id}).sort("timestamp", -1).limit(limit)
        
        results = []
        for doc in cursor:
            doc["_id"] = str(doc["_id"])
            results.append(doc)
        return results