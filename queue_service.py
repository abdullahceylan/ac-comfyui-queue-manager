"""
Core queue service implementation for the ComfyUI Queue Manager.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from archive_service import ArchiveService
from database import SQLiteDatabase
from error_handler import ErrorHandler, with_error_handling
from exceptions import QueueServiceError, ValidationError
from filter_service import FilterService
from interfaces import DatabaseInterface, QueueServiceInterface
from models import QueueConfig, QueueFilter, QueueItem, QueueState, QueueStatus

logger = logging.getLogger(__name__)


class QueueService(QueueServiceInterface):
    """Core queue service implementation."""

    def __init__(self, database: DatabaseInterface | None = None):
        """Initialize the queue service.
        
        Args:
            database: Database interface implementation. If None, uses SQLiteDatabase.
        """
        self.database = database or SQLiteDatabase()
        self._initialized = False
        
        # Initialize the database
        if not self.database.initialize():
            raise QueueServiceError("Failed to initialize database")
        
        # Initialize archive service
        self.archive_service = ArchiveService(self.database)
        
        self._initialized = True
        logger.info("Queue service initialized successfully")

    @with_error_handling(error_type=QueueServiceError, operation="add_workflow")
    def add_workflow(
        self, workflow_data: dict[str, Any], workflow_name: str = ""
    ) -> str:
        """Add a workflow to the queue and return the item ID.
        
        Args:
            workflow_data: The workflow data to be executed
            workflow_name: Optional name for the workflow
            
        Returns:
            The ID of the created queue item
            
        Raises:
            QueueServiceError: If the workflow cannot be added
        """
        if not self._initialized:
            raise QueueServiceError("Queue service not initialized", operation="add_workflow")
        
        if not workflow_data:
            raise ValidationError("Workflow data cannot be empty", field="workflow_data")
        
        if not isinstance(workflow_data, dict):
            raise ValidationError("Workflow data must be a dictionary", field="workflow_data", value=type(workflow_data).__name__)
        
        # Create a new queue item
        item = QueueItem(
            workflow_name=workflow_name or f"Workflow {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            workflow_data=workflow_data,
            status=QueueStatus.PENDING
        )
        
        # Save to database
        if not self.database.create_queue_item(item):
            raise QueueServiceError(f"Failed to create queue item {item.id}", item_id=item.id, operation="create")
        
        logger.info(f"Added workflow to queue: {item.id} - {item.workflow_name}")
        return item.id

    @with_error_handling(error_type=QueueServiceError, operation="get_queue_items")
    def get_queue_items(self, status: QueueStatus | None = None) -> list[QueueItem]:
        """Get queue items, optionally filtered by status.
        
        Args:
            status: Optional status filter
            
        Returns:
            List of queue items
        """
        if not self._initialized:
            raise QueueServiceError("Queue service not initialized", operation="get_queue_items")
        
        if status is not None:
            return self.database.get_items_by_status(status)
        else:
            return self.database.get_all_queue_items()

    def get_queue_item(self, item_id: str) -> QueueItem | None:
        """Get a specific queue item by ID.
        
        Args:
            item_id: The ID of the queue item
            
        Returns:
            The queue item or None if not found
        """
        if not self._initialized:
            raise QueueServiceError("Queue service not initialized")
        
        if not item_id:
            raise QueueServiceError("Item ID cannot be empty")
        
        try:
            return self.database.get_queue_item(item_id)
        except Exception as e:
            logger.error(f"Failed to get queue item {item_id}: {e}")
            raise QueueServiceError(f"Failed to get queue item: {e}") from e

    def update_item_status(
        self,
        item_id: str,
        status: QueueStatus,
        error_message: str | None = None,
        result_data: dict[str, Any] | None = None,
    ) -> bool:
        """Update the status of a queue item.
        
        Args:
            item_id: The ID of the queue item
            status: The new status
            error_message: Optional error message for failed items
            result_data: Optional result data for completed items
            
        Returns:
            True if the update was successful
            
        Raises:
            QueueServiceError: If the item cannot be updated
        """
        if not self._initialized:
            raise QueueServiceError("Queue service not initialized")
        
        if not item_id:
            raise QueueServiceError("Item ID cannot be empty")
        
        # Get the existing item
        item = self.database.get_queue_item(item_id)
        if not item:
            raise QueueServiceError(f"Queue item {item_id} not found")
        
        # Update the item properties
        old_status = item.status
        item.status = status
        item.error_message = error_message
        item.result_data = result_data
        
        # Set timestamps based on status
        now = datetime.now(timezone.utc)
        if status == QueueStatus.RUNNING and old_status == QueueStatus.PENDING:
            item.started_at = now
        elif status in (QueueStatus.COMPLETED, QueueStatus.FAILED):
            if not item.started_at:
                item.started_at = now
            item.completed_at = now
        
        # Save to database
        if not self.database.update_queue_item(item):
            raise QueueServiceError(f"Failed to update queue item {item_id}")
        
        logger.info(f"Updated queue item {item_id} status: {old_status.value} -> {status.value}")
        return True

    def archive_items(self, item_ids: list[str]) -> bool:
        """Archive the specified queue items.
        
        Args:
            item_ids: List of item IDs to archive
            
        Returns:
            True if all items were archived successfully
            
        Raises:
            QueueServiceError: If items cannot be archived
        """
        if not self._initialized:
            raise QueueServiceError("Queue service not initialized")
        
        if not item_ids:
            return True
        
        try:
            archived_count = self.archive_service.bulk_archive_by_ids(item_ids)
            return archived_count == len(item_ids)
        except Exception as e:
            logger.error(f"Failed to archive items: {e}")
            raise QueueServiceError(f"Failed to archive items: {e}") from e

    def restore_items(self, item_ids: list[str]) -> bool:
        """Restore archived queue items.
        
        Args:
            item_ids: List of item IDs to restore
            
        Returns:
            True if all items were restored successfully
            
        Raises:
            QueueServiceError: If items cannot be restored
        """
        if not self._initialized:
            raise QueueServiceError("Queue service not initialized")
        
        if not item_ids:
            return True
        
        try:
            restored_count = self.archive_service.bulk_restore_by_ids(item_ids)
            return restored_count == len(item_ids)
        except Exception as e:
            logger.error(f"Failed to restore items: {e}")
            raise QueueServiceError(f"Failed to restore items: {e}") from e

    def archive_items_by_status(self, statuses: list[QueueStatus]) -> int:
        """Archive all items with the specified statuses.
        
        Args:
            statuses: List of statuses to archive
            
        Returns:
            Number of items archived
            
        Raises:
            QueueServiceError: If archiving fails
        """
        if not self._initialized:
            raise QueueServiceError("Queue service not initialized")
        
        try:
            return self.archive_service.archive_items_by_status(statuses)
        except Exception as e:
            logger.error(f"Failed to archive items by status: {e}")
            raise QueueServiceError(f"Failed to archive items by status: {e}") from e

    def archive_items_by_age(self, days_old: int, statuses: list[QueueStatus] | None = None) -> int:
        """Archive items older than the specified number of days.
        
        Args:
            days_old: Number of days old items must be to archive
            statuses: Optional list of statuses to consider
            
        Returns:
            Number of items archived
            
        Raises:
            QueueServiceError: If archiving fails
        """
        if not self._initialized:
            raise QueueServiceError("Queue service not initialized")
        
        try:
            return self.archive_service.archive_items_by_age(days_old, statuses)
        except Exception as e:
            logger.error(f"Failed to archive items by age: {e}")
            raise QueueServiceError(f"Failed to archive items by age: {e}") from e

    def restore_items_by_pattern(self, workflow_name_pattern: str) -> int:
        """Restore archived items matching a workflow name pattern.
        
        Args:
            workflow_name_pattern: Pattern to match workflow names
            
        Returns:
            Number of items restored
            
        Raises:
            QueueServiceError: If restoration fails
        """
        if not self._initialized:
            raise QueueServiceError("Queue service not initialized")
        
        try:
            return self.archive_service.restore_items_by_pattern(workflow_name_pattern)
        except Exception as e:
            logger.error(f"Failed to restore items by pattern: {e}")
            raise QueueServiceError(f"Failed to restore items by pattern: {e}") from e

    def get_archive_statistics(self) -> dict[str, Any]:
        """Get statistics about archived items.
        
        Returns:
            Dictionary containing archive statistics
        """
        if not self._initialized:
            raise QueueServiceError("Queue service not initialized")
        
        return self.archive_service.get_archive_statistics()

    def cleanup_old_archived_items(self, days_old: int) -> int:
        """Permanently delete archived items older than specified days.
        
        Args:
            days_old: Number of days old archived items must be to delete
            
        Returns:
            Number of items deleted
            
        Raises:
            QueueServiceError: If cleanup fails
        """
        if not self._initialized:
            raise QueueServiceError("Queue service not initialized")
        
        try:
            return self.archive_service.cleanup_old_archived_items(days_old)
        except Exception as e:
            logger.error(f"Failed to cleanup old archived items: {e}")
            raise QueueServiceError(f"Failed to cleanup old archived items: {e}") from e

    def delete_items(self, item_ids: list[str]) -> bool:
        """Delete the specified queue items.
        
        Args:
            item_ids: List of item IDs to delete
            
        Returns:
            True if all items were deleted successfully
            
        Raises:
            QueueServiceError: If items cannot be deleted
        """
        if not self._initialized:
            raise QueueServiceError("Queue service not initialized")
        
        if not item_ids:
            return True
        
        # Validate that no items are currently running
        for item_id in item_ids:
            item = self.database.get_queue_item(item_id)
            if item and item.status == QueueStatus.RUNNING:
                raise QueueServiceError(f"Cannot delete running item {item_id}")
        
        # Delete all items
        deleted_count = 0
        for item_id in item_ids:
            if self.database.delete_queue_item(item_id):
                deleted_count += 1
        
        if deleted_count != len(item_ids):
            logger.warning(f"Only deleted {deleted_count} out of {len(item_ids)} items")
        
        logger.info(f"Deleted {deleted_count} queue items")
        return deleted_count > 0

    def pause_queue(self) -> bool:
        """Pause queue processing.
        
        Returns:
            True if the queue was paused successfully
            
        Raises:
            QueueServiceError: If the queue cannot be paused
        """
        if not self._initialized:
            raise QueueServiceError("Queue service not initialized")
        
        try:
            if not self.database.set_config("queue_state", json.dumps(QueueState.PAUSED.value)):
                raise QueueServiceError("Failed to update queue state in database")
            
            logger.info("Queue processing paused")
            return True
        except Exception as e:
            logger.error(f"Failed to pause queue: {e}")
            raise QueueServiceError(f"Failed to pause queue: {e}") from e

    def resume_queue(self) -> bool:
        """Resume queue processing.
        
        Returns:
            True if the queue was resumed successfully
            
        Raises:
            QueueServiceError: If the queue cannot be resumed
        """
        if not self._initialized:
            raise QueueServiceError("Queue service not initialized")
        
        try:
            if not self.database.set_config("queue_state", json.dumps(QueueState.RUNNING.value)):
                raise QueueServiceError("Failed to update queue state in database")
            
            logger.info("Queue processing resumed")
            return True
        except Exception as e:
            logger.error(f"Failed to resume queue: {e}")
            raise QueueServiceError(f"Failed to resume queue: {e}") from e

    def get_queue_state(self) -> QueueState:
        """Get the current queue processing state.
        
        Returns:
            The current queue state
        """
        if not self._initialized:
            raise QueueServiceError("Queue service not initialized")
        
        try:
            state_value = self.database.get_config("queue_state")
            if state_value:
                return QueueState(json.loads(state_value))
            else:
                # Default to running if not set
                return QueueState.RUNNING
        except Exception as e:
            logger.error(f"Failed to get queue state: {e}")
            # Return default state on error
            return QueueState.RUNNING

    def export_queue(self, item_ids: list[str] | None = None) -> dict[str, Any]:
        """Export queue items to a dictionary format.
        
        Args:
            item_ids: Optional list of specific item IDs to export. If None, exports all items.
            
        Returns:
            Dictionary containing the exported queue data
            
        Raises:
            QueueServiceError: If the export fails
        """
        if not self._initialized:
            raise QueueServiceError("Queue service not initialized")
        
        try:
            if item_ids:
                # Export specific items
                items = []
                for item_id in item_ids:
                    item = self.database.get_queue_item(item_id)
                    if item:
                        items.append(item)
            else:
                # Export all items
                items = self.database.get_all_queue_items()
            
            # Convert items to dictionary format
            export_data = {
                "version": "1.0",
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "items": [item.to_dict() for item in items],
                "config": self.get_config().to_dict()
            }
            
            logger.info(f"Exported {len(items)} queue items")
            return export_data
        except Exception as e:
            logger.error(f"Failed to export queue: {e}")
            raise QueueServiceError(f"Failed to export queue: {e}") from e

    def import_queue(self, queue_data: dict[str, Any], merge: bool = True) -> bool:
        """Import queue items from a dictionary format.
        
        Args:
            queue_data: Dictionary containing the queue data to import
            merge: If True, merge with existing items. If False, replace existing items.
            
        Returns:
            True if the import was successful
            
        Raises:
            QueueServiceError: If the import fails
        """
        if not self._initialized:
            raise QueueServiceError("Queue service not initialized")
        
        if not queue_data or "items" not in queue_data:
            raise QueueServiceError("Invalid queue data format")
        
        try:
            items_data = queue_data["items"]
            imported_count = 0
            skipped_count = 0
            
            for item_data in items_data:
                try:
                    item = QueueItem.from_dict(item_data)
                    
                    # Check if item already exists when merging
                    if merge:
                        existing_item = self.database.get_queue_item(item.id)
                        if existing_item:
                            logger.debug(f"Skipping existing item {item.id}")
                            skipped_count += 1
                            continue
                    
                    # Create the item
                    if self.database.create_queue_item(item):
                        imported_count += 1
                    else:
                        logger.warning(f"Failed to import item {item.id}")
                        
                except Exception as e:
                    logger.error(f"Failed to import item: {e}")
                    continue
            
            logger.info(f"Imported {imported_count} items, skipped {skipped_count} items")
            return imported_count > 0 or skipped_count > 0
            
        except Exception as e:
            logger.error(f"Failed to import queue: {e}")
            raise QueueServiceError(f"Failed to import queue: {e}") from e

    def filter_items(self, filter_criteria: QueueFilter) -> list[QueueItem]:
        """Filter queue items based on criteria.
        
        Args:
            filter_criteria: The filter criteria to apply
            
        Returns:
            List of filtered queue items
            
        Raises:
            QueueServiceError: If the filtering fails
        """
        if not self._initialized:
            raise QueueServiceError("Queue service not initialized")
        
        try:
            # Validate the filter criteria
            FilterService.validate_filter(filter_criteria)
            
            # Use database filtering first for performance
            items = self.database.filter_queue_items(filter_criteria)
            
            # Apply additional client-side filtering if needed
            items = FilterService.apply_client_side_filter(items, filter_criteria)
            
            return items
        except Exception as e:
            logger.error(f"Failed to filter queue items: {e}")
            raise QueueServiceError(f"Failed to filter queue items: {e}") from e

    def search_items(self, search_query: str) -> list[QueueItem]:
        """Search queue items using a query string.
        
        Args:
            search_query: Search query string (supports advanced syntax)
            
        Returns:
            List of matching queue items
            
        Raises:
            QueueServiceError: If the search fails
        """
        if not self._initialized:
            raise QueueServiceError("Queue service not initialized")
        
        if not search_query or not search_query.strip():
            return self.get_queue_items()
        
        try:
            # Build filter from search query
            filter_criteria = FilterService.build_filter_from_query(search_query)
            
            # Apply the filter
            return self.filter_items(filter_criteria)
        except Exception as e:
            logger.error(f"Failed to search queue items: {e}")
            raise QueueServiceError(f"Failed to search queue items: {e}") from e

    def get_config(self) -> QueueConfig:
        """Get the current queue configuration.
        
        Returns:
            The current queue configuration
        """
        if not self._initialized:
            raise QueueServiceError("Queue service not initialized")
        
        try:
            config = QueueConfig()
            
            # Load configuration from database
            for key in ["queue_state", "max_concurrent_workflows", "auto_archive_completed", "auto_archive_days"]:
                value = self.database.get_config(key)
                if value:
                    parsed_value = json.loads(value)
                    if key == "queue_state":
                        config.queue_state = QueueState(parsed_value)
                    elif key == "max_concurrent_workflows":
                        config.max_concurrent_workflows = parsed_value
                    elif key == "auto_archive_completed":
                        config.auto_archive_completed = parsed_value
                    elif key == "auto_archive_days":
                        config.auto_archive_days = parsed_value
            
            return config
        except Exception as e:
            logger.error(f"Failed to get config: {e}")
            # Return default config on error
            return QueueConfig()

    def update_config(self, config: QueueConfig) -> bool:
        """Update the queue configuration.
        
        Args:
            config: The new configuration
            
        Returns:
            True if the configuration was updated successfully
            
        Raises:
            QueueServiceError: If the configuration cannot be updated
        """
        if not self._initialized:
            raise QueueServiceError("Queue service not initialized")
        
        try:
            config_dict = config.to_dict()
            
            # Save each configuration value
            for key, value in config_dict.items():
                if not self.database.set_config(key, json.dumps(value)):
                    raise QueueServiceError(f"Failed to update config key: {key}")
            
            logger.info("Queue configuration updated successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to update config: {e}")
            raise QueueServiceError(f"Failed to update config: {e}") from e

    def close(self) -> None:
        """Close the queue service and cleanup resources."""
        if self.database:
            self.database.close()
        self._initialized = False
        logger.info("Queue service closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()