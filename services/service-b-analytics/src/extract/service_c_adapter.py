import httpx
import pandas as pd
import logging
import os
from typing import Optional, List, Dict, Any
import requests

logger = logging.getLogger(__name__)

class ServiceCAdapter:
    """
    Client to fetch Climate Data from Service C.
    """
    
    def __init__(self):
        # 1. FIX: Initialize base_url
        self.base_url = os.getenv("SERVICE_C_URL", "http://localhost:8100/api/v1")

    # --- Legacy Async Method ---
    async def get_rainfall_history(self, region_id: str, days: int = 365) -> pd.DataFrame:
        url = f"{self.base_url}/rainfall/"
        params = {"region_id": region_id, "limit": days}
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=10.0)
                response.raise_for_status()
                data = response.json().get("data", [])
                if not data:
                    return pd.DataFrame(columns=["date", "rainfall_mm"])
                df = pd.DataFrame(data)
                df['date'] = pd.to_datetime(df['timestamp']).dt.normalize()
                df.rename(columns={'amount_mm': 'rainfall_mm'}, inplace=True)
                return df[['date', 'rainfall_mm']]
        except Exception as e:
            logger.error(f"❌ Failed to fetch rainfall: {e}")
            return pd.DataFrame(columns=["date", "rainfall_mm"])

    # --- 🆕 Synchronous Methods for Aggregation Job ---

    # 2. FIX: Add the missing synchronous method
    def fetch_rainfall_data(self, region_id: str) -> List[Dict[str, Any]]:
        try:
            url = f"{self.base_url}/rainfall"
            params = {"region_id": region_id, "limit": 1000}
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 404:
                return []
            response.raise_for_status()
            return response.json().get('data', [])
        except Exception as e:
            logger.warning(f"Failed to fetch rainfall from Service C: {e}")
            return []

    # 3. FIX: Ensure this uses self.base_url
    def fetch_weather_history(self, region_id: str) -> List[Dict[str, Any]]:
        try:
            url = f"{self.base_url}/weather"
            params = {"region_id": region_id, "limit": 1000}
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 404:
                return []
            response.raise_for_status()
            return response.json().get('data', [])
        except Exception as e:
            logger.warning(f"Failed to fetch weather from Service C: {e}")
            return []