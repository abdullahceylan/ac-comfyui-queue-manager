"""
SQLite database implementation for the ComfyUI Queue Manager.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator

from error_handler import ErrorHandler, with_database_error_handling
from exceptions import ConnectionError, DatabaseError, SchemaError, ValidationError
from interfaces import DatabaseInterface
from logging_config import get_logger
from models import QueueConfig, QueueFilter, QueueItem, QueueStatus
from performance_monitor import get_performance_monitor, time_function

logger = get_logger("database")


class SQLiteDatabase(DatabaseInterface):
    """SQLite implementation of the database interface."""

    # Database schema version for migrations
    SCHEMA_VERSION = 1
    
    # SQL statements for table creation
    CREATE_TABLES_SQL = """
    -- Queue Items Table
    CREATE TABLE IF NOT EXISTS queue_items (
        id TEXT PRIMARY KEY,
        workflow_name TEXT NOT NULL,
        workflow_data TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        started_at TEXT,
        completed_at TEXT,
        error_message TEXT,
        result_data TEXT
    );

    -- Queue Configuration Table
    CREATE TABLE IF NOT EXISTS queue_config (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );

    -- Schema Version Table
    CREATE TABLE IF NOT EXISTS schema_version (
        version INTEGER PRIMARY KEY
    );

    -- Indexes for better query performance
    CREATE INDEX IF NOT EXISTS idx_queue_items_status ON queue_items(status);
    CREATE INDEX IF NOT EXISTS idx_queue_items_created_at ON queue_items(created_at);
    CREATE INDEX IF NOT EXISTS idx_queue_items_workflow_name ON queue_items(workflow_name);
    """

    def __init__(self, db_path: str | Path = "queue_manager.db"):
        """Initialize the SQLite database.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = Path(db_path)
        self._connection_lock = threading.RLock()
        self._local = threading.local()
        self._initialized = False
        
        # Ensure the directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _get_connection(self) -> sqlite3.Connection:
        """Get a thread-local database connection."""
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            try:
                conn = sqlite3.connect(
                    str(self.db_path),
                    check_same_thread=False,
                    timeout=30.0,
                    isolation_level=None  # Autocommit mode
                )
                conn.row_factory = sqlite3.Row
                # Enable WAL mode for better concurrency
                conn.execute("PRAGMA journal_mode=WAL")
                # Enable foreign key constraints
                conn.execute("PRAGMA foreign_keys=ON")
                self._local.connection = conn
                logger.debug(f"Created new database connection for thread {threading.current_thread().name}")
            except sqlite3.Error as e:
                logger.error(f"Failed to connect to database: {e}")
                raise ErrorHandler.handle_database_error(e, "connect", context={"db_path": str(self.db_path)})
        
        return self._local.connection

    @contextmanager
    def _get_cursor(self) -> Generator[sqlite3.Cursor, None, None]:
        """Get a database cursor with automatic error handling."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
        except sqlite3.Error as e:
            logger.error(f"Database operation failed: {e}")
            try:
                conn.rollback()
            except sqlite3.Error as rollback_error:
                logger.error(f"Failed to rollback transaction: {rollback_error}")
            raise ErrorHandler.handle_database_error(e, "cursor_operation")
        finally:
            try:
                cursor.close()
            except sqlite3.Error as close_error:
                logger.warning(f"Failed to close cursor: {close_error}")

    @with_database_error_handling(operation="initialize")
    def initialize(self) -> bool:
        """Initialize the database and create tables if needed."""
        if self._initialized:
            return True
            
        with self._connection_lock:
            with self._get_cursor() as cursor:
                # Create all tables
                cursor.executescript(self.CREATE_TABLES_SQL)
                
                # Check and update schema version
                cursor.execute("SELECT version FROM schema_version LIMIT 1")
                result = cursor.fetchone()
                
                if result is None:
                    # First time setup
                    cursor.execute("INSERT INTO schema_version (version) VALUES (?)", (self.SCHEMA_VERSION,))
                    logger.info(f"Database initialized with schema version {self.SCHEMA_VERSION}")
                else:
                    current_version = result[0]
                    if current_version < self.SCHEMA_VERSION:
                        self._migrate_schema(cursor, current_version, self.SCHEMA_VERSION)
                    elif current_version > self.SCHEMA_VERSION:
                        logger.warning(f"Database schema version {current_version} is newer than expected {self.SCHEMA_VERSION}")
                        raise SchemaError(
                            f"Database schema version {current_version} is newer than expected {self.SCHEMA_VERSION}",
                            schema_version=current_version
                        )
                
                # Set default configuration if not exists
                self._initialize_default_config(cursor)
                
            self._initialized = True
            logger.info("Database initialization completed successfully")
            return True

    def _migrate_schema(self, cursor: sqlite3.Cursor, from_version: int, to_version: int) -> None:
        """Migrate database schema from one version to another."""
        logger.info(f"Migrating database schema from version {from_version} to {to_version}")
        
        # Add migration logic here as schema evolves
        # For now, we only have version 1, so no migrations needed
        
        cursor.execute("UPDATE schema_version SET version = ?", (to_version,))
        logger.info(f"Schema migration completed to version {to_version}")

    def _initialize_default_config(self, cursor: sqlite3.Cursor) -> None:
        """Initialize default configuration values."""
        default_config = QueueConfig()
        config_dict = default_config.to_dict()
        
        for key, value in config_dict.items():
            cursor.execute(
                "INSERT OR IGNORE INTO queue_config (key, value) VALUES (?, ?)",
                (key, json.dumps(value))
            )

    @with_database_error_handling(operation="INSERT", table="queue_items")
    @time_function("database.create_queue_item")
    def create_queue_item(self, item: QueueItem) -> bool:
        """Create a new queue item in the database."""
        # Validate item data
        if not item.id:
            raise ValidationError("Queue item ID cannot be empty", field="id")
        if not item.workflow_name:
            raise ValidationError("Workflow name cannot be empty", field="workflow_name")
        
        with self._get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO queue_items (
                    id, workflow_name, workflow_data, status, created_at, updated_at,
                    started_at, completed_at, error_message, result_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item.id,
                item.workflow_name,
                json.dumps(item.workflow_data),
                item.status.value,
                item.created_at.isoformat(),
                item.updated_at.isoformat(),
                item.started_at.isoformat() if item.started_at else None,
                item.completed_at.isoformat() if item.completed_at else None,
                item.error_message,
                json.dumps(item.result_data) if item.result_data else None
            ))
            logger.debug(f"Created queue item {item.id}")
            return True

    @with_database_error_handling(operation="SELECT", table="queue_items")
    @time_function("database.get_queue_item")
    def get_queue_item(self, item_id: str) -> QueueItem | None:
        """Retrieve a queue item by ID."""
        if not item_id:
            raise ValidationError("Item ID cannot be empty", field="item_id")
        
        with self._get_cursor() as cursor:
            cursor.execute("SELECT * FROM queue_items WHERE id = ?", (item_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_queue_item(row)
            return None

    @with_database_error_handling(operation="SELECT", table="queue_items")
    @time_function("database.get_all_queue_items")
    def get_all_queue_items(self) -> list[QueueItem]:
        """Retrieve all queue items."""
        with self._get_cursor() as cursor:
            cursor.execute("SELECT * FROM queue_items ORDER BY created_at DESC")
            rows = cursor.fetchall()
            return [self._row_to_queue_item(row) for row in rows]

    @with_database_error_handling(operation="UPDATE", table="queue_items")
    def update_queue_item(self, item: QueueItem) -> bool:
        """Update an existing queue item."""
        if not item.id:
            raise ValidationError("Queue item ID cannot be empty", field="id")
        
        # Update the updated_at timestamp
        item.updated_at = datetime.now(timezone.utc)
        
        with self._get_cursor() as cursor:
            cursor.execute("""
                UPDATE queue_items SET
                    workflow_name = ?, workflow_data = ?, status = ?, updated_at = ?,
                    started_at = ?, completed_at = ?, error_message = ?, result_data = ?
                WHERE id = ?
            """, (
                item.workflow_name,
                json.dumps(item.workflow_data),
                item.status.value,
                item.updated_at.isoformat(),
                item.started_at.isoformat() if item.started_at else None,
                item.completed_at.isoformat() if item.completed_at else None,
                item.error_message,
                json.dumps(item.result_data) if item.result_data else None,
                item.id
            ))
            
            if cursor.rowcount > 0:
                logger.debug(f"Updated queue item {item.id}")
                return True
            else:
                logger.warning(f"Queue item {item.id} not found for update")
                return False

    @with_database_error_handling(operation="DELETE", table="queue_items")
    def delete_queue_item(self, item_id: str) -> bool:
        """Delete a queue item by ID."""
        if not item_id:
            raise ValidationError("Item ID cannot be empty", field="item_id")
        
        with self._get_cursor() as cursor:
            cursor.execute("DELETE FROM queue_items WHERE id = ?", (item_id,))
            if cursor.rowcount > 0:
                logger.debug(f"Deleted queue item {item_id}")
                return True
            else:
                logger.warning(f"Queue item {item_id} not found for deletion")
                return False

    def get_items_by_status(self, status: QueueStatus) -> list[QueueItem]:
        """Retrieve queue items by status."""
        try:
            with self._get_cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM queue_items WHERE status = ? ORDER BY created_at DESC",
                    (status.value,)
                )
                rows = cursor.fetchall()
                return [self._row_to_queue_item(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get items by status {status}: {e}")
            return []

    def filter_queue_items(self, filter_criteria: QueueFilter) -> list[QueueItem]:
        """Filter queue items based on criteria."""
        try:
            query_parts = ["SELECT * FROM queue_items WHERE 1=1"]
            params = []

            if filter_criteria.status:
                placeholders = ",".join("?" * len(filter_criteria.status))
                query_parts.append(f"AND status IN ({placeholders})")
                params.extend([s.value for s in filter_criteria.status])

            if filter_criteria.workflow_name:
                query_parts.append("AND workflow_name LIKE ?")
                params.append(f"%{filter_criteria.workflow_name}%")

            if filter_criteria.date_range:
                start_date, end_date = filter_criteria.date_range
                query_parts.append("AND created_at BETWEEN ? AND ?")
                params.extend([start_date.isoformat(), end_date.isoformat()])

            if filter_criteria.search_term:
                query_parts.append("AND (workflow_name LIKE ? OR workflow_data LIKE ?)")
                search_param = f"%{filter_criteria.search_term}%"
                params.extend([search_param, search_param])

            query_parts.append("ORDER BY created_at DESC")
            query = " ".join(query_parts)

            with self._get_cursor() as cursor:
                cursor.execute(query, params)
                rows = cursor.fetchall()
                return [self._row_to_queue_item(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to filter queue items: {e}")
            return []

    def bulk_update_status(self, item_ids: list[str], status: QueueStatus) -> bool:
        """Update status for multiple items."""
        if not item_ids:
            return True

        try:
            placeholders = ",".join("?" * len(item_ids))
            updated_at = datetime.now(timezone.utc).isoformat()
            
            with self._get_cursor() as cursor:
                cursor.execute(f"""
                    UPDATE queue_items 
                    SET status = ?, updated_at = ?
                    WHERE id IN ({placeholders})
                """, [status.value, updated_at] + item_ids)
                
                logger.debug(f"Bulk updated {cursor.rowcount} items to status {status}")
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to bulk update status: {e}")
            return False

    def get_config(self, key: str) -> str | None:
        """Get a configuration value."""
        try:
            with self._get_cursor() as cursor:
                cursor.execute("SELECT value FROM queue_config WHERE key = ?", (key,))
                row = cursor.fetchone()
                return row[0] if row else None
        except Exception as e:
            logger.error(f"Failed to get config {key}: {e}")
            return None

    def set_config(self, key: str, value: str) -> bool:
        """Set a configuration value."""
        try:
            with self._get_cursor() as cursor:
                cursor.execute("""
                    INSERT OR REPLACE INTO queue_config (key, value) VALUES (?, ?)
                """, (key, value))
                logger.debug(f"Set config {key} = {value}")
                return True
        except Exception as e:
            logger.error(f"Failed to set config {key}: {e}")
            return False

    def close(self) -> None:
        """Close the database connection."""
        if hasattr(self._local, 'connection') and self._local.connection:
            try:
                self._local.connection.close()
                self._local.connection = None
                logger.debug("Database connection closed")
            except Exception as e:
                logger.error(f"Error closing database connection: {e}")

    def _row_to_queue_item(self, row: sqlite3.Row) -> QueueItem:
        """Convert a database row to a QueueItem object."""
        return QueueItem(
            id=row["id"],
            workflow_name=row["workflow_name"],
            workflow_data=json.loads(row["workflow_data"]) if row["workflow_data"] else {},
            status=QueueStatus(row["status"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
            error_message=row["error_message"],
            result_data=json.loads(row["result_data"]) if row["result_data"] else None
        )

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()