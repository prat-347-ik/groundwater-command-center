import csv
import os
import logging
from datetime import datetime
from typing import Dict, Any

from config.database import db

# Configure Logger
logger = logging.getLogger("service-c-ingestion")
logger.setLevel(logging.INFO)

class IngestionService:
    BATCH_SIZE = 1000

    @staticmethod
    def process_csv_background(file_path: str):
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