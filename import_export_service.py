"""
Import/export service for queue data file operations.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from models import QueueItem, QueueStatus
from serialization_service import QueueDataSerializer, SerializationError, ValidationError


class ImportExportError(Exception):
    """Exception raised when import/export operations fail."""

    pass


class QueueImportExportService:
    """Handles file-based import and export operations for queue data."""

    def __init__(self, serializer: QueueDataSerializer | None = None):
        """
        Initialize the import/export service.
        
        Args:
            serializer: Optional serializer instance. If None, creates a new one.
        """
        self.serializer = serializer or QueueDataSerializer()

    def export_to_file(
        self,
        items: list[QueueItem],
        file_path: str | Path,
        overwrite: bool = False
    ) -> bool:
        """
        Export queue items to a file.
        
        Args:
            items: List of QueueItem objects to export
            file_path: Path where to save the export file
            overwrite: Whether to overwrite existing files
            
        Returns:
            True if export was successful
            
        Raises:
            ImportExportError: If export fails
        """
        try:
            file_path = Path(file_path)
            
            # Check if file exists and overwrite is not allowed
            if file_path.exists() and not overwrite:
                raise ImportExportError(
                    f"File already exists: {file_path}. Use overwrite=True to replace it."
                )
            
            # Create directory if it doesn't exist
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Serialize items to JSON
            json_data = self.serializer.serialize_to_json(items, indent=2)
            
            # Write to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(json_data)
            
            return True
            
        except (OSError, IOError) as e:
            raise ImportExportError(f"Failed to write file {file_path}: {str(e)}") from e
        except SerializationError as e:
            raise ImportExportError(f"Failed to serialize queue data: {str(e)}") from e

    def import_from_file(
        self,
        file_path: str | Path,
        merge: bool = True,
        existing_items: list[QueueItem] | None = None
    ) -> list[QueueItem]:
        """
        Import queue items from a file.
        
        Args:
            file_path: Path to the file to import
            merge: Whether to merge with existing items (avoid duplicates)
            existing_items: List of existing items for merge logic
            
        Returns:
            List of imported QueueItem objects
            
        Raises:
            ImportExportError: If import fails
        """
        try:
            file_path = Path(file_path)
            
            # Check if file exists
            if not file_path.exists():
                raise ImportExportError(f"Import file not found: {file_path}")
            
            # Check if file is readable
            if not os.access(file_path, os.R_OK):
                raise ImportExportError(f"Cannot read file: {file_path}")
            
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                json_data = f.read()
            
            # Deserialize items
            imported_items = self.serializer.deserialize_from_json(json_data)
            
            # Apply merge logic if requested
            if merge and existing_items:
                imported_items = self._merge_items(imported_items, existing_items)
            
            return imported_items
            
        except (OSError, IOError) as e:
            raise ImportExportError(f"Failed to read file {file_path}: {str(e)}") from e
        except (SerializationError, ValidationError) as e:
            raise ImportExportError(f"Failed to deserialize queue data: {str(e)}") from e

    def export_filtered_items(
        self,
        items: list[QueueItem],
        file_path: str | Path,
        status_filter: list[QueueStatus] | None = None,
        name_filter: str | None = None,
        overwrite: bool = False
    ) -> bool:
        """
        Export filtered queue items to a file.
        
        Args:
            items: List of QueueItem objects to filter and export
            file_path: Path where to save the export file
            status_filter: Optional list of statuses to include
            name_filter: Optional workflow name pattern to match
            overwrite: Whether to overwrite existing files
            
        Returns:
            True if export was successful
            
        Raises:
            ImportExportError: If export fails
        """
        try:
            # Apply filters
            filtered_items = self._apply_filters(items, status_filter, name_filter)
            
            # Export filtered items
            return self.export_to_file(filtered_items, file_path, overwrite)
            
        except Exception as e:
            raise ImportExportError(f"Failed to export filtered items: {str(e)}") from e

    def get_file_info(self, file_path: str | Path) -> dict[str, Any]:
        """
        Get information about an import file without fully loading it.
        
        Args:
            file_path: Path to the file to inspect
            
        Returns:
            Dictionary containing file information
            
        Raises:
            ImportExportError: If file inspection fails
        """
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                raise ImportExportError(f"File not found: {file_path}")
            
            # Get file stats
            stat = file_path.stat()
            
            # Read and parse just the metadata
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Validate basic structure
            self.serializer._validate_queue_data(data)
            
            return {
                "file_path": str(file_path),
                "file_size": stat.st_size,
                "modified_time": stat.st_mtime,
                "data_version": data.get("version"),
                "export_timestamp": data.get("timestamp"),
                "item_count": data.get("count", len(data.get("items", []))),
                "supported": data.get("version") in self.serializer.get_supported_versions()
            }
            
        except (OSError, IOError) as e:
            raise ImportExportError(f"Failed to read file {file_path}: {str(e)}") from e
        except json.JSONDecodeError as e:
            raise ImportExportError(f"Invalid JSON in file {file_path}: {str(e)}") from e
        except ValidationError as e:
            raise ImportExportError(f"Invalid queue data format: {str(e)}") from e

    def _merge_items(
        self,
        imported_items: list[QueueItem],
        existing_items: list[QueueItem]
    ) -> list[QueueItem]:
        """
        Merge imported items with existing items, avoiding duplicates.
        
        Args:
            imported_items: Items being imported
            existing_items: Items that already exist
            
        Returns:
            List of items to actually import (duplicates removed)
        """
        # Create set of existing item IDs for fast lookup
        existing_ids = {item.id for item in existing_items}
        
        # Filter out items that already exist
        unique_items = []
        duplicate_count = 0
        
        for item in imported_items:
            if item.id not in existing_ids:
                unique_items.append(item)
            else:
                duplicate_count += 1
        
        # Log information about duplicates (could be enhanced with proper logging)
        if duplicate_count > 0:
            print(f"Skipped {duplicate_count} duplicate items during import")
        
        return unique_items

    def _apply_filters(
        self,
        items: list[QueueItem],
        status_filter: list[QueueStatus] | None = None,
        name_filter: str | None = None
    ) -> list[QueueItem]:
        """
        Apply filters to a list of queue items.
        
        Args:
            items: Items to filter
            status_filter: Optional list of statuses to include
            name_filter: Optional workflow name pattern to match
            
        Returns:
            Filtered list of items
        """
        filtered_items = items
        
        # Apply status filter
        if status_filter:
            filtered_items = [
                item for item in filtered_items
                if item.status in status_filter
            ]
        
        # Apply name filter (case-insensitive substring match)
        if name_filter:
            name_filter_lower = name_filter.lower()
            filtered_items = [
                item for item in filtered_items
                if name_filter_lower in item.workflow_name.lower()
            ]
        
        return filtered_items

    def validate_import_file(self, file_path: str | Path) -> tuple[bool, str]:
        """
        Validate an import file without importing it.
        
        Args:
            file_path: Path to the file to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            self.get_file_info(file_path)
            return True, ""
        except ImportExportError as e:
            return False, str(e)

    def create_backup(
        self,
        items: list[QueueItem],
        backup_dir: str | Path = "backups"
    ) -> str:
        """
        Create a timestamped backup of queue items.
        
        Args:
            items: Items to backup
            backup_dir: Directory to store backups
            
        Returns:
            Path to the created backup file
            
        Raises:
            ImportExportError: If backup creation fails
        """
        try:
            from datetime import datetime
            
            backup_dir = Path(backup_dir)
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Create timestamped filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = backup_dir / f"queue_backup_{timestamp}.json"
            
            # Export to backup file
            self.export_to_file(items, backup_file, overwrite=True)
            
            return str(backup_file)
            
        except Exception as e:
            raise ImportExportError(f"Failed to create backup: {str(e)}") from e