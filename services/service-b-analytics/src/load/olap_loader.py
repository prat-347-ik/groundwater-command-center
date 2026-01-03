import logging
from typing import List, Dict, Any
from datetime import datetime, timezone, timedelta
from pymongo.collection import Collection
from src.config.mongo_client import mongo_client

# Configure Logger
logger = logging.getLogger(__name__)

def _execute_partition_overwrite(
    collection_name: str, 
    data: List[Dict[str, Any]], 
    target_date: datetime
):
    """
    Helper: Performs an idempotent 'Delete -> Insert' operation for a specific date.
    
    Logic:
    1. Delete all records in the collection matching 'target_date'.
    2. Bulk Insert the new batch of records.
    
    This strategy is preferred over 'Upsert' for batch analytics because:
    - It is faster (bulk insert vs individual update checks).
    - It handles record deletions (if a well is removed from source, it disappears here on rerun).
    
    Args:
        collection_name: Target OLAP collection.
        data: List of record dictionaries to insert.
        target_date: The specific date partition to overwrite (UTC Midnight).
    """
    db = mongo_client.get_olap_db()
    collection: Collection = db[collection_name]
    
    # 1. Define the Time Partition (Single Day)
    # Ensure strict midnight boundaries
    start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
    end_of_day = start_of_day + timedelta(days=1)
    
    try:
        # 2. DELETE existing partition (Idempotency Step)
        delete_result = collection.delete_many({
            "date": {
                "$gte": start_of_day,
                "$lt": end_of_day
            }
        })
        
        # 3. INSERT new data (if any)
        inserted_count = 0
        if data:
            insert_result = collection.insert_many(data, ordered=False)
            inserted_count = len(insert_result.inserted_ids)
            
        logger.info(
            f"📥 Load [{collection_name}] for {start_of_day.date()}: "
            f"Deleted {delete_result.deleted_count} stale records | "
            f"Inserted {inserted_count} new records."
        )

    except Exception as e:
        logger.error(f"❌ Failed to load data into {collection_name}: {e}")
        raise e  # Propagate error to stop the pipeline job

def load_daily_groundwater(data: List[Dict[str, Any]], target_date: datetime):
    """
    Loads aggregated groundwater stats into 'daily_region_groundwater'.
    """
    _execute_partition_overwrite("daily_region_groundwater", data, target_date)

def load_daily_rainfall(data: List[Dict[str, Any]], target_date: datetime):
    """
    Loads aggregated rainfall totals into 'daily_region_rainfall'.
    """
    _execute_partition_overwrite("daily_region_rainfall", data, target_date)

def load_region_features(data: List[Dict[str, Any]], target_date: datetime):
    """
    Loads engineered features into 'region_feature_store'.
    """
    _execute_partition_overwrite("region_feature_store", data, target_date)