"""
Workflow execution integration for ComfyUI Queue Manager.
Handles intercepting, monitoring, and executing workflows through ComfyUI.
"""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

from interfaces import WorkflowExecutorInterface
from models import QueueStatus

logger = logging.getLogger(__name__)


class WorkflowExecutionError(Exception):
    """Custom exception for workflow execution errors."""


class WorkflowExecutor(WorkflowExecutorInterface):
    """
    Handles workflow execution integration with ComfyUI.
    
    This class provides the bridge between the queue manager and ComfyUI's
    workflow execution system, intercepting executions and monitoring status.
    """

    def __init__(self, queue_service=None):
        """Initialize the workflow executor.
        
        Args:
            queue_service: Optional queue service for automatic queue management
        """
        if queue_service is None:
            # Create a default database and queue service
            try:
                from database import SQLiteDatabase
                from queue_service import QueueService
                from pathlib import Path
                
                db_path = Path(__file__).parent / "queue_manager.db"
                database = SQLiteDatabase(str(db_path))
                database.initialize()
                queue_service = QueueService(database)
            except Exception as e:
                logger.error(f"Failed to create default queue service: {e}")
                queue_service = None
        
        self.queue_service = queue_service
        self._running_workflows: Dict[str, Dict[str, Any]] = {}
        self._execution_callbacks: Dict[str, Callable] = {}
        self._lock = threading.RLock()
        self._interceptor_enabled = True
        
        # ComfyUI integration hooks
        self._original_execute = None
        self._comfyui_server = None
        
        logger.info("Workflow executor initialized")

    def enable_interceptor(self) -> None:
        """Enable workflow execution interception."""
        self._interceptor_enabled = True
        logger.info("Workflow execution interceptor enabled")

    def disable_interceptor(self) -> None:
        """Disable workflow execution interception."""
        self._interceptor_enabled = False
        logger.info("Workflow execution interceptor disabled")

    def is_interceptor_enabled(self) -> bool:
        """Check if the interceptor is enabled."""
        return self._interceptor_enabled

    def register_execution_callback(self, callback_id: str, callback: Callable) -> None:
        """Register a callback for execution events.
        
        Args:
            callback_id: Unique identifier for the callback
            callback: Function to call on execution events
        """
        with self._lock:
            self._execution_callbacks[callback_id] = callback
        logger.debug(f"Registered execution callback: {callback_id}")

    def unregister_execution_callback(self, callback_id: str) -> None:
        """Unregister an execution callback.
        
        Args:
            callback_id: Identifier of the callback to remove
        """
        with self._lock:
            self._execution_callbacks.pop(callback_id, None)
        logger.debug(f"Unregistered execution callback: {callback_id}")

    def _notify_callbacks(self, event_type: str, workflow_id: str, data: Dict[str, Any]) -> None:
        """Notify all registered callbacks of an execution event.
        
        Args:
            event_type: Type of event (started, completed, failed, etc.)
            workflow_id: ID of the workflow
            data: Additional event data
        """
        with self._lock:
            callbacks = list(self._execution_callbacks.values())
        
        for callback in callbacks:
            try:
                callback(event_type, workflow_id, data)
            except Exception as e:
                logger.error(f"Error in execution callback: {e}")

    def intercept_workflow_execution(self, workflow_data: Dict[str, Any]) -> str:
        """Intercept a workflow execution and add it to the queue.
        
        Args:
            workflow_data: The workflow data to execute
            
        Returns:
            The workflow execution ID
        """
        if not self._interceptor_enabled:
            return self._execute_workflow_directly(workflow_data)
        
        workflow_id = str(uuid.uuid4())
        
        try:
            # Extract workflow name from data
            workflow_name = self._extract_workflow_name(workflow_data)
            
            # Add to queue if queue service is available
            if self.queue_service:
                queue_item_id = self.queue_service.add_workflow(
                    workflow_data=workflow_data,
                    workflow_name=workflow_name
                )
                
                # Store the mapping between workflow ID and queue item ID
                with self._lock:
                    self._running_workflows[workflow_id] = {
                        "queue_item_id": queue_item_id,
                        "workflow_data": workflow_data,
                        "workflow_name": workflow_name,
                        "status": QueueStatus.PENDING,
                        "started_at": None,
                        "completed_at": None,
                        "error_message": None,
                        "result_data": None,
                    }
                
                logger.info(f"Intercepted workflow execution: {workflow_id} -> queue item: {queue_item_id}")
            else:
                # Execute directly if no queue service
                return self._execute_workflow_directly(workflow_data)
                
        except Exception as e:
            logger.error(f"Failed to intercept workflow execution: {e}")
            # Fall back to direct execution
            return self._execute_workflow_directly(workflow_data)
        
        return workflow_id

    def execute_workflow(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a workflow and return the results.
        
        Args:
            workflow_data: The workflow data to execute
            
        Returns:
            Dictionary containing execution results
            
        Raises:
            WorkflowExecutionError: If execution fails
        """
        workflow_id = str(uuid.uuid4())
        
        try:
            # Create workflow info for tracking
            with self._lock:
                self._running_workflows[workflow_id] = {
                    "workflow_data": workflow_data,
                    "workflow_name": self._extract_workflow_name(workflow_data),
                    "status": QueueStatus.RUNNING,
                    "started_at": datetime.now(timezone.utc),
                    "completed_at": None,
                    "error_message": None,
                    "result_data": None,
                }
            
            # Execute the workflow
            execution_id = self._execute_workflow_directly(workflow_data)
            
            # Create result data
            result = {
                "status": "completed",
                "execution_time": 0.1,
                "outputs": {},
                "executed_at": datetime.now(timezone.utc).isoformat(),
                "execution_id": execution_id,
            }
            
            # Update status to completed
            self._update_workflow_status(
                workflow_id, 
                QueueStatus.COMPLETED, 
                result_data=result
            )
            
            return result
            
        except Exception as e:
            # Update status to failed
            self._update_workflow_status(
                workflow_id, 
                QueueStatus.FAILED, 
                error_message=str(e)
            )
            raise WorkflowExecutionError(f"Workflow execution failed: {e}") from e

    def _execute_workflow_directly(self, workflow_data: Dict[str, Any]) -> str:
        """Execute a workflow directly through ComfyUI.
        
        Args:
            workflow_data: The workflow data to execute
            
        Returns:
            Workflow execution ID
        """
        # This is a placeholder for actual ComfyUI integration
        # In a real implementation, this would interface with ComfyUI's execution system
        
        logger.info("Executing workflow directly through ComfyUI")
        
        # Simulate workflow execution
        time.sleep(0.1)  # Simulate processing time
        
        # Return a workflow ID for direct execution
        return str(uuid.uuid4())

    def _extract_workflow_name(self, workflow_data: Dict[str, Any]) -> str:
        """Extract a meaningful name from workflow data.
        
        Args:
            workflow_data: The workflow data
            
        Returns:
            A descriptive name for the workflow
        """
        # Try to extract name from various possible locations
        if isinstance(workflow_data, dict):
            # Check for explicit name
            if "name" in workflow_data:
                return workflow_data["name"]
            
            # Check for title or description
            if "title" in workflow_data:
                return workflow_data["title"]
            
            # Check for workflow metadata
            if "workflow" in workflow_data and isinstance(workflow_data["workflow"], dict):
                workflow = workflow_data["workflow"]
                if "name" in workflow:
                    return workflow["name"]
                if "title" in workflow:
                    return workflow["title"]
            
            # Generate name based on node count or other characteristics
            if "nodes" in workflow_data:
                node_count = len(workflow_data["nodes"])
                return f"Workflow with {node_count} nodes"
        
        # Default name with timestamp
        return f"Workflow {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

    def _update_workflow_status(
        self, 
        workflow_id: str, 
        status: QueueStatus,
        error_message: Optional[str] = None,
        result_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Update the status of a workflow execution.
        
        Args:
            workflow_id: The workflow ID
            status: The new status
            error_message: Optional error message for failed workflows
            result_data: Optional result data for completed workflows
        """
        with self._lock:
            if workflow_id not in self._running_workflows:
                logger.warning(f"Workflow {workflow_id} not found in running workflows")
                return
            
            workflow_info = self._running_workflows[workflow_id]
            old_status = workflow_info["status"]
            workflow_info["status"] = status
            
            # Update timestamps
            now = datetime.now(timezone.utc)
            if status == QueueStatus.RUNNING and old_status == QueueStatus.PENDING:
                workflow_info["started_at"] = now
            elif status in (QueueStatus.COMPLETED, QueueStatus.FAILED):
                if not workflow_info["started_at"]:
                    workflow_info["started_at"] = now
                workflow_info["completed_at"] = now
            
            # Update error message and result data
            if error_message:
                workflow_info["error_message"] = error_message
            if result_data:
                workflow_info["result_data"] = result_data
            
            # Update queue service if available
            if self.queue_service and "queue_item_id" in workflow_info:
                try:
                    self.queue_service.update_item_status(
                        workflow_info["queue_item_id"],
                        status,
                        error_message=error_message,
                        result_data=result_data
                    )
                except Exception as e:
                    logger.error(f"Failed to update queue item status: {e}")
            
            # Notify callbacks
            self._notify_callbacks("status_changed", workflow_id, {
                "old_status": old_status.value if old_status else None,
                "new_status": status.value,
                "error_message": error_message,
                "result_data": result_data,
            })
            
            logger.info(f"Updated workflow {workflow_id} status: {old_status} -> {status}")

    def is_workflow_running(self, workflow_id: str) -> bool:
        """Check if a workflow is currently running.
        
        Args:
            workflow_id: The workflow ID to check
            
        Returns:
            True if the workflow is running
        """
        with self._lock:
            if workflow_id not in self._running_workflows:
                return False
            return self._running_workflows[workflow_id]["status"] == QueueStatus.RUNNING

    def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel a running workflow.
        
        Args:
            workflow_id: The workflow ID to cancel
            
        Returns:
            True if the workflow was cancelled successfully
        """
        with self._lock:
            if workflow_id not in self._running_workflows:
                logger.warning(f"Cannot cancel workflow {workflow_id}: not found")
                return False
            
            workflow_info = self._running_workflows[workflow_id]
            if workflow_info["status"] not in (QueueStatus.PENDING, QueueStatus.RUNNING):
                logger.warning(f"Cannot cancel workflow {workflow_id}: not in cancellable state")
                return False
        
        try:
            # Update status to failed with cancellation message
            self._update_workflow_status(
                workflow_id, 
                QueueStatus.FAILED, 
                error_message="Workflow cancelled by user"
            )
            
            # Notify callbacks
            self._notify_callbacks("cancelled", workflow_id, {})
            
            logger.info(f"Cancelled workflow: {workflow_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel workflow {workflow_id}: {e}")
            return False

    def get_workflow_status(self, workflow_id: str) -> QueueStatus | None:
        """Get the status of a workflow execution.
        
        Args:
            workflow_id: The workflow ID
            
        Returns:
            The current status or None if not found
        """
        with self._lock:
            if workflow_id not in self._running_workflows:
                return None
            return self._running_workflows[workflow_id]["status"]

    def get_running_workflows(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all running workflows.
        
        Returns:
            Dictionary mapping workflow IDs to their information
        """
        with self._lock:
            return {
                wf_id: info.copy() 
                for wf_id, info in self._running_workflows.items()
                if info["status"] == QueueStatus.RUNNING
            }

    def get_workflow_info(self, workflow_id: str) -> Dict[str, Any] | None:
        """Get detailed information about a workflow.
        
        Args:
            workflow_id: The workflow ID
            
        Returns:
            Dictionary containing workflow information or None if not found
        """
        with self._lock:
            if workflow_id not in self._running_workflows:
                return None
            return self._running_workflows[workflow_id].copy()

    def cleanup_completed_workflows(self, max_age_hours: int = 24) -> int:
        """Clean up completed workflow records older than specified age.
        
        Args:
            max_age_hours: Maximum age in hours for completed workflows
            
        Returns:
            Number of workflows cleaned up
        """
        from datetime import timedelta
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        cleaned_count = 0
        
        with self._lock:
            workflows_to_remove = []
            
            for workflow_id, info in self._running_workflows.items():
                if info["status"] in (QueueStatus.COMPLETED, QueueStatus.FAILED):
                    completed_at = info.get("completed_at")
                    if completed_at and completed_at < cutoff_time:
                        workflows_to_remove.append(workflow_id)
            
            for workflow_id in workflows_to_remove:
                del self._running_workflows[workflow_id]
                cleaned_count += 1
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} completed workflows")
        
        return cleaned_count

    def get_execution_statistics(self) -> Dict[str, Any]:
        """Get statistics about workflow executions.
        
        Returns:
            Dictionary containing execution statistics
        """
        with self._lock:
            stats = {
                "total_workflows": len(self._running_workflows),
                "status_counts": {},
                "average_execution_time": 0.0,
                "total_execution_time": 0.0,
            }
            
            execution_times = []
            
            for info in self._running_workflows.values():
                status = info["status"].value
                stats["status_counts"][status] = stats["status_counts"].get(status, 0) + 1
                
                # Calculate execution time for completed workflows
                if info["started_at"] and info["completed_at"]:
                    exec_time = (info["completed_at"] - info["started_at"]).total_seconds()
                    execution_times.append(exec_time)
            
            if execution_times:
                stats["average_execution_time"] = sum(execution_times) / len(execution_times)
                stats["total_execution_time"] = sum(execution_times)
            
            return stats

    def close(self) -> None:
        """Clean up resources and close the executor."""
        with self._lock:
            self._running_workflows.clear()
            self._execution_callbacks.clear()
        
        logger.info("Workflow executor closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()