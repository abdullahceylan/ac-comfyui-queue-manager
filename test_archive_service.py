"""
Unit tests for the ArchiveService class.
"""

import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock

from archive_service import ArchiveService, ArchiveServiceError
from database import SQLiteDatabase
from models import QueueItem, QueueStatus


class TestArchiveService(unittest.TestCase):
    """Test cases for the ArchiveService class."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary database for testing
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = Path(self.temp_db.name)
        
        # Create database and service instances
        self.database = SQLiteDatabase(self.db_path)
        self.database.initialize()
        self.service = ArchiveService(self.database)
        
        # Create test items
        self.test_items = [
            QueueItem(
                id="item1",
                workflow_name="Test Workflow 1",
                workflow_data={"test": "data1"},
                status=QueueStatus.COMPLETED,
                created_at=datetime.now(timezone.utc) - timedelta(days=10)
            ),
            QueueItem(
                id="item2",
                workflow_name="Test Workflow 2",
                workflow_data={"test": "data2"},
                status=QueueStatus.FAILED,
                created_at=datetime.now(timezone.utc) - timedelta(days=5)
            ),
            QueueItem(
                id="item3",
                workflow_name="Production Workflow",
                workflow_data={"test": "data3"},
                status=QueueStatus.PENDING,
                created_at=datetime.now(timezone.utc) - timedelta(days=15)
            ),
            QueueItem(
                id="item4",
                workflow_name="Running Workflow",
                workflow_data={"test": "data4"},
                status=QueueStatus.RUNNING,
                created_at=datetime.now(timezone.utc) - timedelta(days=1)
            )
        ]
        
        # Add test items to database
        for item in self.test_items:
            self.database.create_queue_item(item)

    def tearDown(self):
        """Clean up test fixtures."""
        self.database.close()
        if self.db_path.exists():
            self.db_path.unlink()

    def test_archive_items_by_status_success(self):
        """Test successful archiving by status."""
        result = self.service.archive_items_by_status([QueueStatus.COMPLETED, QueueStatus.FAILED])
        
        self.assertEqual(result, 2)  # Should archive 2 items
        
        # Verify items are archived
        item1 = self.database.get_queue_item("item1")
        item2 = self.database.get_queue_item("item2")
        self.assertEqual(item1.status, QueueStatus.ARCHIVED)
        self.assertEqual(item2.status, QueueStatus.ARCHIVED)

    def test_archive_items_by_status_empty_list(self):
        """Test archiving with empty status list."""
        result = self.service.archive_items_by_status([])
        
        self.assertEqual(result, 0)

    def test_archive_items_by_status_no_running(self):
        """Test that running items are not archived."""
        result = self.service.archive_items_by_status([QueueStatus.RUNNING])
        
        self.assertEqual(result, 0)  # Should not archive running items
        
        # Verify running item is still running
        item4 = self.database.get_queue_item("item4")
        self.assertEqual(item4.status, QueueStatus.RUNNING)

    def test_archive_items_by_age_success(self):
        """Test successful archiving by age."""
        result = self.service.archive_items_by_age(7)  # Archive items older than 7 days
        
        self.assertEqual(result, 1)  # Should archive item1 (10 days old)
        
        # Verify correct item is archived
        item1 = self.database.get_queue_item("item1")
        self.assertEqual(item1.status, QueueStatus.ARCHIVED)
        
        # Verify newer item is not archived
        item2 = self.database.get_queue_item("item2")
        self.assertEqual(item2.status, QueueStatus.FAILED)

    def test_archive_items_by_age_invalid_days(self):
        """Test archiving by age with invalid days."""
        with self.assertRaises(ArchiveServiceError):
            self.service.archive_items_by_age(0)
        
        with self.assertRaises(ArchiveServiceError):
            self.service.archive_items_by_age(-1)

    def test_archive_items_by_age_custom_statuses(self):
        """Test archiving by age with custom statuses."""
        result = self.service.archive_items_by_age(12, [QueueStatus.PENDING])  # Archive pending items older than 12 days
        
        self.assertEqual(result, 1)  # Should archive item3 (15 days old, pending)
        
        # Verify correct item is archived
        item3 = self.database.get_queue_item("item3")
        self.assertEqual(item3.status, QueueStatus.ARCHIVED)

    def test_restore_items_by_pattern_success(self):
        """Test successful restoration by pattern."""
        # First archive some items
        self.service.archive_items_by_status([QueueStatus.COMPLETED, QueueStatus.FAILED])
        
        # Restore items matching pattern
        result = self.service.restore_items_by_pattern("Test")
        
        self.assertEqual(result, 2)  # Should restore 2 "Test Workflow" items
        
        # Verify items are restored
        item1 = self.database.get_queue_item("item1")
        item2 = self.database.get_queue_item("item2")
        self.assertEqual(item1.status, QueueStatus.PENDING)
        self.assertEqual(item2.status, QueueStatus.PENDING)

    def test_restore_items_by_pattern_empty_pattern(self):
        """Test restoration with empty pattern."""
        with self.assertRaises(ArchiveServiceError):
            self.service.restore_items_by_pattern("")
        
        with self.assertRaises(ArchiveServiceError):
            self.service.restore_items_by_pattern("   ")

    def test_restore_items_by_pattern_no_matches(self):
        """Test restoration with no matching items."""
        # First archive some items
        self.service.archive_items_by_status([QueueStatus.COMPLETED])
        
        # Try to restore with non-matching pattern
        result = self.service.restore_items_by_pattern("NonExistent")
        
        self.assertEqual(result, 0)

    def test_get_archive_statistics_empty(self):
        """Test getting statistics with no archived items."""
        stats = self.service.get_archive_statistics()
        
        self.assertEqual(stats["total_archived"], 0)
        self.assertIsNone(stats["oldest_archived"])
        self.assertIsNone(stats["newest_archived"])
        self.assertEqual(stats["workflow_counts"], {})
        self.assertEqual(stats["average_age_days"], 0)

    def test_get_archive_statistics_with_items(self):
        """Test getting statistics with archived items."""
        # Archive some items
        self.service.archive_items_by_status([QueueStatus.COMPLETED, QueueStatus.FAILED])
        
        stats = self.service.get_archive_statistics()
        
        self.assertEqual(stats["total_archived"], 2)
        self.assertIsNotNone(stats["oldest_archived"])
        self.assertIsNotNone(stats["newest_archived"])
        self.assertEqual(stats["workflow_counts"]["Test Workflow 1"], 1)
        self.assertEqual(stats["workflow_counts"]["Test Workflow 2"], 1)
        self.assertGreater(stats["average_age_days"], 0)

    def test_cleanup_old_archived_items_success(self):
        """Test successful cleanup of old archived items."""
        # Archive some items
        self.service.archive_items_by_status([QueueStatus.COMPLETED, QueueStatus.FAILED])
        
        # Cleanup items older than 8 days (should delete item1)
        result = self.service.cleanup_old_archived_items(8)
        
        self.assertEqual(result, 1)  # Should delete 1 item
        
        # Verify item is deleted
        item1 = self.database.get_queue_item("item1")
        self.assertIsNone(item1)
        
        # Verify newer item still exists
        item2 = self.database.get_queue_item("item2")
        self.assertIsNotNone(item2)

    def test_cleanup_old_archived_items_invalid_days(self):
        """Test cleanup with invalid days."""
        with self.assertRaises(ArchiveServiceError):
            self.service.cleanup_old_archived_items(0)
        
        with self.assertRaises(ArchiveServiceError):
            self.service.cleanup_old_archived_items(-1)

    def test_cleanup_old_archived_items_no_items(self):
        """Test cleanup with no old items."""
        # Archive some items
        self.service.archive_items_by_status([QueueStatus.COMPLETED])
        
        # Try to cleanup items older than 20 days (none should match)
        result = self.service.cleanup_old_archived_items(20)
        
        self.assertEqual(result, 0)

    def test_bulk_archive_by_ids_success(self):
        """Test successful bulk archiving by IDs."""
        item_ids = ["item1", "item2", "item3"]
        result = self.service.bulk_archive_by_ids(item_ids)
        
        self.assertEqual(result, 3)
        
        # Verify items are archived
        for item_id in item_ids:
            item = self.database.get_queue_item(item_id)
            self.assertEqual(item.status, QueueStatus.ARCHIVED)

    def test_bulk_archive_by_ids_empty_list(self):
        """Test bulk archiving with empty list."""
        result = self.service.bulk_archive_by_ids([])
        
        self.assertEqual(result, 0)

    def test_bulk_archive_by_ids_running_item(self):
        """Test bulk archiving with running item (should fail)."""
        item_ids = ["item1", "item4"]  # item4 is running
        
        with self.assertRaises(ArchiveServiceError):
            self.service.bulk_archive_by_ids(item_ids)

    def test_bulk_archive_by_ids_no_validation(self):
        """Test bulk archiving without status validation."""
        item_ids = ["item1", "item4"]  # item4 is running
        result = self.service.bulk_archive_by_ids(item_ids, validate_status=False)
        
        self.assertEqual(result, 2)  # Should archive both items
        
        # Verify both items are archived
        item1 = self.database.get_queue_item("item1")
        item4 = self.database.get_queue_item("item4")
        self.assertEqual(item1.status, QueueStatus.ARCHIVED)
        self.assertEqual(item4.status, QueueStatus.ARCHIVED)

    def test_bulk_restore_by_ids_success(self):
        """Test successful bulk restoration by IDs."""
        # First archive some items
        item_ids = ["item1", "item2"]
        self.service.bulk_archive_by_ids(item_ids)
        
        # Restore them
        result = self.service.bulk_restore_by_ids(item_ids)
        
        self.assertEqual(result, 2)
        
        # Verify items are restored to pending
        for item_id in item_ids:
            item = self.database.get_queue_item(item_id)
            self.assertEqual(item.status, QueueStatus.PENDING)

    def test_bulk_restore_by_ids_custom_status(self):
        """Test bulk restoration with custom target status."""
        # First archive some items
        item_ids = ["item1", "item2"]
        self.service.bulk_archive_by_ids(item_ids)
        
        # Restore them to completed status
        result = self.service.bulk_restore_by_ids(item_ids, QueueStatus.COMPLETED)
        
        self.assertEqual(result, 2)
        
        # Verify items are restored to completed
        for item_id in item_ids:
            item = self.database.get_queue_item(item_id)
            self.assertEqual(item.status, QueueStatus.COMPLETED)

    def test_bulk_restore_by_ids_empty_list(self):
        """Test bulk restoration with empty list."""
        result = self.service.bulk_restore_by_ids([])
        
        self.assertEqual(result, 0)

    def test_bulk_restore_by_ids_invalid_target_status(self):
        """Test bulk restoration with invalid target status."""
        with self.assertRaises(ArchiveServiceError):
            self.service.bulk_restore_by_ids(["item1"], QueueStatus.ARCHIVED)

    def test_bulk_restore_by_ids_not_archived(self):
        """Test bulk restoration of non-archived items."""
        item_ids = ["item1"]  # Not archived
        
        with self.assertRaises(ArchiveServiceError):
            self.service.bulk_restore_by_ids(item_ids)

    def test_bulk_restore_by_ids_not_found(self):
        """Test bulk restoration of non-existent items."""
        item_ids = ["non-existent"]
        
        with self.assertRaises(ArchiveServiceError):
            self.service.bulk_restore_by_ids(item_ids)

    def test_database_error_handling(self):
        """Test error handling when database operations fail."""
        # Mock database to simulate failure
        mock_database = MagicMock()
        mock_database.get_items_by_status.side_effect = Exception("Database error")
        
        service = ArchiveService(mock_database)
        
        with self.assertRaises(ArchiveServiceError):
            service.archive_items_by_status([QueueStatus.COMPLETED])


if __name__ == "__main__":
    unittest.main()