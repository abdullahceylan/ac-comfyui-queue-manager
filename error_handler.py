"""
Error handling utilities for the ComfyUI Queue Manager.
Provides centralized error handling, logging, and recovery mechanisms.
"""

from __future__ import annotations

import functools
import logging
import sqlite3
import traceback
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional, Type, TypeVar, Union

from exceptions import (
    APIError,
    ConnectionError,
    DatabaseError,
    QueueManagerError,
    QueueServiceError,
    SchemaError,
    TimeoutError,
    ValidationError,
    WorkflowExecutionError,
)

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ErrorHandler:
    """Centralized error handling and recovery utilities."""
    
    @staticmethod
    def handle_database_error(
        error: Exception, 
        operation: str, 
        table: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> DatabaseError:
        """Handle and convert database errors to structured exceptions.
        
        Args:
            error: Original exception
            operation: Database operation that failed
            table: Database table involved
            context: Additional context information
            
        Returns:
            Structured DatabaseError
        """
        context = context or {}
        
        # Handle SQLite-specific errors
        if isinstance(error, sqlite3.Error):
            if isinstance(error, sqlite3.OperationalError):
                error_msg = str(error).lower()
                
                if "database is locked" in error_msg:
                    return ConnectionError(
                        f"Database is locked during {operation}",
                        operation=operation,
                        table=table,
                        details=context,
                        cause=error
                    )
                elif "no such table" in error_msg:
                    return SchemaError(
                        f"Table does not exist during {operation}",
                        operation=operation,
                        table=table,
                        details=context,
                        cause=error
                    )
                elif "disk i/o error" in error_msg:
                    return DatabaseError(
                        f"Disk I/O error during {operation}",
                        error_code="DB_IO_ERROR",
                        operation=operation,
                        table=table,
                        details=context,
                        cause=error
                    )
                else:
                    return DatabaseError(
                        f"Database operational error during {operation}: {error}",
                        error_code="DB_OPERATIONAL_ERROR",
                        operation=operation,
                        table=table,
                        details=context,
                        cause=error
                    )
            
            elif isinstance(error, sqlite3.IntegrityError):
                return ValidationError(
                    f"Data integrity violation during {operation}: {error}",
                    details={**context, "operation": operation, "table": table},
                    cause=error
                )
            
            elif isinstance(error, sqlite3.DatabaseError):
                return DatabaseError(
                    f"Database error during {operation}: {error}",
                    error_code="DB_GENERAL_ERROR",
                    operation=operation,
                    table=table,
                    details=context,
                    cause=error
                )
        
        # Handle general exceptions
        return DatabaseError(
            f"Unexpected error during {operation}: {error}",
            error_code="DB_UNEXPECTED_ERROR",
            operation=operation,
            table=table,
            details=context,
            cause=error
        )
    
    @staticmethod
    def handle_api_error(
        error: Exception,
        endpoint: str,
        method: str = "GET",
        context: Optional[Dict[str, Any]] = None
    ) -> APIError:
        """Handle and convert API errors to structured exceptions.
        
        Args:
            error: Original exception
            endpoint: API endpoint that failed
            method: HTTP method
            context: Additional context information
            
        Returns:
            Structured APIError
        """
        context = context or {}
        context.update({"endpoint": endpoint, "method": method})
        
        if isinstance(error, QueueManagerError):
            # Convert existing queue manager errors to API errors
            return APIError(
                error.message,
                status_code=500,
                endpoint=endpoint,
                details=context,
                cause=error
            )
        
        return APIError(
            f"API error at {method} {endpoint}: {error}",
            status_code=500,
            endpoint=endpoint,
            details=context,
            cause=error
        )
    
    @staticmethod
    def handle_workflow_error(
        error: Exception,
        workflow_id: Optional[str] = None,
        stage: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> WorkflowExecutionError:
        """Handle and convert workflow execution errors.
        
        Args:
            error: Original exception
            workflow_id: ID of the workflow that failed
            stage: Execution stage where error occurred
            context: Additional context information
            
        Returns:
            Structured WorkflowExecutionError
        """
        context = context or {}
        
        return WorkflowExecutionError(
            f"Workflow execution failed: {error}",
            workflow_id=workflow_id,
            execution_stage=stage,
            details=context,
            cause=error
        )
    
    @staticmethod
    def log_error(
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        level: int = logging.ERROR
    ) -> None:
        """Log an error with structured information.
        
        Args:
            error: Exception to log
            context: Additional context information
            level: Logging level
        """
        context = context or {}
        
        if isinstance(error, QueueManagerError):
            # Log structured queue manager errors
            log_data = {
                "error_type": error.__class__.__name__,
                "error_code": error.error_code,
                "message": error.message,
                "details": error.details,
                **context
            }
            
            logger.log(level, f"Queue Manager Error: {error.message}", extra=log_data)
            
            if error.cause:
                logger.log(level, f"Caused by: {error.cause}", exc_info=error.cause)
        else:
            # Log general exceptions
            logger.log(level, f"Unexpected error: {error}", extra=context, exc_info=error)


def with_error_handling(
    error_type: Type[QueueManagerError] = QueueManagerError,
    operation: Optional[str] = None,
    log_errors: bool = True,
    reraise: bool = True
):
    """Decorator for automatic error handling and logging.
    
    Args:
        error_type: Type of exception to convert errors to
        operation: Name of the operation for context
        log_errors: Whether to log errors automatically
        reraise: Whether to reraise the converted exception
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            try:
                return func(*args, **kwargs)
            except QueueManagerError:
                # Re-raise queue manager errors as-is
                raise
            except Exception as e:
                # Convert other exceptions
                operation_name = operation or func.__name__
                
                if error_type == DatabaseError:
                    converted_error = ErrorHandler.handle_database_error(
                        e, operation_name, context={"function": func.__name__}
                    )
                elif error_type == APIError:
                    converted_error = ErrorHandler.handle_api_error(
                        e, operation_name, context={"function": func.__name__}
                    )
                elif error_type == WorkflowExecutionError:
                    converted_error = ErrorHandler.handle_workflow_error(
                        e, context={"function": func.__name__}
                    )
                else:
                    converted_error = error_type(
                        f"Error in {operation_name}: {e}",
                        details={"function": func.__name__},
                        cause=e
                    )
                
                if log_errors:
                    ErrorHandler.log_error(converted_error)
                
                if reraise:
                    raise converted_error
                
                return converted_error
        
        return wrapper
    return decorator


def with_database_error_handling(
    operation: Optional[str] = None,
    table: Optional[str] = None,
    log_errors: bool = True
):
    """Decorator specifically for database operations.
    
    Args:
        operation: Database operation name
        table: Database table name
        log_errors: Whether to log errors automatically
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            try:
                return func(*args, **kwargs)
            except QueueManagerError:
                # Re-raise queue manager errors as-is
                raise
            except Exception as e:
                operation_name = operation or func.__name__
                converted_error = ErrorHandler.handle_database_error(
                    e, 
                    operation_name, 
                    table=table,
                    context={"function": func.__name__}
                )
                
                if log_errors:
                    ErrorHandler.log_error(converted_error)
                
                raise converted_error
        
        return wrapper
    return decorator


def with_api_error_handling(
    endpoint: Optional[str] = None,
    method: str = "GET",
    log_errors: bool = True
):
    """Decorator specifically for API operations.
    
    Args:
        endpoint: API endpoint name
        method: HTTP method
        log_errors: Whether to log errors automatically
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            try:
                return func(*args, **kwargs)
            except QueueManagerError:
                # Re-raise queue manager errors as-is
                raise
            except Exception as e:
                endpoint_name = endpoint or func.__name__
                converted_error = ErrorHandler.handle_api_error(
                    e, 
                    endpoint_name, 
                    method=method,
                    context={"function": func.__name__}
                )
                
                if log_errors:
                    ErrorHandler.log_error(converted_error)
                
                raise converted_error
        
        return wrapper
    return decorator


class ErrorRecovery:
    """Utilities for error recovery and retry mechanisms."""
    
    @staticmethod
    def retry_with_backoff(
        func: Callable[..., T],
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
        exceptions: tuple = (Exception,)
    ) -> T:
        """Retry a function with exponential backoff.
        
        Args:
            func: Function to retry
            max_retries: Maximum number of retry attempts
            base_delay: Initial delay between retries
            max_delay: Maximum delay between retries
            backoff_factor: Factor to multiply delay by each retry
            exceptions: Tuple of exceptions to catch and retry on
            
        Returns:
            Result of the function call
            
        Raises:
            The last exception if all retries fail
        """
        import time
        
        last_exception = None
        delay = base_delay
        
        for attempt in range(max_retries + 1):
            try:
                return func()
            except exceptions as e:
                last_exception = e
                
                if attempt == max_retries:
                    # Last attempt failed, re-raise
                    break
                
                logger.warning(
                    f"Attempt {attempt + 1} failed, retrying in {delay:.2f}s: {e}"
                )
                
                time.sleep(delay)
                delay = min(delay * backoff_factor, max_delay)
        
        # All retries failed
        if last_exception:
            raise last_exception
        else:
            raise RuntimeError("All retry attempts failed")
    
    @staticmethod
    def safe_execute(
        func: Callable[..., T],
        default_value: Optional[T] = None,
        log_errors: bool = True,
        exceptions: tuple = (Exception,)
    ) -> Optional[T]:
        """Execute a function safely, returning a default value on error.
        
        Args:
            func: Function to execute
            default_value: Value to return on error
            log_errors: Whether to log errors
            exceptions: Tuple of exceptions to catch
            
        Returns:
            Function result or default value
        """
        try:
            return func()
        except exceptions as e:
            if log_errors:
                logger.error(f"Safe execution failed: {e}", exc_info=True)
            return default_value


def create_error_response(
    error: Exception,
    include_traceback: bool = False
) -> Dict[str, Any]:
    """Create a standardized error response dictionary.
    
    Args:
        error: Exception to convert to response
        include_traceback: Whether to include traceback in response
        
    Returns:
        Dictionary containing error information
    """
    if isinstance(error, QueueManagerError):
        response = error.to_dict()
    else:
        response = {
            "error_type": error.__class__.__name__,
            "error_code": "UNEXPECTED_ERROR",
            "message": str(error),
            "details": {},
            "cause": None
        }
    
    response["timestamp"] = datetime.now(timezone.utc).isoformat()
    
    if include_traceback:
        response["traceback"] = traceback.format_exc()
    
    return response