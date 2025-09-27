"""
Health check system for the ComfyUI Queue Manager.
Provides comprehensive health monitoring and diagnostics.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from logging_config import get_logger
from performance_monitor import get_performance_monitor

logger = get_logger("health_check")


class HealthStatus(Enum):
    """Health status enumeration."""
    
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    
    name: str
    status: HealthStatus
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    duration: float = 0.0  # seconds
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "duration": self.duration
        }


class HealthCheck:
    """Base class for health checks."""
    
    def __init__(self, name: str, timeout: float = 30.0):
        """Initialize health check.
        
        Args:
            name: Name of the health check
            timeout: Timeout in seconds
        """
        self.name = name
        self.timeout = timeout
    
    async def check(self) -> HealthCheckResult:
        """Perform the health check.
        
        Returns:
            HealthCheckResult
        """
        start_time = time.time()
        
        try:
            # Run the actual check with timeout
            result = await asyncio.wait_for(self._perform_check(), timeout=self.timeout)
            duration = time.time() - start_time
            result.duration = duration
            return result
            
        except asyncio.TimeoutError:
            duration = time.time() - start_time
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check timed out after {self.timeout} seconds",
                duration=duration,
                details={"timeout": self.timeout}
            )
        except Exception as e:
            duration = time.time() - start_time
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check failed: {e}",
                duration=duration,
                details={"error": str(e), "error_type": type(e).__name__}
            )
    
    async def _perform_check(self) -> HealthCheckResult:
        """Perform the actual health check logic.
        
        This method should be overridden by subclasses.
        
        Returns:
            HealthCheckResult
        """
        raise NotImplementedError("Subclasses must implement _perform_check")


class DatabaseHealthCheck(HealthCheck):
    """Health check for database connectivity and performance."""
    
    def __init__(self, database, timeout: float = 10.0):
        """Initialize database health check.
        
        Args:
            database: Database instance to check
            timeout: Timeout in seconds
        """
        super().__init__("database", timeout)
        self.database = database
    
    async def _perform_check(self) -> HealthCheckResult:
        """Check database health."""
        details = {}
        
        try:
            # Check if database is initialized
            if not hasattr(self.database, '_initialized') or not self.database._initialized:
                return HealthCheckResult(
                    name=self.name,
                    status=HealthStatus.UNHEALTHY,
                    message="Database not initialized",
                    details={"initialized": False}
                )
            
            # Test basic connectivity
            start_time = time.time()
            test_result = await asyncio.get_event_loop().run_in_executor(
                None, self._test_database_connection
            )
            connection_time = time.time() - start_time
            
            details.update(test_result)
            details["connection_time"] = connection_time
            
            # Determine status based on results
            if not test_result.get("connected", False):
                status = HealthStatus.UNHEALTHY
                message = "Database connection failed"
            elif connection_time > 5.0:
                status = HealthStatus.DEGRADED
                message = f"Database connection slow ({connection_time:.2f}s)"
            else:
                status = HealthStatus.HEALTHY
                message = "Database is healthy"
            
            return HealthCheckResult(
                name=self.name,
                status=status,
                message=message,
                details=details
            )
            
        except Exception as e:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Database health check failed: {e}",
                details={"error": str(e)}
            )
    
    def _test_database_connection(self) -> Dict[str, Any]:
        """Test database connection and basic operations."""
        result = {
            "connected": False,
            "schema_version": None,
            "table_count": 0,
            "last_error": None
        }
        
        try:
            # Test connection
            with self.database._get_cursor() as cursor:
                # Check schema version
                cursor.execute("SELECT version FROM schema_version LIMIT 1")
                version_row = cursor.fetchone()
                if version_row:
                    result["schema_version"] = version_row[0]
                
                # Count tables
                cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
                table_count_row = cursor.fetchone()
                if table_count_row:
                    result["table_count"] = table_count_row[0]
                
                # Test a simple query
                cursor.execute("SELECT COUNT(*) FROM queue_items")
                item_count_row = cursor.fetchone()
                if item_count_row:
                    result["queue_item_count"] = item_count_row[0]
                
                result["connected"] = True
                
        except Exception as e:
            result["last_error"] = str(e)
        
        return result


class QueueServiceHealthCheck(HealthCheck):
    """Health check for queue service functionality."""
    
    def __init__(self, queue_service, timeout: float = 15.0):
        """Initialize queue service health check.
        
        Args:
            queue_service: Queue service instance to check
            timeout: Timeout in seconds
        """
        super().__init__("queue_service", timeout)
        self.queue_service = queue_service
    
    async def _perform_check(self) -> HealthCheckResult:
        """Check queue service health."""
        details = {}
        
        try:
            # Check if service is initialized
            if not hasattr(self.queue_service, '_initialized') or not self.queue_service._initialized:
                return HealthCheckResult(
                    name=self.name,
                    status=HealthStatus.UNHEALTHY,
                    message="Queue service not initialized",
                    details={"initialized": False}
                )
            
            # Test basic operations
            start_time = time.time()
            test_result = await asyncio.get_event_loop().run_in_executor(
                None, self._test_queue_service_operations
            )
            operation_time = time.time() - start_time
            
            details.update(test_result)
            details["operation_time"] = operation_time
            
            # Determine status
            if test_result.get("errors", 0) > 0:
                status = HealthStatus.UNHEALTHY
                message = f"Queue service has {test_result['errors']} errors"
            elif operation_time > 10.0:
                status = HealthStatus.DEGRADED
                message = f"Queue service operations slow ({operation_time:.2f}s)"
            else:
                status = HealthStatus.HEALTHY
                message = "Queue service is healthy"
            
            return HealthCheckResult(
                name=self.name,
                status=status,
                message=message,
                details=details
            )
            
        except Exception as e:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Queue service health check failed: {e}",
                details={"error": str(e)}
            )
    
    def _test_queue_service_operations(self) -> Dict[str, Any]:
        """Test queue service operations."""
        result = {
            "queue_state": None,
            "item_count": 0,
            "config_accessible": False,
            "errors": 0,
            "last_error": None
        }
        
        try:
            # Test getting queue state
            queue_state = self.queue_service.get_queue_state()
            result["queue_state"] = queue_state.value
        except Exception as e:
            result["errors"] += 1
            result["last_error"] = f"get_queue_state: {e}"
        
        try:
            # Test getting queue items
            items = self.queue_service.get_queue_items()
            result["item_count"] = len(items)
        except Exception as e:
            result["errors"] += 1
            result["last_error"] = f"get_queue_items: {e}"
        
        try:
            # Test getting configuration
            config = self.queue_service.get_config()
            result["config_accessible"] = config is not None
        except Exception as e:
            result["errors"] += 1
            result["last_error"] = f"get_config: {e}"
        
        return result


class SystemResourceHealthCheck(HealthCheck):
    """Health check for system resources."""
    
    def __init__(self, timeout: float = 5.0):
        """Initialize system resource health check.
        
        Args:
            timeout: Timeout in seconds
        """
        super().__init__("system_resources", timeout)
    
    async def _perform_check(self) -> HealthCheckResult:
        """Check system resource health."""
        try:
            perf_monitor = get_performance_monitor()
            health_status = perf_monitor.get_health_status()
            
            # Map performance monitor status to health status
            status_mapping = {
                "healthy": HealthStatus.HEALTHY,
                "degraded": HealthStatus.DEGRADED,
                "unhealthy": HealthStatus.UNHEALTHY
            }
            
            status = status_mapping.get(health_status["status"], HealthStatus.UNKNOWN)
            
            return HealthCheckResult(
                name=self.name,
                status=status,
                message=f"System resources are {health_status['status']}",
                details=health_status
            )
            
        except Exception as e:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"System resource check failed: {e}",
                details={"error": str(e)}
            )


class HealthCheckManager:
    """Manager for running and coordinating health checks."""
    
    def __init__(self):
        """Initialize health check manager."""
        self._checks: Dict[str, HealthCheck] = {}
        self._last_results: Dict[str, HealthCheckResult] = {}
        self._lock = threading.RLock()
        
        # Monitoring settings
        self._monitoring_enabled = False
        self._monitoring_interval = 60.0  # seconds
        self._monitoring_thread: Optional[threading.Thread] = None
        self._stop_monitoring = threading.Event()
        
        logger.info("Health check manager initialized")
    
    def register_check(self, health_check: HealthCheck) -> None:
        """Register a health check.
        
        Args:
            health_check: Health check to register
        """
        with self._lock:
            self._checks[health_check.name] = health_check
        
        logger.info(f"Registered health check: {health_check.name}")
    
    def unregister_check(self, name: str) -> None:
        """Unregister a health check.
        
        Args:
            name: Name of the health check to remove
        """
        with self._lock:
            self._checks.pop(name, None)
            self._last_results.pop(name, None)
        
        logger.info(f"Unregistered health check: {name}")
    
    async def run_check(self, name: str) -> HealthCheckResult:
        """Run a specific health check.
        
        Args:
            name: Name of the health check to run
            
        Returns:
            HealthCheckResult
        """
        with self._lock:
            health_check = self._checks.get(name)
        
        if not health_check:
            return HealthCheckResult(
                name=name,
                status=HealthStatus.UNKNOWN,
                message=f"Health check '{name}' not found"
            )
        
        result = await health_check.check()
        
        with self._lock:
            self._last_results[name] = result
        
        # Log significant health changes
        if result.status != HealthStatus.HEALTHY:
            logger.warning(
                f"Health check failed: {name}",
                extra={
                    "check_name": name,
                    "status": result.status.value,
                    "message": result.message,
                    "duration": result.duration
                }
            )
        
        return result
    
    async def run_all_checks(self) -> Dict[str, HealthCheckResult]:
        """Run all registered health checks.
        
        Returns:
            Dictionary mapping check names to results
        """
        with self._lock:
            check_names = list(self._checks.keys())
        
        results = {}
        
        # Run checks concurrently
        tasks = [self.run_check(name) for name in check_names]
        check_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for name, result in zip(check_names, check_results):
            if isinstance(result, Exception):
                results[name] = HealthCheckResult(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Health check failed with exception: {result}",
                    details={"exception": str(result)}
                )
            else:
                results[name] = result
        
        return results
    
    def get_last_results(self) -> Dict[str, HealthCheckResult]:
        """Get the last results from all health checks.
        
        Returns:
            Dictionary mapping check names to last results
        """
        with self._lock:
            return self._last_results.copy()
    
    def get_overall_health(self) -> Dict[str, Any]:
        """Get overall health status.
        
        Returns:
            Dictionary containing overall health information
        """
        with self._lock:
            results = self._last_results.copy()
        
        if not results:
            return {
                "status": HealthStatus.UNKNOWN.value,
                "message": "No health checks have been run",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "checks": {}
            }
        
        # Determine overall status
        statuses = [result.status for result in results.values()]
        
        if any(status == HealthStatus.UNHEALTHY for status in statuses):
            overall_status = HealthStatus.UNHEALTHY
            message = "One or more health checks are unhealthy"
        elif any(status == HealthStatus.DEGRADED for status in statuses):
            overall_status = HealthStatus.DEGRADED
            message = "One or more health checks are degraded"
        elif any(status == HealthStatus.UNKNOWN for status in statuses):
            overall_status = HealthStatus.UNKNOWN
            message = "One or more health checks have unknown status"
        else:
            overall_status = HealthStatus.HEALTHY
            message = "All health checks are healthy"
        
        return {
            "status": overall_status.value,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": {name: result.to_dict() for name, result in results.items()}
        }
    
    def start_monitoring(self, interval: float = 60.0) -> None:
        """Start continuous health monitoring.
        
        Args:
            interval: Monitoring interval in seconds
        """
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            logger.warning("Health monitoring is already running")
            return
        
        self._monitoring_interval = interval
        self._monitoring_enabled = True
        self._stop_monitoring.clear()
        
        self._monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            name="HealthMonitor",
            daemon=True
        )
        self._monitoring_thread.start()
        
        logger.info(f"Health monitoring started with {interval}s interval")
    
    def stop_monitoring(self) -> None:
        """Stop continuous health monitoring."""
        if not self._monitoring_thread or not self._monitoring_thread.is_alive():
            return
        
        self._monitoring_enabled = False
        self._stop_monitoring.set()
        self._monitoring_thread.join(timeout=5.0)
        
        if self._monitoring_thread.is_alive():
            logger.warning("Health monitoring thread did not stop gracefully")
        else:
            logger.info("Health monitoring stopped")
    
    def _monitoring_loop(self) -> None:
        """Health monitoring loop that runs in a separate thread."""
        logger.info("Health monitoring loop started")
        
        while self._monitoring_enabled and not self._stop_monitoring.is_set():
            try:
                # Run health checks
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                results = loop.run_until_complete(self.run_all_checks())
                
                # Log overall health status
                overall_health = self.get_overall_health()
                logger.info(
                    f"Health monitoring cycle completed: {overall_health['status']}",
                    extra={
                        "overall_status": overall_health["status"],
                        "check_count": len(results),
                        "healthy_checks": sum(1 for r in results.values() if r.status == HealthStatus.HEALTHY),
                        "degraded_checks": sum(1 for r in results.values() if r.status == HealthStatus.DEGRADED),
                        "unhealthy_checks": sum(1 for r in results.values() if r.status == HealthStatus.UNHEALTHY)
                    }
                )
                
                loop.close()
                
                # Wait for next cycle
                if self._stop_monitoring.wait(timeout=self._monitoring_interval):
                    break
                    
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}", exc_info=True)
                time.sleep(5.0)  # Brief pause before retrying
        
        logger.info("Health monitoring loop stopped")
    
    def close(self) -> None:
        """Close the health check manager and cleanup resources."""
        self.stop_monitoring()
        
        with self._lock:
            self._checks.clear()
            self._last_results.clear()
        
        logger.info("Health check manager closed")


# Global health check manager instance
_health_check_manager: Optional[HealthCheckManager] = None


def get_health_check_manager() -> HealthCheckManager:
    """Get the global health check manager instance.
    
    Returns:
        HealthCheckManager instance
    """
    global _health_check_manager
    if _health_check_manager is None:
        _health_check_manager = HealthCheckManager()
    return _health_check_manager


def setup_health_checks(database=None, queue_service=None) -> HealthCheckManager:
    """Set up health checks for the queue manager.
    
    Args:
        database: Database instance for health checks
        queue_service: Queue service instance for health checks
        
    Returns:
        HealthCheckManager instance
    """
    manager = get_health_check_manager()
    
    # Register system resource check
    manager.register_check(SystemResourceHealthCheck())
    
    # Register database check if available
    if database:
        manager.register_check(DatabaseHealthCheck(database))
    
    # Register queue service check if available
    if queue_service:
        manager.register_check(QueueServiceHealthCheck(queue_service))
    
    return manager