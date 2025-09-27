"""
Integration tests for workflow execution functionality.
Tests the workflow executor, interceptor, and execution monitor.
"""

import json
import pytest
import threading
import time
import uuid
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock

from database import SQLiteDatabase
from execution_monitor import ExecutionMonitor
from models import QueueStatus
from queue_service import QueueService
from workflow_executor import WorkflowExecutor, WorkflowExecutionError
from workflow_interceptor import WorkflowInterceptor, get_workflow_interceptor


class TestWorkflowExecutor:
    """Test cases for the WorkflowExecutor class."""

    @pytest.fixture
    def database(self):
        """Create a test database."""
        db = SQLiteDatabase(":memory:")
        db.initialize()
        return db

    @pytest.fixture
    def queue_service(self, database):
        """Create a test queue service."""
        return QueueService(database)

    @pytest.fixture
    def workflow_executor(self, queue_service):
        """Create a test workflow executor."""
        return WorkflowExecutor(queue_service)

    @pytest.fixture
    def sample_workflow_data(self):
        """Create sample workflow data for testing."""
        return {
            "name": "Test Workflow",
            "nodes": [
                {"id": "1", "type": "LoadImage", "inputs": {}},
                {"id": "2", "type": "SaveImage", "inputs": {"images": ["1", 0]}},
            ],
            "links": [["1", 0, "2", 0]],
            "workflow": {"version": "1.0"},
        }

    def test_workflow_executor_initialization(self, queue_service):
        """Test workflow executor initialization."""
        executor = WorkflowExecutor(queue_service)
        
        assert executor.queue_service == queue_service
        assert executor._interceptor_enabled is True
        assert len(executor._running_workflows) == 0
        assert len(executor._execution_callbacks) == 0

    def test_workflow_executor_without_queue_service(self):
        """Test workflow executor initialization without queue service."""
        executor = WorkflowExecutor()
        
        assert executor.queue_service is not None  # Should create default database
        assert executor._interceptor_enabled is True

    def test_enable_disable_interceptor(self, workflow_executor):
        """Test enabling and disabling the workflow interceptor."""
        # Test initial state
        assert workflow_executor.is_interceptor_enabled() is True
        
        # Test disabling
        workflow_executor.disable_interceptor()
        assert workflow_executor.is_interceptor_enabled() is False
        
        # Test enabling
        workflow_executor.enable_interceptor()
        assert workflow_executor.is_interceptor_enabled() is True

    def test_register_execution_callback(self, workflow_executor):
        """Test registering and unregistering execution callbacks."""
        callback_called = []
        
        def test_callback(event_type, workflow_id, data):
            callback_called.append((event_type, workflow_id, data))
        
        # Register callback
        workflow_executor.register_execution_callback("test", test_callback)
        assert "test" in workflow_executor._execution_callbacks
        
        # Test callback notification
        workflow_executor._notify_callbacks("test_event", "test_id", {"test": "data"})
        assert len(callback_called) == 1
        assert callback_called[0] == ("test_event", "test_id", {"test": "data"})
        
        # Unregister callback
        workflow_executor.unregister_execution_callback("test")
        assert "test" not in workflow_executor._execution_callbacks

    def test_intercept_workflow_execution(self, workflow_executor, sample_workflow_data):
        """Test intercepting workflow execution."""
        # Test with interceptor enabled
        workflow_id = workflow_executor.intercept_workflow_execution(sample_workflow_data)
        
        assert workflow_id is not None
        assert workflow_id in workflow_executor._running_workflows
        
        workflow_info = workflow_executor._running_workflows[workflow_id]
        assert workflow_info["workflow_data"] == sample_workflow_data
        assert workflow_info["status"] == QueueStatus.PENDING

    def test_intercept_workflow_execution_disabled(self, workflow_executor, sample_workflow_data):
        """Test workflow execution with interceptor disabled."""
        workflow_executor.disable_interceptor()
        
        # Should execute directly when interceptor is disabled
        workflow_id = workflow_executor.intercept_workflow_execution(sample_workflow_data)
        
        # Should not be in running workflows since it executed directly
        assert workflow_id not in workflow_executor._running_workflows

    def test_execute_workflow_success(self, workflow_executor, sample_workflow_data):
        """Test successful workflow execution."""
        result = workflow_executor.execute_workflow(sample_workflow_data)
        
        assert isinstance(result, dict)
        assert "status" in result
        assert result["status"] == "completed"

    def test_execute_workflow_failure(self, workflow_executor):
        """Test workflow execution failure handling."""
        # Create invalid workflow data that should cause failure
        invalid_workflow = {"invalid": "data"}
        
        with patch.object(workflow_executor, '_execute_workflow_directly', 
                         side_effect=Exception("Execution failed")):
            with pytest.raises(WorkflowExecutionError):
                workflow_executor.execute_workflow(invalid_workflow)

    def test_extract_workflow_name(self, workflow_executor):
        """Test workflow name extraction from data."""
        # Test explicit name
        data_with_name = {"name": "My Workflow", "nodes": []}
        name = workflow_executor._extract_workflow_name(data_with_name)
        assert name == "My Workflow"
        
        # Test title
        data_with_title = {"title": "My Title", "nodes": []}
        name = workflow_executor._extract_workflow_name(data_with_title)
        assert name == "My Title"
        
        # Test workflow metadata
        data_with_workflow = {"workflow": {"name": "Workflow Name"}, "nodes": []}
        name = workflow_executor._extract_workflow_name(data_with_workflow)
        assert name == "Workflow Name"
        
        # Test node count
        data_with_nodes = {"nodes": [1, 2, 3]}
        name = workflow_executor._extract_workflow_name(data_with_nodes)
        assert "3 nodes" in name
        
        # Test default name
        empty_data = {}
        name = workflow_executor._extract_workflow_name(empty_data)
        assert "Workflow" in name

    def test_update_workflow_status(self, workflow_executor, sample_workflow_data):
        """Test updating workflow status."""
        # First intercept a workflow
        workflow_id = workflow_executor.intercept_workflow_execution(sample_workflow_data)
        
        # Update to running
        workflow_executor._update_workflow_status(workflow_id, QueueStatus.RUNNING)
        
        workflow_info = workflow_executor._running_workflows[workflow_id]
        assert workflow_info["status"] == QueueStatus.RUNNING
        assert workflow_info["started_at"] is not None
        
        # Update to completed
        result_data = {"output": "test"}
        workflow_executor._update_workflow_status(
            workflow_id, QueueStatus.COMPLETED, result_data=result_data
        )
        
        workflow_info = workflow_executor._running_workflows[workflow_id]
        assert workflow_info["status"] == QueueStatus.COMPLETED
        assert workflow_info["completed_at"] is not None
        assert workflow_info["result_data"] == result_data

    def test_is_workflow_running(self, workflow_executor, sample_workflow_data):
        """Test checking if workflow is running."""
        workflow_id = workflow_executor.intercept_workflow_execution(sample_workflow_data)
        
        # Initially pending
        assert workflow_executor.is_workflow_running(workflow_id) is False
        
        # Update to running
        workflow_executor._update_workflow_status(workflow_id, QueueStatus.RUNNING)
        assert workflow_executor.is_workflow_running(workflow_id) is True
        
        # Update to completed
        workflow_executor._update_workflow_status(workflow_id, QueueStatus.COMPLETED)
        assert workflow_executor.is_workflow_running(workflow_id) is False

    def test_cancel_workflow(self, workflow_executor, sample_workflow_data):
        """Test cancelling a workflow."""
        workflow_id = workflow_executor.intercept_workflow_execution(sample_workflow_data)
        
        # Cancel pending workflow
        result = workflow_executor.cancel_workflow(workflow_id)
        assert result is True
        
        workflow_info = workflow_executor._running_workflows[workflow_id]
        assert workflow_info["status"] == QueueStatus.FAILED
        assert "cancelled" in workflow_info["error_message"]

    def test_cancel_nonexistent_workflow(self, workflow_executor):
        """Test cancelling a non-existent workflow."""
        result = workflow_executor.cancel_workflow("nonexistent")
        assert result is False

    def test_get_workflow_status(self, workflow_executor, sample_workflow_data):
        """Test getting workflow status."""
        workflow_id = workflow_executor.intercept_workflow_execution(sample_workflow_data)
        
        status = workflow_executor.get_workflow_status(workflow_id)
        assert status == QueueStatus.PENDING
        
        # Test non-existent workflow
        status = workflow_executor.get_workflow_status("nonexistent")
        assert status is None

    def test_get_running_workflows(self, workflow_executor, sample_workflow_data):
        """Test getting running workflows."""
        # Initially no running workflows
        running = workflow_executor.get_running_workflows()
        assert len(running) == 0
        
        # Add a workflow and set to running
        workflow_id = workflow_executor.intercept_workflow_execution(sample_workflow_data)
        workflow_executor._update_workflow_status(workflow_id, QueueStatus.RUNNING)
        
        running = workflow_executor.get_running_workflows()
        assert len(running) == 1
        assert workflow_id in running

    def test_cleanup_completed_workflows(self, workflow_executor, sample_workflow_data):
        """Test cleaning up completed workflows."""
        # Add and complete a workflow
        workflow_id = workflow_executor.intercept_workflow_execution(sample_workflow_data)
        workflow_executor._update_workflow_status(workflow_id, QueueStatus.COMPLETED)
        
        # Set completed time to old timestamp
        workflow_info = workflow_executor._running_workflows[workflow_id]
        old_time = datetime.now(timezone.utc).replace(year=2020)
        workflow_info["completed_at"] = old_time
        
        # Cleanup should remove the old workflow
        cleaned = workflow_executor.cleanup_completed_workflows(max_age_hours=1)
        assert cleaned == 1
        assert workflow_id not in workflow_executor._running_workflows

    def test_get_execution_statistics(self, workflow_executor, sample_workflow_data):
        """Test getting execution statistics."""
        # Add some workflows with different statuses
        wf1 = workflow_executor.intercept_workflow_execution(sample_workflow_data)
        wf2 = workflow_executor.intercept_workflow_execution(sample_workflow_data)
        
        workflow_executor._update_workflow_status(wf1, QueueStatus.RUNNING)
        workflow_executor._update_workflow_status(wf2, QueueStatus.COMPLETED)
        
        stats = workflow_executor.get_execution_statistics()
        
        assert stats["total_workflows"] == 2
        assert "status_counts" in stats
        assert stats["status_counts"]["running"] == 1
        assert stats["status_counts"]["completed"] == 1


class TestWorkflowInterceptor:
    """Test cases for the WorkflowInterceptor class."""

    @pytest.fixture
    def workflow_interceptor(self):
        """Create a test workflow interceptor."""
        # Reset singleton for testing
        WorkflowInterceptor._instance = None
        return WorkflowInterceptor()

    @pytest.fixture
    def mock_workflow_executor(self):
        """Create a mock workflow executor."""
        executor = Mock()
        executor.intercept_workflow_execution.return_value = "test_workflow_id"
        return executor

    def test_interceptor_singleton(self):
        """Test that interceptor follows singleton pattern."""
        interceptor1 = WorkflowInterceptor()
        interceptor2 = WorkflowInterceptor()
        
        assert interceptor1 is interceptor2

    def test_get_workflow_interceptor_function(self):
        """Test the global get_workflow_interceptor function."""
        interceptor = get_workflow_interceptor()
        assert isinstance(interceptor, WorkflowInterceptor)

    def test_set_workflow_executor(self, workflow_interceptor, mock_workflow_executor):
        """Test setting workflow executor."""
        workflow_interceptor.set_workflow_executor(mock_workflow_executor)
        assert workflow_interceptor._workflow_executor == mock_workflow_executor

    def test_enable_disable_interceptor(self, workflow_interceptor):
        """Test enabling and disabling interceptor."""
        # Initially disabled
        assert workflow_interceptor.is_enabled() is False
        
        # Enable
        result = workflow_interceptor.enable()
        assert result is True
        assert workflow_interceptor.is_enabled() is True
        
        # Disable
        result = workflow_interceptor.disable()
        assert result is True
        assert workflow_interceptor.is_enabled() is False

    def test_register_execution_hook(self, workflow_interceptor):
        """Test registering execution hooks."""
        hook_called = []
        
        def test_hook(event_type, workflow_id, data):
            hook_called.append((event_type, workflow_id, data))
        
        workflow_interceptor.register_execution_hook("test_hook", test_hook)
        assert "test_hook" in workflow_interceptor._execution_hooks
        
        # Unregister
        workflow_interceptor.unregister_execution_hook("test_hook")
        assert "test_hook" not in workflow_interceptor._execution_hooks

    def test_looks_like_workflow_data(self, workflow_interceptor):
        """Test workflow data detection."""
        # Valid workflow data
        valid_data = {"nodes": [], "links": []}
        assert workflow_interceptor._looks_like_workflow_data(valid_data) is True
        
        # Another valid format
        valid_data2 = {"workflow": {"version": "1.0"}}
        assert workflow_interceptor._looks_like_workflow_data(valid_data2) is True
        
        # Invalid data
        invalid_data = {"random": "data"}
        assert workflow_interceptor._looks_like_workflow_data(invalid_data) is False
        
        # Non-dict data
        assert workflow_interceptor._looks_like_workflow_data("not a dict") is False

    def test_extract_workflow_data(self, workflow_interceptor):
        """Test extracting workflow data from arguments."""
        workflow_data = {"nodes": [], "workflow": {"version": "1.0"}}
        
        # Test positional arguments
        args = (workflow_data, "other_arg")
        kwargs = {}
        
        extracted = workflow_interceptor._extract_workflow_data(args, kwargs)
        assert extracted == workflow_data
        
        # Test keyword arguments
        args = ()
        kwargs = {"workflow": workflow_data, "other": "value"}
        
        extracted = workflow_interceptor._extract_workflow_data(args, kwargs)
        assert extracted == workflow_data

    def test_extract_result_data(self, workflow_interceptor):
        """Test extracting result data."""
        # Dict result
        dict_result = {"output": "test", "status": "completed"}
        extracted = workflow_interceptor._extract_result_data(dict_result)
        assert extracted == dict_result
        
        # Object with __dict__
        class TestResult:
            def __init__(self):
                self.output = "test"
                self.status = "completed"
        
        obj_result = TestResult()
        extracted = workflow_interceptor._extract_result_data(obj_result)
        assert extracted["output"] == "test"
        assert extracted["status"] == "completed"
        
        # String result
        str_result = "completed"
        extracted = workflow_interceptor._extract_result_data(str_result)
        assert extracted == {"result": "completed"}

    def test_get_hook_status(self, workflow_interceptor, mock_workflow_executor):
        """Test getting hook status."""
        workflow_interceptor.set_workflow_executor(mock_workflow_executor)
        workflow_interceptor.register_execution_hook("test", lambda: None)
        
        status = workflow_interceptor.get_hook_status()
        
        assert "enabled" in status
        assert "execution_hooks" in status
        assert "has_workflow_executor" in status
        assert status["has_workflow_executor"] is True
        assert "test" in status["execution_hooks"]


class TestExecutionMonitor:
    """Test cases for the ExecutionMonitor class."""

    @pytest.fixture
    def database(self):
        """Create a test database."""
        db = SQLiteDatabase(":memory:")
        db.initialize()
        return db

    @pytest.fixture
    def queue_service(self, database):
        """Create a test queue service."""
        return QueueService(database)

    @pytest.fixture
    def workflow_executor(self, queue_service):
        """Create a test workflow executor."""
        return WorkflowExecutor(queue_service)

    @pytest.fixture
    def execution_monitor(self, queue_service, workflow_executor):
        """Create a test execution monitor."""
        return ExecutionMonitor(queue_service, workflow_executor)

    def test_execution_monitor_initialization(self, queue_service, workflow_executor):
        """Test execution monitor initialization."""
        monitor = ExecutionMonitor(queue_service, workflow_executor)
        
        assert monitor.queue_service == queue_service
        assert monitor.workflow_executor == workflow_executor
        assert monitor.is_monitoring() is False
        assert len(monitor._monitored_workflows) == 0

    def test_start_stop_monitoring(self, execution_monitor):
        """Test starting and stopping monitoring."""
        # Start monitoring
        result = execution_monitor.start_monitoring()
        assert result is True
        assert execution_monitor.is_monitoring() is True
        
        # Stop monitoring
        result = execution_monitor.stop_monitoring()
        assert result is True
        assert execution_monitor.is_monitoring() is False

    def test_set_monitoring_interval(self, execution_monitor):
        """Test setting monitoring interval."""
        execution_monitor.set_monitoring_interval(2.0)
        assert execution_monitor._monitoring_interval == 2.0
        
        # Test invalid interval
        with pytest.raises(ValueError):
            execution_monitor.set_monitoring_interval(-1.0)

    def test_add_remove_workflow_to_monitor(self, execution_monitor):
        """Test adding and removing workflows from monitoring."""
        workflow_id = "test_workflow"
        workflow_info = {
            "status": QueueStatus.PENDING,
            "workflow_name": "Test Workflow",
        }
        
        # Add workflow
        execution_monitor.add_workflow_to_monitor(workflow_id, workflow_info)
        assert workflow_id in execution_monitor._monitored_workflows
        
        # Remove workflow
        result = execution_monitor.remove_workflow_from_monitor(workflow_id)
        assert result is True
        assert workflow_id not in execution_monitor._monitored_workflows
        
        # Remove non-existent workflow
        result = execution_monitor.remove_workflow_from_monitor("nonexistent")
        assert result is False

    def test_register_status_callback(self, execution_monitor):
        """Test registering status callbacks."""
        callback_called = []
        
        def test_callback(data):
            callback_called.append(data)
        
        execution_monitor.register_status_callback("test", test_callback)
        assert "test" in execution_monitor._status_callbacks
        
        # Unregister
        execution_monitor.unregister_status_callback("test")
        assert "test" not in execution_monitor._status_callbacks

    def test_get_monitored_workflows(self, execution_monitor):
        """Test getting monitored workflows."""
        workflow_info = {"status": QueueStatus.PENDING}
        execution_monitor.add_workflow_to_monitor("test1", workflow_info)
        execution_monitor.add_workflow_to_monitor("test2", workflow_info)
        
        workflows = execution_monitor.get_monitored_workflows()
        assert len(workflows) == 2
        assert "test1" in workflows
        assert "test2" in workflows

    def test_get_workflow_status(self, execution_monitor):
        """Test getting workflow status."""
        workflow_info = {"status": QueueStatus.RUNNING}
        execution_monitor.add_workflow_to_monitor("test", workflow_info)
        
        status = execution_monitor.get_workflow_status("test")
        assert status == QueueStatus.RUNNING
        
        # Non-existent workflow
        status = execution_monitor.get_workflow_status("nonexistent")
        assert status is None

    def test_monitoring_statistics(self, execution_monitor):
        """Test getting monitoring statistics."""
        # Add some workflows
        execution_monitor.add_workflow_to_monitor("test1", {"status": QueueStatus.PENDING})
        execution_monitor.add_workflow_to_monitor("test2", {"status": QueueStatus.RUNNING})
        
        stats = execution_monitor.get_monitoring_statistics()
        
        assert stats["monitored_workflows"] == 2
        assert "status_counts" in stats
        assert stats["status_counts"]["pending"] == 1
        assert stats["status_counts"]["running"] == 1

    def test_cleanup_old_workflows(self, execution_monitor):
        """Test cleaning up old workflows."""
        # Add old completed workflow
        old_workflow_info = {
            "status": QueueStatus.COMPLETED,
            "added_at": datetime.now(timezone.utc).replace(year=2020),
        }
        execution_monitor.add_workflow_to_monitor("old", old_workflow_info)
        
        # Add recent workflow
        recent_workflow_info = {
            "status": QueueStatus.PENDING,
            "added_at": datetime.now(timezone.utc),
        }
        execution_monitor.add_workflow_to_monitor("recent", recent_workflow_info)
        
        # Cleanup should remove only the old completed workflow
        cleaned = execution_monitor.cleanup_old_workflows(max_age_hours=1)
        assert cleaned == 1
        assert "old" not in execution_monitor._monitored_workflows
        assert "recent" in execution_monitor._monitored_workflows


class TestWorkflowExecutionIntegration:
    """Integration tests for the complete workflow execution system."""

    @pytest.fixture
    def database(self):
        """Create a test database."""
        db = SQLiteDatabase(":memory:")
        db.initialize()
        return db

    @pytest.fixture
    def queue_service(self, database):
        """Create a test queue service."""
        return QueueService(database)

    @pytest.fixture
    def workflow_executor(self, queue_service):
        """Create a test workflow executor."""
        return WorkflowExecutor(queue_service)

    @pytest.fixture
    def execution_monitor(self, queue_service, workflow_executor):
        """Create a test execution monitor."""
        return ExecutionMonitor(queue_service, workflow_executor)

    @pytest.fixture
    def workflow_interceptor(self, workflow_executor):
        """Create a test workflow interceptor."""
        WorkflowInterceptor._instance = None
        interceptor = WorkflowInterceptor()
        interceptor.set_workflow_executor(workflow_executor)
        return interceptor

    @pytest.fixture
    def sample_workflow_data(self):
        """Create sample workflow data for testing."""
        return {
            "name": "Integration Test Workflow",
            "nodes": [
                {"id": "1", "type": "LoadImage", "inputs": {}},
                {"id": "2", "type": "SaveImage", "inputs": {"images": ["1", 0]}},
            ],
            "links": [["1", 0, "2", 0]],
            "workflow": {"version": "1.0"},
        }

    def test_complete_workflow_execution_flow(
        self, 
        queue_service, 
        workflow_executor, 
        execution_monitor, 
        workflow_interceptor,
        sample_workflow_data
    ):
        """Test the complete workflow execution flow."""
        # Start monitoring
        execution_monitor.start_monitoring()
        
        # Enable interceptor
        workflow_interceptor.enable()
        
        # Track status changes
        status_changes = []
        
        def status_callback(data):
            status_changes.append(data)
        
        execution_monitor.register_status_callback("test", status_callback)
        
        # Intercept a workflow
        workflow_id = workflow_executor.intercept_workflow_execution(sample_workflow_data)
        
        # Verify workflow was added to queue
        queue_items = queue_service.get_queue_items()
        assert len(queue_items) == 1
        
        # Add workflow to monitoring
        workflow_info = workflow_executor.get_workflow_info(workflow_id)
        execution_monitor.add_workflow_to_monitor(workflow_id, workflow_info)
        
        # Simulate workflow execution
        workflow_executor._update_workflow_status(workflow_id, QueueStatus.RUNNING)
        time.sleep(0.1)  # Allow monitor to detect change
        
        workflow_executor._update_workflow_status(
            workflow_id, 
            QueueStatus.COMPLETED,
            result_data={"output": "test_result"}
        )
        time.sleep(0.1)  # Allow monitor to detect change
        
        # Verify final state
        final_status = workflow_executor.get_workflow_status(workflow_id)
        assert final_status == QueueStatus.COMPLETED
        
        # Verify queue item was updated
        queue_item = queue_service.get_queue_item(workflow_info["queue_item_id"])
        assert queue_item.status == QueueStatus.COMPLETED
        assert queue_item.result_data == {"output": "test_result"}
        
        # Stop monitoring
        execution_monitor.stop_monitoring()

    def test_workflow_execution_error_handling(
        self,
        workflow_executor,
        execution_monitor,
        sample_workflow_data
    ):
        """Test error handling in workflow execution."""
        execution_monitor.start_monitoring()
        
        # Intercept workflow
        workflow_id = workflow_executor.intercept_workflow_execution(sample_workflow_data)
        
        # Add to monitoring
        workflow_info = workflow_executor.get_workflow_info(workflow_id)
        execution_monitor.add_workflow_to_monitor(workflow_id, workflow_info)
        
        # Simulate execution failure
        workflow_executor._update_workflow_status(
            workflow_id,
            QueueStatus.FAILED,
            error_message="Test execution error"
        )
        
        # Verify error state
        final_status = workflow_executor.get_workflow_status(workflow_id)
        assert final_status == QueueStatus.FAILED
        
        workflow_info = workflow_executor.get_workflow_info(workflow_id)
        assert workflow_info["error_message"] == "Test execution error"
        
        execution_monitor.stop_monitoring()

    def test_concurrent_workflow_execution(
        self,
        workflow_executor,
        execution_monitor,
        sample_workflow_data
    ):
        """Test concurrent workflow execution."""
        execution_monitor.start_monitoring()
        
        # Start multiple workflows
        workflow_ids = []
        for i in range(3):
            workflow_data = {**sample_workflow_data, "name": f"Workflow {i}"}
            workflow_id = workflow_executor.intercept_workflow_execution(workflow_data)
            workflow_ids.append(workflow_id)
            
            # Add to monitoring
            workflow_info = workflow_executor.get_workflow_info(workflow_id)
            execution_monitor.add_workflow_to_monitor(workflow_id, workflow_info)
        
        # Set all to running
        for workflow_id in workflow_ids:
            workflow_executor._update_workflow_status(workflow_id, QueueStatus.RUNNING)
        
        # Verify all are running
        running_workflows = workflow_executor.get_running_workflows()
        assert len(running_workflows) == 3
        
        # Complete workflows one by one
        for i, workflow_id in enumerate(workflow_ids):
            workflow_executor._update_workflow_status(
                workflow_id,
                QueueStatus.COMPLETED,
                result_data={"output": f"result_{i}"}
            )
        
        # Verify all completed
        for workflow_id in workflow_ids:
            status = workflow_executor.get_workflow_status(workflow_id)
            assert status == QueueStatus.COMPLETED
        
        execution_monitor.stop_monitoring()

    def test_workflow_cancellation(
        self,
        workflow_executor,
        execution_monitor,
        sample_workflow_data
    ):
        """Test workflow cancellation."""
        execution_monitor.start_monitoring()
        
        # Start workflow
        workflow_id = workflow_executor.intercept_workflow_execution(sample_workflow_data)
        workflow_info = workflow_executor.get_workflow_info(workflow_id)
        execution_monitor.add_workflow_to_monitor(workflow_id, workflow_info)
        
        # Set to running
        workflow_executor._update_workflow_status(workflow_id, QueueStatus.RUNNING)
        
        # Cancel workflow
        result = workflow_executor.cancel_workflow(workflow_id)
        assert result is True
        
        # Verify cancelled state
        status = workflow_executor.get_workflow_status(workflow_id)
        assert status == QueueStatus.FAILED
        
        workflow_info = workflow_executor.get_workflow_info(workflow_id)
        assert "cancelled" in workflow_info["error_message"]
        
        execution_monitor.stop_monitoring()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])