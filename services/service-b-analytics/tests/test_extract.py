import unittest
from unittest.mock import MagicMock
from datetime import datetime, timedelta, timezone
from src.extract.service_a_adapter import ServiceAAdapter
from src.extract.base_extractor import MongoExtractor

class TestServiceAAdapter(unittest.TestCase):
    
    def setUp(self):
        # Mock the generic MongoExtractor
        self.mock_extractor = MagicMock(spec=MongoExtractor)
        self.adapter = ServiceAAdapter(self.mock_extractor)
        self.test_date = datetime(2024, 1, 1, tzinfo=timezone.utc)

    def test_fetch_water_readings_query_structure(self):
        """
        Verify that fetch_water_readings builds the correct date-range query
        and uses the strict schema projection.
        """
        start = self.test_date
        end = self.test_date + timedelta(days=1)
        
        # Call the method
        list(self.adapter.fetch_water_readings(start, end))
        
        # Verify the call to the generic extractor
        self.mock_extractor.fetch_batch.assert_called_once()
        args, _ = self.mock_extractor.fetch_batch.call_args
        
        collection, query, projection = args
        
        # Assertions
        self.assertEqual(collection, "water_readings")
        
        # Check Date Logic ($gte, $lt)
        self.assertEqual(query["timestamp"]["$gte"], start)
        self.assertEqual(query["timestamp"]["$lt"], end)
        
        # Check Projection (No _id, specific fields only)
        expected_proj = {
            "_id": 0, "well_id": 1, "region_id": 1, 
            "timestamp": 1, "water_level": 1, "source": 1
        }
        self.assertEqual(projection, expected_proj)

    def test_fetch_regions_active_filter(self):
        """
        Verify that fetch_regions correctly applies the 'active_only' filter.
        """
        # Call with active_only=True
        list(self.adapter.fetch_regions(active_only=True))
        
        # Verify Query
        args, _ = self.mock_extractor.fetch_batch.call_args
        query = args[1]
        self.assertEqual(query, {"is_active": True})

if __name__ == '__main__':
    unittest.main()