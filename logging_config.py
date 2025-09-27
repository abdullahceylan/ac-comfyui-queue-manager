"""
Logging configuration for the ComfyUI Queue Manager.
Provides structured logging with rotation, filtering, and monitoring capabilities.
"""

from __future__ import annotations

import json
import logging
import logging.handlers
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


class StructuredFormatter(logging.Formatter):
    """Custom formatter that outputs structured JSON logs."""
    
    def __init__(self, include_extra: bool = True):
        """Initialize the structured formatter.
        
        Args:
            include_extra: Whether to include extra fields from log records
        """
        super().__init__()
        self.include_extra = include_extra
    
    def format(self, record: logging.LogRecord) -> str:
        """Format a log record as structured JSON.
        
        Args:
            record: Log record to format
            
        Returns:
            JSON-formatted log string
        """
        # Base log data
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add thread information
        if record.thread:
            log_data["thread_id"] = record.thread
            log_data["thread_name"] = record.threadName
        
        # Add process information
        if record.process:
            log_data["process_id"] = record.process
            log_data["process_name"] = record.processName
        
        # Add exception information
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info) if record.exc_info else None
            }
        
        # Add extra fields if enabled
        if self.include_extra:
            # Get all extra attributes (those not in the standard LogRecord)
            standard_attrs = {
                'name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 'filename',
                'module', 'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
                'thread', 'threadName', 'processName', 'process', 'getMessage',
                'exc_info', 'exc_text', 'stack_info', 'message'
            }
            
            extra_data = {}
            for key, value in record.__dict__.items():
                if key not in standard_attrs and not key.startswith('_'):
                    # Ensure value is JSON serializable
                    try:
                        json.dumps(value)
                        extra_data[key] = value
                    except (TypeError, ValueError):
                        extra_data[key] = str(value)
            
            if extra_data:
                log_data["extra"] = extra_data
        
        return json.dumps(log_data, ensure_ascii=False)


class QueueManagerFilter(logging.Filter):
    """Custom filter for queue manager logs."""
    
    def __init__(self, component: Optional[str] = None, min_level: int = logging.INFO):
        """Initialize the filter.
        
        Args:
            component: Specific component to filter for (e.g., 'database', 'api')
            min_level: Minimum log level to allow
        """
        super().__init__()
        self.component = component
        self.min_level = min_level
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Filter log records based on criteria.
        
        Args:
            record: Log record to filter
            
        Returns:
            True if record should be logged
        """
        # Check minimum level
        if record.levelno < self.min_level:
            return False
        
        # Check component filter
        if self.component:
            # Check if the logger name contains the component
            if self.component not in record.name:
                return False
        
        return True


class LoggingConfig:
    """Configuration manager for logging setup."""
    
    DEFAULT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
    
    def __init__(self, log_dir: Optional[Path] = None):
        """Initialize logging configuration.
        
        Args:
            log_dir: Directory for log files. If None, uses default location.
        """
        self.log_dir = log_dir or Path(__file__).parent / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Configuration settings
        self.console_level = logging.INFO
        self.file_level = logging.DEBUG
        self.structured_logging = True
        self.max_file_size = 10 * 1024 * 1024  # 10MB
        self.backup_count = 5
        
        # Logger instances
        self._loggers: Dict[str, logging.Logger] = {}
        self._configured = False
    
    def configure_logging(
        self,
        console_level: int = logging.INFO,
        file_level: int = logging.DEBUG,
        structured: bool = True,
        max_file_size: int = 10 * 1024 * 1024,
        backup_count: int = 5
    ) -> None:
        """Configure logging for the queue manager.
        
        Args:
            console_level: Log level for console output
            file_level: Log level for file output
            structured: Whether to use structured JSON logging
            max_file_size: Maximum size of log files before rotation
            backup_count: Number of backup files to keep
        """
        self.console_level = console_level
        self.file_level = file_level
        self.structured_logging = structured
        self.max_file_size = max_file_size
        self.backup_count = backup_count
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        
        # Remove existing handlers to avoid duplicates
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Configure console handler
        self._configure_console_handler(root_logger)
        
        # Configure file handlers
        self._configure_file_handlers(root_logger)
        
        # Configure component-specific loggers
        self._configure_component_loggers()
        
        self._configured = True
        
        # Log configuration completion
        logger = self.get_logger("logging_config")
        logger.info("Logging configuration completed", extra={
            "console_level": logging.getLevelName(console_level),
            "file_level": logging.getLevelName(file_level),
            "structured": structured,
            "log_dir": str(self.log_dir),
            "max_file_size": max_file_size,
            "backup_count": backup_count
        })
    
    def _configure_console_handler(self, root_logger: logging.Logger) -> None:
        """Configure console logging handler."""
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.console_level)
        
        if self.structured_logging:
            console_formatter = StructuredFormatter(include_extra=False)
        else:
            console_formatter = logging.Formatter(
                self.DEFAULT_FORMAT,
                datefmt=self.DEFAULT_DATE_FORMAT
            )
        
        console_handler.setFormatter(console_formatter)
        console_handler.addFilter(QueueManagerFilter(min_level=self.console_level))
        
        root_logger.addHandler(console_handler)
    
    def _configure_file_handlers(self, root_logger: logging.Logger) -> None:
        """Configure file logging handlers."""
        # Main application log
        main_log_file = self.log_dir / "queue_manager.log"
        main_handler = logging.handlers.RotatingFileHandler(
            main_log_file,
            maxBytes=self.max_file_size,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        main_handler.setLevel(self.file_level)
        
        if self.structured_logging:
            main_formatter = StructuredFormatter(include_extra=True)
        else:
            main_formatter = logging.Formatter(
                self.DEFAULT_FORMAT,
                datefmt=self.DEFAULT_DATE_FORMAT
            )
        
        main_handler.setFormatter(main_formatter)
        root_logger.addHandler(main_handler)
        
        # Error-only log
        error_log_file = self.log_dir / "errors.log"
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_file,
            maxBytes=self.max_file_size,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(main_formatter)
        root_logger.addHandler(error_handler)
        
        # Performance log
        perf_log_file = self.log_dir / "performance.log"
        perf_handler = logging.handlers.RotatingFileHandler(
            perf_log_file,
            maxBytes=self.max_file_size,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        perf_handler.setLevel(logging.INFO)
        perf_handler.setFormatter(main_formatter)
        perf_handler.addFilter(QueueManagerFilter(component="performance"))
        root_logger.addHandler(perf_handler)
    
    def _configure_component_loggers(self) -> None:
        """Configure component-specific loggers."""
        components = [
            "database",
            "queue_service", 
            "api_routes",
            "workflow_executor",
            "execution_monitor",
            "archive_service",
            "filter_service",
            "import_export_service"
        ]
        
        for component in components:
            logger = logging.getLogger(f"custom_nodes.comfyui-queue-manager.{component}")
            logger.setLevel(logging.DEBUG)
            # Inherit handlers from root logger
            logger.propagate = True
    
    def get_logger(self, name: str) -> logging.Logger:
        """Get a logger instance for a specific component.
        
        Args:
            name: Logger name (component name)
            
        Returns:
            Logger instance
        """
        full_name = f"custom_nodes.comfyui-queue-manager.{name}"
        
        if full_name not in self._loggers:
            logger = logging.getLogger(full_name)
            logger.setLevel(logging.DEBUG)
            self._loggers[full_name] = logger
        
        return self._loggers[full_name]
    
    def set_log_level(self, component: str, level: int) -> None:
        """Set log level for a specific component.
        
        Args:
            component: Component name
            level: Log level
        """
        logger = self.get_logger(component)
        logger.setLevel(level)
        
        # Log the level change
        logger.info(f"Log level changed to {logging.getLevelName(level)}", extra={
            "component": component,
            "new_level": logging.getLevelName(level)
        })
    
    def cleanup_old_logs(self, days_to_keep: int = 30) -> int:
        """Clean up old log files.
        
        Args:
            days_to_keep: Number of days of logs to keep
            
        Returns:
            Number of files cleaned up
        """
        from datetime import timedelta
        import time
        
        cutoff_time = time.time() - (days_to_keep * 24 * 60 * 60)
        cleaned_count = 0
        
        for log_file in self.log_dir.glob("*.log*"):
            try:
                if log_file.stat().st_mtime < cutoff_time:
                    log_file.unlink()
                    cleaned_count += 1
            except OSError as e:
                logger = self.get_logger("logging_config")
                logger.warning(f"Failed to clean up log file {log_file}: {e}")
        
        if cleaned_count > 0:
            logger = self.get_logger("logging_config")
            logger.info(f"Cleaned up {cleaned_count} old log files", extra={
                "cleaned_count": cleaned_count,
                "days_to_keep": days_to_keep
            })
        
        return cleaned_count
    
    def get_log_stats(self) -> Dict[str, Any]:
        """Get statistics about log files.
        
        Returns:
            Dictionary containing log file statistics
        """
        stats = {
            "log_dir": str(self.log_dir),
            "total_files": 0,
            "total_size": 0,
            "files": []
        }
        
        for log_file in self.log_dir.glob("*.log*"):
            try:
                file_stat = log_file.stat()
                file_info = {
                    "name": log_file.name,
                    "size": file_stat.st_size,
                    "modified": datetime.fromtimestamp(file_stat.st_mtime, tz=timezone.utc).isoformat()
                }
                stats["files"].append(file_info)
                stats["total_files"] += 1
                stats["total_size"] += file_stat.st_size
            except OSError:
                continue
        
        return stats


# Global logging configuration instance
_logging_config: Optional[LoggingConfig] = None


def get_logging_config() -> LoggingConfig:
    """Get the global logging configuration instance.
    
    Returns:
        LoggingConfig instance
    """
    global _logging_config
    if _logging_config is None:
        _logging_config = LoggingConfig()
    return _logging_config


def setup_logging(
    log_dir: Optional[Path] = None,
    console_level: int = logging.INFO,
    file_level: int = logging.DEBUG,
    structured: bool = True
) -> LoggingConfig:
    """Set up logging for the queue manager.
    
    Args:
        log_dir: Directory for log files
        console_level: Log level for console output
        file_level: Log level for file output
        structured: Whether to use structured JSON logging
        
    Returns:
        LoggingConfig instance
    """
    global _logging_config
    
    if log_dir:
        _logging_config = LoggingConfig(log_dir)
    else:
        _logging_config = get_logging_config()
    
    _logging_config.configure_logging(
        console_level=console_level,
        file_level=file_level,
        structured=structured
    )
    
    return _logging_config


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a component.
    
    Args:
        name: Component name
        
    Returns:
        Logger instance
    """
    config = get_logging_config()
    return config.get_logger(name)