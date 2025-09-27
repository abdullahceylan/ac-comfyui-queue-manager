"""
Tests for error handling functionality in the ComfyUI Queue Manager.
"""

import json
import pytest
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch

from database import SQLiteDatabase
from error_handler import ErrorHandler, ErrorRecovery, with_database_error_handling
from exceptions import (
    APIError,
    ConnectionError,
    DatabaseError,
    NotFoundError,
    QueueManagerError,
    QueueServiceError,
    SchemaError,
    ValidationError,
    WorkflowExecutionError,
)
from models import QueueItem, QueueStatus
from queue_service import QueueService


class TestCustomExceptions:
    """Test custom exception classes."""
    
    def test_queue_manager_error_basic(self):
        """Test basic QueueManagerError functionality."""
        error = QueueManagerError("Test error")
        assert error.message == "Test error"
        assert error.error_code == "QueueManagerError"
        assert error.details == {}
        assert error.cause is None
    
    def test_queue_manager_error_with_details(self):
        """Test QueueManagerError with additional details."""
        details = {"key": "value", "number": 42}
        cause = ValueError("Original error")
        
        error = QueueManagerError(
            "Test error",
            error_code="CUSTOM_ERROR",
            details=details,
            cause=cause
        )
        
        assert error.message == "Test error"
        assert error.error_code == "CUSTOM_ERROR"
        assert error.details == details
        assert error.cause == cause
    
    def test_queue_manager_error_to_dict(self):
        """Test QueueManagerError serialization."""
        error = QueueManagerError(
            "Test error",
            error_code="TEST_ERROR",
            details={"field": "value"},
            cause=ValueError("Cause")
        )
        
        result = error.to_dict()
        
        assert result["error_type"] == "QueueManagerError"
        assert result["error_code"] == "TEST_ERROR"
        assert result["message"] == "Test error"
        assert result["details"] == {"field": "value"}
        assert result["cause"] == "Cause"
    
    def test_database_error_with_operation(self):
        """Test DatabaseError with operation details."""
        error = DatabaseError(
            "Database failed",
            operation="INSERT",
            table="queue_items"
        )
        
        assert error.message == "Database failed"
        assert error.details["operation"] == "INSERT"
        assert error.details["table"] == "queue_items"
    
    def test_validation_error_with_field(self):
        """Test ValidationError with field details."""
        error = ValidationError(
            "Invalid value",
            field="workflow_name",
            value="invalid"
        )
        
        assert error.message == "Invalid value"
        assert error.details["field"] == "workflow_name"
        assert error.details["value"] == "invalid"
    
    def test_api_error_with_status_code(self):
        """Test APIError with status code."""
        error = APIError(
            "API failed",
            status_code=404,
            endpoint="/api/items"
        )
        
        assert error.message == "API failed"
        assert error.details["status_code"] == 404
        assert error.details["endpoint"] == "/api/items"
    
    def test_workflow_execution_error(self):
        """Test WorkflowExecutionError with workflow details."""
        error = WorkflowExecutionError(
            "Execution failed",
            workflow_id="test-123",
            execution_stage="validation"
        )
        
        assert error.message == "Execution failed"
        assert error.details["workflow_id"] == "test-123"
        assert error.details["execution_stage"] == "validation"


class TestErrorHandler:
    """Test ErrorHandler utility functions."""
    
    def test_handle_database_error_sqlite_locked(self):
        """Test handling of SQLite database locked error."""
        original_error = sqlite3.OperationalError("database is locked")
        
        result = ErrorHandler.handle_database_error(
            original_error,
            "INSERT",
            "queue_items"
        )
        
        assert isinstance(result, ConnectionError)
        assert "Database is locked during INSERT" in result.message
        assert result.details["operation"] == "INSERT"
        assert result.details["table"] == "queue_items"
        assert result.cause == original_error
    
    def test_handle_database_error_no_such_table(self):
        """Test handling of SQLite no such table error."""
        original_error = sqlite3.OperationalError("no such table: missing_table")
        
        result = ErrorHandler.handle_database_error(
            original_error,
            "SELECT",
            "missing_table"
        )
        
        assert isinstance(result, SchemaError)
        assert "Table does not exist during SELECT" in result.message
        assert result.details["operation"] == "SELECT"
        assert result.details["table"] == "missing_table"
    
    def test_handle_database_error_integrity_error(self):
        """Test handling of SQLite integrity error."""
        original_error = sqlite3.IntegrityError("UNIQUE constraint failed")
        
        result = ErrorHandler.handle_database_error(
            original_error,
            "INSERT",
            "queue_items"
        )
        
        assert isinstance(result, ValidationError)
        assert "Data integrity violation during INSERT" in result.message
        assert result.details["operation"] == "INSERT"
        assert result.details["table"] == "queue_items"
    
    def test_handle_database_error_generic(self):
        """Test handling of generic database error."""
        original_error = Exception("Generic error")
        
        result = ErrorHandler.handle_database_error(
            original_error,
            "UPDATE",
            "queue_items"
        )
        
        assert isinstance(result, DatabaseError)
        assert "Unexpected error during UPDATE" in result.message
        assert result.details["operation"] == "UPDATE"
        assert result.details["table"] == "queue_items"
    
    def test_handle_api_error(self):
        """Test handling of API errors."""
        original_error = ValueError("Invalid input")
        
        result = ErrorHandler.handle_api_error(
            original_error,
            "/api/items",
            "POST"
        )
        
        assert isinstance(result, APIError)
        assert "API error at POST /api/items" in result.message
        assert result.details["endpoint"] == "/api/items"
        assert result.details["method"] == "POST"
        assert result.cause == original_error
    
    def test_handle_workflow_error(self):
        """Test handling of workflow execution errors."""
        original_error = RuntimeError("Execution failed")
        
        result = ErrorHandler.handle_workflow_error(
            original_error,
            workflow_id="test-123",
            stage="validation"
        )
        
        assert isinstance(result, WorkflowExecutionError)
        assert "Workflow execution failed" in result.message
        assert result.details["workflow_id"] == "test-123"
        assert result.details["execution_stage"] == "validation"
        assert result.cause == original_error


class TestErrorHandlingDecorators:
    """Test error handling decorators."""
    
    def test_with_database_error_handling_success(self):
        """Test database error handling decorator with successful operation."""
        @with_database_error_handling(operation="test_op", table="test_table")
        def successful_function():
            return "success"
        
        result = successful_function()
        assert result == "success"
    
    def test_with_database_error_handling_sqlite_error(self):
        """Test database error handling decorator with SQLite error."""
        @with_database_error_handling(operation="test_op", table="test_table")
        def failing_function():
            raise sqlite3.OperationalError("database is locked")
        
        with pytest.raises(ConnectionError) as exc_info:
            failing_function()
        
        error = exc_info.value
        assert "Database is locked during test_op" in error.message
        assert error.details["operation"] == "test_op"
        assert error.details["table"] == "test_table"
    
    def test_with_database_error_handling_generic_error(self):
        """Test database error handling decorator with generic error."""
        @with_database_error_handling(operation="test_op")
        def failing_function():
            raise ValueError("Generic error")
        
        with pytest.raises(DatabaseError) as exc_info:
            failing_function()
        
        error = exc_info.value
        assert "Unexpected error during test_op" in error.message
        assert error.details["operation"] == "test_op"
    
    def test_with_database_error_handling_reraise_queue_manager_error(self):
        """Test that QueueManagerError is re-raised as-is."""
        @with_database_error_handling(operation="test_op")
        def failing_function():
            raise ValidationError("Already a queue manager error")
        
        with pytest.raises(ValidationError) as exc_info:
            failing_function()
        
        error = exc_info.value
        assert error.message == "Already a queue manager error"


class TestErrorRecovery:
    """Test error recovery utilities."""
    
    def test_retry_with_backoff_success_first_try(self):
        """Test retry mechanism with success on first try."""
        call_count = 0
        
        def successful_function():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = ErrorRecovery.retry_with_backoff(successful_function, max_retries=3)
        
        assert result == "success"
        assert call_count == 1
    
    def test_retry_with_backoff_success_after_retries(self):
        """Test retry mechanism with success after retries."""
        call_count = 0
        
        def eventually_successful_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary error")
            return "success"
        
        with patch('time.sleep'):  # Mock sleep to speed up test
            result = ErrorRecovery.retry_with_backoff(
                eventually_successful_function,
                max_retries=3,
                base_delay=0.1
            )
        
        assert result == "success"
        assert call_count == 3
    
    def test_retry_with_backoff_all_retries_fail(self):
        """Test retry mechanism when all retries fail."""
        call_count = 0
        
        def always_failing_function():
            nonlocal call_count
            call_count += 1
            raise ValueError(f"Error {call_count}")
        
        with patch('time.sleep'):  # Mock sleep to speed up test
            with pytest.raises(ValueError) as exc_info:
                ErrorRecovery.retry_with_backoff(
                    always_failing_function,
                    max_retries=2,
                    base_delay=0.1
                )
        
        assert "Error 3" in str(exc_info.value)  # Last error
        assert call_count == 3  # Initial + 2 retries
    
    def test_safe_execute_success(self):
        """Test safe execution with successful function."""
        def successful_function():
            return "success"
        
        result = ErrorRecovery.safe_execute(successful_function)
        assert result == "success"
    
    def test_safe_execute_with_error(self):
        """Test safe execution with error and default value."""
        def failing_function():
            raise ValueError("Error")
        
        result = ErrorRecovery.safe_execute(failing_function, default_value="default")
        assert result == "default"
    
    def test_safe_execute_with_error_no_default(self):
        """Test safe execution with error and no default value."""
        def failing_function():
            raise ValueError("Error")
        
        result = ErrorRecovery.safe_execute(failing_function)
        assert result is None


class TestDatabaseErrorHandling:
    """Test error handling in database operations."""
    
    def setup_method(self):
        """Set up test database."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test.db"
        self.database = SQLiteDatabase(self.db_path)
    
    def teardown_method(self):
        """Clean up test database."""
        if hasattr(self, 'database'):
            self.database.close()
    
    def test_database_initialization_error_handling(self):
        """Test error handling during database initialization."""
        # Create a database with invalid path (directory instead of file)
        invalid_path = Path(self.temp_dir) / "invalid_dir"
        invalid_path.mkdir()
        
        database = SQLiteDatabase(invalid_path)
        
        # This should handle the error gracefully
        with pytest.raises(DatabaseError):
            database.initialize()
    
    def test_create_queue_item_validation_error(self):
        """Test validation error when creating queue item."""
        self.database.initialize()
        
        # Create item with empty ID
        item = QueueItem(id="", workflow_name="test")
        
        with pytest.raises(ValidationError) as exc_info:
            self.database.create_queue_item(item)
        
        error = exc_info.value
        assert "Queue item ID cannot be empty" in error.message
        assert error.details["field"] == "id"
    
    def test_get_queue_item_validation_error(self):
        """Test validation error when getting queue item."""
        self.database.initialize()
        
        with pytest.raises(ValidationError) as exc_info:
            self.database.get_queue_item("")
        
        error = exc_info.value
        assert "Item ID cannot be empty" in error.message
        assert error.details["field"] == "item_id"
    
    def test_database_connection_error_handling(self):
        """Test database connection error handling."""
        # Create database with invalid permissions
        invalid_db = SQLiteDatabase("/root/invalid.db")  # Should fail on most systems
        
        with pytest.raises(DatabaseError):
            invalid_db._get_connection()


class TestQueueServiceErrorHandling:
    """Test error handling in queue service operations."""
    
    def setup_method(self):
        """Set up test queue service."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test.db"
        self.database = SQLiteDatabase(self.db_path)
        self.database.initialize()
        self.queue_service = QueueService(self.database)
    
    def teardown_method(self):
        """Clean up test resources."""
        if hasattr(self, 'queue_service'):
            self.queue_service.close()
    
    def test_add_workflow_validation_error_empty_data(self):
        """Test validation error when adding workflow with empty data."""
        with pytest.raises(ValidationError) as exc_info:
            self.queue_service.add_workflow({})
        
        error = exc_info.value
        assert "Workflow data cannot be empty" in error.message
        assert error.details["field"] == "workflow_data"
    
    def test_add_workflow_validation_error_invalid_type(self):
        """Test validation error when adding workflow with invalid data type."""
        with pytest.raises(ValidationError) as exc_info:
            self.queue_service.add_workflow("not a dict")
        
        error = exc_info.value
        assert "Workflow data must be a dictionary" in error.message
        assert error.details["field"] == "workflow_data"
        assert error.details["value"] == "str"
    
    def test_queue_service_not_initialized_error(self):
        """Test error when using uninitialized queue service."""
        # Create service without initializing
        uninit_service = QueueService.__new__(QueueService)
        uninit_service._initialized = False
        
        with pytest.raises(QueueServiceError) as exc_info:
            uninit_service.add_workflow({"test": "data"})
        
        error = exc_info.value
        assert "Queue service not initialized" in error.message
        assert error.details["operation"] == "add_workflow"


class TestWorkflowExecutorErrorHandling:
    """Test error handling in workflow executor."""
    
    def setup_method(self):
        """Set up test workflow executor."""
        from workflow_executor import WorkflowExecutor
        self.executor = WorkflowExecutor()
    
    def teardown_method(self):
        """Clean up test resources."""
        if hasattr(self, 'executor'):
            self.executor.close()
    
    def test_execute_workflow_validation_error_empty_data(self):
        """Test validation error when executing workflow with empty data."""
        with pytest.raises(ValidationError) as exc_info:
            self.executor.execute_workflow({})
        
        error = exc_info.value
        assert "Workflow data cannot be empty" in error.message
        assert error.details["field"] == "workflow_data"
    
    def test_execute_workflow_validation_error_invalid_type(self):
        """Test validation error when executing workflow with invalid data type."""
        with pytest.raises(ValidationError) as exc_info:
            self.executor.execute_workflow("not a dict")
        
        error = exc_info.value
        assert "Workflow data must be a dictionary" in error.message
        assert error.details["field"] == "workflow_data"
        assert error.details["value"] == "str"


if __name__ == "__main__":
    pytest.main([__file__])