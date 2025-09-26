"""
Base interfaces for queue service and database operations.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from .models import QueueItem, QueueFilter, QueueConfig, QueueStatus, QueueState


class DatabaseInterface(ABC):
    """Abstract interface for database operations."""

    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the database and create tables if needed."""
        pass

    @abstractmethod
    def create_queue_item(self, item: QueueItem) -> bool:
        """Create a new queue item in the database."""
        pass

    @abstractmethod
    def get_queue_item(self, item_id: str) -> Optional[QueueItem]:
        """Retrieve a queue item by ID."""
        pass

    @abstractmethod
    def get_all_queue_items(self) -> List[QueueItem]:
        """Retrieve all queue items."""
        pass

    @abstractmethod
    def update_queue_item(self, item: QueueItem) -> bool:
        """Update an existing queue item."""
        pass

    @abstractmethod
    def delete_queue_item(self, item_id: str) -> bool:
        """Delete a queue item by ID."""
        pass

    @abstractmethod
    def get_items_by_status(self, status: QueueStatus) -> List[QueueItem]:
        """Retrieve queue items by status."""
        pass

    @abstractmethod
    def filter_queue_items(self, filter_criteria: QueueFilter) -> List[QueueItem]:
        """Filter queue items based on criteria."""
        pass

    @abstractmethod
    def bulk_update_status(self, item_ids: List[str], status: QueueStatus) -> bool:
        """Update status for multiple items."""
        pass

    @abstractmethod
    def get_config(self, key: str) -> Optional[str]:
        """Get a configuration value."""
        pass

    @abstractmethod
    def set_config(self, key: str, value: str) -> bool:
        """Set a configuration value."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close the database connection."""
        pass


class QueueServiceInterface(ABC):
    """Abstract interface for queue service operations."""

    @abstractmethod
    def add_workflow(self, workflow_data: Dict[str, Any], workflow_name: str = "") -> str:
        """Add a workflow to the queue and return the item ID."""
        pass

    @abstractmethod
    def get_queue_items(self, status: Optional[QueueStatus] = None) -> List[QueueItem]:
        """Get queue items, optionally filtered by status."""
        pass

    @abstractmethod
    def get_queue_item(self, item_id: str) -> Optional[QueueItem]:
        """Get a specific queue item by ID."""
        pass

    @abstractmethod
    def update_item_status(self, item_id: str, status: QueueStatus, 
                          error_message: Optional[str] = None,
                          result_data: Optional[Dict[str, Any]] = None) -> bool:
        """Update the status of a queue item."""
        pass

    @abstractmethod
    def archive_items(self, item_ids: List[str]) -> bool:
        """Archive the specified queue items."""
        pass

    @abstractmethod
    def restore_items(self, item_ids: List[str]) -> bool:
        """Restore archived queue items."""
        pass

    @abstractmethod
    def delete_items(self, item_ids: List[str]) -> bool:
        """Delete the specified queue items."""
        pass

    @abstractmethod
    def pause_queue(self) -> bool:
        """Pause queue processing."""
        pass

    @abstractmethod
    def resume_queue(self) -> bool:
        """Resume queue processing."""
        pass

    @abstractmethod
    def get_queue_state(self) -> QueueState:
        """Get the current queue processing state."""
        pass

    @abstractmethod
    def export_queue(self, item_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """Export queue items to a dictionary format."""
        pass

    @abstractmethod
    def import_queue(self, queue_data: Dict[str, Any], merge: bool = True) -> bool:
        """Import queue items from a dictionary format."""
        pass

    @abstractmethod
    def filter_items(self, filter_criteria: QueueFilter) -> List[QueueItem]:
        """Filter queue items based on criteria."""
        pass

    @abstractmethod
    def get_config(self) -> QueueConfig:
        """Get the current queue configuration."""
        pass

    @abstractmethod
    def update_config(self, config: QueueConfig) -> bool:
        """Update the queue configuration."""
        pass


class WorkflowExecutorInterface(ABC):
    """Abstract interface for workflow execution integration."""

    @abstractmethod
    def execute_workflow(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a workflow and return the results."""
        pass

    @abstractmethod
    def is_workflow_running(self, workflow_id: str) -> bool:
        """Check if a workflow is currently running."""
        pass

    @abstractmethod
    def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel a running workflow."""
        pass

    @abstractmethod
    def get_workflow_status(self, workflow_id: str) -> Optional[QueueStatus]:
        """Get the status of a workflow execution."""
        pass