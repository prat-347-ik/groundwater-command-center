import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# Configure logger for data quality alerts
logger = logging.getLogger(__name__)

def normalize_utc_midnight(dt_input: Any) -> Optional[datetime]:
    """
    Normalizes a timestamp to 00:00:00 UTC (Midnight).
    Crucial for daily grouping keys.
    
    Args:
        dt_input: A datetime object, ISO string, or None.
        
    Returns:
        datetime: UTC midnight datetime, or None if invalid.
    """
    if dt_input is None:
        return None
        
    # Handle Strings (if generic extraction yielded JSON)
    if isinstance(dt_input, str):
        try:
            # Handle standard ISO format
            dt_input = datetime.fromisoformat(dt_input.replace('Z', '+00:00'))
        except ValueError:
            return None

    # Handle Datetime objects
    if isinstance(dt_input, datetime):
        # Force Timezone Awareness (Assume UTC if naive)
        if dt_input.tzinfo is None:
            dt_input = dt_input.replace(tzinfo=timezone.utc)
        else:
            dt_input = dt_input.astimezone(timezone.utc)
            
        # Strip time components
        return dt_input.replace(hour=0, minute=0, second=0, microsecond=0)
    
    return None

def safe_cast_float(
    value: Any, 
    min_val: Optional[float] = None, 
    max_val: Optional[float] = None
) -> Optional[float]:
    """
    Safely casts input to float with optional range validation.
    
    Args:
        value: Input value (number or string).
        min_val: Optional lower bound (inclusive).
        max_val: Optional upper bound (inclusive).
        
    Returns:
        float: Casted value, or None if invalid/out of bounds.
    """
    if value is None:
        return None
        
    try:
        f_val = float(value)
        
        # Range Checks
        if min_val is not None and f_val < min_val:
            return None
        if max_val is not None and f_val > max_val:
            return None
            
        return f_val
    except (ValueError, TypeError):
        return None

def clean_water_reading_row(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Validates and cleans a raw WaterReading document.
    
    Validations:
    - well_id must be present
    - timestamp must be valid
    - water_level must be a valid number
    
    Ref: Service A 'WaterReading' Schema
    """
    # 1. Critical Field Check
    if not row.get("well_id") or not row.get("region_id"):
        return None

    # 2. Timestamp Normalization
    date_key = normalize_utc_midnight(row.get("timestamp"))
    if not date_key:
        return None

    # 3. Numeric Casting
    # Note: water_level can be negative (artesian) or positive, so no min_val set unless domain specified.
    level = safe_cast_float(row.get("water_level"))
    if level is None:
        return None

    return {
        "date": date_key,
        "region_id": str(row["region_id"]),
        "well_id": str(row["well_id"]),
        "water_level": level,
        "source": str(row.get("source", "unknown"))
    }

def clean_rainfall_row(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Validates and cleans a raw Rainfall document.
    
    Validations:
    - region_id must be present
    - amount_mm must be >= 0
    
    Ref: Service A 'Rainfall' Schema
    """
    # 1. Critical Field Check
    if not row.get("region_id"):
        return None

    # 2. Timestamp Normalization
    date_key = normalize_utc_midnight(row.get("timestamp"))
    if not date_key:
        return None

    # 3. Numeric Casting
    # Rainfall cannot be negative.
    amount = safe_cast_float(row.get("amount_mm"), min_val=0.0)
    if amount is None:
        return None

    return {
        "date": date_key,
        "region_id": str(row["region_id"]),
        "amount_mm": amount,
        "source": str(row.get("source", "unknown"))
    }