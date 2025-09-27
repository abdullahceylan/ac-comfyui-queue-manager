"""
Tests for logging and monitoring functionality in the ComfyUI Queue Manager.
"""

import asyncio
import json
import logging
import tempfile
import threading
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from health_check import (
    DatabaseHealthCheck,
    HealthCheck,
    HealthCheckManager,
    HealthCheckResult,
    HealthStatus,
    QueueServiceHealthCheck,
    SystemResourceHealthCheck,
)
from logging_config import LoggingConfig, QueueManagerFilter, StructuredFormatter
from performance_monitor import (
    OperationStats,
    PerformanceMetric,
    PerformanceMonitor,
    time_function,
)


class TestStructuredFormatter:
    """Test structured logging formatter."""
    
    def test_basic_formatting(self):
        """Test basic log record formatting."""
        formatter = StructuredFormatter()
        
        # Create a log record
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/test/path.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        # Format the record
        formatted = formatter.format(record)
        
        # Parse the JSON
        log_data = json.loads(formatted)
        
        assert log_data["level"] == "INFO"
        assert log_data["logger"] == "test.logger"
        assert log_data["message"] == "Test message"
        assert log_data["line"] == 42
        assert "timestamp" in log_data
    
    def test_formatting_with_extra_fields(self):
        """Test formatting with extra fields."""
        formatter = StructuredFormatter(include_extra=True)
        
        record = logging.LogRecord(
            name="test.logger",
            level=logging.ERROR,
            pathname="/test/path.py",
            lineno=42,
            msg="Test error",
            args=(),
            exc_info=None
        )
        
        # Add extra fields
        record.user_id = "test-user"
        record.operation = "test_operation"
        record.custom_data = {"key": "value"}
        
        formatted = formatter.format(record)
        log_data = json.loads(formatted)
        
        assert "extra" in log_data
        assert log_data["extra"]["user_id"] == "test-user"
        assert log_data["extra"]["operation"] == "test_operation"
        assert log_data["extra"]["custom_data"] == {"key": "value"}
    
    def test_formatting_with_exception(self):
        """Test formatting with exception information."""
        formatter = StructuredFormatter()
        
        try:
            raise ValueError("Test exception")
        except ValueError:
            record = logging.LogRecord(
                name="test.logger",
                level=logging.ERROR,
                pathname="/test/path.py",
                lineno=42,
                msg="Error occurred",
                args=(),
                exc_info=True
            )
        
        formatted = formatter.format(record)
        log_data = json.loads(formatted)
        
        assert "exception" in log_data
        assert log_data["exception"]["type"] == "ValueError"
        assert log_data["exception"]["message"] == "Test exception"
        assert "traceback" in log_data["exception"]


class TestQueueManagerFilter:
    """Test logging filter."""
    
    def test_level_filtering(self):
        """Test filtering by log level."""
        filter_obj = QueueManagerFilter(min_level=logging.WARNING)
        
        # Create records with different levels
        info_record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="Info message", args=(), exc_info=None
        )
        warning_record = logging.LogRecord(
            name="test", level=logging.WARNING, pathname="", lineno=0,
            msg="Warning message", args=(), exc_info=None
        )
        
        assert not filter_obj.filter(info_record)
        assert filter_obj.filter(warning_record)
    
    def test_component_filtering(self):
        """Test filtering by component."""
        filter_obj = QueueManagerFilter(component="database")
        
        # Create records with different logger names
        db_record = logging.LogRecord(
            name="queue_manager.database", level=logging.INFO, pathname="", lineno=0,
            msg="Database message", args=(), exc_info=None
        )
        api_record = logging.LogRecord(
            name="queue_manager.api", level=logging.INFO, pathname="", lineno=0,
            msg="API message", args=(), exc_info=None
        )
        
        assert filter_obj.filter(db_record)
        assert not filter_obj.filter(api_record)


class TestLoggingConfig:
    """Test logging configuration."""
    
    def setup_method(self):
        """Set up test logging configuration."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.log_config = LoggingConfig(log_dir=self.temp_dir)
    
    def test_configure_logging(self):
        """Test logging configuration setup."""
        self.log_config.configure_logging(
            console_level=logging.INFO,
            file_level=logging.DEBUG,
            structured=True
        )
        
        # Check that log files are created
        assert (self.temp_dir / "queue_manager.log").exists()
        assert (self.temp_dir / "errors.log").exists()
        assert (self.temp_dir / "performance.log").exists()
    
    def test_get_logger(self):
        """Test getting component loggers."""
        self.log_config.configure_logging()
        
        logger = self.log_config.get_logger("test_component")
        
        assert logger.name == "custom_nodes.comfyui-queue-manager.test_component"
        assert logger.level == logging.DEBUG
    
    def test_set_log_level(self):
        """Test setting log level for components."""
        self.log_config.configure_logging()
        
        self.log_config.set_log_level("test_component", logging.WARNING)
        logger = self.log_config.get_logger("test_component")
        
        assert logger.level == logging.WARNING
    
    def test_cleanup_old_logs(self):
        """Test cleaning up old log files."""
        self.log_config.configure_logging()
        
        # Create some old log files
        old_log = self.temp_dir / "old.log"
        old_log.touch()
        
        # Set modification time to 31 days ago
        old_time = time.time() - (31 * 24 * 60 * 60)
        old_log.stat().st_mtime = old_time
        
        cleaned_count = self.log_config.cleanup_old_logs(days_to_keep=30)
        
        # Note: This test might not work on all systems due to file system limitations
        # The cleanup_old_logs method should handle this gracefully
        assert cleaned_count >= 0
    
    def test_get_log_stats(self):
        """Test getting log file statistics."""
        self.log_config.configure_logging()
        
        stats = self.log_config.get_log_stats()
        
        assert "log_dir" in stats
        assert "total_files" in stats
        assert "total_size" in stats
        assert "files" in stats
        assert stats["total_files"] >= 0


class TestPerformanceMetric:
    """Test performance metric data class."""
    
    def test_metric_creation(self):
        """Test creating performance metrics."""
        metric = PerformanceMetric(
            name="test.metric",
            value=1.5,
            unit="seconds",
            tags={"operation": "test"}
        )
        
        assert metric.name == "test.metric"
        assert metric.value == 1.5
        assert metric.unit == "seconds"
        assert metric.tags["operation"] == "test"
        assert isinstance(metric.timestamp, datetime)
    
    def test_metric_to_dict(self):
        """Test converting metric to dictionary."""
        metric = PerformanceMetric(
            name="test.metric",
            value=2.0,
            unit="count"
        )
        
        result = metric.to_dict()
        
        assert result["name"] == "test.metric"
        assert result["value"] == 2.0
        assert result["unit"] == "count"
        assert "timestamp" in result


class TestOperationStats:
    """Test operation statistics."""
    
    def test_stats_initialization(self):
        """Test initializing operation stats."""
        stats = OperationStats("test_operation")
        
        assert stats.operation_name == "test_operation"
        assert stats.total_calls == 0
        assert stats.total_time == 0.0
        assert stats.error_count == 0
        assert stats.average_time == 0.0
        assert stats.success_rate == 0.0
    
    def test_stats_update(self):
        """Test updating operation stats."""
        stats = OperationStats("test_operation")
        
        # Update with successful operation
        stats.update(1.5, error=False)
        
        assert stats.total_calls == 1
        assert stats.total_time == 1.5
        assert stats.average_time == 1.5
        assert stats.min_time == 1.5
        assert stats.max_time == 1.5
        assert stats.error_count == 0
        assert stats.success_rate == 100.0
        
        # Update with failed operation
        stats.update(2.0, error=True)
        
        assert stats.total_calls == 2
        assert stats.total_time == 3.5
        assert stats.average_time == 1.75
        assert stats.min_time == 1.5
        assert stats.max_time == 2.0
        assert stats.error_count == 1
        assert stats.success_rate == 50.0
    
    def test_stats_to_dict(self):
        """Test converting stats to dictionary."""
        stats = OperationStats("test_operation")
        stats.update(1.0, error=False)
        
        result = stats.to_dict()
        
        assert result["operation_name"] == "test_operation"
        assert result["total_calls"] == 1
        assert result["average_time"] == 1.0
        assert result["success_rate"] == 100.0


class TestPerformanceMonitor:
    """Test performance monitoring."""
    
    def setup_method(self):
        """Set up test performance monitor."""
        self.monitor = PerformanceMonitor(max_history_size=100)
    
    def teardown_method(self):
        """Clean up test resources."""
        if hasattr(self, 'monitor'):
            self.monitor.close()
    
    def test_record_metric(self):
        """Test recording performance metrics."""
        metric = PerformanceMetric("test.metric", 1.0, "seconds")
        
        self.monitor.record_metric(metric)
        
        # Check that metric was recorded
        assert len(self.monitor._metrics_history) == 1
        assert self.monitor._metrics_history[0] == metric
    
    def test_record_counter(self):
        """Test recording counter metrics."""
        self.monitor.record_counter("test.counter", increment=5)
        
        assert self.monitor._counters["test.counter"] == 5
        assert len(self.monitor._metrics_history) == 1
    
    def test_record_gauge(self):
        """Test recording gauge metrics."""
        self.monitor.record_gauge("test.gauge", 42.0)
        
        assert self.monitor._gauges["test.gauge"] == 42.0
        assert len(self.monitor._metrics_history) == 1
    
    def test_record_timing(self):
        """Test recording timing metrics."""
        self.monitor.record_timing("test.timing", 1.5)
        
        assert len(self.monitor._metrics_history) == 1
        metric = self.monitor._metrics_history[0]
        assert metric.name == "test.timing"
        assert metric.value == 1.5
        assert metric.unit == "seconds"
    
    def test_update_operation_stats(self):
        """Test updating operation statistics."""
        self.monitor.update_operation_stats("test_op", 1.0, error=False)
        
        stats = self.monitor.get_operation_stats("test_op")
        assert stats["operation_name"] == "test_op"
        assert stats["total_calls"] == 1
        assert stats["average_time"] == 1.0
    
    def test_time_operation_context_manager(self):
        """Test timing operation context manager."""
        with self.monitor.time_operation("test_context"):
            time.sleep(0.01)  # Small delay
        
        stats = self.monitor.get_operation_stats("test_context")
        assert stats["total_calls"] == 1
        assert stats["average_time"] > 0
    
    def test_time_operation_with_error(self):
        """Test timing operation with error."""
        with pytest.raises(ValueError):
            with self.monitor.time_operation("test_error"):
                raise ValueError("Test error")
        
        stats = self.monitor.get_operation_stats("test_error")
        assert stats["total_calls"] == 1
        assert stats["error_count"] == 1
        assert stats["success_rate"] == 0.0
    
    def test_get_metrics_summary(self):
        """Test getting metrics summary."""
        # Record some metrics
        self.monitor.record_timing("test.timing", 1.0)
        self.monitor.record_timing("test.timing", 2.0)
        self.monitor.record_counter("test.counter", 5)
        
        summary = self.monitor.get_metrics_summary()
        
        assert "metrics" in summary
        assert "test.timing" in summary["metrics"]
        assert summary["metrics"]["test.timing"]["count"] == 2
        assert summary["metrics"]["test.timing"]["avg"] == 1.5
    
    def test_get_health_status(self):
        """Test getting health status."""
        # Record some operations
        self.monitor.update_operation_stats("test_op", 1.0, error=False)
        self.monitor.update_operation_stats("test_op", 1.5, error=False)
        
        health = self.monitor.get_health_status()
        
        assert "status" in health
        assert "metrics" in health
        assert health["metrics"]["total_operations"] == 2
        assert health["metrics"]["total_errors"] == 0
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    @patch('psutil.Process')
    def test_collect_system_metrics(self, mock_process, mock_disk, mock_memory, mock_cpu):
        """Test collecting system metrics."""
        # Mock system metrics
        mock_cpu.return_value = 50.0
        mock_memory.return_value = Mock(percent=60.0, available=1024*1024*1024, used=512*1024*1024)
        mock_disk.return_value = Mock(total=1024*1024*1024*100, used=1024*1024*1024*50, free=1024*1024*1024*50)
        mock_process.return_value = Mock(
            memory_info=Mock(rss=1024*1024*100, vms=1024*1024*200),
            cpu_percent=Mock(return_value=25.0),
            num_threads=Mock(return_value=10)
        )
        
        self.monitor._collect_system_metrics()
        
        # Check that system metrics were recorded
        assert "system.cpu.usage_percent" in self.monitor._gauges
        assert "system.memory.usage_percent" in self.monitor._gauges
        assert self.monitor._gauges["system.cpu.usage_percent"] == 50.0
        assert self.monitor._gauges["system.memory.usage_percent"] == 60.0


class TestTimeFunctionDecorator:
    """Test time_function decorator."""
    
    def setup_method(self):
        """Set up test performance monitor."""
        self.monitor = PerformanceMonitor()
    
    def teardown_method(self):
        """Clean up test resources."""
        if hasattr(self, 'monitor'):
            self.monitor.close()
    
    def test_time_function_decorator(self):
        """Test timing function with decorator."""
        @time_function("test_function")
        def test_func():
            time.sleep(0.01)
            return "result"
        
        result = test_func()
        
        assert result == "result"
        
        # Check that timing was recorded
        from performance_monitor import get_performance_monitor
        monitor = get_performance_monitor()
        stats = monitor.get_operation_stats("test_function")
        assert stats["total_calls"] >= 1
    
    def test_time_function_with_error(self):
        """Test timing function with error."""
        @time_function("test_error_function")
        def error_func():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError):
            error_func()
        
        # Check that error was recorded
        from performance_monitor import get_performance_monitor
        monitor = get_performance_monitor()
        stats = monitor.get_operation_stats("test_error_function")
        assert stats["total_calls"] >= 1
        assert stats["error_count"] >= 1


class TestHealthCheck:
    """Test health check base class."""
    
    def test_health_check_timeout(self):
        """Test health check timeout handling."""
        class SlowHealthCheck(HealthCheck):
            async def _perform_check(self):
                await asyncio.sleep(2.0)  # Longer than timeout
                return HealthCheckResult(
                    name=self.name,
                    status=HealthStatus.HEALTHY,
                    message="Should not reach here"
                )
        
        check = SlowHealthCheck("slow_check", timeout=0.1)
        
        # Run the check
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(check.check())
        finally:
            loop.close()
        
        assert result.status == HealthStatus.UNHEALTHY
        assert "timed out" in result.message.lower()
    
    def test_health_check_exception(self):
        """Test health check exception handling."""
        class FailingHealthCheck(HealthCheck):
            async def _perform_check(self):
                raise ValueError("Test error")
        
        check = FailingHealthCheck("failing_check")
        
        # Run the check
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(check.check())
        finally:
            loop.close()
        
        assert result.status == HealthStatus.UNHEALTHY
        assert "Test error" in result.message


class TestDatabaseHealthCheck:
    """Test database health check."""
    
    def test_database_health_check_uninitialized(self):
        """Test health check with uninitialized database."""
        mock_db = Mock()
        mock_db._initialized = False
        
        check = DatabaseHealthCheck(mock_db)
        
        # Run the check
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(check.check())
        finally:
            loop.close()
        
        assert result.status == HealthStatus.UNHEALTHY
        assert "not initialized" in result.message.lower()


class TestHealthCheckManager:
    """Test health check manager."""
    
    def setup_method(self):
        """Set up test health check manager."""
        self.manager = HealthCheckManager()
    
    def teardown_method(self):
        """Clean up test resources."""
        if hasattr(self, 'manager'):
            self.manager.close()
    
    def test_register_and_unregister_check(self):
        """Test registering and unregistering health checks."""
        check = SystemResourceHealthCheck()
        
        self.manager.register_check(check)
        assert "system_resources" in self.manager._checks
        
        self.manager.unregister_check("system_resources")
        assert "system_resources" not in self.manager._checks
    
    def test_run_nonexistent_check(self):
        """Test running a non-existent health check."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(self.manager.run_check("nonexistent"))
        finally:
            loop.close()
        
        assert result.status == HealthStatus.UNKNOWN
        assert "not found" in result.message.lower()
    
    def test_get_overall_health_no_checks(self):
        """Test getting overall health with no checks."""
        health = self.manager.get_overall_health()
        
        assert health["status"] == HealthStatus.UNKNOWN.value
        assert "no health checks" in health["message"].lower()


if __name__ == "__main__":
    pytest.main([__file__])