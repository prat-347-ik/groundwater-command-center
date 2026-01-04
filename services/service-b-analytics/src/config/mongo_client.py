import os
import logging
from pymongo import MongoClient, ReadPreference
from pymongo.database import Database
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

class AnalyticsMongoClient:
    """
    Wrapper for MongoDB connection handling specific to Service B (Analytics).
    Enforces architectural separation between Operational (OLTP) and Analytical (OLAP) data.
    """
    
    def __init__(self):
        self._uri = os.getenv("MONGO_URI")
        # Service A Database Name (Source)
        self._oltp_db_name = os.getenv("MONGO_DB_NAME", "groundwater_operations")
        # Service B Database Name (Target)
        self._olap_db_name = os.getenv("ANALYTICS_DB_NAME", "groundwater_analytics")
        
        self._client: MongoClient = None

    def connect(self) -> None:
        """
        Establishes the MongoDB connection with DEBUG logging.
        """
        if not self._uri:
            raise ValueError("MONGO_URI environment variable is not set.")

        # --- DEBUG: Mask the URI to see where we are going ---
        if "@" in self._uri:
            # Mask password for safety
            masked_uri = self._uri.split("@")[1] 
        else:
            masked_uri = self._uri
            
        logger.info(f"🔌 ATTEMPTING CONNECT: {masked_uri}")
        logger.info(f"🎯 TARGET DATABASE: {self._olap_db_name}")

        try:
            self._client = MongoClient(
                self._uri, 
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000
            )
            
            # Verify connection
            info = self._client.server_info()
            logger.info(f"✅ Connected Successfully! Server Version: {info.get('version')}")
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.critical(f"❌ Failed to connect to MongoDB: {e}")
            raise e

    def get_oltp_db(self) -> Database:
        """
        Returns the handle for Service A (Operational Data).
        
        ENFORCEMENT:
        - Configured with ReadPreference.SECONDARY_PREFERRED.
        - This signals intent to read from replicas (scaling reads) 
          and avoids impacting the Primary node used by Service A for writes.
        """
        if not self._client:
            self.connect()
            
        return self._client.get_database(
            self._oltp_db_name, 
            read_preference=ReadPreference.SECONDARY_PREFERRED
        )

    def get_olap_db(self) -> Database:
        """
        Returns the handle for Service B (Analytical Data).
        
        ENFORCEMENT:
        - Uses default ReadPreference (PRIMARY).
        - Targeted for Write operations (ETL output).
        """
        if not self._client:
            self.connect()
            
        return self._client.get_database(self._olap_db_name)

    def close(self):
        """Closes the connection."""
        if self._client:
            self._client.close()
            logger.info("MongoDB connection closed.")

# Singleton instance for easy import across modules
mongo_client = AnalyticsMongoClient()