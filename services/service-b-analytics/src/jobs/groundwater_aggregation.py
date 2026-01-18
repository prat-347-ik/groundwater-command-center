import logging
from datetime import datetime, timedelta, timezone
import sys
from pymongo import UpdateOne
from src.config.mongo_client import mongo_client
from src.schemas.olap_models import DailyRegionGroundwater

# 🆕 Phase 3 Imports
from src.extract.service_a_adapter import ServiceAAdapter
from src.extract.service_c_adapter import ServiceCAdapter
from src.transform.feature_engineering import generate_region_features

# Configure Logger to show everything
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def get_region_metadata(db):
    """
    Helper: Fetches Region metadata for schema compliance.
    """
    regions = {}
    projection = {
        "region_id": 1, "name": 1, "state": 1, 
        "soil_type": 1, "permeability_index": 1, "_id": 0
    }
    cursor = db.regions.find({}, projection)
    
    count = 0
    for r in cursor:
        regions[r["region_id"]] = {
            "name": r["name"],
            "state": r["state"],
            "soil_type": r.get("soil_type", "sandy_loam"),
            "permeability_index": r.get("permeability_index", 0.5)
        }
        count += 1
    
    logger.info(f"📋 Loaded Metadata for {count} regions.")
    return regions

def get_total_well_counts(db):
    """
    Helper: Fetches total active well counts per region.
    """
    pipeline = [
        {"$match": {"status": "active"}},
        {"$group": {"_id": "$region_id", "count": {"$sum": 1}}}
    ]
    results = db.wells.aggregate(pipeline)
    return {r["_id"]: r["count"] for r in results}

def update_feature_store(region_id: str, region_meta: dict, olap_db):
    """
    🆕 Phase 3: Fetches all multi-source data and updates the Feature Store.
    """
    logger.info(f"   🔍 Fetching external data for Region: {region_id}...")
    
    try:
        # 1. Initialize Adapters
        adapter_a = ServiceAAdapter() 
        adapter_c = ServiceCAdapter()

        # 2. Fetch Historical Data needed for Features
        # A. Groundwater (Target)
        gw_cursor = olap_db.daily_region_groundwater.find(
            {"region_id": region_id},
            {"date": 1, "avg_water_level": 1, "region_id": 1, "_id": 0}
        ).sort("date", 1).limit(90)
        gw_data = list(gw_cursor)
        logger.info(f"      🔹 Groundwater History: {len(gw_data)} records")

        # B. Rainfall (Service C)
        rain_data = adapter_c.fetch_rainfall_data(region_id)
        logger.info(f"      🔹 Rainfall Data: {len(rain_data)} records")
        
        # C. Weather (Service C)
        weather_data = adapter_c.fetch_weather_history(region_id)
        logger.info(f"      🔹 Weather Data: {len(weather_data)} records")
        
        # D. Extraction (Service A)
        extraction_data = adapter_a.fetch_extraction_history(region_id)
        logger.info(f"      🔹 Extraction Data: {len(extraction_data)} records")
        
        # 3. Generate Features
        logger.info(f"      ⚙️ Generating Physics Features...")
        features = generate_region_features(
            groundwater_data=gw_data,
            rainfall_data=rain_data, 
            weather_data=weather_data,
            extraction_data=extraction_data,
            region_metadata=region_meta
        )
        
        if not features:
            logger.warning(f"      ⚠️ No features generated for {region_id}. (Check if history exists for lags)")
            return

        logger.info(f"      ✅ Generated {len(features)} feature rows. Writing to DB...")

        # 4. Save to Feature Store
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
            logger.info(f"      ✨ Successfully saved features for {region_id}")

    except Exception as e:
        logger.error(f"      ❌ Feature Gen Failed for {region_id}: {e}", exc_info=True)

def run_groundwater_aggregation(target_date_str: str):
    # 1. Parse Date
    try:
        target_date = datetime.strptime(target_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        start_of_day = target_date
        end_of_day = target_date + timedelta(days=1)
    except ValueError:
        logger.error("Invalid date format. Use YYYY-MM-DD.")
        return

    logger.info(f"🌊 STARTING AGGREGATION for: {target_date_str}")
    logger.info(f"   Time Window: {start_of_day} to {end_of_day}")

    # 2. Database Handles
    try:
        oltp_db = mongo_client.get_oltp_db()
        olap_db = mongo_client.get_olap_db()
        logger.info("   ✅ Database connection successful.")
    except Exception as e:
        logger.error(f"   ❌ Database connection failed: {e}")
        return

    # 3. Fetch Metadata
    region_meta = get_region_metadata(oltp_db)
    well_counts = get_total_well_counts(oltp_db)

    # 4. Build Aggregation Pipeline
    pipeline = [
        {
            "$match": {
                "timestamp": {
                    "$gte": start_of_day,
                    "$lt": end_of_day
                }
            }
        },
        {
            "$group": {
                "_id": "$region_id",
                "avg_val": {"$avg": "$water_level"},
                "min_val": {"$min": "$water_level"},
                "max_val": {"$max": "$water_level"},
                "reading_count": {"$sum": 1},
                "unique_wells": {"$addToSet": "$well_id"} 
            }
        },
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

    # 5. Execute Aggregation
    logger.info("   ⏳ Running Aggregation Query on Service A (Water Readings)...")
    raw_results = list(oltp_db.waterreadings.aggregate(pipeline))
    logger.info(f"   📊 Aggregation Results: Found data for {len(raw_results)} regions.")

    # 6. Transform & Validate
    bulk_ops = []
    active_regions = []
    
    for row in raw_results:
        region_id = row["region_id"]
        
        if region_id not in region_meta:
            logger.warning(f"   ⚠️ Skipping unknown region_id: {region_id}")
            continue

        total_wells = well_counts.get(region_id, 1)
        reporting = row["reporting_wells_count"]
        completeness = round(reporting / total_wells, 4) if total_wells > 0 else 0.0

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
            
            bulk_ops.append(
                UpdateOne(
                    {"region_id": region_id, "date": target_date},
                    {"$set": record.model_dump()},
                    upsert=True
                )
            )
            active_regions.append(region_id)
            
        except Exception as e:
            logger.error(f"   ❌ Schema Error for Region {region_id}: {e}")

    # 7. Batch Write
    if bulk_ops:
        result = olap_db.daily_region_groundwater.bulk_write(bulk_ops)
        logger.info(f"   ✅ OLAP Write: {result.upserted_count} inserted, {result.modified_count} updated.")
        
        # 🆕 Phase 3 Trigger
        logger.info("   🚀 Triggering Feature Generation for active regions...")
        for rid in active_regions:
            update_feature_store(rid, region_meta[rid], olap_db)
        logger.info("   🏁 Job Complete.")
        
    else:
        logger.warning("   ⚠️ No data found for this date. Feature generation skipped.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        date_arg = sys.argv[1]
    else:
        date_arg = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    
    run_groundwater_aggregation(date_arg)