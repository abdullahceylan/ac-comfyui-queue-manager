"""
Unit tests for the QueueService class.
"""

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

from database import SQLiteDatabase
from models import QueueConfig, QueueFilter, QueueItem, QueueState, QueueStatus
from queue_service import QueueService, QueueServiceError


class TestQueueService(unittest.TestCase):
    """Test cases for the QueueService class."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary database for testing
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = Path(self.temp_db.name)
        
        # Create database and service instances
        self.database = SQLiteDatabase(self.db_path)
        self.service = QueueService(self.database)

    def tearDown(self):
        """Clean up test fixtures."""
        self.service.close()
        if self.db_path.exists():
            self.db_path.unlink()

    def test_initialization(self):
        """Test queue service initialization."""
        # Service should be initialized
        self.assertTrue(self.service._initialized)
        
        # Database should be initialized
        self.assertTrue(self.database._initialized)

    def test_initialization_with_database_failure(self):
        """Test initialization failure when database fails."""
        # Mock database initialization failure
        mock_database = MagicMock()
        mock_database.initialize.return_value = False
        
        with self.assertRaises(QueueServiceError):
            QueueService(mock_database)

    def test_add_workflow_success(self):
        """Test successful workflow addition."""
        workflow_data = {"nodes": {"1": {"class_type": "TestNode"}}}
        workflow_name = "Test Workflow"
        
        item_id = self.service.add_workflow(workflow_data, workflow_name)
        
        # Should return a valid ID
        self.assertIsInstance(item_id, str)
        self.assertTrue(len(item_id) > 0)
        
        # Item should exist in database
        item = self.service.get_queue_item(item_id)
        self.assertIsNotNone(item)
        self.assertEqual(item.workflow_name, workflow_name)
        self.assertEqual(item.workflow_data, workflow_data)
        self.assertEqual(item.status, QueueStatus.PENDING)

    def test_add_workflow_with_default_name(self):
        """Test workflow addition with default name."""
        workflow_data = {"nodes": {"1": {"class_type": "TestNode"}}}
        
        item_id = self.service.add_workflow(workflow_data)
        
        item = self.service.get_queue_item(item_id)
        self.assertIsNotNone(item)
        self.assertTrue(item.workflow_name.startswith("Workflow"))

    def test_add_workflow_empty_data(self):
        """Test workflow addition with empty data."""
        with self.assertRaises(QueueServiceError):
            self.service.add_workflow({})

    def test_add_workflow_uninitialized_service(self):
        """Test workflow addition with uninitialized service."""
        service = QueueService.__new__(QueueService)
        service._initialized = False
        
        with self.assertRaises(QueueServiceError):
            service.add_workflow({"test": "data"})

    def test_get_queue_items_all(self):
        """Test getting all queue items."""
        # Add some test items
        item_id1 = self.service.add_workflow({"test": "data1"}, "Workflow 1")
        item_id2 = self.service.add_workflow({"test": "data2"}, "Workflow 2")
        
        items = self.service.get_queue_items()
        
        self.assertEqual(len(items), 2)
        item_ids = [item.id for item in items]
        self.assertIn(item_id1, item_ids)
        self.assertIn(item_id2, item_ids)

    def test_get_queue_items_by_status(self):
        """Test getting queue items filtered by status."""
        # Add test items with different statuses
        item_id1 = self.service.add_workflow({"test": "data1"}, "Workflow 1")
        item_id2 = self.service.add_workflow({"test": "data2"}, "Workflow 2")
        
        # Update one item to completed status
        self.service.update_item_status(item_id1, QueueStatus.COMPLETED)
        
        # Get pending items
        pending_items = self.service.get_queue_items(QueueStatus.PENDING)
        self.assertEqual(len(pending_items), 1)
        self.assertEqual(pending_items[0].id, item_id2)
        
        # Get completed items
        completed_items = self.service.get_queue_items(QueueStatus.COMPLETED)
        self.assertEqual(len(completed_items), 1)
        self.assertEqual(completed_items[0].id, item_id1)

    def test_get_queue_item_success(self):
        """Test getting a specific queue item."""
        workflow_data = {"test": "data"}
        item_id = self.service.add_workflow(workflow_data, "Test Workflow")
        
        item = self.service.get_queue_item(item_id)
        
        self.assertIsNotNone(item)
        self.assertEqual(item.id, item_id)
        self.assertEqual(item.workflow_data, workflow_data)

    def test_get_queue_item_not_found(self):
        """Test getting a non-existent queue item."""
        item = self.service.get_queue_item("non-existent-id")
        self.assertIsNone(item)

    def test_get_queue_item_empty_id(self):
        """Test getting queue item with empty ID."""
        with self.assertRaises(QueueServiceError):
            self.service.get_queue_item("")

    def test_update_item_status_success(self):
        """Test successful status update."""
        item_id = self.service.add_workflow({"test": "data"}, "Test Workflow")
        
        # Update to running status
        result = self.service.update_item_status(item_id, QueueStatus.RUNNING)
        self.assertTrue(result)
        
        # Verify the update
        item = self.service.get_queue_item(item_id)
        self.assertEqual(item.status, QueueStatus.RUNNING)
        self.assertIsNotNone(item.started_at)

    def test_update_item_status_with_error(self):
        """Test status update with error message."""
        item_id = self.service.add_workflow({"test": "data"}, "Test Workflow")
        error_message = "Test error"
        
        result = self.service.update_item_status(
            item_id, QueueStatus.FAILED, error_message=error_message
        )
        self.assertTrue(result)
        
        # Verify the update
        item = self.service.get_queue_item(item_id)
        self.assertEqual(item.status, QueueStatus.FAILED)
        self.assertEqual(item.error_message, error_message)
        self.assertIsNotNone(item.completed_at)

    def test_update_item_status_with_result(self):
        """Test status update with result data."""
        item_id = self.service.add_workflow({"test": "data"}, "Test Workflow")
        result_data = {"output": "test result"}
        
        result = self.service.update_item_status(
            item_id, QueueStatus.COMPLETED, result_data=result_data
        )
        self.assertTrue(result)
        
        # Verify the update
        item = self.service.get_queue_item(item_id)
        self.assertEqual(item.status, QueueStatus.COMPLETED)
        self.assertEqual(item.result_data, result_data)

    def test_update_item_status_not_found(self):
        """Test status update for non-existent item."""
        with self.assertRaises(QueueServiceError):
            self.service.update_item_status("non-existent-id", QueueStatus.COMPLETED)

    def test_archive_items_success(self):
        """Test successful item archiving."""
        item_id1 = self.service.add_workflow({"test": "data1"}, "Workflow 1")
        item_id2 = self.service.add_workflow({"test": "data2"}, "Workflow 2")
        
        result = self.service.archive_items([item_id1, item_id2])
        self.assertTrue(result)
        
        # Verify items are archived
        item1 = self.service.get_queue_item(item_id1)
        item2 = self.service.get_queue_item(item_id2)
        self.assertEqual(item1.status, QueueStatus.ARCHIVED)
        self.assertEqual(item2.status, QueueStatus.ARCHIVED)

    def test_archive_items_empty_list(self):
        """Test archiving empty list of items."""
        result = self.service.archive_items([])
        self.assertTrue(result)

    def test_archive_items_running_item(self):
        """Test archiving a running item (should fail)."""
        item_id = self.service.add_workflow({"test": "data"}, "Test Workflow")
        self.service.update_item_status(item_id, QueueStatus.RUNNING)
        
        with self.assertRaises(QueueServiceError):
            self.service.archive_items([item_id])

    def test_archive_items_not_found(self):
        """Test archiving non-existent item."""
        with self.assertRaises(QueueServiceError):
            self.service.archive_items(["non-existent-id"])

    def test_restore_items_success(self):
        """Test successful item restoration."""
        item_id1 = self.service.add_workflow({"test": "data1"}, "Workflow 1")
        item_id2 = self.service.add_workflow({"test": "data2"}, "Workflow 2")
        
        # Archive items first
        self.service.archive_items([item_id1, item_id2])
        
        # Restore items
        result = self.service.restore_items([item_id1, item_id2])
        self.assertTrue(result)
        
        # Verify items are restored
        item1 = self.service.get_queue_item(item_id1)
        item2 = self.service.get_queue_item(item_id2)
        self.assertEqual(item1.status, QueueStatus.PENDING)
        self.assertEqual(item2.status, QueueStatus.PENDING)

    def test_restore_items_empty_list(self):
        """Test restoring empty list of items."""
        result = self.service.restore_items([])
        self.assertTrue(result)

    def test_restore_items_not_archived(self):
        """Test restoring non-archived item."""
        item_id = self.service.add_workflow({"test": "data"}, "Test Workflow")
        
        with self.assertRaises(QueueServiceError):
            self.service.restore_items([item_id])

    def test_delete_items_success(self):
        """Test successful item deletion."""
        item_id1 = self.service.add_workflow({"test": "data1"}, "Workflow 1")
        item_id2 = self.service.add_workflow({"test": "data2"}, "Workflow 2")
        
        result = self.service.delete_items([item_id1, item_id2])
        self.assertTrue(result)
        
        # Verify items are deleted
        item1 = self.service.get_queue_item(item_id1)
        item2 = self.service.get_queue_item(item_id2)
        self.assertIsNone(item1)
        self.assertIsNone(item2)

    def test_delete_items_empty_list(self):
        """Test deleting empty list of items."""
        result = self.service.delete_items([])
        self.assertTrue(result)

    def test_delete_items_running_item(self):
        """Test deleting a running item (should fail)."""
        item_id = self.service.add_workflow({"test": "data"}, "Test Workflow")
        self.service.update_item_status(item_id, QueueStatus.RUNNING)
        
        with self.assertRaises(QueueServiceError):
            self.service.delete_items([item_id])

    def test_pause_queue(self):
        """Test pausing the queue."""
        result = self.service.pause_queue()
        self.assertTrue(result)
        
        # Verify queue state
        state = self.service.get_queue_state()
        self.assertEqual(state, QueueState.PAUSED)

    def test_resume_queue(self):
        """Test resuming the queue."""
        # Pause first
        self.service.pause_queue()
        
        # Resume
        result = self.service.resume_queue()
        self.assertTrue(result)
        
        # Verify queue state
        state = self.service.get_queue_state()
        self.assertEqual(state, QueueState.RUNNING)

    def test_get_queue_state_default(self):
        """Test getting default queue state."""
        state = self.service.get_queue_state()
        self.assertEqual(state, QueueState.RUNNING)

    def test_export_queue_all_items(self):
        """Test exporting all queue items."""
        item_id1 = self.service.add_workflow({"test": "data1"}, "Workflow 1")
        item_id2 = self.service.add_workflow({"test": "data2"}, "Workflow 2")
        
        export_data = self.service.export_queue()
        
        self.assertIn("version", export_data)
        self.assertIn("exported_at", export_data)
        self.assertIn("items", export_data)
        self.assertIn("config", export_data)
        self.assertEqual(len(export_data["items"]), 2)

    def test_export_queue_specific_items(self):
        """Test exporting specific queue items."""
        item_id1 = self.service.add_workflow({"test": "data1"}, "Workflow 1")
        item_id2 = self.service.add_workflow({"test": "data2"}, "Workflow 2")
        
        export_data = self.service.export_queue([item_id1])
        
        self.assertEqual(len(export_data["items"]), 1)
        self.assertEqual(export_data["items"][0]["id"], item_id1)

    def test_import_queue_success(self):
        """Test successful queue import."""
        # Create export data
        export_data = {
            "version": "1.0",
            "items": [
                {
                    "id": "test-id-1",
                    "workflow_name": "Imported Workflow 1",
                    "workflow_data": {"test": "data1"},
                    "status": "pending",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "started_at": None,
                    "completed_at": None,
                    "error_message": None,
                    "result_data": None
                }
            ]
        }
        
        result = self.service.import_queue(export_data)
        self.assertTrue(result)
        
        # Verify item was imported
        item = self.service.get_queue_item("test-id-1")
        self.assertIsNotNone(item)
        self.assertEqual(item.workflow_name, "Imported Workflow 1")

    def test_import_queue_merge_existing(self):
        """Test importing queue with merge option."""
        # Add existing item
        existing_id = self.service.add_workflow({"existing": "data"}, "Existing")
        
        # Create import data with same ID
        export_data = {
            "version": "1.0",
            "items": [
                {
                    "id": existing_id,
                    "workflow_name": "Should be skipped",
                    "workflow_data": {"should": "be_skipped"},
                    "status": "pending",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "started_at": None,
                    "completed_at": None,
                    "error_message": None,
                    "result_data": None
                }
            ]
        }
        
        result = self.service.import_queue(export_data, merge=True)
        self.assertTrue(result)
        
        # Verify original item was not overwritten
        item = self.service.get_queue_item(existing_id)
        self.assertEqual(item.workflow_name, "Existing")

    def test_import_queue_invalid_data(self):
        """Test importing invalid queue data."""
        with self.assertRaises(QueueServiceError):
            self.service.import_queue({})

    def test_filter_items_by_status(self):
        """Test filtering items by status."""
        item_id1 = self.service.add_workflow({"test": "data1"}, "Workflow 1")
        item_id2 = self.service.add_workflow({"test": "data2"}, "Workflow 2")
        
        # Update one item status
        self.service.update_item_status(item_id1, QueueStatus.COMPLETED)
        
        # Filter by completed status
        filter_criteria = QueueFilter(status=[QueueStatus.COMPLETED])
        filtered_items = self.service.filter_items(filter_criteria)
        
        self.assertEqual(len(filtered_items), 1)
        self.assertEqual(filtered_items[0].id, item_id1)

    def test_filter_items_by_workflow_name(self):
        """Test filtering items by workflow name."""
        item_id1 = self.service.add_workflow({"test": "data1"}, "Test Workflow")
        item_id2 = self.service.add_workflow({"test": "data2"}, "Other Workflow")
        
        # Filter by workflow name
        filter_criteria = QueueFilter(workflow_name="Test")
        filtered_items = self.service.filter_items(filter_criteria)
        
        self.assertEqual(len(filtered_items), 1)
        self.assertEqual(filtered_items[0].id, item_id1)

    def test_get_config_default(self):
        """Test getting default configuration."""
        config = self.service.get_config()
        
        self.assertIsInstance(config, QueueConfig)
        self.assertEqual(config.queue_state, QueueState.RUNNING)
        self.assertEqual(config.max_concurrent_workflows, 1)

    def test_update_config_success(self):
        """Test successful configuration update."""
        new_config = QueueConfig(
            queue_state=QueueState.PAUSED,
            max_concurrent_workflows=2,
            auto_archive_completed=True,
            auto_archive_days=7
        )
        
        result = self.service.update_config(new_config)
        self.assertTrue(result)
        
        # Verify configuration was updated
        config = self.service.get_config()
        self.assertEqual(config.queue_state, QueueState.PAUSED)
        self.assertEqual(config.max_concurrent_workflows, 2)
        self.assertTrue(config.auto_archive_completed)
        self.assertEqual(config.auto_archive_days, 7)

    def test_context_manager(self):
        """Test using queue service as context manager."""
        with QueueService(SQLiteDatabase(":memory:")) as service:
            item_id = service.add_workflow({"test": "data"}, "Test")
            item = service.get_queue_item(item_id)
            self.assertIsNotNone(item)

    def test_search_items_simple(self):
        """Test simple search functionality."""
        item_id1 = self.service.add_workflow({"node": "input"}, "Test Workflow")
        item_id2 = self.service.add_workflow({"node": "output"}, "Production Workflow")
        
        # Search for "Test"
        results = self.service.search_items("Test")
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].id, item_id1)

    def test_search_items_advanced_query(self):
        """Test advanced search query functionality."""
        item_id1 = self.service.add_workflow({"node": "input"}, "Test Workflow")
        item_id2 = self.service.add_workflow({"node": "output"}, "Production Workflow")
        
        # Update one item to completed status
        self.service.update_item_status(item_id1, QueueStatus.COMPLETED)
        
        # Search for completed items with "Test" in name
        results = self.service.search_items("status:completed Test")
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].id, item_id1)

    def test_search_items_empty_query(self):
        """Test search with empty query."""
        item_id1 = self.service.add_workflow({"node": "input"}, "Test Workflow")
        item_id2 = self.service.add_workflow({"node": "output"}, "Production Workflow")
        
        # Empty query should return all items
        results = self.service.search_items("")
        
        self.assertEqual(len(results), 2)

    def test_search_items_no_matches(self):
        """Test search with no matches."""
        item_id1 = self.service.add_workflow({"node": "input"}, "Test Workflow")
        
        # Search for non-existent term
        results = self.service.search_items("NonExistent")
        
        self.assertEqual(len(results), 0)

    def test_archive_items_by_status(self):
        """Test archiving items by status."""
        item_id1 = self.service.add_workflow({"test": "data1"}, "Test Workflow")
        item_id2 = self.service.add_workflow({"test": "data2"}, "Production Workflow")
        
        # Update items to completed status
        self.service.update_item_status(item_id1, QueueStatus.COMPLETED)
        self.service.update_item_status(item_id2, QueueStatus.FAILED)
        
        # Archive completed and failed items
        archived_count = self.service.archive_items_by_status([QueueStatus.COMPLETED, QueueStatus.FAILED])
        
        self.assertEqual(archived_count, 2)
        
        # Verify items are archived
        item1 = self.service.get_queue_item(item_id1)
        item2 = self.service.get_queue_item(item_id2)
        self.assertEqual(item1.status, QueueStatus.ARCHIVED)
        self.assertEqual(item2.status, QueueStatus.ARCHIVED)

    def test_archive_items_by_age(self):
        """Test archiving items by age."""
        # This test would require manipulating item creation dates
        # For now, test that the method works without errors
        archived_count = self.service.archive_items_by_age(30)  # Archive items older than 30 days
        
        # Should return 0 since we just created the items
        self.assertEqual(archived_count, 0)

    def test_restore_items_by_pattern(self):
        """Test restoring items by pattern."""
        item_id1 = self.service.add_workflow({"test": "data1"}, "Test Workflow")
        item_id2 = self.service.add_workflow({"test": "data2"}, "Production Workflow")
        
        # Archive items first
        self.service.archive_items([item_id1, item_id2])
        
        # Restore items matching pattern
        restored_count = self.service.restore_items_by_pattern("Test")
        
        self.assertEqual(restored_count, 1)
        
        # Verify correct item is restored
        item1 = self.service.get_queue_item(item_id1)
        self.assertEqual(item1.status, QueueStatus.PENDING)

    def test_get_archive_statistics(self):
        """Test getting archive statistics."""
        item_id1 = self.service.add_workflow({"test": "data1"}, "Test Workflow")
        item_id2 = self.service.add_workflow({"test": "data2"}, "Test Workflow")
        
        # Archive items
        self.service.archive_items([item_id1, item_id2])
        
        # Get statistics
        stats = self.service.get_archive_statistics()
        
        self.assertEqual(stats["total_archived"], 2)
        self.assertEqual(stats["workflow_counts"]["Test Workflow"], 2)
        self.assertGreaterEqual(stats["average_age_days"], 0)

    def test_cleanup_old_archived_items(self):
        """Test cleaning up old archived items."""
        item_id1 = self.service.add_workflow({"test": "data1"}, "Test Workflow")
        
        # Archive item
        self.service.archive_items([item_id1])
        
        # Try to cleanup items older than 30 days (should not delete recent items)
        deleted_count = self.service.cleanup_old_archived_items(30)
        
        self.assertEqual(deleted_count, 0)
        
        # Verify item still exists
        item = self.service.get_queue_item(item_id1)
        self.assertIsNotNone(item)


if __name__ == "__main__":
    unittest.main()