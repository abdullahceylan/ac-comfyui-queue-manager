"""
Performance monitoring for the ComfyUI Queue Manager.
Tracks metrics, performance data, and system health.
"""

from __future__ import annotations

import functools
import logging
import psutil
import threading
import time
from collections import defaultdict, deque
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Callable, Dict, List, Optional, TypeVar

from logging_config import get_logger

logger = get_logger("performance_monitor")

T = TypeVar('T')


@dataclass
class PerformanceMetric:
    """Data class for performance metrics."""
    
    name: str
    value: float
    unit: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tags: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metric to dictionary."""
        return {
            "name": self.name,
            "value": self.value,
            "unit": self.unit,
            "timestamp": self.timestamp.isoformat(),
            "tags": self.tags
        }


@dataclass
class OperationStats:
    """Statistics for a specific operation."""
    
    operation_name: str
    total_calls: int = 0
    total_time: float = 0.0
    min_time: float = float('inf')
    max_time: float = 0.0
    error_count: int = 0
    last_called: Optional[datetime] = None
    
    @property
    def average_time(self) -> float:
        """Calculate average execution time."""
        return self.total_time / self.total_calls if self.total_calls > 0 else 0.0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_calls == 0:
            return 0.0
        return ((self.total_calls - self.error_count) / self.total_calls) * 100
    
    def update(self, execution_time: float, error: bool = False) -> None:
        """Update statistics with new execution data."""
        self.total_calls += 1
        self.total_time += execution_time
        self.min_time = min(self.min_time, execution_time)
        self.max_time = max(self.max_time, execution_time)
        self.last_called = datetime.now(timezone.utc)
        
        if error:
            self.error_count += 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary."""
        return {
            "operation_name": self.operation_name,
            "total_calls": self.total_calls,
            "total_time": self.total_time,
            "average_time": self.average_time,
            "min_time": self.min_time if self.min_time != float('inf') else 0.0,
            "max_time": self.max_time,
            "error_count": self.error_count,
            "success_rate": self.success_rate,
            "last_called": self.last_called.isoformat() if self.last_called else None
        }


class PerformanceMonitor:
    """Performance monitoring and metrics collection."""
    
    def __init__(self, max_history_size: int = 1000):
        """Initialize performance monitor.
        
        Args:
            max_history_size: Maximum number of metrics to keep in history
        """
        self.max_history_size = max_history_size
        self._lock = threading.RLock()
        
        # Metrics storage
        self._metrics_history: deque = deque(maxlen=max_history_size)
        self._operation_stats: Dict[str, OperationStats] = {}
        self._counters: Dict[str, int] = defaultdict(int)
        self._gauges: Dict[str, float] = {}
        
        # System monitoring
        self._system_metrics_enabled = True
        self._system_metrics_interval = 60.0  # seconds
        self._system_monitor_thread: Optional[threading.Thread] = None
        self._stop_system_monitoring = threading.Event()
        
        # Performance thresholds
        self._thresholds = {
            "database_operation_time": 1.0,  # seconds
            "api_response_time": 2.0,  # seconds
            "workflow_execution_time": 300.0,  # seconds
            "memory_usage_percent": 80.0,  # percent
            "cpu_usage_percent": 90.0,  # percent
        }
        
        logger.info("Performance monitor initialized", extra={
            "max_history_size": max_history_size,
            "system_metrics_enabled": self._system_metrics_enabled
        })
    
    def start_system_monitoring(self) -> None:
        """Start system metrics monitoring thread."""
        if self._system_monitor_thread and self._system_monitor_thread.is_alive():
            logger.warning("System monitoring is already running")
            return
        
        self._stop_system_monitoring.clear()
        self._system_monitor_thread = threading.Thread(
            target=self._system_monitoring_loop,
            name="SystemMonitor",
            daemon=True
        )
        self._system_monitor_thread.start()
        
        logger.info("System monitoring started", extra={
            "interval": self._system_metrics_interval
        })
    
    def stop_system_monitoring(self) -> None:
        """Stop system metrics monitoring thread."""
        if not self._system_monitor_thread or not self._system_monitor_thread.is_alive():
            return
        
        self._stop_system_monitoring.set()
        self._system_monitor_thread.join(timeout=5.0)
        
        if self._system_monitor_thread.is_alive():
            logger.warning("System monitoring thread did not stop gracefully")
        else:
            logger.info("System monitoring stopped")
    
    def _system_monitoring_loop(self) -> None:
        """System monitoring loop that runs in a separate thread."""
        logger.info("System monitoring loop started")
        
        while not self._stop_system_monitoring.is_set():
            try:
                self._collect_system_metrics()
                
                # Wait for interval or stop signal
                if self._stop_system_monitoring.wait(timeout=self._system_metrics_interval):
                    break
                    
            except Exception as e:
                logger.error(f"Error in system monitoring loop: {e}", exc_info=True)
                time.sleep(5.0)  # Brief pause before retrying
        
        logger.info("System monitoring loop stopped")
    
    def _collect_system_metrics(self) -> None:
        """Collect system performance metrics."""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            self.record_gauge("system.cpu.usage_percent", cpu_percent)
            
            # Memory metrics
            memory = psutil.virtual_memory()
            self.record_gauge("system.memory.usage_percent", memory.percent)
            self.record_gauge("system.memory.available_mb", memory.available / 1024 / 1024)
            self.record_gauge("system.memory.used_mb", memory.used / 1024 / 1024)
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            self.record_gauge("system.disk.usage_percent", (disk.used / disk.total) * 100)
            self.record_gauge("system.disk.free_gb", disk.free / 1024 / 1024 / 1024)
            
            # Process metrics
            process = psutil.Process()
            process_memory = process.memory_info()
            self.record_gauge("process.memory.rss_mb", process_memory.rss / 1024 / 1024)
            self.record_gauge("process.memory.vms_mb", process_memory.vms / 1024 / 1024)
            self.record_gauge("process.cpu.percent", process.cpu_percent())
            self.record_gauge("process.threads.count", process.num_threads())
            
            # Check thresholds
            self._check_performance_thresholds({
                "cpu_usage_percent": cpu_percent,
                "memory_usage_percent": memory.percent,
            })
            
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
    
    def _check_performance_thresholds(self, metrics: Dict[str, float]) -> None:
        """Check if metrics exceed performance thresholds."""
        for metric_name, value in metrics.items():
            threshold = self._thresholds.get(metric_name)
            if threshold and value > threshold:
                logger.warning(
                    f"Performance threshold exceeded: {metric_name}",
                    extra={
                        "metric": metric_name,
                        "value": value,
                        "threshold": threshold,
                        "severity": "high" if value > threshold * 1.2 else "medium"
                    }
                )
    
    def record_metric(self, metric: PerformanceMetric) -> None:
        """Record a performance metric.
        
        Args:
            metric: Performance metric to record
        """
        with self._lock:
            self._metrics_history.append(metric)
        
        # Log metric if it's significant
        if metric.name.endswith("_time") and metric.value > 1.0:
            logger.info(f"Performance metric recorded: {metric.name}", extra={
                "metric_name": metric.name,
                "value": metric.value,
                "unit": metric.unit,
                "tags": metric.tags
            })
    
    def record_counter(self, name: str, increment: int = 1, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a counter metric.
        
        Args:
            name: Counter name
            increment: Amount to increment by
            tags: Optional tags for the metric
        """
        with self._lock:
            self._counters[name] += increment
        
        metric = PerformanceMetric(
            name=name,
            value=increment,
            unit="count",
            tags=tags or {}
        )
        self.record_metric(metric)
    
    def record_gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a gauge metric.
        
        Args:
            name: Gauge name
            value: Gauge value
            tags: Optional tags for the metric
        """
        with self._lock:
            self._gauges[name] = value
        
        metric = PerformanceMetric(
            name=name,
            value=value,
            unit="gauge",
            tags=tags or {}
        )
        self.record_metric(metric)
    
    def record_timing(self, name: str, duration: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a timing metric.
        
        Args:
            name: Timing metric name
            duration: Duration in seconds
            tags: Optional tags for the metric
        """
        metric = PerformanceMetric(
            name=name,
            value=duration,
            unit="seconds",
            tags=tags or {}
        )
        self.record_metric(metric)
        
        # Check timing thresholds
        threshold_key = name.replace(".", "_")
        threshold = self._thresholds.get(threshold_key)
        if threshold and duration > threshold:
            logger.warning(
                f"Timing threshold exceeded: {name}",
                extra={
                    "metric": name,
                    "duration": duration,
                    "threshold": threshold,
                    "tags": tags or {}
                }
            )
    
    def update_operation_stats(self, operation: str, execution_time: float, error: bool = False) -> None:
        """Update statistics for an operation.
        
        Args:
            operation: Operation name
            execution_time: Execution time in seconds
            error: Whether the operation resulted in an error
        """
        with self._lock:
            if operation not in self._operation_stats:
                self._operation_stats[operation] = OperationStats(operation)
            
            self._operation_stats[operation].update(execution_time, error)
        
        # Record timing metric
        self.record_timing(f"operation.{operation}.time", execution_time, {
            "operation": operation,
            "status": "error" if error else "success"
        })
    
    @contextmanager
    def time_operation(self, operation: str, tags: Optional[Dict[str, str]] = None):
        """Context manager for timing operations.
        
        Args:
            operation: Operation name
            tags: Optional tags for the metric
        """
        start_time = time.time()
        error_occurred = False
        
        try:
            yield
        except Exception as e:
            error_occurred = True
            raise
        finally:
            execution_time = time.time() - start_time
            self.update_operation_stats(operation, execution_time, error_occurred)
            
            # Add error status to tags
            final_tags = tags or {}
            final_tags["status"] = "error" if error_occurred else "success"
            
            self.record_timing(f"operation.{operation}.time", execution_time, final_tags)
    
    def get_operation_stats(self, operation: Optional[str] = None) -> Dict[str, Any]:
        """Get operation statistics.
        
        Args:
            operation: Specific operation name, or None for all operations
            
        Returns:
            Dictionary containing operation statistics
        """
        with self._lock:
            if operation:
                stats = self._operation_stats.get(operation)
                return stats.to_dict() if stats else {}
            else:
                return {
                    op_name: stats.to_dict()
                    for op_name, stats in self._operation_stats.items()
                }
    
    def get_metrics_summary(self, since: Optional[datetime] = None) -> Dict[str, Any]:
        """Get summary of recorded metrics.
        
        Args:
            since: Only include metrics since this timestamp
            
        Returns:
            Dictionary containing metrics summary
        """
        with self._lock:
            # Filter metrics by timestamp if specified
            if since:
                filtered_metrics = [
                    metric for metric in self._metrics_history
                    if metric.timestamp >= since
                ]
            else:
                filtered_metrics = list(self._metrics_history)
            
            # Group metrics by name
            metrics_by_name = defaultdict(list)
            for metric in filtered_metrics:
                metrics_by_name[metric.name].append(metric.value)
            
            # Calculate summary statistics
            summary = {}
            for name, values in metrics_by_name.items():
                if values:
                    summary[name] = {
                        "count": len(values),
                        "min": min(values),
                        "max": max(values),
                        "avg": sum(values) / len(values),
                        "total": sum(values) if name.endswith("_count") else None
                    }
            
            return {
                "period": {
                    "start": since.isoformat() if since else None,
                    "end": datetime.now(timezone.utc).isoformat(),
                    "total_metrics": len(filtered_metrics)
                },
                "metrics": summary,
                "counters": dict(self._counters),
                "gauges": dict(self._gauges)
            }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall system health status.
        
        Returns:
            Dictionary containing health status information
        """
        with self._lock:
            # Check recent errors
            recent_time = datetime.now(timezone.utc) - timedelta(minutes=5)
            recent_errors = sum(
                1 for metric in self._metrics_history
                if (metric.timestamp >= recent_time and 
                    metric.tags.get("status") == "error")
            )
            
            # Calculate error rates
            total_operations = sum(stats.total_calls for stats in self._operation_stats.values())
            total_errors = sum(stats.error_count for stats in self._operation_stats.values())
            overall_error_rate = (total_errors / total_operations * 100) if total_operations > 0 else 0
            
            # Determine health status
            if recent_errors > 10 or overall_error_rate > 10:
                health_status = "unhealthy"
            elif recent_errors > 5 or overall_error_rate > 5:
                health_status = "degraded"
            else:
                health_status = "healthy"
            
            return {
                "status": health_status,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "metrics": {
                    "recent_errors": recent_errors,
                    "total_operations": total_operations,
                    "total_errors": total_errors,
                    "error_rate_percent": overall_error_rate
                },
                "system": {
                    "cpu_percent": self._gauges.get("system.cpu.usage_percent", 0),
                    "memory_percent": self._gauges.get("system.memory.usage_percent", 0),
                    "disk_percent": self._gauges.get("system.disk.usage_percent", 0)
                }
            }
    
    def reset_stats(self) -> None:
        """Reset all performance statistics."""
        with self._lock:
            self._metrics_history.clear()
            self._operation_stats.clear()
            self._counters.clear()
            self._gauges.clear()
        
        logger.info("Performance statistics reset")
    
    def close(self) -> None:
        """Close the performance monitor and cleanup resources."""
        self.stop_system_monitoring()
        logger.info("Performance monitor closed")


def time_function(operation_name: Optional[str] = None, tags: Optional[Dict[str, str]] = None):
    """Decorator for timing function execution.
    
    Args:
        operation_name: Name for the operation (defaults to function name)
        tags: Optional tags for the metric
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            op_name = operation_name or func.__name__
            
            with get_performance_monitor().time_operation(op_name, tags):
                return func(*args, **kwargs)
        
        return wrapper
    return decorator


# Global performance monitor instance
_performance_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor instance.
    
    Returns:
        PerformanceMonitor instance
    """
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
        _performance_monitor.start_system_monitoring()
    return _performance_monitor


def setup_performance_monitoring(max_history_size: int = 1000) -> PerformanceMonitor:
    """Set up performance monitoring.
    
    Args:
        max_history_size: Maximum number of metrics to keep in history
        
    Returns:
        PerformanceMonitor instance
    """
    global _performance_monitor
    
    if _performance_monitor:
        _performance_monitor.close()
    
    _performance_monitor = PerformanceMonitor(max_history_size)
    _performance_monitor.start_system_monitoring()
    
    return _performance_monitor