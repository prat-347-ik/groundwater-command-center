from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Iterator
from pymongo.database import Database

class BaseExtractor(ABC):
    """
    Abstract Base Class for extracting data from a source database.
    Enforces a standard interface for all extraction adapters.
    """

    def __init__(self, db: Database):
        """
        Initialize with a database connection.
        
        Args:
            db (Database): The source database handle (Read-Only).
        """
        self.db = db

    @abstractmethod
    def fetch_batch(
        self, 
        collection: str, 
        query: Dict[str, Any], 
        projection: Optional[Dict[str, int]] = None,
        batch_size: int = 1000
    ) -> Iterator[Dict[str, Any]]:
        """
        Yields data in batches from the specified collection.
        
        Args:
            collection: Name of the collection to read from.
            query: MongoDB filter dictionary.
            projection: Fields to include/exclude (0 or 1).
            batch_size: Number of documents to yield per iteration (cursor batching).
            
        Returns:
            Iterator yielding dictionary representations of documents.
        """
        pass

class MongoExtractor(BaseExtractor):
    """
    Concrete implementation for MongoDB extraction.
    """
    
    def fetch_batch(
        self, 
        collection: str, 
        query: Dict[str, Any], 
        projection: Optional[Dict[str, int]] = None,
        batch_size: int = 1000
    ) -> Iterator[Dict[str, Any]]:
        
        # Safety Check: Ensure we aren't accidentally passing an empty query 
        # that dumps the whole DB unless explicitly intended.
        if query is None:
            query = {}

        cursor = self.db[collection].find(query, projection).batch_size(batch_size)
        
        for document in cursor:
            yield document