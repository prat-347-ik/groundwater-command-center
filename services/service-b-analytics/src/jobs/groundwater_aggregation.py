import logging
from datetime import datetime, timedelta, timezone
import sys
import pandas as pd
from pymongo import UpdateOne
from src.config.mongo_client import mongo_client
from src.schemas.olap_models import DailyRegionGroundwater

# 🆕 Phase 3 Imports
from src.extract.service_a_adapter import ServiceAAdapter
from src.extract.service_c_adapter import ServiceCAdapter
from src.transform.feature_engineering import generate_region_features

# Configure Logger
logger = logging.getLogger(__name__)

def get_region_metadata(db):
    """
    Helper: Fetches Region metadata for schema compliance.
    Performs an Application-Side Join (adhering to 'No DB Joins' constraint).
    
    Returns:
        dict: {region_id: {name: str, state: str, soil_type: str, permeability: float}}
    """
    regions = {}
    # Read-Only access to Service A 'regions' collection
    # 🆕 Phase 3: Fetch Soil/Hydro Context
    projection = {
        "region_id": 1, "name": 1, "state": 1, 
        "soil_type": 1, "permeability_index": 1, "_id": 0
    }
    cursor = db.regions.find({}, projection)
    
    for r in cursor:
        regions[r["region_id"]] = {
            "name": r["name"],
            "state": r["state"],
            "soil_type": r.get("soil_type", "sandy_loam"), # Default if missing
            "permeability_index": r.get("permeability_index", 0.5)
        }
    return regions

def get_total_well_counts(db):
    """
    Helper: Fetches total active well counts per region.
    Required for 'data_completeness_score'.
    
    Returns:
        dict: {region_id: total_wells_count}
    """
    # Group by region_id to count active wells
    pipeline = [
        {"$match": {"status": "active"}},
        {"$group": {"_id": "$region_id", "count": {"$sum": 1}}}
    ]
    results = db.wells.aggregate(pipeline)
    return {r["_id"]: r["count"] for r in results}

def update_feature_store(region_id: str, region_meta: dict, olap_db):
    """
    🆕 Phase 3: Fetches all multi-source data and updates the Feature Store.
    This runs AFTER the daily aggregation to ensure the latest target is available.
    """
    try:
        # 1. Initialize Adapters
        # We use API adapters for external services, but can direct fetch from OLAP for local data
        adapter_a = ServiceAAdapter() 
        adapter_c = ServiceCAdapter()

        # 2. Fetch Historical Data needed for Features
        # A. Groundwater (Target) - Fetch last 90 days from OLAP
        gw_cursor = olap_db.daily_region_groundwater.find(
            {"region_id": region_id},
            {"date": 1, "avg_water_level": 1, "region_id": 1, "_id": 0}
        ).sort("date", 1).limit(90)
        gw_data = list(gw_cursor)
        
        # B. Rainfall (Service C)
        rain_data = list(adapter_c.fetch_rainfall_data(region_id)) # Note: method name in adapter might vary, assuming logic
        # If using async in adapter, we might need a sync wrapper, or use requests directly here for simplicity
        # (Assuming the Adapter has a sync fallback or we use the API directly)
        
        # C. Weather (Service C) - 🆕 Phase 3
        weather_data = adapter_c.fetch_weather_history(region_id)
        
        # D. Extraction (Service A) - 🆕 Phase 3
        extraction_data = adapter_a.fetch_extraction_history(region_id)
        
        # 3. Generate Features (Physics-Informed)
        features = generate_region_features(
            groundwater_data=gw_data,
            rainfall_data=rain_data, # Pass empty list if fetch fails, handler inside handles it
            weather_data=weather_data,
            extraction_data=extraction_data,
            region_metadata=region_meta
        )
        
        # 4. Save to Feature Store (Upsert)
        if features:
            ops = []
            for feat in features:
                ops.append(
                    UpdateOne(
                        {"region_id": feat["region_id"], "date": feat["date"]},
                        {"$set": feat},
                        upsert=True
                    )
                )
            if ops:
                olap_db.region_feature_store.bulk_write(ops)
                # logger.info(f"   ✨ Features updated for {region_id}")

    except Exception as e:
        logger.error(f"Feature Gen Failed for {region_id}: {e}")

def run_groundwater_aggregation(target_date_str: str):
    """
    Aggregates water readings for a specific date and upserts to OLAP.
    
    Args:
        target_date_str (str): Date in 'YYYY-MM-DD' format.
    """
    # 1. Parse Date (UTC Midnight)
    try:
        target_date = datetime.strptime(target_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        start_of_day = target_date
        end_of_day = target_date + timedelta(days=1)
    except ValueError:
        logger.error("Invalid date format. Use YYYY-MM-DD.")
        return

    logger.info(f"🌊 Starting Groundwater Aggregation for {target_date_str}")

    # 2. Database Handles
    oltp_db = mongo_client.get_oltp_db()  # READ SOURCE
    olap_db = mongo_client.get_olap_db()  # WRITE TARGET

    # 3. Fetch Metadata (Application-Side Join)
    # Necessary to satisfy the locked DailyRegionGroundwater schema
    region_meta = get_region_metadata(oltp_db)
    well_counts = get_total_well_counts(oltp_db)

    # 4. Build Aggregation Pipeline
    # CONSTRAINT: No DB Joins ($lookup), No Rainfall, No Window Functions
    pipeline = [
        # Filter: Only readings for the target day
        {
            "$match": {
                "timestamp": {
                    "$gte": start_of_day,
                    "$lt": end_of_day
                }
            }
        },
        # Group: By Region
        {
            "$group": {
                "_id": "$region_id",
                "avg_val": {"$avg": "$water_level"},
                "min_val": {"$min": "$water_level"},
                "max_val": {"$max": "$water_level"},
                "reading_count": {"$sum": 1},
                "unique_wells": {"$addToSet": "$well_id"} # Set of unique well IDs
            }
        },
        # Project: Format output for Python processing
        {
            "$project": {
                "region_id": "$_id",
                "avg_water_level": "$avg_val",
                "min_water_level": "$min_val",
                "max_water_level": "$max_val",
                "reading_count": "$reading_count",
                "reporting_wells_count": {"$size": "$unique_wells"}
            }
        }
    ]

    # 5. Execute Aggregation (Read from Service A)
    raw_results = list(oltp_db.water_readings.aggregate(pipeline))
    logger.info(f"Fetched {len(raw_results)} regional aggregates.")

    # 6. Transform & Validate (Python Layer)
    bulk_ops = []
    active_regions = []
    
    for row in raw_results:
        region_id = row["region_id"]
        
        # Skip if region metadata is missing (integrity check)
        if region_id not in region_meta:
            logger.warning(f"Skipping unknown region_id: {region_id}")
            continue

        # Calculate Completeness Score
        total_wells = well_counts.get(region_id, 1) # Prevent division by zero
        reporting = row["reporting_wells_count"]
        completeness = round(reporting / total_wells, 4) if total_wells > 0 else 0.0

        # Construct Pydantic Model (Enforces Schema)
        try:
            record = DailyRegionGroundwater(
                date=target_date,
                region_id=region_id,
                region_name=region_meta[region_id]["name"],
                state=region_meta[region_id]["state"],
                avg_water_level=round(row["avg_water_level"], 2),
                min_water_level=round(row["min_water_level"], 2),
                max_water_level=round(row["max_water_level"], 2),
                reading_count=row["reading_count"],
                reporting_wells_count=reporting,
                data_completeness_score=completeness
            )
            
            # Prepare Idempotent Upsert
            # Filter: (region_id + date)
            # Update: Set all fields
            bulk_ops.append(
                UpdateOne(
                    {"region_id": region_id, "date": target_date},
                    {"$set": record.model_dump()},
                    upsert=True
                )
            )
            active_regions.append(region_id)
            
        except Exception as e:
            logger.error(f"Schema Validation Error for Region {region_id}: {e}")

    # 7. Batch Write (Write to Service B)
    if bulk_ops:
        result = olap_db.daily_region_groundwater.bulk_write(bulk_ops)
        logger.info(f"✅ Write Complete: {result.upserted_count} inserted, {result.modified_count} updated.")
        
        # 🆕 Phase 3: Trigger Feature Generation for Affected Regions
        logger.info("⚙️ Starting Phase 3 Feature Generation...")
        for rid in active_regions:
            # We pass the metadata dictionary for that region (includes soil info)
            update_feature_store(rid, region_meta[rid], olap_db)
        logger.info("✅ Feature Generation Complete.")
        
    else:
        logger.info("No data to process for this date.")


if __name__ == "__main__":
    # Default to yesterday if no date provided
    if len(sys.argv) > 1:
        date_arg = sys.argv[1]
    else:
        date_arg = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    
    run_groundwater_aggregation(date_arg)