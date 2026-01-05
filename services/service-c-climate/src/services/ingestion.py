import csv
import io
from datetime import datetime
from typing import List, Dict, Any
from fastapi import UploadFile

from config.database import db

class IngestionService:
    @staticmethod
    async def process_csv(file: UploadFile) -> Dict[str, Any]:
        """
        Parses a CSV file, validates rows, and bulk inserts into MongoDB.
        Returns a summary of the operation.
        """
        # 1. Read File
        content = await file.read()
        decoded_content = content.decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(decoded_content))

        batch = []
        errors = []
        row_count = 0

        # 2. Process Rows
        for row in csv_reader:
            row_count += 1
            try:
                # Validation: Required Columns
                if 'region_id' not in row or 'amount_mm' not in row:
                    raise ValueError("Missing columns. Required: region_id, amount_mm")

                # Validation: Data Types
                amount = float(row['amount_mm'])
                if amount < 0:
                    raise ValueError(f"Rainfall cannot be negative: {amount}")

                # Parsing: Timestamp (Handle flexible formats or default to now)
                ts = datetime.utcnow()
                if row.get('timestamp'):
                    # Basic ISO 8601 parsing; can be enhanced for other formats
                    ts = datetime.fromisoformat(row['timestamp'].replace('Z', '+00:00'))

                record = {
                    "region_id": row['region_id'].strip(),
                    "amount_mm": amount,
                    "timestamp": ts,
                    "source": "csv_upload"
                }
                batch.append(record)

            except Exception as e:
                errors.append(f"Row {row_count}: {str(e)}")

        # 3. Bulk Insert
        inserted_count = 0
        if batch:
            collection = db.get_rainfall_collection()
            result = collection.insert_many(batch)
            inserted_count = len(result.inserted_ids)

        return {
            "total_rows": row_count,
            "inserted": inserted_count,
            "failed": len(errors),
            "errors": errors[:10]  # Limit error output
        }