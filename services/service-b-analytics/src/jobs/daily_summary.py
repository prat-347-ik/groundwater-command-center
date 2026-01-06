import logging
import asyncio
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any

# Config
from src.config.mongo_client import mongo_client

# Extract Layer
from src.extract.base_extractor import MongoExtractor
from src.extract.service_a_adapter import ServiceAAdapter
from src.extract.service_c_adapter import ServiceCAdapter  # <--- [NEW] Import Service C Adapter

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

async def run_daily_pipeline(target_date_str: str):
    """
    Orchestrates the End-to-End ETL pipeline for a specific date.
    Updated to fetch Rainfall from Service C (Climate Service).
    """
    try:
        # 1. Pipeline Setup & Date Math
        # ------------------------------------------------------------------
        target_date = datetime.strptime(target_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        
        # We need 7 days of history to compute lag features (T-1 to T-7)
        history_start = target_date - timedelta(days=8)
        next_day = target_date + timedelta(days=1)
        
        logger.info(f"🚀 Starting Pipeline for {target_date.date()}")
        logger.info(f"📅 Extraction Window: {history_start.date()} -> {target_date.date()}")

        # Initialize Connections
        oltp_db = mongo_client.get_oltp_db()
        extractor = MongoExtractor(oltp_db)
        service_a = ServiceAAdapter(extractor)

        # 2. EXTRACT
        # ------------------------------------------------------------------
        logger.info("🔍 [Step 1/5] Extracting Raw Data...")
        
        # A. Fetch Metadata & Groundwater from Service A (Operational)
        raw_regions = list(service_a.fetch_regions(active_only=True))
        
        # Create lookup map for feature engineering
        region_critical_map = {
            r["region_id"]: r.get("critical_level", 0.0) 
            for r in raw_regions
        }
        
        # Fetch Water Readings (Service A)
        raw_readings = list(service_a.fetch_water_readings(history_start, next_day))
        
        # B. Fetch Rainfall from Service C (Climate) -- [UPDATED]
        raw_rainfall = []
        days_count = (next_day - history_start).days
        
        logger.info(f"   - Fetching climate data from Service C for {len(raw_regions)} regions...")
        
        for region in raw_regions:
            r_id = region["region_id"]
            # Fetch DataFrame from Service C
            df_rain = await ServiceCAdapter.get_rainfall_history(r_id, days=days_count)
            
            # Convert DataFrame rows back to Dicts for the existing pipeline
            if not df_rain.empty:
                for _, row in df_rain.iterrows():
                    raw_rainfall.append({
                        "region_id": r_id,
                        "timestamp": row["date"],   # Adapter standardized this column
                        "amount_mm": row["rainfall_mm"]
                    })

        logger.info(
            f"   - Fetched {len(raw_regions)} Regions, "
            f"{len(raw_readings)} Readings, "
            f"{len(raw_rainfall)} Rainfall records (from Service C)."
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
            # We reuse the existing cleaner, ensuring fields match
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
        
        agg_groundwater = aggregate_daily_groundwater(cleaned_readings)
        agg_rainfall = aggregate_daily_rainfall(cleaned_rainfall)
        
        # Filter for Target Date (Load Payload)
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
        
        all_features = generate_region_features(
            agg_groundwater, 
            agg_rainfall, 
            region_critical_map
        )
        
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
        raise e

if __name__ == "__main__":
    import sys
    # Use asyncio.run to execute the async pipeline
    if len(sys.argv) > 1:
        asyncio.run(run_daily_pipeline(sys.argv[1]))
    else:
        print("Usage: python daily_summary.py YYYY-MM-DD")