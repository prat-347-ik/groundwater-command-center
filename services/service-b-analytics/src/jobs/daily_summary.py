import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any

# Config
from src.config.mongo_client import mongo_client

# Extract Layer
from src.extract.base_extractor import MongoExtractor
from src.extract.service_a_adapter import ServiceAAdapter

# Transform Layer
from src.transform.cleaning import (
    clean_water_reading_row, 
    clean_rainfall_row
)
from src.transform.aggregations import (
    aggregate_daily_groundwater, 
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

def run_daily_pipeline(target_date_str: str):
    """
    Orchestrates the End-to-End ETL pipeline for a specific date.
    
    Flow:
    1. EXTRACT: Fetch raw data (Target Date + 7 days history for lag features).
    2. CLEAN: Normalize types, handle nulls, fix timestamps.
    3. AGGREGATE: Group raw data into daily stats.
    4. FEATURE: Compute lags, trends, and seasonality.
    5. LOAD: Write final datasets to OLAP collections.
    
    Args:
        target_date_str (str): Target execution date 'YYYY-MM-DD'.
    """
    try:
        # 1. Pipeline Setup & Date Math
        # ------------------------------------------------------------------
        target_date = datetime.strptime(target_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        
        # We need 7 days of history to compute lag features (T-1 to T-7)
        # So we extract: [Target - 8 days, Target + 1 day)
        history_start = target_date - timedelta(days=8)
        next_day = target_date + timedelta(days=1)
        
        logger.info(f"🚀 Starting Pipeline for {target_date.date()}")
        logger.info(f"📅 Extraction Window: {history_start.date()} -> {target_date.date()}")

        # Initialize Connections
        oltp_db = mongo_client.get_oltp_db()
        extractor = MongoExtractor(oltp_db)
        adapter = ServiceAAdapter(extractor)

        # 2. EXTRACT (Read-Only from Service A)
        # ------------------------------------------------------------------
        logger.info("🔍 [Step 1/5] Extracting Raw Data...")
        
        # Fetch Metadata
        raw_regions = list(adapter.fetch_regions(active_only=True))
        # Convert to Lookup Dict for Feature Engineering: {id: critical_level}
        region_critical_map = {
            r["region_id"]: r.get("critical_level", 0.0) 
            for r in raw_regions
        }
        
        # Fetch Time-Series Data (Windowed)
        raw_readings = list(adapter.fetch_water_readings(history_start, next_day))
        raw_rainfall = list(adapter.fetch_rainfall(history_start, next_day))
        
        logger.info(
            f"   - Fetched {len(raw_regions)} Regions, "
            f"{len(raw_readings)} Readings, "
            f"{len(raw_rainfall)} Rainfall records."
        )

        # 3. CLEAN (Pure Functions)
        # ------------------------------------------------------------------
        logger.info("🧹 [Step 2/5] Cleaning Data...")
        
        cleaned_readings = []
        for r in raw_readings:
            res = clean_water_reading_row(r)
            if res is not None:
                cleaned_readings.append(res)
        
        cleaned_rainfall = []
        for r in raw_rainfall:
            res = clean_rainfall_row(r)
            if res is not None:
                cleaned_rainfall.append(res)
        
        logger.info(
            f"   - Cleaned: {len(cleaned_readings)} Readings, "
            f"{len(cleaned_rainfall)} Rainfall records."
        )

        # 4. AGGREGATE (Pure Functions)
        # ------------------------------------------------------------------
        logger.info("∑  [Step 3/5] Aggregating Daily Stats...")
        
        # Generate Daily Stats for the whole window (needed for features)
        agg_groundwater = aggregate_daily_groundwater(cleaned_readings)
        agg_rainfall = aggregate_daily_rainfall(cleaned_rainfall)
        
        # Filter: We only want to LOAD the data for the specific target_date
        # (But we keep the full history in memory for Step 4)
        target_gw_payload = [
            row for row in agg_groundwater 
            if row['date'] == target_date
        ]
        target_rf_payload = [
            row for row in agg_rainfall 
            if row['date'] == target_date
        ]
        
        logger.info(
            f"   - Generated {len(target_gw_payload)} GW aggregates, "
            f"{len(target_rf_payload)} Rainfall aggregates for {target_date.date()}."
        )

        # 5. FEATURE ENGINEERING (Pure Functions)
        # ------------------------------------------------------------------
        logger.info("🧠 [Step 4/5] Engineering Features...")
        
        # Pass the FULL history to generate lags/trends
        all_features = generate_region_features(
            agg_groundwater, 
            agg_rainfall, 
            region_critical_map
        )
        
        # Filter output to only save the requested day
        target_features_payload = [
            row for row in all_features 
            if row['date'] == target_date
        ]
        
        logger.info(f"   - Generated {len(target_features_payload)} Feature Vector(s).")

        # 6. LOAD (Write-Only to OLAP)
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
        # Fail Fast: Raise error to ensure scheduler marks job as failed
        raise e
    finally:
        # Close DB Connection
        mongo_client.close()

if __name__ == "__main__":
    # Simple CLI for manual testing
    import sys
    if len(sys.argv) > 1:
        run_daily_pipeline(sys.argv[1])
    else:
        print("Usage: python daily_summary.py YYYY-MM-DD")