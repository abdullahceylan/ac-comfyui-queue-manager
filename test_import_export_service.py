"""
Unit tests for the import/export service.
"""

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from models import QueueItem, QueueStatus
from import_export_service import ImportExportError, QueueImportExportService
from serialization_service import QueueDataSerializer


class TestQueueImportExportService:
    """Test cases for QueueImportExportService."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = QueueImportExportService()
        
        # Create test queue items
        self.test_items = [
            QueueItem(
                id="test-id-1",
                workflow_name="Test Workflow 1",
                workflow_data={"nodes": [{"id": 1, "type": "input"}]},
                status=QueueStatus.COMPLETED,
                created_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                updated_at=datetime(2024, 1, 1, 12, 30, 0, tzinfo=timezone.utc),
                result_data={"output": "success"}
            ),
            QueueItem(
                id="test-id-2",
                workflow_name="Test Workflow 2",
                workflow_data={"nodes": [{"id": 2, "type": "process"}]},
                status=QueueStatus.FAILED,
                created_at=datetime(2024, 1, 2, 10, 0, 0, tzinfo=timezone.utc),
                updated_at=datetime(2024, 1, 2, 10, 15, 0, tzinfo=timezone.utc),
                error_message="Test error"
            )
        ]

    def test_init_with_custom_serializer(self):
        """Test initialization with custom serializer."""
        custom_serializer = Mock(spec=QueueDataSerializer)
        service = QueueImportExportService(custom_serializer)
        assert service.serializer is custom_serializer

    def test_init_with_default_serializer(self):
        """Test initialization with default serializer."""
        service = QueueImportExportService()
        assert isinstance(service.serializer, QueueDataSerializer)

    def test_export_to_file_success(self):
        """Test successful export to file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test_export.json"
            
            result = self.service.export_to_file(self.test_items, file_path)
            
            assert result is True
            assert file_path.exists()
            
            # Verify file content
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            assert data["version"] == "1.0.0"
            assert data["count"] == 2
            assert len(data["items"]) == 2

    def test_export_to_file_creates_directory(self):
        """Test that export creates parent directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "subdir" / "test_export.json"
            
            result = self.service.export_to_file(self.test_items, file_path)
            
            assert result is True
            assert file_path.exists()
            assert file_path.parent.exists()

    def test_export_to_file_overwrite_false(self):
        """Test export fails when file exists and overwrite is False."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test_export.json"
            
            # Create existing file
            file_path.write_text("existing content")
            
            with pytest.raises(ImportExportError, match="File already exists"):
                self.service.export_to_file(self.test_items, file_path, overwrite=False)

    def test_export_to_file_overwrite_true(self):
        """Test export succeeds when file exists and overwrite is True."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test_export.json"
            
            # Create existing file
            file_path.write_text("existing content")
            
            result = self.service.export_to_file(self.test_items, file_path, overwrite=True)
            
            assert result is True
            # Verify content was overwritten
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            assert data["count"] == 2

    def test_export_to_file_permission_error(self):
        """Test export handles permission errors."""
        with patch('builtins.open', side_effect=PermissionError("Permission denied")):
            with pytest.raises(ImportExportError, match="Failed to write file"):
                self.service.export_to_file(self.test_items, "/invalid/path.json")

    def test_import_from_file_success(self):
        """Test successful import from file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test_import.json"
            
            # First export to create a valid file
            self.service.export_to_file(self.test_items, file_path)
            
            # Then import it back
            imported_items = self.service.import_from_file(file_path)
            
            assert len(imported_items) == 2
            assert imported_items[0].id == "test-id-1"
            assert imported_items[0].workflow_name == "Test Workflow 1"
            assert imported_items[1].id == "test-id-2"
            assert imported_items[1].status == QueueStatus.FAILED

    def test_import_from_file_not_found(self):
        """Test import fails when file doesn't exist."""
        with pytest.raises(ImportExportError, match="Import file not found"):
            self.service.import_from_file("/nonexistent/file.json")

    def test_import_from_file_permission_error(self):
        """Test import handles permission errors."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test_import.json"
            file_path.write_text("{}")
            
            with patch('os.access', return_value=False):
                with pytest.raises(ImportExportError, match="Cannot read file"):
                    self.service.import_from_file(file_path)

    def test_import_from_file_invalid_json(self):
        """Test import handles invalid JSON."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "invalid.json"
            file_path.write_text("invalid json content")
            
            with pytest.raises(ImportExportError, match="Failed to deserialize"):
                self.service.import_from_file(file_path)

    def test_import_from_file_with_merge(self):
        """Test import with merge logic."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test_import.json"
            
            # Export test items
            self.service.export_to_file(self.test_items, file_path)
            
            # Create existing items (one duplicate, one unique)
            existing_items = [
                self.test_items[0],  # Duplicate
                QueueItem(id="existing-1", workflow_name="Existing")  # Unique
            ]
            
            # Import with merge
            imported_items = self.service.import_from_file(
                file_path, merge=True, existing_items=existing_items
            )
            
            # Should only import the non-duplicate item
            assert len(imported_items) == 1
            assert imported_items[0].id == "test-id-2"

    def test_import_from_file_without_merge(self):
        """Test import without merge logic."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test_import.json"
            
            # Export test items
            self.service.export_to_file(self.test_items, file_path)
            
            # Create existing items
            existing_items = [self.test_items[0]]
            
            # Import without merge
            imported_items = self.service.import_from_file(
                file_path, merge=False, existing_items=existing_items
            )
            
            # Should import all items regardless of duplicates
            assert len(imported_items) == 2

    def test_export_filtered_items_by_status(self):
        """Test export with status filter."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "filtered_export.json"
            
            result = self.service.export_filtered_items(
                self.test_items,
                file_path,
                status_filter=[QueueStatus.COMPLETED]
            )
            
            assert result is True
            
            # Verify only completed items were exported
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            assert data["count"] == 1
            assert data["items"][0]["status"] == "completed"

    def test_export_filtered_items_by_name(self):
        """Test export with name filter."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "filtered_export.json"
            
            result = self.service.export_filtered_items(
                self.test_items,
                file_path,
                name_filter="Workflow 1"
            )
            
            assert result is True
            
            # Verify only matching items were exported
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            assert data["count"] == 1
            assert "Workflow 1" in data["items"][0]["workflow_name"]

    def test_export_filtered_items_combined_filters(self):
        """Test export with combined filters."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "filtered_export.json"
            
            result = self.service.export_filtered_items(
                self.test_items,
                file_path,
                status_filter=[QueueStatus.FAILED],
                name_filter="Workflow 2"
            )
            
            assert result is True
            
            # Verify filtering worked
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            assert data["count"] == 1
            assert data["items"][0]["status"] == "failed"
            assert "Workflow 2" in data["items"][0]["workflow_name"]

    def test_get_file_info_success(self):
        """Test getting file information."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test_info.json"
            
            # Export test items
            self.service.export_to_file(self.test_items, file_path)
            
            info = self.service.get_file_info(file_path)
            
            assert info["file_path"] == str(file_path)
            assert info["file_size"] > 0
            assert info["data_version"] == "1.0.0"
            assert info["item_count"] == 2
            assert info["supported"] is True

    def test_get_file_info_not_found(self):
        """Test file info for non-existent file."""
        with pytest.raises(ImportExportError, match="File not found"):
            self.service.get_file_info("/nonexistent/file.json")

    def test_get_file_info_invalid_json(self):
        """Test file info for invalid JSON."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "invalid.json"
            file_path.write_text("invalid json")
            
            with pytest.raises(ImportExportError, match="Invalid JSON"):
                self.service.get_file_info(file_path)

    def test_validate_import_file_valid(self):
        """Test validation of valid import file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "valid.json"
            
            # Export test items to create valid file
            self.service.export_to_file(self.test_items, file_path)
            
            is_valid, error_msg = self.service.validate_import_file(file_path)
            
            assert is_valid is True
            assert error_msg == ""

    def test_validate_import_file_invalid(self):
        """Test validation of invalid import file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "invalid.json"
            file_path.write_text("invalid json")
            
            is_valid, error_msg = self.service.validate_import_file(file_path)
            
            assert is_valid is False
            assert "Invalid JSON" in error_msg

    def test_create_backup_success(self):
        """Test successful backup creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            backup_path = self.service.create_backup(self.test_items, temp_dir)
            
            assert backup_path.startswith(temp_dir)
            assert "queue_backup_" in backup_path
            assert backup_path.endswith(".json")
            
            # Verify backup file exists and contains data
            backup_file = Path(backup_path)
            assert backup_file.exists()
            
            with open(backup_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            assert data["count"] == 2

    def test_create_backup_creates_directory(self):
        """Test backup creation creates directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            backup_dir = Path(temp_dir) / "backups"
            
            backup_path = self.service.create_backup(self.test_items, backup_dir)
            
            assert backup_dir.exists()
            assert Path(backup_path).exists()

    def test_merge_items_removes_duplicates(self):
        """Test merge logic removes duplicates."""
        imported_items = [
            QueueItem(id="duplicate", workflow_name="Duplicate"),
            QueueItem(id="unique", workflow_name="Unique")
        ]
        existing_items = [
            QueueItem(id="duplicate", workflow_name="Existing Duplicate"),
            QueueItem(id="other", workflow_name="Other")
        ]
        
        merged = self.service._merge_items(imported_items, existing_items)
        
        assert len(merged) == 1
        assert merged[0].id == "unique"

    def test_apply_filters_status_only(self):
        """Test applying status filter only."""
        filtered = self.service._apply_filters(
            self.test_items,
            status_filter=[QueueStatus.COMPLETED]
        )
        
        assert len(filtered) == 1
        assert filtered[0].status == QueueStatus.COMPLETED

    def test_apply_filters_name_only(self):
        """Test applying name filter only."""
        filtered = self.service._apply_filters(
            self.test_items,
            name_filter="workflow 1"  # Case insensitive
        )
        
        assert len(filtered) == 1
        assert "Workflow 1" in filtered[0].workflow_name

    def test_apply_filters_combined(self):
        """Test applying combined filters."""
        filtered = self.service._apply_filters(
            self.test_items,
            status_filter=[QueueStatus.FAILED],
            name_filter="workflow 2"
        )
        
        assert len(filtered) == 1
        assert filtered[0].status == QueueStatus.FAILED
        assert "Workflow 2" in filtered[0].workflow_name

    def test_apply_filters_no_matches(self):
        """Test filters with no matches."""
        filtered = self.service._apply_filters(
            self.test_items,
            status_filter=[QueueStatus.PENDING]
        )
        
        assert len(filtered) == 0

    def test_roundtrip_export_import(self):
        """Test complete export-import roundtrip."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "roundtrip.json"
            
            # Export
            export_result = self.service.export_to_file(self.test_items, file_path)
            assert export_result is True
            
            # Import
            imported_items = self.service.import_from_file(file_path)
            
            # Verify data integrity
            assert len(imported_items) == len(self.test_items)
            
            for original, imported in zip(self.test_items, imported_items):
                assert original.id == imported.id
                assert original.workflow_name == imported.workflow_name
                assert original.workflow_data == imported.workflow_data
                assert original.status == imported.status
                assert original.created_at == imported.created_at
                assert original.updated_at == imported.updated_at
                assert original.error_message == imported.error_message
                assert original.result_data == imported.result_data