"""
Custom exception classes for the ComfyUI Queue Manager.
Provides structured error handling across all components.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


class QueueManagerError(Exception):
    """Base exception class for all queue manager errors."""
    
    def __init__(
        self, 
        message: str, 
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        """Initialize the exception.
        
        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            details: Additional error details
            cause: Original exception that caused this error
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        self.cause = cause
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the exception to a dictionary for serialization."""
        return {
            "error_type": self.__class__.__name__,
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
            "cause": str(self.cause) if self.cause else None
        }


class DatabaseError(QueueManagerError):
    """Exception raised for database-related errors."""
    
    def __init__(
        self, 
        message: str, 
        operation: Optional[str] = None,
        table: Optional[str] = None,
        **kwargs
    ):
        """Initialize the database error.
        
        Args:
            message: Error message
            operation: Database operation that failed (e.g., 'INSERT', 'UPDATE')
            table: Database table involved in the operation
            **kwargs: Additional arguments passed to parent
        """
        details = kwargs.get('details', {})
        if operation:
            details['operation'] = operation
        if table:
            details['table'] = table
        
        super().__init__(message, details=details, **kwargs)


class ConnectionError(DatabaseError):
    """Exception raised for database connection errors."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message, 
            error_code="DB_CONNECTION_ERROR",
            **kwargs
        )


class SchemaError(DatabaseError):
    """Exception raised for database schema-related errors."""
    
    def __init__(self, message: str, schema_version: Optional[int] = None, **kwargs):
        details = kwargs.get('details', {})
        if schema_version is not None:
            details['schema_version'] = schema_version
        
        super().__init__(
            message, 
            error_code="DB_SCHEMA_ERROR",
            details=details,
            **kwargs
        )


class ValidationError(QueueManagerError):
    """Exception raised for data validation errors."""
    
    def __init__(
        self, 
        message: str, 
        field: Optional[str] = None,
        value: Optional[Any] = None,
        **kwargs
    ):
        """Initialize the validation error.
        
        Args:
            message: Error message
            field: Field name that failed validation
            value: Value that failed validation
            **kwargs: Additional arguments passed to parent
        """
        details = kwargs.get('details', {})
        if field:
            details['field'] = field
        if value is not None:
            details['value'] = str(value)  # Convert to string for serialization
        
        super().__init__(
            message, 
            error_code="VALIDATION_ERROR",
            details=details,
            **kwargs
        )


class QueueServiceError(QueueManagerError):
    """Exception raised for queue service operations."""
    
    def __init__(
        self, 
        message: str, 
        item_id: Optional[str] = None,
        operation: Optional[str] = None,
        **kwargs
    ):
        """Initialize the queue service error.
        
        Args:
            message: Error message
            item_id: Queue item ID involved in the operation
            operation: Queue operation that failed
            **kwargs: Additional arguments passed to parent
        """
        details = kwargs.get('details', {})
        if item_id:
            details['item_id'] = item_id
        if operation:
            details['operation'] = operation
        
        super().__init__(
            message, 
            error_code="QUEUE_SERVICE_ERROR",
            details=details,
            **kwargs
        )


class WorkflowExecutionError(QueueManagerError):
    """Exception raised for workflow execution errors."""
    
    def __init__(
        self, 
        message: str, 
        workflow_id: Optional[str] = None,
        execution_stage: Optional[str] = None,
        **kwargs
    ):
        """Initialize the workflow execution error.
        
        Args:
            message: Error message
            workflow_id: Workflow ID that failed
            execution_stage: Stage of execution where error occurred
            **kwargs: Additional arguments passed to parent
        """
        details = kwargs.get('details', {})
        if workflow_id:
            details['workflow_id'] = workflow_id
        if execution_stage:
            details['execution_stage'] = execution_stage
        
        super().__init__(
            message, 
            error_code="WORKFLOW_EXECUTION_ERROR",
            details=details,
            **kwargs
        )


class TimeoutError(QueueManagerError):
    """Exception raised for timeout-related errors."""
    
    def __init__(
        self, 
        message: str, 
        timeout_seconds: Optional[float] = None,
        operation: Optional[str] = None,
        **kwargs
    ):
        """Initialize the timeout error.
        
        Args:
            message: Error message
            timeout_seconds: Timeout value that was exceeded
            operation: Operation that timed out
            **kwargs: Additional arguments passed to parent
        """
        details = kwargs.get('details', {})
        if timeout_seconds is not None:
            details['timeout_seconds'] = timeout_seconds
        if operation:
            details['operation'] = operation
        
        super().__init__(
            message, 
            error_code="TIMEOUT_ERROR",
            details=details,
            **kwargs
        )


class ConfigurationError(QueueManagerError):
    """Exception raised for configuration-related errors."""
    
    def __init__(
        self, 
        message: str, 
        config_key: Optional[str] = None,
        config_value: Optional[Any] = None,
        **kwargs
    ):
        """Initialize the configuration error.
        
        Args:
            message: Error message
            config_key: Configuration key that caused the error
            config_value: Configuration value that caused the error
            **kwargs: Additional arguments passed to parent
        """
        details = kwargs.get('details', {})
        if config_key:
            details['config_key'] = config_key
        if config_value is not None:
            details['config_value'] = str(config_value)
        
        super().__init__(
            message, 
            error_code="CONFIGURATION_ERROR",
            details=details,
            **kwargs
        )


class APIError(QueueManagerError):
    """Exception raised for API-related errors."""
    
    def __init__(
        self, 
        message: str, 
        status_code: int = 500,
        endpoint: Optional[str] = None,
        **kwargs
    ):
        """Initialize the API error.
        
        Args:
            message: Error message
            status_code: HTTP status code
            endpoint: API endpoint that caused the error
            **kwargs: Additional arguments passed to parent
        """
        details = kwargs.get('details', {})
        details['status_code'] = status_code
        if endpoint:
            details['endpoint'] = endpoint
        
        super().__init__(
            message, 
            error_code="API_ERROR",
            details=details,
            **kwargs
        )


class AuthenticationError(APIError):
    """Exception raised for authentication errors."""
    
    def __init__(self, message: str = "Authentication required", **kwargs):
        super().__init__(
            message, 
            status_code=401,
            error_code="AUTHENTICATION_ERROR",
            **kwargs
        )


class AuthorizationError(APIError):
    """Exception raised for authorization errors."""
    
    def __init__(self, message: str = "Access denied", **kwargs):
        super().__init__(
            message, 
            status_code=403,
            error_code="AUTHORIZATION_ERROR",
            **kwargs
        )


class NotFoundError(APIError):
    """Exception raised when a resource is not found."""
    
    def __init__(
        self, 
        message: str, 
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        **kwargs
    ):
        """Initialize the not found error.
        
        Args:
            message: Error message
            resource_type: Type of resource that was not found
            resource_id: ID of resource that was not found
            **kwargs: Additional arguments passed to parent
        """
        details = kwargs.get('details', {})
        if resource_type:
            details['resource_type'] = resource_type
        if resource_id:
            details['resource_id'] = resource_id
        
        super().__init__(
            message, 
            status_code=404,
            error_code="NOT_FOUND_ERROR",
            details=details,
            **kwargs
        )


class ConflictError(APIError):
    """Exception raised for resource conflicts."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message, 
            status_code=409,
            error_code="CONFLICT_ERROR",
            **kwargs
        )


class RateLimitError(APIError):
    """Exception raised when rate limits are exceeded."""
    
    def __init__(
        self, 
        message: str = "Rate limit exceeded", 
        retry_after: Optional[int] = None,
        **kwargs
    ):
        """Initialize the rate limit error.
        
        Args:
            message: Error message
            retry_after: Seconds to wait before retrying
            **kwargs: Additional arguments passed to parent
        """
        details = kwargs.get('details', {})
        if retry_after is not None:
            details['retry_after'] = retry_after
        
        super().__init__(
            message, 
            status_code=429,
            error_code="RATE_LIMIT_ERROR",
            details=details,
            **kwargs
        )


class ImportExportError(QueueManagerError):
    """Exception raised for import/export operations."""
    
    def __init__(
        self, 
        message: str, 
        operation: Optional[str] = None,
        file_path: Optional[str] = None,
        **kwargs
    ):
        """Initialize the import/export error.
        
        Args:
            message: Error message
            operation: Operation that failed ('import' or 'export')
            file_path: File path involved in the operation
            **kwargs: Additional arguments passed to parent
        """
        details = kwargs.get('details', {})
        if operation:
            details['operation'] = operation
        if file_path:
            details['file_path'] = file_path
        
        super().__init__(
            message, 
            error_code="IMPORT_EXPORT_ERROR",
            details=details,
            **kwargs
        )


class ArchiveError(QueueManagerError):
    """Exception raised for archive operations."""
    
    def __init__(
        self, 
        message: str, 
        operation: Optional[str] = None,
        item_count: Optional[int] = None,
        **kwargs
    ):
        """Initialize the archive error.
        
        Args:
            message: Error message
            operation: Archive operation that failed
            item_count: Number of items involved in the operation
            **kwargs: Additional arguments passed to parent
        """
        details = kwargs.get('details', {})
        if operation:
            details['operation'] = operation
        if item_count is not None:
            details['item_count'] = item_count
        
        super().__init__(
            message, 
            error_code="ARCHIVE_ERROR",
            details=details,
            **kwargs
        )