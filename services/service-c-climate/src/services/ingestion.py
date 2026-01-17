import csv
import os
import logging
from datetime import datetime,timezone
from typing import Dict, Any

import requests

from config.database import db
from models.weather import WeatherRecord

# Configure Logger
logger = logging.getLogger("service-c-ingestion")
logger.setLevel(logging.INFO)

class IngestionService:
    BATCH_SIZE = 1000

    @staticmethod
    def process_csv_background(file_path: str):
        """Legacy wrapper for rainfall ingestion."""
        return IngestionService._ingest_rainfall(file_path)

    @staticmethod
    def _ingest_rainfall(file_path: str):
        """
        Background Worker for Rainfall Data Ingestion from CSV.
        Expects CSV with columns: region_id, rainfall_mm, timestamp
        """
        logger.info(f"🌧️ Starting Rainfall ingestion for {file_path}")
        """
        Background Worker:
        1. Streams CSV from disk line-by-line (low memory).
        2. Validates and transforms data.
        3. Inserts into MongoDB in batches (efficient I/O).
        4. Cleans up the temp file.
        """
        logger.info(f"🚀 Starting background ingestion for {file_path}")
        
        collection = db.get_rainfall_collection()
        batch = []
        total_inserted = 0
        row_count = 0
        errors = 0

        try:
            # Open file in text mode (streaming)
            with open(file_path, mode='r', encoding='utf-8') as f:
                csv_reader = csv.DictReader(f)

                for row in csv_reader:
                    row_count += 1
                    try:
                        # --- Validation Logic ---
                        if 'region_id' not in row or 'amount_mm' not in row:
                            continue # Skip invalid rows silently or log debug

                        amount = float(row['amount_mm'])
                        if amount < 0:
                            continue

                        # Timestamp Parsing
                        ts = datetime.utcnow()
                        if row.get('timestamp'):
                            # Handle 'Z' for UTC if present
                            ts_str = row['timestamp'].replace('Z', '+00:00')
                            try:
                                ts = datetime.fromisoformat(ts_str)
                            except ValueError:
                                pass # Fallback to now() or skip

                        record = {
                            "region_id": row['region_id'].strip(),
                            "amount_mm": amount,
                            "timestamp": ts,
                            "source": "csv_bulk_ingest"
                        }
                        
                        batch.append(record)

                        # --- Batch Insert Trigger ---
                        if len(batch) >= IngestionService.BATCH_SIZE:
                            collection.insert_many(batch)
                            total_inserted += len(batch)
                            batch = [] # Clear memory
                            logger.info(f"   ...processed {row_count} rows")

                    except Exception as e:
                        errors += 1
                        # Optional: Log specific row errors to a separate collection

                # --- Insert Remaining Rows ---
                if batch:
                    collection.insert_many(batch)
                    total_inserted += len(batch)

            logger.info(f"✅ Ingestion Complete: {total_inserted} inserted, {errors} skipped.")

        except Exception as e:
            logger.error(f"❌ Critical Ingestion Failure: {e}")

        finally:
            # Cleanup: Remove temp file to free disk space
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"🗑️ Cleaned up temp file: {file_path}")
        



     # 🆕 Phase 2: Weather Data Ingestion
    @staticmethod
    def process_weather_csv_background(file_path: str):
        """
        Background Worker for Weather Data (Temp/Humidity).
        """
        logger.info(f"☀️ Starting Weather ingestion for {file_path}")
        
        collection = db.get_weather_collection()
        batch = []
        total_inserted = 0
        errors = 0

        try:
            with open(file_path, mode='r', encoding='utf-8') as f:
                csv_reader = csv.DictReader(f)

                for row in csv_reader:
                    try:
                        # Validation
                        if 'region_id' not in row or 'temp_c' not in row:
                            continue

                        # Parse
                        ts = datetime.utcnow()
                        if row.get('timestamp'):
                            ts = datetime.fromisoformat(row['timestamp'].replace('Z', '+00:00'))

                        record = WeatherRecord(
                            region_id=row['region_id'].strip(),
                            temperature_c=float(row['temp_c']),
                            humidity_percent=float(row.get('humidity', 50.0)),
                            solar_radiation=float(row.get('solar', 0.0)),
                            timestamp=ts,
                            source="csv_history"
                        )
                        
                        batch.append(record.dict())

                        if len(batch) >= IngestionService.BATCH_SIZE:
                            collection.insert_many(batch)
                            total_inserted += len(batch)
                            batch = []

                    except Exception as e:
                        errors += 1

                if batch:
                    collection.insert_many(batch)
                    total_inserted += len(batch)

            logger.info(f"✅ Weather Ingestion: {total_inserted} inserted, {errors} skipped.")

        except Exception as e:
            logger.error(f"❌ Weather Ingestion Failure: {e}")
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)

    # 🆕 Phase 2: External API Fetcher (Skeleton)
    @staticmethod
    def fetch_external_weather(region_id: str, lat: float, lon: float):
        """
        Fetches live weather from an open API (e.g., OpenMeteo)
        """
        try:
            # Example: Open-Meteo Free API
            url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
            response = requests.get(url)
            
            if response.status_code == 200:
                data = response.json()
                current = data.get('current_weather', {})
                
                record = WeatherRecord(
                    region_id=region_id,
                    temperature_c=current.get('temperature'),
                    humidity_percent=50.0, # API might need specific endpoint for humidity
                    timestamp=datetime.now(timezone.utc),
                    source="open_meteo_api"
                )
                
                db.get_weather_collection().insert_one(record.dict())
                logger.info(f"✅ Fetched live weather for {region_id}")
            else:
                logger.error(f"API Error: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Failed to fetch external weather: {e}")           