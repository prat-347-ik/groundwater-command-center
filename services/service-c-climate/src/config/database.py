import os
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "test")

class Database:
    client: MongoClient = None
    db = None

    def connect(self):
        """Establishes connection to MongoDB."""
        self.client = MongoClient(MONGO_URI)
        self.db = self.client[DB_NAME]
        print(f"✅ [Service C] Connected to MongoDB: {DB_NAME}")

    def get_rainfall_collection(self):
        """Returns the specific collection for Rainfall data."""
        return self.db["rainfall"]

    def close(self):
        """Closes the connection."""
        if self.client:
            self.client.close()

# Singleton Instance
db = Database()