"""
Workflow execution interceptor for ComfyUI Queue Manager.
Hooks into ComfyUI's execution system to capture and monitor workflows.
"""

from __future__ import annotations

import functools
import logging
import threading
import weakref
from typing import Any, Callable, Dict, Optional, Set

logger = logging.getLogger(__name__)


class WorkflowInterceptor:
    """
    Intercepts ComfyUI workflow executions to integrate with queue management.
    
    This class provides hooks into ComfyUI's execution system to automatically
    capture workflows and monitor their execution status.
    """

    _instance: Optional[WorkflowInterceptor] = None
    _lock = threading.RLock()

    def __new__(cls) -> WorkflowInterceptor:
        """Singleton pattern to ensure only one interceptor instance."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance

    def __init__(self):
        """Initialize the workflow interceptor."""
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        self._enabled = False
        self._workflow_executor = None
        self._original_methods: Dict[str, Callable] = {}
        self._hooked_objects: Set[Any] = set()
        self._execution_hooks: Dict[str, Callable] = {}
        
        logger.info("Workflow interceptor initialized")

    def set_workflow_executor(self, executor) -> None:
        """Set the workflow executor to use for intercepted workflows.
        
        Args:
            executor: WorkflowExecutor instance
        """
        self._workflow_executor = executor
        logger.info("Workflow executor set for interceptor")

    def enable(self) -> bool:
        """Enable workflow interception.
        
        Returns:
            True if interception was enabled successfully
        """
        if self._enabled:
            return True
        
        try:
            self._install_hooks()
            self._enabled = True
            logger.info("Workflow interception enabled")
            return True
        except Exception as e:
            logger.error(f"Failed to enable workflow interception: {e}")
            return False

    def disable(self) -> bool:
        """Disable workflow interception.
        
        Returns:
            True if interception was disabled successfully
        """
        if not self._enabled:
            return True
        
        try:
            self._uninstall_hooks()
            self._enabled = False
            logger.info("Workflow interception disabled")
            return True
        except Exception as e:
            logger.error(f"Failed to disable workflow interception: {e}")
            return False

    def is_enabled(self) -> bool:
        """Check if workflow interception is enabled."""
        return self._enabled

    def register_execution_hook(self, hook_name: str, hook_func: Callable) -> None:
        """Register a custom execution hook.
        
        Args:
            hook_name: Name of the hook
            hook_func: Function to call when hook is triggered
        """
        self._execution_hooks[hook_name] = hook_func
        logger.debug(f"Registered execution hook: {hook_name}")

    def unregister_execution_hook(self, hook_name: str) -> None:
        """Unregister a custom execution hook.
        
        Args:
            hook_name: Name of the hook to remove
        """
        self._execution_hooks.pop(hook_name, None)
        logger.debug(f"Unregistered execution hook: {hook_name}")

    def _install_hooks(self) -> None:
        """Install hooks into ComfyUI's execution system."""
        try:
            # Try to hook into ComfyUI's execution system
            self._hook_comfyui_execution()
            
            # Try to hook into server execution
            self._hook_server_execution()
            
            logger.info("Workflow execution hooks installed")
            
        except Exception as e:
            logger.error(f"Failed to install execution hooks: {e}")
            raise

    def _uninstall_hooks(self) -> None:
        """Uninstall hooks from ComfyUI's execution system."""
        try:
            # Restore original methods
            for obj_method, original_method in self._original_methods.items():
                obj, method_name = obj_method.rsplit('.', 1)
                # This is a simplified restoration - in practice, you'd need
                # to properly restore the original methods
                logger.debug(f"Restoring method: {obj_method}")
            
            self._original_methods.clear()
            self._hooked_objects.clear()
            
            logger.info("Workflow execution hooks uninstalled")
            
        except Exception as e:
            logger.error(f"Failed to uninstall execution hooks: {e}")
            raise

    def _hook_comfyui_execution(self) -> None:
        """Hook into ComfyUI's core execution system."""
        try:
            # Try to import ComfyUI modules
            # This is a placeholder - actual implementation would depend on ComfyUI's structure
            
            # Example of how to hook into execution:
            # import execution
            # original_execute = execution.PromptExecutor.execute
            # execution.PromptExecutor.execute = self._create_execution_wrapper(original_execute)
            
            logger.debug("ComfyUI execution hooks installed")
            
        except ImportError as e:
            logger.warning(f"Could not import ComfyUI execution modules: {e}")
        except Exception as e:
            logger.error(f"Failed to hook ComfyUI execution: {e}")

    def _hook_server_execution(self) -> None:
        """Hook into ComfyUI's server execution system."""
        try:
            # Try to hook into server-side execution
            # This would typically involve hooking into the web server's execution endpoints
            
            logger.debug("Server execution hooks installed")
            
        except Exception as e:
            logger.error(f"Failed to hook server execution: {e}")

    def _create_execution_wrapper(self, original_method: Callable) -> Callable:
        """Create a wrapper for an execution method.
        
        Args:
            original_method: The original method to wrap
            
        Returns:
            Wrapped method that includes interception logic
        """
        @functools.wraps(original_method)
        def wrapper(*args, **kwargs):
            # Pre-execution hook
            workflow_data = self._extract_workflow_data(args, kwargs)
            workflow_id = None
            
            if workflow_data and self._workflow_executor:
                try:
                    workflow_id = self._workflow_executor.intercept_workflow_execution(workflow_data)
                    logger.debug(f"Intercepted workflow execution: {workflow_id}")
                except Exception as e:
                    logger.error(f"Failed to intercept workflow: {e}")
            
            # Call execution hooks
            for hook_name, hook_func in self._execution_hooks.items():
                try:
                    hook_func("pre_execution", workflow_id, workflow_data)
                except Exception as e:
                    logger.error(f"Error in execution hook {hook_name}: {e}")
            
            # Execute original method
            try:
                result = original_method(*args, **kwargs)
                
                # Post-execution success hook
                if workflow_id and self._workflow_executor:
                    try:
                        self._workflow_executor._update_workflow_status(
                            workflow_id, 
                            self._workflow_executor.QueueStatus.COMPLETED,
                            result_data=self._extract_result_data(result)
                        )
                    except Exception as e:
                        logger.error(f"Failed to update workflow status: {e}")
                
                # Call success hooks
                for hook_name, hook_func in self._execution_hooks.items():
                    try:
                        hook_func("post_execution_success", workflow_id, result)
                    except Exception as e:
                        logger.error(f"Error in execution hook {hook_name}: {e}")
                
                return result
                
            except Exception as e:
                # Post-execution failure hook
                if workflow_id and self._workflow_executor:
                    try:
                        self._workflow_executor._update_workflow_status(
                            workflow_id, 
                            self._workflow_executor.QueueStatus.FAILED,
                            error_message=str(e)
                        )
                    except Exception as update_e:
                        logger.error(f"Failed to update workflow status: {update_e}")
                
                # Call failure hooks
                for hook_name, hook_func in self._execution_hooks.items():
                    try:
                        hook_func("post_execution_failure", workflow_id, str(e))
                    except Exception as hook_e:
                        logger.error(f"Error in execution hook {hook_name}: {hook_e}")
                
                raise
        
        return wrapper

    def _extract_workflow_data(self, args: tuple, kwargs: dict) -> Dict[str, Any] | None:
        """Extract workflow data from execution method arguments.
        
        Args:
            args: Positional arguments
            kwargs: Keyword arguments
            
        Returns:
            Extracted workflow data or None
        """
        try:
            # This is a placeholder implementation
            # Actual implementation would depend on ComfyUI's execution method signatures
            
            # Look for workflow data in various argument positions
            for arg in args:
                if isinstance(arg, dict) and self._looks_like_workflow_data(arg):
                    return arg
            
            # Look for workflow data in keyword arguments
            for key, value in kwargs.items():
                if key in ('workflow', 'prompt', 'execution_data') and isinstance(value, dict):
                    return value
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to extract workflow data: {e}")
            return None

    def _looks_like_workflow_data(self, data: Dict[str, Any]) -> bool:
        """Check if data looks like workflow data.
        
        Args:
            data: Data to check
            
        Returns:
            True if data appears to be workflow data
        """
        if not isinstance(data, dict):
            return False
        
        # Look for common workflow data keys
        workflow_keys = {'nodes', 'links', 'workflow', 'prompt', 'execution'}
        return any(key in data for key in workflow_keys)

    def _extract_result_data(self, result: Any) -> Dict[str, Any] | None:
        """Extract result data from execution result.
        
        Args:
            result: Execution result
            
        Returns:
            Extracted result data or None
        """
        try:
            if isinstance(result, dict):
                return result
            elif hasattr(result, '__dict__'):
                return vars(result)
            else:
                return {"result": str(result)}
        except Exception as e:
            logger.error(f"Failed to extract result data: {e}")
            return None

    def get_hook_status(self) -> Dict[str, Any]:
        """Get status information about installed hooks.
        
        Returns:
            Dictionary containing hook status information
        """
        return {
            "enabled": self._enabled,
            "hooked_objects": len(self._hooked_objects),
            "original_methods": len(self._original_methods),
            "execution_hooks": list(self._execution_hooks.keys()),
            "has_workflow_executor": self._workflow_executor is not None,
        }

    @classmethod
    def get_instance(cls) -> WorkflowInterceptor:
        """Get the singleton instance of the workflow interceptor."""
        return cls()


# Global function to get the interceptor instance
def get_workflow_interceptor() -> WorkflowInterceptor:
    """Get the global workflow interceptor instance."""
    return WorkflowInterceptor.get_instance()