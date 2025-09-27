"""
Unit tests for the SQLite database implementation.
"""

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from database import SQLiteDatabase, DatabaseError
from models import QueueFilter, QueueItem, QueueStatus


class TestSQLiteDatabase(unittest.TestCase):
    """Test cases for SQLiteDatabase class."""

    def setUp(self):
        """Set up test database."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_queue.db"
        self.db = SQLiteDatabase(self.db_path)
        self.assertTrue(self.db.initialize())

    def tearDown(self):
        """Clean up test database."""
        self.db.close()
        if self.db_path.exists():
            self.db_path.unlink()

    def test_database_initialization(self):
        """Test database initialization."""
        # Test that tables are created
        with self.db._get_cursor() as cursor:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
        expected_tables = ["queue_items", "queue_config", "schema_version"]
        for table in expected_tables:
            self.assertIn(table, tables)

    def test_create_queue_item(self):
        """Test creating a queue item."""
        item = QueueItem(
            workflow_name="test_workflow",
            workflow_data={"nodes": [{"id": 1, "type": "test"}]},
            status=QueueStatus.PENDING
        )
        
        self.assertTrue(self.db.create_queue_item(item))
        
        # Verify item was created
        retrieved_item = self.db.get_queue_item(item.id)
        self.assertIsNotNone(retrieved_item)
        self.assertEqual(retrieved_item.workflow_name, "test_workflow")
        self.assertEqual(retrieved_item.status, QueueStatus.PENDING)

    def test_get_queue_item(self):
        """Test retrieving a queue item by ID."""
        item = QueueItem(workflow_name="test_workflow")
        self.db.create_queue_item(item)
        
        retrieved_item = self.db.get_queue_item(item.id)
        self.assertIsNotNone(retrieved_item)
        self.assertEqual(retrieved_item.id, item.id)
        self.assertEqual(retrieved_item.workflow_name, "test_workflow")
        
        # Test non-existent item
        non_existent = self.db.get_queue_item("non-existent-id")
        self.assertIsNone(non_existent)

    def test_get_all_queue_items(self):
        """Test retrieving all queue items."""
        # Initially empty
        items = self.db.get_all_queue_items()
        self.assertEqual(len(items), 0)
        
        # Add some items
        item1 = QueueItem(workflow_name="workflow1")
        item2 = QueueItem(workflow_name="workflow2")
        self.db.create_queue_item(item1)
        self.db.create_queue_item(item2)
        
        items = self.db.get_all_queue_items()
        self.assertEqual(len(items), 2)
        workflow_names = [item.workflow_name for item in items]
        self.assertIn("workflow1", workflow_names)
        self.assertIn("workflow2", workflow_names)

    def test_update_queue_item(self):
        """Test updating a queue item."""
        item = QueueItem(
            workflow_name="original_name",
            status=QueueStatus.PENDING
        )
        self.db.create_queue_item(item)
        
        # Update the item
        item.workflow_name = "updated_name"
        item.status = QueueStatus.RUNNING
        item.error_message = "test error"
        
        self.assertTrue(self.db.update_queue_item(item))
        
        # Verify update
        retrieved_item = self.db.get_queue_item(item.id)
        self.assertEqual(retrieved_item.workflow_name, "updated_name")
        self.assertEqual(retrieved_item.status, QueueStatus.RUNNING)
        self.assertEqual(retrieved_item.error_message, "test error")

    def test_delete_queue_item(self):
        """Test deleting a queue item."""
        item = QueueItem(workflow_name="to_delete")
        self.db.create_queue_item(item)
        
        # Verify item exists
        self.assertIsNotNone(self.db.get_queue_item(item.id))
        
        # Delete item
        self.assertTrue(self.db.delete_queue_item(item.id))
        
        # Verify item is deleted
        self.assertIsNone(self.db.get_queue_item(item.id))
        
        # Test deleting non-existent item
        self.assertFalse(self.db.delete_queue_item("non-existent-id"))

    def test_get_items_by_status(self):
        """Test retrieving items by status."""
        # Create items with different statuses
        pending_item = QueueItem(workflow_name="pending", status=QueueStatus.PENDING)
        running_item = QueueItem(workflow_name="running", status=QueueStatus.RUNNING)
        completed_item = QueueItem(workflow_name="completed", status=QueueStatus.COMPLETED)
        
        self.db.create_queue_item(pending_item)
        self.db.create_queue_item(running_item)
        self.db.create_queue_item(completed_item)
        
        # Test filtering by status
        pending_items = self.db.get_items_by_status(QueueStatus.PENDING)
        self.assertEqual(len(pending_items), 1)
        self.assertEqual(pending_items[0].workflow_name, "pending")
        
        running_items = self.db.get_items_by_status(QueueStatus.RUNNING)
        self.assertEqual(len(running_items), 1)
        self.assertEqual(running_items[0].workflow_name, "running")
        
        # Test status with no items
        failed_items = self.db.get_items_by_status(QueueStatus.FAILED)
        self.assertEqual(len(failed_items), 0)

    def test_filter_queue_items(self):
        """Test filtering queue items with various criteria."""
        # Create test items
        item1 = QueueItem(
            workflow_name="image_generation",
            status=QueueStatus.PENDING,
            workflow_data={"type": "image", "model": "sdxl"}
        )
        item2 = QueueItem(
            workflow_name="text_processing",
            status=QueueStatus.COMPLETED,
            workflow_data={"type": "text", "model": "gpt"}
        )
        item3 = QueueItem(
            workflow_name="image_upscale",
            status=QueueStatus.PENDING,
            workflow_data={"type": "image", "model": "esrgan"}
        )
        
        for item in [item1, item2, item3]:
            self.db.create_queue_item(item)

        # Test filter by status
        filter_pending = QueueFilter(status=[QueueStatus.PENDING])
        pending_items = self.db.filter_queue_items(filter_pending)
        self.assertEqual(len(pending_items), 2)
        
        # Test filter by workflow name
        filter_image = QueueFilter(workflow_name="image")
        image_items = self.db.filter_queue_items(filter_image)
        self.assertEqual(len(image_items), 2)
        
        # Test filter by search term
        filter_search = QueueFilter(search_term="sdxl")
        search_items = self.db.filter_queue_items(filter_search)
        self.assertEqual(len(search_items), 1)
        self.assertEqual(search_items[0].workflow_name, "image_generation")
        
        # Test combined filters
        filter_combined = QueueFilter(
            status=[QueueStatus.PENDING],
            workflow_name="image"
        )
        combined_items = self.db.filter_queue_items(filter_combined)
        self.assertEqual(len(combined_items), 2)

    def test_bulk_update_status(self):
        """Test bulk status updates."""
        # Create test items
        items = []
        for i in range(3):
            item = QueueItem(
                workflow_name=f"workflow_{i}",
                status=QueueStatus.PENDING
            )
            items.append(item)
            self.db.create_queue_item(item)
        
        # Bulk update status
        item_ids = [item.id for item in items[:2]]  # Update first 2 items
        self.assertTrue(self.db.bulk_update_status(item_ids, QueueStatus.ARCHIVED))
        
        # Verify updates
        for i, item in enumerate(items):
            retrieved_item = self.db.get_queue_item(item.id)
            if i < 2:
                self.assertEqual(retrieved_item.status, QueueStatus.ARCHIVED)
            else:
                self.assertEqual(retrieved_item.status, QueueStatus.PENDING)
        
        # Test empty list
        self.assertTrue(self.db.bulk_update_status([], QueueStatus.COMPLETED))

    def test_config_operations(self):
        """Test configuration get/set operations."""
        # Test setting and getting config
        self.assertTrue(self.db.set_config("test_key", "test_value"))
        value = self.db.get_config("test_key")
        self.assertEqual(value, "test_value")
        
        # Test updating existing config
        self.assertTrue(self.db.set_config("test_key", "updated_value"))
        value = self.db.get_config("test_key")
        self.assertEqual(value, "updated_value")
        
        # Test non-existent config
        value = self.db.get_config("non_existent_key")
        self.assertIsNone(value)
        
        # Test JSON serialization
        json_data = {"nested": {"key": "value"}, "list": [1, 2, 3]}
        self.assertTrue(self.db.set_config("json_key", json.dumps(json_data)))
        retrieved_json = self.db.get_config("json_key")
        self.assertEqual(json.loads(retrieved_json), json_data)

    def test_date_range_filtering(self):
        """Test filtering by date range."""
        # Create items with different timestamps
        now = datetime.now(timezone.utc)
        old_item = QueueItem(workflow_name="old_workflow")
        old_item.created_at = datetime(2023, 1, 1, tzinfo=timezone.utc)
        
        new_item = QueueItem(workflow_name="new_workflow")
        new_item.created_at = now
        
        self.db.create_queue_item(old_item)
        self.db.create_queue_item(new_item)
        
        # Filter by date range
        start_date = datetime(2023, 6, 1, tzinfo=timezone.utc)
        end_date = now
        filter_date = QueueFilter(date_range=(start_date, end_date))
        
        filtered_items = self.db.filter_queue_items(filter_date)
        self.assertEqual(len(filtered_items), 1)
        self.assertEqual(filtered_items[0].workflow_name, "new_workflow")

    def test_error_handling(self):
        """Test error handling in database operations."""
        # Test with invalid database path (read-only directory)
        import tempfile
        import os
        
        # Create a read-only directory
        readonly_dir = tempfile.mkdtemp()
        os.chmod(readonly_dir, 0o444)  # Read-only
        
        try:
            readonly_db_path = os.path.join(readonly_dir, "readonly.db")
            readonly_db = SQLiteDatabase(readonly_db_path)
            
            # This should fail gracefully
            self.assertFalse(readonly_db.initialize())
            
            item = QueueItem(workflow_name="test")
            self.assertFalse(readonly_db.create_queue_item(item))
            
        finally:
            # Clean up - restore permissions and remove directory
            os.chmod(readonly_dir, 0o755)
            if os.path.exists(readonly_dir):
                import shutil
                shutil.rmtree(readonly_dir)

    def test_json_serialization(self):
        """Test JSON serialization of complex workflow data."""
        complex_data = {
            "nodes": [
                {"id": 1, "type": "LoadImage", "inputs": {"image": "test.png"}},
                {"id": 2, "type": "VAEDecode", "inputs": {"samples": [1, "samples"]}}
            ],
            "metadata": {
                "version": "1.0",
                "created_by": "test_user",
                "tags": ["test", "image_generation"]
            }
        }
        
        item = QueueItem(
            workflow_name="complex_workflow",
            workflow_data=complex_data,
            result_data={"output_images": ["result1.png", "result2.png"]}
        )
        
        self.assertTrue(self.db.create_queue_item(item))
        
        retrieved_item = self.db.get_queue_item(item.id)
        self.assertEqual(retrieved_item.workflow_data, complex_data)
        self.assertEqual(retrieved_item.result_data["output_images"], ["result1.png", "result2.png"])

    def test_concurrent_access(self):
        """Test thread-safe database access."""
        import threading
        import time
        
        results = []
        errors = []
        
        def create_items(thread_id):
            try:
                for i in range(10):
                    item = QueueItem(workflow_name=f"thread_{thread_id}_item_{i}")
                    success = self.db.create_queue_item(item)
                    results.append(success)
                    time.sleep(0.001)  # Small delay to increase chance of concurrency
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=create_items, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check results
        self.assertEqual(len(errors), 0, f"Errors occurred: {errors}")
        self.assertEqual(len(results), 30)  # 3 threads * 10 items each
        self.assertTrue(all(results), "Some database operations failed")
        
        # Verify all items were created
        all_items = self.db.get_all_queue_items()
        self.assertEqual(len(all_items), 30)


if __name__ == "__main__":
    unittest.main()