"""
Queue data serialization service for import/export functionality.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from models import QueueConfig, QueueItem, QueueStatus


class SerializationError(Exception):
    """Exception raised when serialization/deserialization fails."""

    pass


class ValidationError(Exception):
    """Exception raised when data validation fails."""

    pass


class QueueDataSerializer:
    """Handles serialization and deserialization of queue data."""

    # Current data format version for compatibility
    CURRENT_VERSION = "1.0.0"
    SUPPORTED_VERSIONS = ["1.0.0"]

    def serialize_queue_items(self, items: list[QueueItem]) -> dict[str, Any]:
        """
        Serialize queue items to a dictionary format.
        
        Args:
            items: List of QueueItem objects to serialize
            
        Returns:
            Dictionary containing serialized queue data with version info
            
        Raises:
            SerializationError: If serialization fails
        """
        try:
            serialized_items = []
            for item in items:
                serialized_items.append(item.to_dict())
            
            return {
                "version": self.CURRENT_VERSION,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "items": serialized_items,
                "count": len(serialized_items)
            }
        except Exception as e:
            raise SerializationError(f"Failed to serialize queue items: {str(e)}") from e

    def deserialize_queue_items(self, data: dict[str, Any]) -> list[QueueItem]:
        """
        Deserialize queue items from dictionary format.
        
        Args:
            data: Dictionary containing serialized queue data
            
        Returns:
            List of QueueItem objects
            
        Raises:
            ValidationError: If data validation fails
            SerializationError: If deserialization fails
        """
        try:
            # Validate data format
            self._validate_queue_data(data)
            
            items = []
            for item_data in data.get("items", []):
                # Validate individual item data
                self._validate_item_data(item_data)
                items.append(QueueItem.from_dict(item_data))
            
            return items
        except ValidationError:
            raise
        except Exception as e:
            raise SerializationError(f"Failed to deserialize queue items: {str(e)}") from e

    def serialize_to_json(self, items: list[QueueItem], indent: int = 2) -> str:
        """
        Serialize queue items to JSON string.
        
        Args:
            items: List of QueueItem objects to serialize
            indent: JSON indentation level
            
        Returns:
            JSON string representation of queue data
            
        Raises:
            SerializationError: If JSON serialization fails
        """
        try:
            data = self.serialize_queue_items(items)
            return json.dumps(data, indent=indent, ensure_ascii=False)
        except json.JSONEncodeError as e:
            raise SerializationError(f"Failed to encode JSON: {str(e)}") from e

    def deserialize_from_json(self, json_str: str) -> list[QueueItem]:
        """
        Deserialize queue items from JSON string.
        
        Args:
            json_str: JSON string containing serialized queue data
            
        Returns:
            List of QueueItem objects
            
        Raises:
            ValidationError: If data validation fails
            SerializationError: If JSON deserialization fails
        """
        try:
            data = json.loads(json_str)
            return self.deserialize_queue_items(data)
        except json.JSONDecodeError as e:
            raise SerializationError(f"Failed to decode JSON: {str(e)}") from e

    def _validate_queue_data(self, data: dict[str, Any]) -> None:
        """
        Validate the structure and version of queue data.
        
        Args:
            data: Dictionary containing queue data to validate
            
        Raises:
            ValidationError: If validation fails
        """
        if not isinstance(data, dict):
            raise ValidationError("Queue data must be a dictionary")
        
        # Check version compatibility
        version = data.get("version")
        if not version:
            raise ValidationError("Queue data missing version information")
        
        if version not in self.SUPPORTED_VERSIONS:
            raise ValidationError(
                f"Unsupported data format version: {version}. "
                f"Supported versions: {', '.join(self.SUPPORTED_VERSIONS)}"
            )
        
        # Check required fields
        if "items" not in data:
            raise ValidationError("Queue data missing 'items' field")
        
        if not isinstance(data["items"], list):
            raise ValidationError("Queue data 'items' field must be a list")
        
        # Validate count if present
        if "count" in data:
            expected_count = data["count"]
            actual_count = len(data["items"])
            if expected_count != actual_count:
                raise ValidationError(
                    f"Item count mismatch: expected {expected_count}, got {actual_count}"
                )

    def _validate_item_data(self, item_data: dict[str, Any]) -> None:
        """
        Validate individual queue item data.
        
        Args:
            item_data: Dictionary containing item data to validate
            
        Raises:
            ValidationError: If validation fails
        """
        if not isinstance(item_data, dict):
            raise ValidationError("Queue item data must be a dictionary")
        
        # Check required fields
        required_fields = ["id", "workflow_name", "workflow_data", "status"]
        for field in required_fields:
            if field not in item_data:
                raise ValidationError(f"Queue item missing required field: {field}")
        
        # Validate status
        status = item_data.get("status")
        try:
            QueueStatus(status)
        except ValueError:
            valid_statuses = [s.value for s in QueueStatus]
            raise ValidationError(
                f"Invalid status '{status}'. Valid statuses: {', '.join(valid_statuses)}"
            )
        
        # Validate workflow_data is a dictionary
        if not isinstance(item_data.get("workflow_data"), dict):
            raise ValidationError("Queue item 'workflow_data' must be a dictionary")
        
        # Validate datetime fields if present
        datetime_fields = ["created_at", "updated_at", "started_at", "completed_at"]
        for field in datetime_fields:
            if field in item_data and item_data[field] is not None:
                try:
                    datetime.fromisoformat(item_data[field])
                except ValueError:
                    raise ValidationError(
                        f"Invalid datetime format for field '{field}': {item_data[field]}"
                    )

    def get_supported_versions(self) -> list[str]:
        """
        Get list of supported data format versions.
        
        Returns:
            List of supported version strings
        """
        return self.SUPPORTED_VERSIONS.copy()

    def get_current_version(self) -> str:
        """
        Get current data format version.
        
        Returns:
            Current version string
        """
        return self.CURRENT_VERSION