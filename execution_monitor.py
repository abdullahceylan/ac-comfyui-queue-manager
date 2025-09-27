"""
Execution monitoring system for ComfyUI Queue Manager.
Monitors workflow execution status and provides real-time updates.
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Callable, Dict, List, Optional

from models import QueueStatus

logger = logging.getLogger(__name__)


class ExecutionMonitor:
    """
    Monitors workflow execution status and provides real-time updates.
    
    This class tracks running workflows, monitors their progress, and provides
    callbacks for status changes and completion events.
    """

    def __init__(self, queue_service=None, workflow_executor=None):
        """Initialize the execution monitor.
        
        Args:
            queue_service: Optional queue service for status updates
            workflow_executor: Optional workflow executor for execution monitoring
        """
        self.queue_service = queue_service
        self.workflow_executor = workflow_executor
        
        self._monitoring_thread: Optional[threading.Thread] = None
        self._stop_monitoring = threading.Event()
        self._lock = threading.RLock()
        
        # Monitoring state
        self._monitored_workflows: Dict[str, Dict[str, Any]] = {}
        self._status_callbacks: Dict[str, Callable] = {}
        self._monitoring_interval = 1.0  # seconds
        self._is_monitoring = False
        
        logger.info("Execution monitor initialized")

    def start_monitoring(self) -> bool:
        """Start the execution monitoring thread.
        
        Returns:
            True if monitoring was started successfully
        """
        with self._lock:
            if self._is_monitoring:
                logger.warning("Execution monitoring is already running")
                return True
            
            try:
                self._stop_monitoring.clear()
                self._monitoring_thread = threading.Thread(
                    target=self._monitoring_loop,
                    name="ExecutionMonitor",
                    daemon=True
                )
                self._monitoring_thread.start()
                self._is_monitoring = True
                
                logger.info("Execution monitoring started")
                return True
                
            except Exception as e:
                logger.error(f"Failed to start execution monitoring: {e}")
                return False

    def stop_monitoring(self) -> bool:
        """Stop the execution monitoring thread.
        
        Returns:
            True if monitoring was stopped successfully
        """
        with self._lock:
            if not self._is_monitoring:
                return True
            
            try:
                self._stop_monitoring.set()
                
                if self._monitoring_thread and self._monitoring_thread.is_alive():
                    self._monitoring_thread.join(timeout=5.0)
                    
                    if self._monitoring_thread.is_alive():
                        logger.warning("Monitoring thread did not stop gracefully")
                
                self._is_monitoring = False
                self._monitoring_thread = None
                
                logger.info("Execution monitoring stopped")
                return True
                
            except Exception as e:
                logger.error(f"Failed to stop execution monitoring: {e}")
                return False

    def is_monitoring(self) -> bool:
        """Check if execution monitoring is active."""
        return self._is_monitoring

    def set_monitoring_interval(self, interval: float) -> None:
        """Set the monitoring interval in seconds.
        
        Args:
            interval: Monitoring interval in seconds
        """
        if interval <= 0:
            raise ValueError("Monitoring interval must be positive")
        
        self._monitoring_interval = interval
        logger.info(f"Monitoring interval set to {interval} seconds")

    def add_workflow_to_monitor(self, workflow_id: str, workflow_info: Dict[str, Any]) -> None:
        """Add a workflow to the monitoring system.
        
        Args:
            workflow_id: Unique identifier for the workflow
            workflow_info: Information about the workflow
        """
        with self._lock:
            # Preserve existing added_at if provided, otherwise use current time
            added_at = workflow_info.get("added_at", datetime.now(timezone.utc))
            
            self._monitored_workflows[workflow_id] = {
                **workflow_info,
                "added_at": added_at,
                "last_checked": None,
                "check_count": 0,
            }
        
        logger.debug(f"Added workflow to monitor: {workflow_id}")

    def remove_workflow_from_monitor(self, workflow_id: str) -> bool:
        """Remove a workflow from the monitoring system.
        
        Args:
            workflow_id: Identifier of the workflow to remove
            
        Returns:
            True if the workflow was removed
        """
        with self._lock:
            removed = self._monitored_workflows.pop(workflow_id, None) is not None
        
        if removed:
            logger.debug(f"Removed workflow from monitor: {workflow_id}")
        
        return removed

    def register_status_callback(self, callback_id: str, callback: Callable) -> None:
        """Register a callback for status change events.
        
        Args:
            callback_id: Unique identifier for the callback
            callback: Function to call on status changes
        """
        self._status_callbacks[callback_id] = callback
        logger.debug(f"Registered status callback: {callback_id}")

    def unregister_status_callback(self, callback_id: str) -> None:
        """Unregister a status callback.
        
        Args:
            callback_id: Identifier of the callback to remove
        """
        self._status_callbacks.pop(callback_id, None)
        logger.debug(f"Unregistered status callback: {callback_id}")

    def get_monitored_workflows(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all monitored workflows.
        
        Returns:
            Dictionary mapping workflow IDs to their information
        """
        with self._lock:
            return {wf_id: info.copy() for wf_id, info in self._monitored_workflows.items()}

    def get_workflow_status(self, workflow_id: str) -> QueueStatus | None:
        """Get the current status of a monitored workflow.
        
        Args:
            workflow_id: The workflow ID
            
        Returns:
            Current status or None if not monitored
        """
        with self._lock:
            if workflow_id not in self._monitored_workflows:
                return None
            
            workflow_info = self._monitored_workflows[workflow_id]
            return workflow_info.get("status")

    def _monitoring_loop(self) -> None:
        """Main monitoring loop that runs in a separate thread."""
        logger.info("Execution monitoring loop started")
        
        try:
            while not self._stop_monitoring.is_set():
                try:
                    self._check_workflow_statuses()
                    
                    # Wait for the monitoring interval or stop signal
                    if self._stop_monitoring.wait(timeout=self._monitoring_interval):
                        break
                        
                except Exception as e:
                    logger.error(f"Error in monitoring loop: {e}")
                    # Continue monitoring even if there's an error
                    time.sleep(1.0)
        
        except Exception as e:
            logger.error(f"Fatal error in monitoring loop: {e}")
        
        finally:
            logger.info("Execution monitoring loop stopped")

    def _check_workflow_statuses(self) -> None:
        """Check the status of all monitored workflows."""
        with self._lock:
            workflows_to_check = list(self._monitored_workflows.items())
        
        for workflow_id, workflow_info in workflows_to_check:
            try:
                self._check_single_workflow_status(workflow_id, workflow_info)
            except Exception as e:
                logger.error(f"Error checking workflow {workflow_id}: {e}")

    def _check_single_workflow_status(self, workflow_id: str, workflow_info: Dict[str, Any]) -> None:
        """Check the status of a single workflow.
        
        Args:
            workflow_id: The workflow ID
            workflow_info: Current workflow information
        """
        old_status = workflow_info.get("status")
        new_status = None
        
        # Update check information
        now = datetime.now(timezone.utc)
        workflow_info["last_checked"] = now
        workflow_info["check_count"] = workflow_info.get("check_count", 0) + 1
        
        # Check status from workflow executor if available
        if self.workflow_executor:
            try:
                new_status = self.workflow_executor.get_workflow_status(workflow_id)
            except Exception as e:
                logger.error(f"Failed to get workflow status from executor: {e}")
        
        # Check status from queue service if available and executor didn't provide status
        if new_status is None and self.queue_service:
            try:
                queue_item_id = workflow_info.get("queue_item_id")
                if queue_item_id:
                    queue_item = self.queue_service.get_queue_item(queue_item_id)
                    if queue_item:
                        new_status = queue_item.status
            except Exception as e:
                logger.error(f"Failed to get workflow status from queue service: {e}")
        
        # Update status if it changed
        if new_status and new_status != old_status:
            workflow_info["status"] = new_status
            workflow_info["status_changed_at"] = now
            
            # Notify callbacks
            self._notify_status_callbacks(workflow_id, old_status, new_status, workflow_info)
            
            # Remove completed/failed workflows from monitoring after a delay
            if new_status in (QueueStatus.COMPLETED, QueueStatus.FAILED):
                self._schedule_workflow_removal(workflow_id)

    def _notify_status_callbacks(
        self, 
        workflow_id: str, 
        old_status: QueueStatus | None, 
        new_status: QueueStatus,
        workflow_info: Dict[str, Any]
    ) -> None:
        """Notify all registered callbacks about a status change.
        
        Args:
            workflow_id: The workflow ID
            old_status: Previous status
            new_status: New status
            workflow_info: Current workflow information
        """
        callback_data = {
            "workflow_id": workflow_id,
            "old_status": old_status.value if old_status else None,
            "new_status": new_status.value,
            "workflow_info": workflow_info.copy(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        for callback_id, callback in list(self._status_callbacks.items()):
            try:
                callback(callback_data)
            except Exception as e:
                logger.error(f"Error in status callback {callback_id}: {e}")

    def _schedule_workflow_removal(self, workflow_id: str, delay_seconds: float = 60.0) -> None:
        """Schedule a workflow for removal from monitoring after a delay.
        
        Args:
            workflow_id: The workflow ID
            delay_seconds: Delay before removal in seconds
        """
        def remove_after_delay():
            time.sleep(delay_seconds)
            self.remove_workflow_from_monitor(workflow_id)
        
        removal_thread = threading.Thread(
            target=remove_after_delay,
            name=f"RemoveWorkflow-{workflow_id}",
            daemon=True
        )
        removal_thread.start()

    def get_monitoring_statistics(self) -> Dict[str, Any]:
        """Get statistics about the monitoring system.
        
        Returns:
            Dictionary containing monitoring statistics
        """
        with self._lock:
            stats = {
                "is_monitoring": self._is_monitoring,
                "monitoring_interval": self._monitoring_interval,
                "monitored_workflows": len(self._monitored_workflows),
                "registered_callbacks": len(self._status_callbacks),
                "status_counts": {},
            }
            
            # Count workflows by status
            for workflow_info in self._monitored_workflows.values():
                status = workflow_info.get("status")
                if status:
                    status_value = status.value if hasattr(status, 'value') else str(status)
                    stats["status_counts"][status_value] = stats["status_counts"].get(status_value, 0) + 1
            
            return stats

    def cleanup_old_workflows(self, max_age_hours: int = 24) -> int:
        """Clean up old workflow monitoring records.
        
        Args:
            max_age_hours: Maximum age in hours for workflow records
            
        Returns:
            Number of workflows cleaned up
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        cleaned_count = 0
        
        with self._lock:
            workflows_to_remove = []
            
            for workflow_id, workflow_info in self._monitored_workflows.items():
                added_at = workflow_info.get("added_at")
                if added_at and added_at < cutoff_time:
                    # Only remove completed or failed workflows
                    status = workflow_info.get("status")
                    if status in (QueueStatus.COMPLETED, QueueStatus.FAILED):
                        workflows_to_remove.append(workflow_id)
            
            for workflow_id in workflows_to_remove:
                del self._monitored_workflows[workflow_id]
                cleaned_count += 1
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} old workflow monitoring records")
        
        return cleaned_count

    def close(self) -> None:
        """Close the execution monitor and clean up resources."""
        self.stop_monitoring()
        
        with self._lock:
            self._monitored_workflows.clear()
            self._status_callbacks.clear()
        
        logger.info("Execution monitor closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()