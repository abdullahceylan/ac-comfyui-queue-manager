"""
Base interfaces for queue service and database operations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .models import QueueConfig, QueueFilter, QueueItem, QueueState, QueueStatus


class DatabaseInterface(ABC):
    """Abstract interface for database operations."""

    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the database and create tables if needed."""

    @abstractmethod
    def create_queue_item(self, item: QueueItem) -> bool:
        """Create a new queue item in the database."""

    @abstractmethod
    def get_queue_item(self, item_id: str) -> QueueItem | None:
        """Retrieve a queue item by ID."""

    @abstractmethod
    def get_all_queue_items(self) -> list[QueueItem]:
        """Retrieve all queue items."""

    @abstractmethod
    def update_queue_item(self, item: QueueItem) -> bool:
        """Update an existing queue item."""

    @abstractmethod
    def delete_queue_item(self, item_id: str) -> bool:
        """Delete a queue item by ID."""

    @abstractmethod
    def get_items_by_status(self, status: QueueStatus) -> list[QueueItem]:
        """Retrieve queue items by status."""

    @abstractmethod
    def filter_queue_items(self, filter_criteria: QueueFilter) -> list[QueueItem]:
        """Filter queue items based on criteria."""

    @abstractmethod
    def bulk_update_status(self, item_ids: list[str], status: QueueStatus) -> bool:
        """Update status for multiple items."""

    @abstractmethod
    def get_config(self, key: str) -> str | None:
        """Get a configuration value."""

    @abstractmethod
    def set_config(self, key: str, value: str) -> bool:
        """Set a configuration value."""

    @abstractmethod
    def close(self) -> None:
        """Close the database connection."""


class QueueServiceInterface(ABC):
    """Abstract interface for queue service operations."""

    @abstractmethod
    def add_workflow(
        self, workflow_data: dict[str, Any], workflow_name: str = ""
    ) -> str:
        """Add a workflow to the queue and return the item ID."""

    @abstractmethod
    def get_queue_items(self, status: QueueStatus | None = None) -> list[QueueItem]:
        """Get queue items, optionally filtered by status."""

    @abstractmethod
    def get_queue_item(self, item_id: str) -> QueueItem | None:
        """Get a specific queue item by ID."""

    @abstractmethod
    def update_item_status(
        self,
        item_id: str,
        status: QueueStatus,
        error_message: str | None = None,
        result_data: dict[str, Any] | None = None,
    ) -> bool:
        """Update the status of a queue item."""

    @abstractmethod
    def archive_items(self, item_ids: list[str]) -> bool:
        """Archive the specified queue items."""

    @abstractmethod
    def restore_items(self, item_ids: list[str]) -> bool:
        """Restore archived queue items."""

    @abstractmethod
    def delete_items(self, item_ids: list[str]) -> bool:
        """Delete the specified queue items."""

    @abstractmethod
    def pause_queue(self) -> bool:
        """Pause queue processing."""

    @abstractmethod
    def resume_queue(self) -> bool:
        """Resume queue processing."""

    @abstractmethod
    def get_queue_state(self) -> QueueState:
        """Get the current queue processing state."""

    @abstractmethod
    def export_queue(self, item_ids: list[str] | None = None) -> dict[str, Any]:
        """Export queue items to a dictionary format."""

    @abstractmethod
    def import_queue(self, queue_data: dict[str, Any], merge: bool = True) -> bool:
        """Import queue items from a dictionary format."""

    @abstractmethod
    def filter_items(self, filter_criteria: QueueFilter) -> list[QueueItem]:
        """Filter queue items based on criteria."""

    @abstractmethod
    def get_config(self) -> QueueConfig:
        """Get the current queue configuration."""

    @abstractmethod
    def update_config(self, config: QueueConfig) -> bool:
        """Update the queue configuration."""


class WorkflowExecutorInterface(ABC):
    """Abstract interface for workflow execution integration."""

    @abstractmethod
    def execute_workflow(self, workflow_data: dict[str, Any]) -> dict[str, Any]:
        """Execute a workflow and return the results."""

    @abstractmethod
    def is_workflow_running(self, workflow_id: str) -> bool:
        """Check if a workflow is currently running."""

    @abstractmethod
    def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel a running workflow."""

    @abstractmethod
    def get_workflow_status(self, workflow_id: str) -> QueueStatus | None:
        """Get the status of a workflow execution."""
