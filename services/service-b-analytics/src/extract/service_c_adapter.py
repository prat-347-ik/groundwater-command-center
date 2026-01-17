import httpx
import pandas as pd
import logging
import os
from typing import Optional, List, Dict, Any
import requests

# Configuration
SERVICE_C_URL = os.getenv("SERVICE_C_URL", "http://localhost:8100/api/v1")

logger = logging.getLogger(__name__)

class ServiceCAdapter:
    """
    Client to fetch Climate Data from Service C.
    """
    
    @staticmethod
    async def get_rainfall_history(region_id: str, days: int = 365) -> pd.DataFrame:
        """
        Fetches rainfall data and returns it as a standardized Pandas DataFrame.
        Columns: [date, rainfall_mm]
        """
        url = f"{SERVICE_C_URL}/rainfall/"
        params = {"region_id": region_id, "limit": days}
        
        try:
            async with httpx.AsyncClient() as client:
                logger.info(f"🌧️ Fetching Rainfall from {url} for {region_id}...")
                response = await client.get(url, params=params, timeout=10.0)
                response.raise_for_status()
                
                data = response.json().get("data", [])
                
                if not data:
                    logger.warning(f"⚠️ No rainfall data found for {region_id}")
                    return pd.DataFrame(columns=["date", "rainfall_mm"])

                # Convert to DataFrame
                df = pd.DataFrame(data)
                
                # Standardize Columns
                df['date'] = pd.to_datetime(df['timestamp']).dt.normalize() # Strip time
                df.rename(columns={'amount_mm': 'rainfall_mm'}, inplace=True)
                
                # Deduplicate (Sum multiple readings per day)
                df = df.groupby('date')['rainfall_mm'].sum().reset_index()
                
                logger.info(f"✅ Loaded {len(df)} rainfall records.")
                return df[['date', 'rainfall_mm']]

        except Exception as e:
            logger.error(f"❌ Failed to fetch rainfall: {e}")
            # Return empty DF so pipeline doesn't crash, but logs error
            return pd.DataFrame(columns=["date", "rainfall_mm"])
        
    # 🆕 Phase 3: Fetch Weather Data
    def fetch_weather_history(self, region_id: str) -> List[Dict[str, Any]]:
        """
        Fetches Temperature & Humidity logs (Evaporation inputs).
        """
        try:
            url = f"{SERVICE_C_URL}/weather"
            params = {"region_id": region_id, "limit": 1000}
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json().get('data', [])
        except Exception as e:
            logger.warning(f"Failed to fetch weather from Service C: {e}")
            return []