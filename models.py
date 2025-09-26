"""
Core data models and enums for the ComfyUI Queue Manager.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
import uuid


class QueueStatus(Enum):
    """Enumeration of possible queue item statuses."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"


class QueueState(Enum):
    """Enumeration of queue processing states."""

    RUNNING = "running"
    PAUSED = "paused"


@dataclass
class QueueItem:
    """Data model for a queue item representing a workflow execution."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    workflow_name: str = ""
    workflow_data: dict[str, Any] = field(default_factory=dict)
    status: QueueStatus = QueueStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
    result_data: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert the queue item to a dictionary for serialization."""
        return {
            "id": self.id,
            "workflow_name": self.workflow_name,
            "workflow_data": self.workflow_data,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat()
            if self.completed_at
            else None,
            "error_message": self.error_message,
            "result_data": self.result_data,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> QueueItem:
        """Create a QueueItem from a dictionary."""
        item = cls()
        item.id = data.get("id", str(uuid.uuid4()))
        item.workflow_name = data.get("workflow_name", "")
        item.workflow_data = data.get("workflow_data", {})
        item.status = QueueStatus(data.get("status", QueueStatus.PENDING.value))
        item.created_at = (
            datetime.fromisoformat(data["created_at"])
            if data.get("created_at")
            else datetime.now(timezone.utc)
        )
        item.updated_at = (
            datetime.fromisoformat(data["updated_at"])
            if data.get("updated_at")
            else datetime.now(timezone.utc)
        )
        item.started_at = (
            datetime.fromisoformat(data["started_at"])
            if data.get("started_at")
            else None
        )
        item.completed_at = (
            datetime.fromisoformat(data["completed_at"])
            if data.get("completed_at")
            else None
        )
        item.error_message = data.get("error_message")
        item.result_data = data.get("result_data")
        return item


@dataclass
class QueueFilter:
    """Data model for filtering queue items."""

    status: list[QueueStatus] | None = None
    workflow_name: str | None = None
    date_range: tuple[datetime, datetime] | None = None
    search_term: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert the filter to a dictionary."""
        return {
            "status": [s.value for s in self.status] if self.status else None,
            "workflow_name": self.workflow_name,
            "date_range": [d.isoformat() for d in self.date_range]
            if self.date_range
            else None,
            "search_term": self.search_term,
        }


@dataclass
class QueueConfig:
    """Configuration settings for the queue manager."""

    queue_state: QueueState = QueueState.RUNNING
    max_concurrent_workflows: int = 1
    auto_archive_completed: bool = False
    auto_archive_days: int = 30

    def to_dict(self) -> dict[str, Any]:
        """Convert the configuration to a dictionary."""
        return {
            "queue_state": self.queue_state.value,
            "max_concurrent_workflows": self.max_concurrent_workflows,
            "auto_archive_completed": self.auto_archive_completed,
            "auto_archive_days": self.auto_archive_days,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> QueueConfig:
        """Create a QueueConfig from a dictionary."""
        config = cls()
        config.queue_state = QueueState(
            data.get("queue_state", QueueState.RUNNING.value)
        )
        config.max_concurrent_workflows = data.get("max_concurrent_workflows", 1)
        config.auto_archive_completed = data.get("auto_archive_completed", False)
        config.auto_archive_days = data.get("auto_archive_days", 30)
        return config
