"""
Unit tests for the serialization service.
"""

import json
import pytest
from datetime import datetime, timezone
from unittest.mock import patch

from models import QueueItem, QueueStatus
from serialization_service import (
    QueueDataSerializer,
    SerializationError,
    ValidationError,
)


class TestQueueDataSerializer:
    """Test cases for QueueDataSerializer."""

    def setup_method(self):
        """Set up test fixtures."""
        self.serializer = QueueDataSerializer()
        
        # Create test queue items
        self.test_items = [
            QueueItem(
                id="test-id-1",
                workflow_name="Test Workflow 1",
                workflow_data={"nodes": [{"id": 1, "type": "input"}]},
                status=QueueStatus.COMPLETED,
                created_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                updated_at=datetime(2024, 1, 1, 12, 30, 0, tzinfo=timezone.utc),
                started_at=datetime(2024, 1, 1, 12, 5, 0, tzinfo=timezone.utc),
                completed_at=datetime(2024, 1, 1, 12, 25, 0, tzinfo=timezone.utc),
                result_data={"output": "success"}
            ),
            QueueItem(
                id="test-id-2",
                workflow_name="Test Workflow 2",
                workflow_data={"nodes": [{"id": 2, "type": "process"}]},
                status=QueueStatus.FAILED,
                created_at=datetime(2024, 1, 2, 10, 0, 0, tzinfo=timezone.utc),
                updated_at=datetime(2024, 1, 2, 10, 15, 0, tzinfo=timezone.utc),
                started_at=datetime(2024, 1, 2, 10, 5, 0, tzinfo=timezone.utc),
                error_message="Test error"
            )
        ]

    def test_serialize_queue_items_success(self):
        """Test successful serialization of queue items."""
        with patch('serialization_service.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 15, 14, 30, 0, tzinfo=timezone.utc)
            mock_datetime.timezone = timezone
            
            result = self.serializer.serialize_queue_items(self.test_items)
        
        assert result["version"] == "1.0.0"
        assert result["timestamp"] == "2024-01-15T14:30:00+00:00"
        assert result["count"] == 2
        assert len(result["items"]) == 2
        
        # Check first item
        item1 = result["items"][0]
        assert item1["id"] == "test-id-1"
        assert item1["workflow_name"] == "Test Workflow 1"
        assert item1["status"] == "completed"
        assert item1["result_data"] == {"output": "success"}
        
        # Check second item
        item2 = result["items"][1]
        assert item2["id"] == "test-id-2"
        assert item2["workflow_name"] == "Test Workflow 2"
        assert item2["status"] == "failed"
        assert item2["error_message"] == "Test error"

    def test_serialize_empty_list(self):
        """Test serialization of empty queue items list."""
        result = self.serializer.serialize_queue_items([])
        
        assert result["version"] == "1.0.0"
        assert result["count"] == 0
        assert result["items"] == []

    def test_serialize_queue_items_error(self):
        """Test serialization error handling."""
        # Create an item that will cause serialization to fail
        bad_item = QueueItem()
        bad_item.workflow_data = {"circular": None}
        bad_item.workflow_data["circular"] = bad_item.workflow_data  # Circular reference
        
        with pytest.raises(SerializationError):
            self.serializer.serialize_queue_items([bad_item])

    def test_deserialize_queue_items_success(self):
        """Test successful deserialization of queue items."""
        data = {
            "version": "1.0.0",
            "timestamp": "2024-01-15T14:30:00+00:00",
            "count": 2,
            "items": [
                {
                    "id": "test-id-1",
                    "workflow_name": "Test Workflow 1",
                    "workflow_data": {"nodes": [{"id": 1, "type": "input"}]},
                    "status": "completed",
                    "created_at": "2024-01-01T12:00:00+00:00",
                    "updated_at": "2024-01-01T12:30:00+00:00",
                    "started_at": "2024-01-01T12:05:00+00:00",
                    "completed_at": "2024-01-01T12:25:00+00:00",
                    "error_message": None,
                    "result_data": {"output": "success"}
                },
                {
                    "id": "test-id-2",
                    "workflow_name": "Test Workflow 2",
                    "workflow_data": {"nodes": [{"id": 2, "type": "process"}]},
                    "status": "failed",
                    "created_at": "2024-01-02T10:00:00+00:00",
                    "updated_at": "2024-01-02T10:15:00+00:00",
                    "started_at": "2024-01-02T10:05:00+00:00",
                    "completed_at": None,
                    "error_message": "Test error",
                    "result_data": None
                }
            ]
        }
        
        items = self.serializer.deserialize_queue_items(data)
        
        assert len(items) == 2
        
        # Check first item
        item1 = items[0]
        assert item1.id == "test-id-1"
        assert item1.workflow_name == "Test Workflow 1"
        assert item1.status == QueueStatus.COMPLETED
        assert item1.result_data == {"output": "success"}
        
        # Check second item
        item2 = items[1]
        assert item2.id == "test-id-2"
        assert item2.workflow_name == "Test Workflow 2"
        assert item2.status == QueueStatus.FAILED
        assert item2.error_message == "Test error"

    def test_deserialize_empty_items(self):
        """Test deserialization of empty items list."""
        data = {
            "version": "1.0.0",
            "timestamp": "2024-01-15T14:30:00+00:00",
            "count": 0,
            "items": []
        }
        
        items = self.serializer.deserialize_queue_items(data)
        assert len(items) == 0

    def test_serialize_to_json_success(self):
        """Test successful JSON serialization."""
        json_str = self.serializer.serialize_to_json(self.test_items)
        
        # Verify it's valid JSON
        data = json.loads(json_str)
        assert data["version"] == "1.0.0"
        assert data["count"] == 2
        assert len(data["items"]) == 2

    def test_serialize_to_json_with_indent(self):
        """Test JSON serialization with custom indentation."""
        json_str = self.serializer.serialize_to_json(self.test_items, indent=4)
        
        # Check that indentation is applied
        assert "    " in json_str  # 4-space indentation
        
        # Verify it's still valid JSON
        data = json.loads(json_str)
        assert data["version"] == "1.0.0"

    def test_deserialize_from_json_success(self):
        """Test successful JSON deserialization."""
        json_str = '''
        {
            "version": "1.0.0",
            "timestamp": "2024-01-15T14:30:00+00:00",
            "count": 1,
            "items": [
                {
                    "id": "test-id",
                    "workflow_name": "Test Workflow",
                    "workflow_data": {"test": "data"},
                    "status": "pending",
                    "created_at": "2024-01-01T12:00:00+00:00",
                    "updated_at": "2024-01-01T12:00:00+00:00",
                    "started_at": null,
                    "completed_at": null,
                    "error_message": null,
                    "result_data": null
                }
            ]
        }
        '''
        
        items = self.serializer.deserialize_from_json(json_str)
        
        assert len(items) == 1
        assert items[0].id == "test-id"
        assert items[0].workflow_name == "Test Workflow"
        assert items[0].status == QueueStatus.PENDING

    def test_deserialize_from_json_invalid_json(self):
        """Test JSON deserialization with invalid JSON."""
        invalid_json = '{"invalid": json}'
        
        with pytest.raises(SerializationError, match="Failed to decode JSON"):
            self.serializer.deserialize_from_json(invalid_json)

    def test_validate_queue_data_missing_version(self):
        """Test validation with missing version."""
        data = {"items": []}
        
        with pytest.raises(ValidationError, match="missing version information"):
            self.serializer._validate_queue_data(data)

    def test_validate_queue_data_unsupported_version(self):
        """Test validation with unsupported version."""
        data = {"version": "2.0.0", "items": []}
        
        with pytest.raises(ValidationError, match="Unsupported data format version"):
            self.serializer._validate_queue_data(data)

    def test_validate_queue_data_missing_items(self):
        """Test validation with missing items field."""
        data = {"version": "1.0.0"}
        
        with pytest.raises(ValidationError, match="missing 'items' field"):
            self.serializer._validate_queue_data(data)

    def test_validate_queue_data_items_not_list(self):
        """Test validation with items field not being a list."""
        data = {"version": "1.0.0", "items": "not a list"}
        
        with pytest.raises(ValidationError, match="'items' field must be a list"):
            self.serializer._validate_queue_data(data)

    def test_validate_queue_data_count_mismatch(self):
        """Test validation with count mismatch."""
        data = {
            "version": "1.0.0",
            "items": [{"test": "item"}],
            "count": 5
        }
        
        with pytest.raises(ValidationError, match="Item count mismatch"):
            self.serializer._validate_queue_data(data)

    def test_validate_item_data_not_dict(self):
        """Test item validation with non-dictionary data."""
        with pytest.raises(ValidationError, match="must be a dictionary"):
            self.serializer._validate_item_data("not a dict")

    def test_validate_item_data_missing_required_field(self):
        """Test item validation with missing required field."""
        item_data = {
            "id": "test-id",
            "workflow_name": "Test",
            "workflow_data": {}
            # Missing 'status' field
        }
        
        with pytest.raises(ValidationError, match="missing required field: status"):
            self.serializer._validate_item_data(item_data)

    def test_validate_item_data_invalid_status(self):
        """Test item validation with invalid status."""
        item_data = {
            "id": "test-id",
            "workflow_name": "Test",
            "workflow_data": {},
            "status": "invalid_status"
        }
        
        with pytest.raises(ValidationError, match="Invalid status"):
            self.serializer._validate_item_data(item_data)

    def test_validate_item_data_workflow_data_not_dict(self):
        """Test item validation with workflow_data not being a dictionary."""
        item_data = {
            "id": "test-id",
            "workflow_name": "Test",
            "workflow_data": "not a dict",
            "status": "pending"
        }
        
        with pytest.raises(ValidationError, match="'workflow_data' must be a dictionary"):
            self.serializer._validate_item_data(item_data)

    def test_validate_item_data_invalid_datetime(self):
        """Test item validation with invalid datetime format."""
        item_data = {
            "id": "test-id",
            "workflow_name": "Test",
            "workflow_data": {},
            "status": "pending",
            "created_at": "invalid-datetime"
        }
        
        with pytest.raises(ValidationError, match="Invalid datetime format"):
            self.serializer._validate_item_data(item_data)

    def test_get_supported_versions(self):
        """Test getting supported versions."""
        versions = self.serializer.get_supported_versions()
        assert "1.0.0" in versions
        assert isinstance(versions, list)

    def test_get_current_version(self):
        """Test getting current version."""
        version = self.serializer.get_current_version()
        assert version == "1.0.0"

    def test_roundtrip_serialization(self):
        """Test complete roundtrip serialization and deserialization."""
        # Serialize to JSON
        json_str = self.serializer.serialize_to_json(self.test_items)
        
        # Deserialize back to objects
        deserialized_items = self.serializer.deserialize_from_json(json_str)
        
        # Verify the data matches
        assert len(deserialized_items) == len(self.test_items)
        
        for original, deserialized in zip(self.test_items, deserialized_items):
            assert original.id == deserialized.id
            assert original.workflow_name == deserialized.workflow_name
            assert original.workflow_data == deserialized.workflow_data
            assert original.status == deserialized.status
            assert original.created_at == deserialized.created_at
            assert original.updated_at == deserialized.updated_at
            assert original.started_at == deserialized.started_at
            assert original.completed_at == deserialized.completed_at
            assert original.error_message == deserialized.error_message
            assert original.result_data == deserialized.result_data