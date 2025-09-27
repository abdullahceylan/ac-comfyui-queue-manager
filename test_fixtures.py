#!/usr/bin/env python3
"""
Test fixtures and data generators for ComfyUI Queue Manager tests.
Provides reusable test data, mock objects, and testing utilities.
"""

import json
import random
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from unittest.mock import Mock, MagicMock

from models import QueueItem, QueueStatus, QueueState, QueueConfig


class WorkflowTemplates:
    """Pre-defined workflow templates for testing."""
    
    SIMPLE_IMAGE_WORKFLOW = {
        "name": "Simple Image Processing",
        "workflow": {"version": "1.0"},
        "nodes": [
            {
                "id": "1",
                "type": "LoadImage",
                "inputs": {
                    "image": "test_image.png"
                }
            },
            {
                "id": "2", 
                "type": "SaveImage",
                "inputs": {
                    "images": ["1", 0],
                    "filename_prefix": "output"
                }
            }
        ],
        "links": [["1", 0, "2", 0]]
    }
    
    COMPLEX_GENERATION_WORKFLOW = {
        "name": "Complex Generation Pipeline",
        "workflow": {"version": "1.0"},
        "nodes": [
            {
                "id": "1",
                "type": "CheckpointLoaderSimple",
                "inputs": {
                    "ckpt_name": "model.safetensors"
                }
            },
            {
                "id": "2",
                "type": "CLIPTextEncode",
                "inputs": {
                    "text": "a beautiful landscape",
                    "clip": ["1", 1]
                }
            },
            {
                "id": "3",
                "type": "CLIPTextEncode", 
                "inputs": {
                    "text": "blurry, low quality",
                    "clip": ["1", 1]
                }
            },
            {
                "id": "4",
                "type": "EmptyLatentImage",
                "inputs": {
                    "width": 512,
                    "height": 512,
                    "batch_size": 1
                }
            },
            {
                "id": "5",
                "type": "KSampler",
                "inputs": {
                    "seed": 42,
                    "steps": 20,
                    "cfg": 7.0,
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "model": ["1", 0],
                    "positive": ["2", 0],
                    "negative": ["3", 0],
                    "latent_image": ["4", 0]
                }
            },
            {
                "id": "6",
                "type": "VAEDecode",
                "inputs": {
                    "samples": ["5", 0],
                    "vae": ["1", 2]
                }
            },
            {
                "id": "7",
                "type": "SaveImage",
                "inputs": {
                    "images": ["6", 0],
                    "filename_prefix": "generated"
                }
            }
        ],
        "links": [
            ["1", 1, "2", 0],
            ["1", 1, "3", 0],
            ["1", 0, "5", 0],
            ["1", 2, "6", 1],
            ["2", 0, "5", 1],
            ["3", 0, "5", 2],
            ["4", 0, "5", 3],
            ["5", 0, "6", 0],
            ["6", 0, "7", 0]
        ]
    }
    
    BATCH_PROCESSING_WORKFLOW = {
        "name": "Batch Processing Workflow",
        "workflow": {"version": "1.0"},
        "nodes": [
            {
                "id": "1",
                "type": "LoadImageBatch",
                "inputs": {
                    "mode": "incremental_image",
                    "index": 0,
                    "label": "Batch"
                }
            },
            {
                "id": "2",
                "type": "ImageScale",
                "inputs": {
                    "image": ["1", 0],
                    "upscale_method": "nearest-exact",
                    "width": 1024,
                    "height": 1024,
                    "crop": "disabled"
                }
            },
            {
                "id": "3",
                "type": "ImageEnhance",
                "inputs": {
                    "image": ["2", 0],
                    "brightness": 1.1,
                    "contrast": 1.2,
                    "saturation": 1.0
                }
            },
            {
                "id": "4",
                "type": "SaveImage",
                "inputs": {
                    "images": ["3", 0],
                    "filename_prefix": "batch_processed"
                }
            }
        ],
        "links": [
            ["1", 0, "2", 0],
            ["2", 0, "3", 0],
            ["3", 0, "4", 0]
        ]
    }


class TestDataFactory:
    """Factory for creating test data with various configurations."""
    
    @staticmethod
    def create_queue_item(
        item_id: Optional[str] = None,
        workflow_name: Optional[str] = None,
        workflow_data: Optional[Dict] = None,
        status: QueueStatus = QueueStatus.PENDING,
        created_at: Optional[datetime] = None,
        **kwargs
    ) -> QueueItem:
        """Create a test queue item with optional parameters."""
        
        if item_id is None:
            item_id = f"test-item-{uuid.uuid4().hex[:8]}"
        
        if workflow_name is None:
            workflow_name = f"Test Workflow {uuid.uuid4().hex[:8]}"
        
        if workflow_data is None:
            workflow_data = WorkflowTemplates.SIMPLE_IMAGE_WORKFLOW.copy()
            workflow_data["name"] = workflow_name
        
        if created_at is None:
            created_at = datetime.now(timezone.utc)
        
        item = QueueItem(
            id=item_id,
            workflow_name=workflow_name,
            workflow_data=workflow_data,
            status=status,
            created_at=created_at,
            updated_at=created_at,
            **kwargs
        )
        
        # Set additional fields based on status
        if status == QueueStatus.RUNNING:
            item.started_at = created_at + timedelta(seconds=1)
        elif status in [QueueStatus.COMPLETED, QueueStatus.FAILED]:
            item.started_at = created_at + timedelta(seconds=1)
            item.completed_at = created_at + timedelta(seconds=10)
            
            if status == QueueStatus.COMPLETED:
                item.result_data = {"output": f"result_for_{item_id}"}
            else:
                item.error_message = f"Test error for {item_id}"
        
        return item
    
    @staticmethod
    def create_queue_items_batch(
        count: int = 10,
        status_distribution: Optional[Dict[QueueStatus, float]] = None,
        workflow_templates: Optional[List[Dict]] = None
    ) -> List[QueueItem]:
        """Create a batch of queue items with specified distribution."""
        
        if status_distribution is None:
            status_distribution = {
                QueueStatus.PENDING: 0.4,
                QueueStatus.RUNNING: 0.1,
                QueueStatus.COMPLETED: 0.4,
                QueueStatus.FAILED: 0.05,
                QueueStatus.ARCHIVED: 0.05
            }
        
        if workflow_templates is None:
            workflow_templates = [
                WorkflowTemplates.SIMPLE_IMAGE_WORKFLOW,
                WorkflowTemplates.COMPLEX_GENERATION_WORKFLOW,
                WorkflowTemplates.BATCH_PROCESSING_WORKFLOW
            ]
        
        items = []
        for i in range(count):
            # Determine status based on distribution
            rand_val = i / count
            cumulative = 0
            status = QueueStatus.PENDING
            
            for stat, prob in status_distribution.items():
                cumulative += prob
                if rand_val <= cumulative:
                    status = stat
                    break
            
            # Select workflow template
            template = workflow_templates[i % len(workflow_templates)].copy()
            template["name"] = f"{template['name']} #{i:04d}"
            
            # Create item with time variation
            created_at = datetime.now(timezone.utc) - timedelta(
                minutes=random.randint(0, 1440)  # Random time in last 24 hours
            )
            
            item = TestDataFactory.create_queue_item(
                item_id=f"batch-item-{i:04d}",
                workflow_name=template["name"],
                workflow_data=template,
                status=status,
                created_at=created_at
            )
            
            items.append(item)
        
        return items
    
    @staticmethod
    def create_workflow_variations(base_workflow: Dict, count: int = 5) -> List[Dict]:
        """Create variations of a base workflow for testing."""
        variations = []
        
        for i in range(count):
            variation = json.loads(json.dumps(base_workflow))  # Deep copy
            
            # Modify workflow name
            variation["name"] = f"{base_workflow['name']} - Variation {i+1}"
            
            # Add random parameters
            variation["test_params"] = {
                "variation_id": i,
                "seed": random.randint(1, 1000000),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Modify some node parameters if they exist
            if "nodes" in variation:
                for node in variation["nodes"]:
                    if node.get("type") == "KSampler" and "inputs" in node:
                        node["inputs"]["seed"] = random.randint(1, 1000000)
                        node["inputs"]["steps"] = random.randint(10, 50)
                    elif node.get("type") == "SaveImage" and "inputs" in node:
                        node["inputs"]["filename_prefix"] = f"var_{i}_output"
            
            variations.append(variation)
        
        return variations


class MockFactory:
    """Factory for creating mock objects for testing."""
    
    @staticmethod
    def create_mock_database() -> Mock:
        """Create a mock database with common methods."""
        mock_db = Mock()
        mock_db.initialize.return_value = None
        mock_db.close.return_value = None
        mock_db.execute_query.return_value = []
        mock_db.execute_update.return_value = True
        mock_db.get_connection.return_value = Mock()
        return mock_db
    
    @staticmethod
    def create_mock_queue_service(items: Optional[List[QueueItem]] = None) -> Mock:
        """Create a mock queue service with predefined items."""
        if items is None:
            items = TestDataFactory.create_queue_items_batch(5)
        
        mock_service = Mock()
        mock_service.get_queue_items.return_value = items
        mock_service.get_queue_item.side_effect = lambda item_id: next(
            (item for item in items if item.id == item_id), None
        )
        mock_service.add_workflow.return_value = f"new-item-{uuid.uuid4().hex[:8]}"
        mock_service.update_item_status.return_value = True
        mock_service.delete_items.return_value = True
        mock_service.archive_items.return_value = True
        mock_service.restore_items.return_value = True
        mock_service.filter_items.return_value = items[:3]  # Return subset
        mock_service.search_items.return_value = items[:2]  # Return subset
        mock_service.export_queue.return_value = {
            "version": "1.0",
            "items": [item.to_dict() for item in items]
        }
        mock_service.import_queue.return_value = True
        mock_service.get_queue_state.return_value = QueueState.RUNNING
        mock_service.pause_queue.return_value = True
        mock_service.resume_queue.return_value = True
        mock_service.get_config.return_value = QueueConfig()
        mock_service.update_config.return_value = True
        
        return mock_service
    
    @staticmethod
    def create_mock_workflow_executor() -> Mock:
        """Create a mock workflow executor."""
        mock_executor = Mock()
        mock_executor.intercept_workflow_execution.return_value = f"workflow-{uuid.uuid4().hex[:8]}"
        mock_executor.execute_workflow.return_value = {"status": "completed", "output": "test"}
        mock_executor.cancel_workflow.return_value = True
        mock_executor.get_workflow_status.return_value = QueueStatus.PENDING
        mock_executor.get_running_workflows.return_value = []
        mock_executor.is_workflow_running.return_value = False
        mock_executor.get_workflow_info.return_value = {
            "workflow_data": WorkflowTemplates.SIMPLE_IMAGE_WORKFLOW,
            "status": QueueStatus.PENDING,
            "queue_item_id": f"item-{uuid.uuid4().hex[:8]}"
        }
        mock_executor.cleanup_completed_workflows.return_value = 0
        mock_executor.get_execution_statistics.return_value = {
            "total_workflows": 0,
            "status_counts": {}
        }
        mock_executor.enable_interceptor.return_value = None
        mock_executor.disable_interceptor.return_value = None
        mock_executor.is_interceptor_enabled.return_value = True
        
        return mock_executor
    
    @staticmethod
    def create_mock_execution_monitor() -> Mock:
        """Create a mock execution monitor."""
        mock_monitor = Mock()
        mock_monitor.start_monitoring.return_value = True
        mock_monitor.stop_monitoring.return_value = True
        mock_monitor.is_monitoring.return_value = False
        mock_monitor.add_workflow_to_monitor.return_value = None
        mock_monitor.remove_workflow_from_monitor.return_value = True
        mock_monitor.get_monitored_workflows.return_value = {}
        mock_monitor.get_workflow_status.return_value = QueueStatus.PENDING
        mock_monitor.get_monitoring_statistics.return_value = {
            "monitored_workflows": 0,
            "status_counts": {}
        }
        mock_monitor.cleanup_old_workflows.return_value = 0
        mock_monitor.set_monitoring_interval.return_value = None
        mock_monitor.register_status_callback.return_value = None
        mock_monitor.unregister_status_callback.return_value = None
        
        return mock_monitor
    
    @staticmethod
    def create_mock_api_client() -> Mock:
        """Create a mock API client for testing."""
        mock_client = Mock()
        
        # Mock successful responses
        def create_response(status_code=200, data=None):
            response = Mock()
            response.status_code = status_code
            response.data = json.dumps(data or {}).encode()
            return response
        
        mock_client.get.return_value = create_response(200, {"status": "ok"})
        mock_client.post.return_value = create_response(201, {"id": "new-item"})
        mock_client.put.return_value = create_response(200, {"updated": True})
        mock_client.delete.return_value = create_response(200, {"deleted": True})
        
        return mock_client


class TestScenarios:
    """Pre-defined test scenarios for common use cases."""
    
    @staticmethod
    def get_typical_queue_scenario() -> Dict[str, Any]:
        """Get a typical queue scenario with mixed statuses."""
        items = TestDataFactory.create_queue_items_batch(
            count=20,
            status_distribution={
                QueueStatus.PENDING: 0.3,
                QueueStatus.RUNNING: 0.2,
                QueueStatus.COMPLETED: 0.4,
                QueueStatus.FAILED: 0.1
            }
        )
        
        return {
            "name": "Typical Queue Scenario",
            "description": "Mixed queue with various statuses",
            "items": items,
            "expected_pending": 6,
            "expected_running": 4,
            "expected_completed": 8,
            "expected_failed": 2
        }
    
    @staticmethod
    def get_high_load_scenario() -> Dict[str, Any]:
        """Get a high load scenario with many items."""
        items = TestDataFactory.create_queue_items_batch(
            count=1000,
            status_distribution={
                QueueStatus.PENDING: 0.6,
                QueueStatus.RUNNING: 0.05,
                QueueStatus.COMPLETED: 0.3,
                QueueStatus.FAILED: 0.05
            }
        )
        
        return {
            "name": "High Load Scenario",
            "description": "Large queue with mostly pending items",
            "items": items,
            "expected_pending": 600,
            "expected_running": 50,
            "expected_completed": 300,
            "expected_failed": 50
        }
    
    @staticmethod
    def get_error_recovery_scenario() -> Dict[str, Any]:
        """Get a scenario for testing error recovery."""
        items = TestDataFactory.create_queue_items_batch(
            count=10,
            status_distribution={
                QueueStatus.FAILED: 0.8,
                QueueStatus.PENDING: 0.2
            }
        )
        
        # Add specific error messages
        for i, item in enumerate(items):
            if item.status == QueueStatus.FAILED:
                error_types = [
                    "Out of memory",
                    "Model not found",
                    "Invalid input parameters",
                    "Network timeout",
                    "Disk space full"
                ]
                item.error_message = error_types[i % len(error_types)]
        
        return {
            "name": "Error Recovery Scenario",
            "description": "Queue with many failed items for recovery testing",
            "items": items,
            "error_types": ["Out of memory", "Model not found", "Invalid input parameters", 
                          "Network timeout", "Disk space full"]
        }
    
    @staticmethod
    def get_archive_scenario() -> Dict[str, Any]:
        """Get a scenario for testing archive functionality."""
        items = TestDataFactory.create_queue_items_batch(
            count=50,
            status_distribution={
                QueueStatus.COMPLETED: 0.6,
                QueueStatus.ARCHIVED: 0.3,
                QueueStatus.PENDING: 0.1
            }
        )
        
        # Set older timestamps for completed items
        for item in items:
            if item.status == QueueStatus.COMPLETED:
                item.created_at = datetime.now(timezone.utc) - timedelta(days=random.randint(1, 30))
                item.completed_at = item.created_at + timedelta(minutes=random.randint(1, 60))
        
        return {
            "name": "Archive Scenario",
            "description": "Queue with items ready for archiving",
            "items": items,
            "archivable_items": [item for item in items if item.status == QueueStatus.COMPLETED]
        }


class TestAssertions:
    """Custom assertions for queue manager testing."""
    
    @staticmethod
    def assert_queue_item_valid(item: QueueItem):
        """Assert that a queue item has valid structure."""
        assert item.id is not None and len(item.id) > 0
        assert item.workflow_name is not None and len(item.workflow_name) > 0
        assert item.workflow_data is not None and isinstance(item.workflow_data, dict)
        assert isinstance(item.status, QueueStatus)
        assert item.created_at is not None
        assert item.updated_at is not None
        assert item.created_at <= item.updated_at
        
        if item.status == QueueStatus.RUNNING:
            assert item.started_at is not None
            assert item.started_at >= item.created_at
        
        if item.status in [QueueStatus.COMPLETED, QueueStatus.FAILED]:
            assert item.completed_at is not None
            assert item.completed_at >= item.created_at
            
            if item.status == QueueStatus.COMPLETED:
                assert item.result_data is not None
            else:
                assert item.error_message is not None
    
    @staticmethod
    def assert_queue_items_sorted_by_created_at(items: List[QueueItem], ascending: bool = True):
        """Assert that queue items are sorted by creation time."""
        if len(items) <= 1:
            return
        
        for i in range(1, len(items)):
            if ascending:
                assert items[i-1].created_at <= items[i].created_at
            else:
                assert items[i-1].created_at >= items[i].created_at
    
    @staticmethod
    def assert_status_distribution(items: List[QueueItem], expected_distribution: Dict[QueueStatus, float], tolerance: float = 0.1):
        """Assert that items match expected status distribution within tolerance."""
        total_items = len(items)
        if total_items == 0:
            return
        
        status_counts = {}
        for item in items:
            status_counts[item.status] = status_counts.get(item.status, 0) + 1
        
        for status, expected_ratio in expected_distribution.items():
            actual_count = status_counts.get(status, 0)
            actual_ratio = actual_count / total_items
            expected_count = int(total_items * expected_ratio)
            
            assert abs(actual_ratio - expected_ratio) <= tolerance, \
                f"Status {status}: expected {expected_ratio:.2%}, got {actual_ratio:.2%}"
    
    @staticmethod
    def assert_workflow_data_valid(workflow_data: Dict):
        """Assert that workflow data has valid structure."""
        assert isinstance(workflow_data, dict)
        assert "name" in workflow_data or "workflow" in workflow_data
        
        # Should have either nodes or workflow structure
        has_nodes = "nodes" in workflow_data
        has_workflow = "workflow" in workflow_data
        assert has_nodes or has_workflow, "Workflow must have 'nodes' or 'workflow' structure"
        
        if has_nodes:
            assert isinstance(workflow_data["nodes"], list)
            for node in workflow_data["nodes"]:
                assert isinstance(node, dict)
                assert "id" in node
                assert "type" in node
    
    @staticmethod
    def assert_performance_metrics(metrics: Dict, max_time: float = None, min_throughput: float = None):
        """Assert that performance metrics meet requirements."""
        if max_time is not None and "total_time" in metrics:
            assert metrics["total_time"] <= max_time, \
                f"Operation took {metrics['total_time']:.3f}s, expected <= {max_time}s"
        
        if min_throughput is not None and "operations_per_second" in metrics:
            assert metrics["operations_per_second"] >= min_throughput, \
                f"Throughput {metrics['operations_per_second']:.1f} ops/s, expected >= {min_throughput} ops/s"


# Convenience functions for common test setups
def setup_test_database():
    """Set up a test database with sample data."""
    from database import SQLiteDatabase
    
    db = SQLiteDatabase(":memory:")
    db.initialize()
    return db


def setup_test_queue_service(item_count: int = 10):
    """Set up a test queue service with sample data."""
    from queue_service import QueueService
    
    db = setup_test_database()
    service = QueueService(db)
    
    # Add sample items
    items = TestDataFactory.create_queue_items_batch(item_count)
    for item in items:
        service.add_workflow(
            item.workflow_name,
            item.workflow_data,
            item.status
        )
    
    return service, db


def setup_test_api_client(queue_service=None):
    """Set up a test API client."""
    from api_routes import QueueManagerAPI
    
    if queue_service is None:
        queue_service, _ = setup_test_queue_service()
    
    api = QueueManagerAPI(queue_service=queue_service)
    return api.app.test_client(), api


# Export commonly used items
__all__ = [
    'WorkflowTemplates',
    'TestDataFactory', 
    'MockFactory',
    'TestScenarios',
    'TestAssertions',
    'setup_test_database',
    'setup_test_queue_service',
    'setup_test_api_client'
]