"""
Archive and restore service for the ComfyUI Queue Manager.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from interfaces import DatabaseInterface
from models import QueueItem, QueueStatus

logger = logging.getLogger(__name__)


class ArchiveServiceError(Exception):
    """Exception raised for archive service operations."""


class ArchiveService:
    """Service for advanced archive and restore operations."""

    def __init__(self, database: DatabaseInterface):
        """Initialize the archive service.
        
        Args:
            database: Database interface for persistence
        """
        self.database = database

    def archive_items_by_status(self, statuses: list[QueueStatus]) -> int:
        """Archive all items with the specified statuses.
        
        Args:
            statuses: List of statuses to archive
            
        Returns:
            Number of items archived
            
        Raises:
            ArchiveServiceError: If archiving fails
        """
        if not statuses:
            return 0
        
        try:
            # Get all items with the specified statuses
            items_to_archive = []
            for status in statuses:
                if status != QueueStatus.RUNNING:  # Don't archive running items
                    items = self.database.get_items_by_status(status)
                    items_to_archive.extend(items)
            
            if not items_to_archive:
                return 0
            
            # Archive the items
            item_ids = [item.id for item in items_to_archive]
            if self.database.bulk_update_status(item_ids, QueueStatus.ARCHIVED):
                logger.info(f"Archived {len(item_ids)} items by status")
                return len(item_ids)
            else:
                raise ArchiveServiceError("Failed to archive items")
                
        except Exception as e:
            logger.error(f"Failed to archive items by status: {e}")
            raise ArchiveServiceError(f"Failed to archive items by status: {e}") from e

    def archive_items_by_age(self, days_old: int, statuses: list[QueueStatus] | None = None) -> int:
        """Archive items older than the specified number of days.
        
        Args:
            days_old: Number of days old items must be to archive
            statuses: Optional list of statuses to consider (defaults to completed/failed)
            
        Returns:
            Number of items archived
            
        Raises:
            ArchiveServiceError: If archiving fails
        """
        if days_old <= 0:
            raise ArchiveServiceError("Days old must be positive")
        
        if statuses is None:
            statuses = [QueueStatus.COMPLETED, QueueStatus.FAILED]
        
        try:
            # Calculate cutoff date
            from datetime import timedelta
            cutoff_date = datetime.now(timezone.utc).replace(
                hour=0, minute=0, second=0, microsecond=0
            ) - timedelta(days=days_old)
            
            # Get all items to consider
            items_to_archive = []
            for status in statuses:
                if status not in [QueueStatus.RUNNING, QueueStatus.ARCHIVED]:
                    items = self.database.get_items_by_status(status)
                    # Filter by age
                    old_items = [
                        item for item in items
                        if item.created_at < cutoff_date
                    ]
                    items_to_archive.extend(old_items)
            
            if not items_to_archive:
                return 0
            
            # Archive the items
            item_ids = [item.id for item in items_to_archive]
            if self.database.bulk_update_status(item_ids, QueueStatus.ARCHIVED):
                logger.info(f"Archived {len(item_ids)} items by age ({days_old} days)")
                return len(item_ids)
            else:
                raise ArchiveServiceError("Failed to archive items by age")
                
        except Exception as e:
            logger.error(f"Failed to archive items by age: {e}")
            raise ArchiveServiceError(f"Failed to archive items by age: {e}") from e

    def restore_items_by_pattern(self, workflow_name_pattern: str) -> int:
        """Restore archived items matching a workflow name pattern.
        
        Args:
            workflow_name_pattern: Pattern to match workflow names (case-insensitive)
            
        Returns:
            Number of items restored
            
        Raises:
            ArchiveServiceError: If restoration fails
        """
        if not workflow_name_pattern.strip():
            raise ArchiveServiceError("Workflow name pattern cannot be empty")
        
        try:
            # Get all archived items
            archived_items = self.database.get_items_by_status(QueueStatus.ARCHIVED)
            
            # Filter by pattern
            pattern = workflow_name_pattern.lower()
            matching_items = [
                item for item in archived_items
                if pattern in item.workflow_name.lower()
            ]
            
            if not matching_items:
                return 0
            
            # Restore the items (set to PENDING status)
            item_ids = [item.id for item in matching_items]
            if self.database.bulk_update_status(item_ids, QueueStatus.PENDING):
                logger.info(f"Restored {len(item_ids)} items by pattern: {workflow_name_pattern}")
                return len(item_ids)
            else:
                raise ArchiveServiceError("Failed to restore items by pattern")
                
        except Exception as e:
            logger.error(f"Failed to restore items by pattern: {e}")
            raise ArchiveServiceError(f"Failed to restore items by pattern: {e}") from e

    def get_archive_statistics(self) -> dict[str, Any]:
        """Get statistics about archived items.
        
        Returns:
            Dictionary containing archive statistics
        """
        try:
            archived_items = self.database.get_items_by_status(QueueStatus.ARCHIVED)
            
            if not archived_items:
                return {
                    "total_archived": 0,
                    "oldest_archived": None,
                    "newest_archived": None,
                    "workflow_counts": {},
                    "average_age_days": 0
                }
            
            # Calculate statistics
            workflow_counts = {}
            total_age_days = 0
            now = datetime.now(timezone.utc)
            
            oldest_date = archived_items[0].created_at
            newest_date = archived_items[0].created_at
            
            for item in archived_items:
                # Count workflows
                workflow_counts[item.workflow_name] = workflow_counts.get(item.workflow_name, 0) + 1
                
                # Track date range
                if item.created_at < oldest_date:
                    oldest_date = item.created_at
                if item.created_at > newest_date:
                    newest_date = item.created_at
                
                # Calculate age
                age_days = (now - item.created_at).days
                total_age_days += age_days
            
            average_age_days = total_age_days / len(archived_items)
            
            return {
                "total_archived": len(archived_items),
                "oldest_archived": oldest_date.isoformat(),
                "newest_archived": newest_date.isoformat(),
                "workflow_counts": workflow_counts,
                "average_age_days": round(average_age_days, 1)
            }
            
        except Exception as e:
            logger.error(f"Failed to get archive statistics: {e}")
            return {
                "total_archived": 0,
                "oldest_archived": None,
                "newest_archived": None,
                "workflow_counts": {},
                "average_age_days": 0,
                "error": str(e)
            }

    def cleanup_old_archived_items(self, days_old: int) -> int:
        """Permanently delete archived items older than specified days.
        
        Args:
            days_old: Number of days old archived items must be to delete
            
        Returns:
            Number of items deleted
            
        Raises:
            ArchiveServiceError: If cleanup fails
        """
        if days_old <= 0:
            raise ArchiveServiceError("Days old must be positive")
        
        try:
            # Calculate cutoff date
            from datetime import timedelta
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)
            
            # Get old archived items
            archived_items = self.database.get_items_by_status(QueueStatus.ARCHIVED)
            old_items = [
                item for item in archived_items
                if item.created_at < cutoff_date
            ]
            
            if not old_items:
                return 0
            
            # Delete the items
            deleted_count = 0
            for item in old_items:
                if self.database.delete_queue_item(item.id):
                    deleted_count += 1
            
            logger.info(f"Cleaned up {deleted_count} old archived items")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old archived items: {e}")
            raise ArchiveServiceError(f"Failed to cleanup old archived items: {e}") from e

    def bulk_archive_by_ids(self, item_ids: list[str], validate_status: bool = True) -> int:
        """Archive multiple items by their IDs.
        
        Args:
            item_ids: List of item IDs to archive
            validate_status: Whether to validate items are not running before archiving
            
        Returns:
            Number of items successfully archived
            
        Raises:
            ArchiveServiceError: If archiving fails
        """
        if not item_ids:
            return 0
        
        try:
            if validate_status:
                # Check that no items are running
                for item_id in item_ids:
                    item = self.database.get_queue_item(item_id)
                    if item and item.status == QueueStatus.RUNNING:
                        raise ArchiveServiceError(f"Cannot archive running item: {item_id}")
            
            # Archive all items
            if self.database.bulk_update_status(item_ids, QueueStatus.ARCHIVED):
                logger.info(f"Bulk archived {len(item_ids)} items")
                return len(item_ids)
            else:
                raise ArchiveServiceError("Failed to bulk archive items")
                
        except Exception as e:
            logger.error(f"Failed to bulk archive items: {e}")
            raise ArchiveServiceError(f"Failed to bulk archive items: {e}") from e

    def bulk_restore_by_ids(self, item_ids: list[str], target_status: QueueStatus = QueueStatus.PENDING) -> int:
        """Restore multiple archived items by their IDs.
        
        Args:
            item_ids: List of item IDs to restore
            target_status: Status to restore items to (default: PENDING)
            
        Returns:
            Number of items successfully restored
            
        Raises:
            ArchiveServiceError: If restoration fails
        """
        if not item_ids:
            return 0
        
        if target_status == QueueStatus.ARCHIVED:
            raise ArchiveServiceError("Cannot restore items to archived status")
        
        try:
            # Validate that all items are archived
            for item_id in item_ids:
                item = self.database.get_queue_item(item_id)
                if not item:
                    raise ArchiveServiceError(f"Item not found: {item_id}")
                if item.status != QueueStatus.ARCHIVED:
                    raise ArchiveServiceError(f"Item is not archived: {item_id}")
            
            # Restore all items
            if self.database.bulk_update_status(item_ids, target_status):
                logger.info(f"Bulk restored {len(item_ids)} items to {target_status.value}")
                return len(item_ids)
            else:
                raise ArchiveServiceError("Failed to bulk restore items")
                
        except Exception as e:
            logger.error(f"Failed to bulk restore items: {e}")
            raise ArchiveServiceError(f"Failed to bulk restore items: {e}") from e