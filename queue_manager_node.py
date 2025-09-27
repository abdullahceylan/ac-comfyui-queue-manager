"""
Main ComfyUI custom node for the Queue Manager.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, Optional

from models import QueueStatus


class QueueManagerNode:
    """
    ComfyUI custom node for queue management functionality.
    This node serves as the entry point for the queue manager system.
    """

    @classmethod
    def INPUT_TYPES(cls) -> dict[str, Any]:  # noqa: N802
        """Define the input types for the node."""
        return {
            "required": {},
            "optional": {
                "workflow_name": ("STRING", {"default": "Workflow"}),
                "auto_queue": ("BOOLEAN", {"default": True}),
                "priority": ("INT", {"default": 0, "min": -10, "max": 10}),
                "tags": ("STRING", {"default": ""}),
            },
        }

    RETURN_TYPES = ("STRING", "BOOLEAN")
    RETURN_NAMES = ("queue_item_id", "queued_successfully")
    FUNCTION = "process"
    CATEGORY = "Queue Management"
    DESCRIPTION = (
        "Manages workflow execution queues with persistence and control features. "
        "Automatically captures and queues workflows for later execution."
    )
    
    # ComfyUI node metadata
    OUTPUT_NODE = False
    
    def __init__(self):
        """Initialize the queue manager node."""
        self._queue_service = None
        self._workflow_executor = None
        self._execution_monitor = None

    @property
    def queue_service(self):
        """Lazy initialization of queue service."""
        if self._queue_service is None:
            try:
                from database import SQLiteDatabase
                from queue_service import QueueService
                from pathlib import Path
                
                # Initialize database and queue service
                db_path = Path(__file__).parent / "queue_manager.db"
                database = SQLiteDatabase(str(db_path))
                database.initialize()
                self._queue_service = QueueService(database)
                
                # Initialize workflow execution components
                self._initialize_workflow_execution()
                
            except Exception as e:
                print(f"[Queue Manager] Failed to initialize queue service: {e}")
                # Don't set to None, leave it as None to indicate failure
                return None
        return self._queue_service

    def _initialize_workflow_execution(self):
        """Initialize workflow execution integration components."""
        try:
            from workflow_executor import WorkflowExecutor
            from execution_monitor import ExecutionMonitor
            from workflow_interceptor import get_workflow_interceptor
            
            # Initialize workflow executor
            self._workflow_executor = WorkflowExecutor(self._queue_service)
            
            # Initialize execution monitor
            self._execution_monitor = ExecutionMonitor(
                queue_service=self._queue_service,
                workflow_executor=self._workflow_executor
            )
            
            # Set up workflow interceptor
            interceptor = get_workflow_interceptor()
            interceptor.set_workflow_executor(self._workflow_executor)
            
            # Start execution monitoring
            self._execution_monitor.start_monitoring()
            
            # Enable workflow interception
            interceptor.enable()
            
            print("[Queue Manager] Workflow execution integration initialized")
            
        except Exception as e:
            print(f"[Queue Manager] Failed to initialize workflow execution: {e}")
            # Continue without workflow execution integration

    def process(
        self, 
        workflow_name: str = "Workflow", 
        auto_queue: bool = True,
        priority: int = 0,
        tags: str = ""
    ) -> tuple[str, bool]:
        """
        Process the node execution and optionally add to queue.

        Args:
            workflow_name: Name for the workflow
            auto_queue: Whether to automatically add to queue
            priority: Priority level for queue processing
            tags: Comma-separated tags for the workflow

        Returns:
            Tuple containing (queue_item_id, queued_successfully)
        """
        queue_item_id = str(uuid.uuid4())
        queued_successfully = False
        
        if auto_queue and self.queue_service:
            try:
                # Create workflow data structure
                workflow_data = {
                    "name": workflow_name,
                    "priority": priority,
                    "tags": [tag.strip() for tag in tags.split(",") if tag.strip()],
                    "created_at": datetime.now().isoformat(),
                    "node_id": queue_item_id,
                }
                
                # Add to queue
                actual_id = self.queue_service.add_workflow(workflow_data)
                if actual_id:
                    queue_item_id = actual_id
                    queued_successfully = True
                    print(f"[Queue Manager] Added workflow '{workflow_name}' to queue: {queue_item_id}")
                else:
                    print(f"[Queue Manager] Failed to add workflow '{workflow_name}' to queue")
                    
            except Exception as e:
                print(f"[Queue Manager] Error adding workflow to queue: {e}")
        
        elif not auto_queue:
            print(f"[Queue Manager] Auto-queue disabled for workflow '{workflow_name}'")
        
        return (queue_item_id, queued_successfully)

    @classmethod
    def IS_CHANGED(cls, **kwargs: Any) -> float:  # noqa: N802
        """
        Determine if the node needs to be re-executed.
        
        For queue management, we want to execute every time to capture workflows.
        """
        # Return NaN to always execute
        return float("nan")

    @classmethod
    def VALIDATE_INPUTS(cls, **kwargs: Any) -> bool:  # noqa: N802
        """Validate the inputs to the node."""
        # Basic validation
        workflow_name = kwargs.get("workflow_name", "")
        priority = kwargs.get("priority", 0)
        
        # Validate workflow name is not empty if provided
        if workflow_name and not isinstance(workflow_name, str):
            return False
            
        # Validate priority is within range
        if not isinstance(priority, int) or priority < -10 or priority > 10:
            return False
            
        return True

    def get_queue_status(self) -> dict[str, Any]:
        """
        Get current queue status information.
        
        Returns:
            Dictionary containing queue status information
        """
        if not self.queue_service:
            return {"error": "Queue service not available"}
            
        try:
            items = self.queue_service.get_queue_items()
            status_counts = {}
            
            for item in items:
                status = item.status.value
                status_counts[status] = status_counts.get(status, 0) + 1
                
            # Check if pause functionality is available
            is_paused = False
            if hasattr(self.queue_service, 'is_paused'):
                is_paused = self.queue_service.is_paused()
                
            return {
                "total_items": len(items),
                "status_counts": status_counts,
                "is_paused": is_paused,
            }
        except Exception as e:
            return {"error": f"Failed to get queue status: {e}"}

    def get_workflow_executor(self):
        """Get the workflow executor instance."""
        # Ensure queue service is initialized
        _ = self.queue_service
        return self._workflow_executor

    def get_execution_monitor(self):
        """Get the execution monitor instance."""
        # Ensure queue service is initialized
        _ = self.queue_service
        return self._execution_monitor

    def execute_workflow_directly(self, workflow_data: dict[str, Any]) -> dict[str, Any]:
        """Execute a workflow directly through the workflow executor.
        
        Args:
            workflow_data: The workflow data to execute
            
        Returns:
            Dictionary containing execution results
        """
        if not self._workflow_executor:
            raise RuntimeError("Workflow executor not initialized")
        
        try:
            return self._workflow_executor.execute_workflow(workflow_data)
        except Exception as e:
            print(f"[Queue Manager] Failed to execute workflow: {e}")
            raise

    def get_execution_statistics(self) -> dict[str, Any]:
        """Get statistics about workflow executions.
        
        Returns:
            Dictionary containing execution statistics
        """
        stats = {}
        
        if self._workflow_executor:
            stats["executor"] = self._workflow_executor.get_execution_statistics()
        
        if self._execution_monitor:
            stats["monitor"] = self._execution_monitor.get_monitoring_statistics()
        
        return stats

    def cleanup_execution_resources(self) -> dict[str, int]:
        """Clean up old execution resources.
        
        Returns:
            Dictionary containing cleanup counts
        """
        cleanup_counts = {}
        
        if self._workflow_executor:
            try:
                count = self._workflow_executor.cleanup_completed_workflows()
                cleanup_counts["executor_workflows"] = count
            except Exception as e:
                print(f"[Queue Manager] Failed to cleanup executor workflows: {e}")
        
        if self._execution_monitor:
            try:
                count = self._execution_monitor.cleanup_old_workflows()
                cleanup_counts["monitor_workflows"] = count
            except Exception as e:
                print(f"[Queue Manager] Failed to cleanup monitor workflows: {e}")
        
        return cleanup_counts

    @classmethod
    def get_node_info(cls) -> dict[str, Any]:
        """
        Get information about this node for ComfyUI.
        
        Returns:
            Dictionary containing node information
        """
        return {
            "name": "QueueManagerNode",
            "display_name": "Queue Manager",
            "category": "Queue Management",
            "description": cls.DESCRIPTION,
            "version": "1.0.0",
            "author": "ComfyUI Queue Manager",
            "input_types": cls.INPUT_TYPES(),
            "return_types": cls.RETURN_TYPES,
            "return_names": cls.RETURN_NAMES,
        }
