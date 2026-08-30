import logging
import asyncio
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any

# Config
from src.config.mongo_client import mongo_client

# Extract Layer
from src.extract.base_extractor import MongoExtractor
from src.extract.service_a_adapter import ServiceAAdapter
from src.extract.service_c_adapter import ServiceCAdapter

# Transform Layer
from src.transform.cleaning import (
    clean_water_reading_row, 
    clean_rainfall_row
)
from src.transform.aggregations import (
    GroundwaterStreamAggregator,  # <--- [NEW] Import the streaming aggregator
    aggregate_daily_rainfall
)
from src.transform.feature_engineering import generate_region_features

# Load Layer
from src.load.olap_loader import (
    load_daily_groundwater, 
    load_daily_rainfall, 
    load_region_features
)

# Setup Logger
logger = logging.getLogger(__name__)

async def run_daily_pipeline(target_date_str: str):
    """
    Orchestrates the End-to-End ETL pipeline for a specific date.
    Optimized for memory efficiency via Stream Processing.
    """
    try:
        # 1. Pipeline Setup & Date Math
        target_date = datetime.strptime(target_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        history_start = target_date - timedelta(days=8)
        next_day = target_date + timedelta(days=1)
        
        logger.info(f"🚀 Starting Pipeline for {target_date.date()}")
        logger.info(f"📅 Extraction Window: {history_start.date()} -> {target_date.date()}")

        # Initialize Connections
        oltp_db = mongo_client.get_oltp_db()
        extractor = MongoExtractor(oltp_db)
        service_a = ServiceAAdapter(extractor)

        # 2. EXTRACT & TRANSFORM (STREAMING)
        # ------------------------------------------------------------------
        logger.info("🔍 [Step 1-3] Streaming Extraction & Aggregation...")
        
        # A. Fetch Metadata
        raw_regions = list(service_a.fetch_regions(active_only=True))
        region_critical_map = {r["region_id"]: r.get("critical_level", 0.0) for r in raw_regions}
        
        # B. Stream Groundwater Readings (Fixes OOM)
        # ------------------------------------------------
        gw_aggregator = GroundwaterStreamAggregator()
        readings_count = 0
        
        # Generator returns one document at a time; no giant list created.
        readings_iterator = service_a.fetch_water_readings(history_start, next_day)
        
        for raw_doc in readings_iterator:
            cleaned = clean_water_reading_row(raw_doc)
            if cleaned:
                gw_aggregator.consume(cleaned)
                readings_count += 1
                
            if readings_count % 10000 == 0:
                logger.debug(f"   ...processed {readings_count} readings")

        # Finalize Groundwater Aggregates
        agg_groundwater = gw_aggregator.get_results()
        logger.info(f"✅ Processed {readings_count} groundwater readings into {len(agg_groundwater)} daily stats.")

        # C. Fetch & Process Rainfall (Per Region Optimization)
        # ------------------------------------------------
        # Instead of collecting all raw rainfall, we process region-by-region.
        agg_rainfall = []
        days_count = (next_day - history_start).days
        total_rain_records = 0
        
        logger.info(f"   - Processing climate data for {len(raw_regions)} regions...")
        
        for region in raw_regions:
            r_id = region["region_id"]
            
            # 1. Fetch
            df_rain = await ServiceCAdapter.get_rainfall_history(r_id, days=days_count)
            
            if not df_rain.empty:
                # 2. Clean (Batch)
                cleaned_batch = []
                # Convert DataFrame to dicts for the existing cleaner logic
                for _, row in df_rain.iterrows():
                    raw_row = {
                        "region_id": r_id,
                        "timestamp": row["date"],
                        "amount_mm": row["rainfall_mm"]
                    }
                    res = clean_rainfall_row(raw_row)
                    if res:
                        cleaned_batch.append(res)
                
                total_rain_records += len(cleaned_batch)

                # 3. Aggregate (Immediate)
                # We aggregate this single region's data immediately and discard the raw rows
                if cleaned_batch:
                    region_aggs = aggregate_daily_rainfall(cleaned_batch)
                    agg_rainfall.extend(region_aggs)

        logger.info(f"✅ Processed {total_rain_records} rainfall records into {len(agg_rainfall)} daily stats.")

        # 4. FILTER TARGET DATE (Load Payloads)
        # ------------------------------------------------------------------
        # The aggregators returned stats for the whole 7-day window.
        # We need the whole window for Feature Engineering, but only load Today's stats to OLAP.
        
        target_gw_payload = [row for row in agg_groundwater if row['date'] == target_date]
        target_rf_payload = [row for row in agg_rainfall if row['date'] == target_date]

        # 5. FEATURE ENGINEERING
        # ------------------------------------------------------------------
        logger.info("🧠 [Step 4/5] Engineering Features...")
        
        # Feature Engineering still requires the 7-day window of Aggregates.
        # Since aggregates are ~1000x smaller than raw data, this fits in memory easily.
        all_features = generate_region_features(
            agg_groundwater, 
            agg_rainfall, 
            region_critical_map
        )
        
        target_features_payload = [row for row in all_features if row['date'] == target_date]
        
        logger.info(f"   - Generated {len(target_features_payload)} Feature Vector(s).")

        # 6. LOAD
        # ------------------------------------------------------------------
        logger.info("💾 [Step 5/5] Loading to OLAP...")
        
        if target_gw_payload:
            load_daily_groundwater(target_gw_payload, target_date)
            
        if target_rf_payload:
            load_daily_rainfall(target_rf_payload, target_date)
            
        if target_features_payload:
            load_region_features(target_features_payload, target_date)

        logger.info(f"✅ Pipeline Completed Successfully for {target_date.date()}")

    except Exception as e:
        logger.exception(f"❌ Pipeline Failed: {str(e)}")
        raise e

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        asyncio.run(run_daily_pipeline(sys.argv[1]))
    else:
        print("Usage: python daily_summary.py YYYY-MM-DD")