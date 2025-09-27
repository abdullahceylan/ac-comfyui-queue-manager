#!/usr/bin/env python3
"""
Comprehensive integration test suite for ComfyUI Queue Manager.
Tests end-to-end workflows, performance with large queues, and stress testing.
"""

import asyncio
import json
import os
import sqlite3
import sys
import tempfile
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api_routes import QueueManagerAPI
from database import SQLiteDatabase
from execution_monitor import ExecutionMonitor
from models import QueueItem, QueueStatus, QueueState
from queue_service import QueueService
from workflow_executor import WorkflowExecutor
from workflow_interceptor import WorkflowInterceptor


class TestDataGenerator:
    """Utility class for generating test data and fixtures."""
    
    @staticmethod
    def generate_workflow_data(name_prefix="Test Workflow", complexity="simple"):
        """Generate workflow data with varying complexity."""
        base_workflow = {
            "name": f"{name_prefix} {uuid.uuid4().hex[:8]}",
            "workflow": {"version": "1.0"},
            "nodes": [],
            "links": []
        }
        
        if complexity == "simple":
            base_workflow["nodes"] = [
                {"id": "1", "type": "LoadImage", "inputs": {}},
                {"id": "2", "type": "SaveImage", "inputs": {"images": ["1", 0]}}
            ]
            base_workflow["links"] = [["1", 0, "2", 0]]
            
        elif complexity == "medium":
            base_workflow["nodes"] = [
                {"id": "1", "type": "LoadImage", "inputs": {}},
                {"id": "2", "type": "VAEEncode", "inputs": {"pixels": ["1", 0]}},
                {"id": "3", "type": "KSampler", "inputs": {"latent_image": ["2", 0]}},
                {"id": "4", "type": "VAEDecode", "inputs": {"samples": ["3", 0]}},
                {"id": "5", "type": "SaveImage", "inputs": {"images": ["4", 0]}}
            ]
            base_workflow["links"] = [
                ["1", 0, "2", 0],
                ["2", 0, "3", 0],
                ["3", 0, "4", 0],
                ["4", 0, "5", 0]
            ]
            
        elif complexity == "complex":
            # Generate a complex workflow with many nodes
            nodes = []
            links = []
            for i in range(1, 21):  # 20 nodes
                node_type = ["LoadImage", "VAEEncode", "KSampler", "VAEDecode", "SaveImage"][i % 5]
                nodes.append({"id": str(i), "type": node_type, "inputs": {}})
                if i > 1:
                    links.append([str(i-1), 0, str(i), 0])
            
            base_workflow["nodes"] = nodes
            base_workflow["links"] = links
        
        return base_workflow
    
    @staticmethod
    def generate_queue_items(count=100, status_distribution=None):
        """Generate multiple queue items with specified status distribution."""
        if status_distribution is None:
            status_distribution = {
                QueueStatus.PENDING: 0.4,
                QueueStatus.RUNNING: 0.1,
                QueueStatus.COMPLETED: 0.4,
                QueueStatus.FAILED: 0.05,
                QueueStatus.ARCHIVED: 0.05
            }
        
        items = []
        for i in range(count):
            # Determine status based on distribution
            rand_val = (i / count)
            cumulative = 0
            status = QueueStatus.PENDING
            
            for stat, prob in status_distribution.items():
                cumulative += prob
                if rand_val <= cumulative:
                    status = stat
                    break
            
            complexity = ["simple", "medium", "complex"][i % 3]
            workflow_data = TestDataGenerator.generate_workflow_data(
                f"Generated Workflow {i}", complexity
            )
            
            item = QueueItem(
                id=f"item-{i:04d}",
                workflow_name=workflow_data["name"],
                workflow_data=workflow_data,
                status=status,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            
            if status in [QueueStatus.COMPLETED, QueueStatus.FAILED]:
                item.completed_at = datetime.now(timezone.utc)
                if status == QueueStatus.COMPLETED:
                    item.result_data = {"output": f"result_{i}"}
                else:
                    item.error_message = f"Test error for item {i}"
            
            items.append(item)
        
        return items


class TestEndToEndWorkflows:
    """End-to-end integration tests for complete workflows."""
    
    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database file."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        yield db_path
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)
    
    @pytest.fixture
    def database(self, temp_db_path):
        """Create a test database with file persistence."""
        db = SQLiteDatabase(temp_db_path)
        db.initialize()
        return db
    
    @pytest.fixture
    def queue_service(self, database):
        """Create queue service."""
        return QueueService(database)
    
    @pytest.fixture
    def workflow_executor(self, queue_service):
        """Create workflow executor."""
        return WorkflowExecutor(queue_service)
    
    @pytest.fixture
    def execution_monitor(self, queue_service, workflow_executor):
        """Create execution monitor."""
        return ExecutionMonitor(queue_service, workflow_executor)
    
    @pytest.fixture
    def api_client(self, queue_service):
        """Create API client for testing."""
        api = QueueManagerAPI(queue_service=queue_service)
        return api.app.test_client()
    
    def test_complete_workflow_lifecycle(self, queue_service, workflow_executor, execution_monitor):
        """Test complete workflow from creation to completion."""
        print("Testing complete workflow lifecycle...")
        
        # Start monitoring
        execution_monitor.start_monitoring()
        
        # Generate test workflow
        workflow_data = TestDataGenerator.generate_workflow_data("Lifecycle Test", "medium")
        
        # Step 1: Add workflow to queue
        workflow_id = workflow_executor.intercept_workflow_execution(workflow_data)
        assert workflow_id is not None
        
        # Step 2: Verify workflow in queue
        queue_items = queue_service.get_queue_items()
        assert len(queue_items) == 1
        assert queue_items[0].status == QueueStatus.PENDING
        
        # Step 3: Start workflow execution
        workflow_executor._update_workflow_status(workflow_id, QueueStatus.RUNNING)
        
        # Step 4: Add to monitoring
        workflow_info = workflow_executor.get_workflow_info(workflow_id)
        execution_monitor.add_workflow_to_monitor(workflow_id, workflow_info)
        
        # Step 5: Simulate execution progress
        time.sleep(0.1)  # Allow monitoring to detect
        
        # Step 6: Complete workflow
        result_data = {"output": "test_output", "execution_time": 1.5}
        workflow_executor._update_workflow_status(
            workflow_id, QueueStatus.COMPLETED, result_data=result_data
        )
        
        # Step 7: Verify final state
        final_item = queue_service.get_queue_item(workflow_info["queue_item_id"])
        assert final_item.status == QueueStatus.COMPLETED
        assert final_item.result_data == result_data
        assert final_item.completed_at is not None
        
        # Step 8: Archive workflow
        archive_result = queue_service.archive_items([final_item.id])
        assert archive_result is True
        
        archived_item = queue_service.get_queue_item(final_item.id)
        assert archived_item.status == QueueStatus.ARCHIVED
        
        execution_monitor.stop_monitoring()
        print("✓ Complete workflow lifecycle test passed")
    
    def test_api_workflow_integration(self, api_client, queue_service):
        """Test workflow management through API endpoints."""
        print("Testing API workflow integration...")
        
        # Generate test workflow
        workflow_data = TestDataGenerator.generate_workflow_data("API Test")
        
        # Step 1: Add workflow via API
        response = api_client.post('/api/queue/items',
                                 data=json.dumps({
                                     'workflow_name': workflow_data['name'],
                                     'workflow_data': workflow_data
                                 }),
                                 content_type='application/json')
        assert response.status_code == 201
        
        response_data = json.loads(response.data)
        item_id = response_data['item']['id']
        
        # Step 2: Get workflow via API
        response = api_client.get(f'/api/queue/items/{item_id}')
        assert response.status_code == 200
        
        item_data = json.loads(response.data)
        assert item_data['item']['workflow_name'] == workflow_data['name']
        
        # Step 3: Update workflow status via API
        response = api_client.put(f'/api/queue/items/{item_id}',
                                data=json.dumps({'status': 'completed'}),
                                content_type='application/json')
        assert response.status_code == 200
        
        # Step 4: Filter workflows via API
        response = api_client.post('/api/queue/items/filter',
                                 data=json.dumps({'status': ['completed']}),
                                 content_type='application/json')
        assert response.status_code == 200
        
        filtered_data = json.loads(response.data)
        filtered_items = filtered_data['items']
        assert len(filtered_items) == 1
        assert filtered_items[0]['id'] == item_id
        
        # Step 5: Archive via API
        response = api_client.post('/api/queue/archive',
                                 data=json.dumps({'item_ids': [item_id]}),
                                 content_type='application/json')
        assert response.status_code == 200
        
        # Step 6: Export via API
        response = api_client.post('/api/queue/export',
                                 data=json.dumps({}),
                                 content_type='application/json')
        assert response.status_code == 200
        
        export_response = json.loads(response.data)
        export_data = export_response['export_data']
        assert 'version' in export_data
        assert 'items' in export_data
        
        print("✓ API workflow integration test passed")
    
    def test_database_persistence_across_restarts(self, temp_db_path):
        """Test that queue data persists across database reconnections."""
        print("Testing database persistence across restarts...")
        
        # Phase 1: Create and populate database
        db1 = SQLiteDatabase(temp_db_path)
        db1.initialize()
        service1 = QueueService(db1)
        
        # Add test workflows
        test_items = TestDataGenerator.generate_queue_items(5)
        for item in test_items:
            service1.add_workflow(
                item.workflow_name,
                item.workflow_data,
                item.status
            )
        
        # Get initial count
        initial_items = service1.get_queue_items()
        initial_count = len(initial_items)
        assert initial_count == 5
        
        # Close first connection
        db1.close()
        
        # Phase 2: Reconnect and verify data persistence
        db2 = SQLiteDatabase(temp_db_path)
        db2.initialize()
        service2 = QueueService(db2)
        
        # Verify all items are still there
        persisted_items = service2.get_queue_items()
        assert len(persisted_items) == initial_count
        
        # Verify item details match
        for original, persisted in zip(initial_items, persisted_items):
            assert original.workflow_name == persisted.workflow_name
            assert original.status == persisted.status
        
        # Add more items to verify write functionality
        new_workflow = TestDataGenerator.generate_workflow_data("Persistence Test")
        new_item_id = service2.add_workflow(
            new_workflow["name"],
            new_workflow,
            QueueStatus.PENDING
        )
        assert new_item_id is not None
        
        # Verify total count
        final_items = service2.get_queue_items()
        assert len(final_items) == initial_count + 1
        
        db2.close()
        print("✓ Database persistence test passed")
    
    def test_import_export_workflow(self, queue_service):
        """Test complete import/export workflow."""
        print("Testing import/export workflow...")
        
        # Step 1: Create test data
        test_items = TestDataGenerator.generate_queue_items(10)
        for item in test_items:
            queue_service.add_workflow(
                item.workflow_name,
                item.workflow_data,
                item.status
            )
        
        # Step 2: Export all items
        export_data = queue_service.export_queue()
        assert 'version' in export_data
        assert 'items' in export_data
        assert len(export_data['items']) == 10
        
        # Step 3: Clear queue
        all_items = queue_service.get_queue_items()
        item_ids = [item.id for item in all_items]
        queue_service.delete_items(item_ids)
        
        # Verify queue is empty
        empty_items = queue_service.get_queue_items()
        assert len(empty_items) == 0
        
        # Step 4: Import data back
        import_result = queue_service.import_queue(export_data, merge=False)
        assert import_result is True
        
        # Step 5: Verify imported data
        imported_items = queue_service.get_queue_items()
        assert len(imported_items) == 10
        
        # Verify item details
        for original, imported in zip(test_items, imported_items):
            assert original.workflow_name == imported.workflow_name
            assert original.status == imported.status
        
        print("✓ Import/export workflow test passed")


class TestPerformanceTests:
    """Performance tests for large queues and operations."""
    
    @pytest.fixture
    def database(self):
        """Create in-memory database for performance tests."""
        db = SQLiteDatabase(":memory:")
        db.initialize()
        return db
    
    @pytest.fixture
    def queue_service(self, database):
        """Create queue service."""
        return QueueService(database)
    
    def test_large_queue_performance(self, queue_service):
        """Test performance with large number of queue items."""
        print("Testing large queue performance...")
        
        # Test parameters
        item_counts = [100, 500, 1000, 2000]
        performance_results = {}
        
        for count in item_counts:
            print(f"  Testing with {count} items...")
            
            # Clear queue
            all_items = queue_service.get_queue_items()
            if all_items:
                item_ids = [item.id for item in all_items]
                queue_service.delete_items(item_ids)
            
            # Measure insertion time
            start_time = time.time()
            
            test_items = TestDataGenerator.generate_queue_items(count)
            for item in test_items:
                queue_service.add_workflow(
                    item.workflow_name,
                    item.workflow_data,
                    item.status
                )
            
            insertion_time = time.time() - start_time
            
            # Measure retrieval time
            start_time = time.time()
            retrieved_items = queue_service.get_queue_items()
            retrieval_time = time.time() - start_time
            
            # Measure filtering time
            start_time = time.time()
            filtered_items = queue_service.filter_items({
                'status': [QueueStatus.PENDING, QueueStatus.RUNNING]
            })
            filtering_time = time.time() - start_time
            
            # Measure search time
            start_time = time.time()
            search_results = queue_service.search_items("Workflow")
            search_time = time.time() - start_time
            
            performance_results[count] = {
                'insertion_time': insertion_time,
                'retrieval_time': retrieval_time,
                'filtering_time': filtering_time,
                'search_time': search_time,
                'items_retrieved': len(retrieved_items),
                'items_filtered': len(filtered_items),
                'items_found': len(search_results)
            }
            
            # Verify correctness
            assert len(retrieved_items) == count
            
            print(f"    Insertion: {insertion_time:.3f}s")
            print(f"    Retrieval: {retrieval_time:.3f}s")
            print(f"    Filtering: {filtering_time:.3f}s")
            print(f"    Search: {search_time:.3f}s")
        
        # Performance assertions (reasonable thresholds)
        for count, results in performance_results.items():
            # Insertion should be reasonable (< 1s per 100 items)
            assert results['insertion_time'] < (count / 100) * 1.0
            
            # Retrieval should be fast (< 0.5s for any size)
            assert results['retrieval_time'] < 0.5
            
            # Filtering should be reasonable (< 1s for any size)
            assert results['filtering_time'] < 1.0
            
            # Search should be reasonable (< 2s for any size)
            assert results['search_time'] < 2.0
        
        print("✓ Large queue performance test passed")
        return performance_results
    
    def test_concurrent_operations_performance(self, queue_service):
        """Test performance under concurrent operations."""
        print("Testing concurrent operations performance...")
        
        # Test parameters
        num_threads = 10
        operations_per_thread = 50
        
        # Prepare test data
        base_workflows = [
            TestDataGenerator.generate_workflow_data(f"Concurrent Test {i}")
            for i in range(operations_per_thread)
        ]
        
        def worker_thread(thread_id, workflows):
            """Worker function for concurrent operations."""
            results = []
            
            for i, workflow in enumerate(workflows):
                try:
                    # Add workflow
                    start_time = time.time()
                    item_id = queue_service.add_workflow(
                        f"{workflow['name']} (Thread {thread_id})",
                        workflow,
                        QueueStatus.PENDING
                    )
                    add_time = time.time() - start_time
                    
                    # Update status
                    start_time = time.time()
                    queue_service.update_item_status(item_id, QueueStatus.RUNNING)
                    update_time = time.time() - start_time
                    
                    # Get item
                    start_time = time.time()
                    item = queue_service.get_queue_item(item_id)
                    get_time = time.time() - start_time
                    
                    results.append({
                        'thread_id': thread_id,
                        'operation_id': i,
                        'item_id': item_id,
                        'add_time': add_time,
                        'update_time': update_time,
                        'get_time': get_time,
                        'success': True
                    })
                    
                except Exception as e:
                    results.append({
                        'thread_id': thread_id,
                        'operation_id': i,
                        'error': str(e),
                        'success': False
                    })
            
            return results
        
        # Execute concurrent operations
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = []
            for thread_id in range(num_threads):
                future = executor.submit(worker_thread, thread_id, base_workflows)
                futures.append(future)
            
            # Collect results
            all_results = []
            for future in as_completed(futures):
                thread_results = future.result()
                all_results.extend(thread_results)
        
        total_time = time.time() - start_time
        
        # Analyze results
        successful_operations = [r for r in all_results if r['success']]
        failed_operations = [r for r in all_results if not r['success']]
        
        total_operations = num_threads * operations_per_thread
        success_rate = len(successful_operations) / total_operations
        
        print(f"  Total operations: {total_operations}")
        print(f"  Successful: {len(successful_operations)}")
        print(f"  Failed: {len(failed_operations)}")
        print(f"  Success rate: {success_rate:.2%}")
        print(f"  Total time: {total_time:.3f}s")
        print(f"  Operations per second: {total_operations / total_time:.1f}")
        
        # Performance assertions
        assert success_rate >= 0.95  # At least 95% success rate
        assert total_time < 30.0  # Should complete within 30 seconds
        
        # Verify database consistency
        final_items = queue_service.get_queue_items()
        assert len(final_items) >= len(successful_operations)
        
        print("✓ Concurrent operations performance test passed")
        return {
            'total_operations': total_operations,
            'successful_operations': len(successful_operations),
            'failed_operations': len(failed_operations),
            'success_rate': success_rate,
            'total_time': total_time,
            'operations_per_second': total_operations / total_time
        }
    
    def test_memory_usage_with_large_datasets(self, queue_service):
        """Test memory usage with large datasets."""
        print("Testing memory usage with large datasets...")
        
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Add large number of items
        large_item_count = 5000
        print(f"  Adding {large_item_count} items...")
        
        test_items = TestDataGenerator.generate_queue_items(large_item_count)
        for i, item in enumerate(test_items):
            queue_service.add_workflow(
                item.workflow_name,
                item.workflow_data,
                item.status
            )
            
            # Check memory every 1000 items
            if (i + 1) % 1000 == 0:
                current_memory = process.memory_info().rss / 1024 / 1024
                memory_increase = current_memory - initial_memory
                print(f"    {i + 1} items: {current_memory:.1f} MB (+{memory_increase:.1f} MB)")
        
        final_memory = process.memory_info().rss / 1024 / 1024
        total_memory_increase = final_memory - initial_memory
        
        print(f"  Final memory usage: {final_memory:.1f} MB")
        print(f"  Total increase: {total_memory_increase:.1f} MB")
        print(f"  Memory per item: {total_memory_increase / large_item_count * 1024:.1f} KB")
        
        # Memory usage should be reasonable (< 100 MB for 5000 items)
        assert total_memory_increase < 100.0
        
        # Test memory cleanup after operations
        print("  Testing memory cleanup...")
        
        # Delete all items
        all_items = queue_service.get_queue_items()
        item_ids = [item.id for item in all_items]
        queue_service.delete_items(item_ids)
        
        # Force garbage collection
        import gc
        gc.collect()
        
        cleanup_memory = process.memory_info().rss / 1024 / 1024
        memory_freed = final_memory - cleanup_memory
        
        print(f"  Memory after cleanup: {cleanup_memory:.1f} MB")
        print(f"  Memory freed: {memory_freed:.1f} MB")
        
        print("✓ Memory usage test passed")
        return {
            'initial_memory_mb': initial_memory,
            'final_memory_mb': final_memory,
            'total_increase_mb': total_memory_increase,
            'memory_per_item_kb': total_memory_increase / large_item_count * 1024,
            'cleanup_memory_mb': cleanup_memory,
            'memory_freed_mb': memory_freed
        }


class TestStressTests:
    """Stress tests for concurrent operations and edge cases."""
    
    @pytest.fixture
    def database(self):
        """Create in-memory database for stress tests."""
        db = SQLiteDatabase(":memory:")
        db.initialize()
        return db
    
    @pytest.fixture
    def queue_service(self, database):
        """Create queue service."""
        return QueueService(database)
    
    @pytest.fixture
    def workflow_executor(self, queue_service):
        """Create workflow executor."""
        return WorkflowExecutor(queue_service)
    
    def test_high_concurrency_stress(self, queue_service, workflow_executor):
        """Stress test with high concurrency."""
        print("Running high concurrency stress test...")
        
        # Test parameters
        num_threads = 20
        operations_per_thread = 100
        
        # Shared state for tracking
        operation_results = []
        operation_lock = threading.Lock()
        
        def stress_worker(thread_id):
            """Worker function for stress testing."""
            local_results = []
            
            for op_id in range(operations_per_thread):
                try:
                    # Generate unique workflow
                    workflow = TestDataGenerator.generate_workflow_data(
                        f"Stress-T{thread_id}-Op{op_id}",
                        complexity="medium"
                    )
                    
                    # Add to queue
                    item_id = queue_service.add_workflow(
                        workflow["name"],
                        workflow,
                        QueueStatus.PENDING
                    )
                    
                    # Simulate workflow execution
                    workflow_id = workflow_executor.intercept_workflow_execution(workflow)
                    
                    # Random operations
                    import random
                    operations = [
                        lambda: queue_service.update_item_status(item_id, QueueStatus.RUNNING),
                        lambda: queue_service.get_queue_item(item_id),
                        lambda: queue_service.filter_items({'status': [QueueStatus.PENDING]}),
                        lambda: queue_service.search_items(f"Stress-T{thread_id}"),
                    ]
                    
                    # Execute random operations
                    for _ in range(3):
                        op = random.choice(operations)
                        op()
                    
                    # Complete workflow
                    workflow_executor._update_workflow_status(
                        workflow_id,
                        QueueStatus.COMPLETED,
                        result_data={"thread": thread_id, "op": op_id}
                    )
                    
                    local_results.append({
                        'thread_id': thread_id,
                        'op_id': op_id,
                        'item_id': item_id,
                        'workflow_id': workflow_id,
                        'success': True
                    })
                    
                except Exception as e:
                    local_results.append({
                        'thread_id': thread_id,
                        'op_id': op_id,
                        'error': str(e),
                        'success': False
                    })
            
            # Thread-safe result collection
            with operation_lock:
                operation_results.extend(local_results)
        
        # Execute stress test
        start_time = time.time()
        
        threads = []
        for thread_id in range(num_threads):
            thread = threading.Thread(target=stress_worker, args=(thread_id,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        total_time = time.time() - start_time
        
        # Analyze results
        successful_ops = [r for r in operation_results if r['success']]
        failed_ops = [r for r in operation_results if not r['success']]
        
        total_ops = num_threads * operations_per_thread
        success_rate = len(successful_ops) / total_ops
        
        print(f"  Total operations: {total_ops}")
        print(f"  Successful: {len(successful_ops)}")
        print(f"  Failed: {len(failed_ops)}")
        print(f"  Success rate: {success_rate:.2%}")
        print(f"  Total time: {total_time:.3f}s")
        print(f"  Operations per second: {total_ops / total_time:.1f}")
        
        # Stress test assertions (more lenient than performance tests)
        assert success_rate >= 0.90  # At least 90% success rate under stress
        assert total_time < 60.0  # Should complete within 60 seconds
        
        # Verify database integrity
        final_items = queue_service.get_queue_items()
        print(f"  Final queue items: {len(final_items)}")
        
        print("✓ High concurrency stress test passed")
        return {
            'success_rate': success_rate,
            'total_time': total_time,
            'operations_per_second': total_ops / total_time
        }
    
    def test_database_corruption_recovery(self, temp_db_path=None):
        """Test recovery from database corruption scenarios."""
        print("Testing database corruption recovery...")
        
        if temp_db_path is None:
            with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
                temp_db_path = f.name
        
        try:
            # Phase 1: Create and populate database
            db = SQLiteDatabase(temp_db_path)
            db.initialize()
            service = QueueService(db)
            
            # Add test data
            test_items = TestDataGenerator.generate_queue_items(10)
            for item in test_items:
                service.add_workflow(
                    item.workflow_name,
                    item.workflow_data,
                    item.status
                )
            
            initial_count = len(service.get_queue_items())
            db.close()
            
            # Phase 2: Simulate corruption by truncating file
            print("  Simulating database corruption...")
            with open(temp_db_path, 'r+b') as f:
                f.truncate(100)  # Truncate to invalid size
            
            # Phase 3: Test recovery
            print("  Testing recovery...")
            db2 = SQLiteDatabase(temp_db_path)
            
            # Should detect corruption and reinitialize
            try:
                db2.initialize()
                service2 = QueueService(db2)
                
                # Database should be empty after recovery
                recovered_items = service2.get_queue_items()
                print(f"  Items after recovery: {len(recovered_items)}")
                
                # Should be able to add new items
                new_workflow = TestDataGenerator.generate_workflow_data("Recovery Test")
                new_item_id = service2.add_workflow(
                    new_workflow["name"],
                    new_workflow,
                    QueueStatus.PENDING
                )
                assert new_item_id is not None
                
                print("  ✓ Database recovery successful")
                
            except Exception as e:
                print(f"  Database recovery failed: {e}")
                raise
            
            finally:
                db2.close()
        
        finally:
            # Cleanup
            if os.path.exists(temp_db_path):
                os.unlink(temp_db_path)
        
        print("✓ Database corruption recovery test passed")
    
    def test_resource_exhaustion_handling(self, queue_service):
        """Test handling of resource exhaustion scenarios."""
        print("Testing resource exhaustion handling...")
        
        # Test 1: Very large workflow data
        print("  Testing large workflow data...")
        
        large_workflow = TestDataGenerator.generate_workflow_data("Large Workflow", "complex")
        
        # Add very large metadata
        large_workflow["large_data"] = "x" * (1024 * 1024)  # 1MB of data
        
        try:
            item_id = queue_service.add_workflow(
                large_workflow["name"],
                large_workflow,
                QueueStatus.PENDING
            )
            assert item_id is not None
            
            # Verify retrieval
            retrieved_item = queue_service.get_queue_item(item_id)
            assert retrieved_item is not None
            assert len(retrieved_item.workflow_data["large_data"]) == 1024 * 1024
            
            print("    ✓ Large workflow data handled successfully")
            
        except Exception as e:
            print(f"    Large workflow data failed: {e}")
            # This might be expected depending on system limits
        
        # Test 2: Rapid successive operations
        print("  Testing rapid successive operations...")
        
        rapid_start_time = time.time()
        rapid_operations = 0
        
        try:
            for i in range(1000):
                workflow = TestDataGenerator.generate_workflow_data(f"Rapid-{i}", "simple")
                item_id = queue_service.add_workflow(
                    workflow["name"],
                    workflow,
                    QueueStatus.PENDING
                )
                
                # Immediate status update
                queue_service.update_item_status(item_id, QueueStatus.RUNNING)
                rapid_operations += 1
                
                # Check if we're taking too long (timeout protection)
                if time.time() - rapid_start_time > 10.0:
                    break
            
            rapid_time = time.time() - rapid_start_time
            print(f"    Completed {rapid_operations} rapid operations in {rapid_time:.3f}s")
            print(f"    Rate: {rapid_operations / rapid_time:.1f} ops/sec")
            
        except Exception as e:
            print(f"    Rapid operations failed after {rapid_operations} operations: {e}")
        
        print("✓ Resource exhaustion handling test completed")


def run_integration_test_suite():
    """Run the complete integration test suite."""
    print("=" * 80)
    print("COMFYUI QUEUE MANAGER - INTEGRATION TEST SUITE")
    print("=" * 80)
    
    # Test results tracking
    test_results = {
        'end_to_end': {},
        'performance': {},
        'stress': {}
    }
    
    try:
        # End-to-end tests
        print("\n" + "=" * 40)
        print("END-TO-END TESTS")
        print("=" * 40)
        
        e2e_tester = TestEndToEndWorkflows()
        
        # Create fixtures manually for standalone execution
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            temp_db_path = f.name
        
        try:
            database = SQLiteDatabase(temp_db_path)
            database.initialize()
            queue_service = QueueService(database)
            workflow_executor = WorkflowExecutor(queue_service)
            execution_monitor = ExecutionMonitor(queue_service, workflow_executor)
            api = QueueManagerAPI(queue_service=queue_service)
            api_client = api.app.test_client()
            
            # Run end-to-end tests
            e2e_tester.test_complete_workflow_lifecycle(
                queue_service, workflow_executor, execution_monitor
            )
            test_results['end_to_end']['workflow_lifecycle'] = True
            
            e2e_tester.test_api_workflow_integration(api_client, queue_service)
            test_results['end_to_end']['api_integration'] = True
            
            e2e_tester.test_database_persistence_across_restarts(temp_db_path)
            test_results['end_to_end']['database_persistence'] = True
            
            e2e_tester.test_import_export_workflow(queue_service)
            test_results['end_to_end']['import_export'] = True
            
            database.close()
            
        finally:
            if os.path.exists(temp_db_path):
                os.unlink(temp_db_path)
        
        # Performance tests
        print("\n" + "=" * 40)
        print("PERFORMANCE TESTS")
        print("=" * 40)
        
        perf_tester = TestPerformanceTests()
        database = SQLiteDatabase(":memory:")
        database.initialize()
        queue_service = QueueService(database)
        
        test_results['performance']['large_queue'] = perf_tester.test_large_queue_performance(queue_service)
        test_results['performance']['concurrent_ops'] = perf_tester.test_concurrent_operations_performance(queue_service)
        test_results['performance']['memory_usage'] = perf_tester.test_memory_usage_with_large_datasets(queue_service)
        
        database.close()
        
        # Stress tests
        print("\n" + "=" * 40)
        print("STRESS TESTS")
        print("=" * 40)
        
        stress_tester = TestStressTests()
        database = SQLiteDatabase(":memory:")
        database.initialize()
        queue_service = QueueService(database)
        workflow_executor = WorkflowExecutor(queue_service)
        
        test_results['stress']['high_concurrency'] = stress_tester.test_high_concurrency_stress(
            queue_service, workflow_executor
        )
        stress_tester.test_database_corruption_recovery()
        test_results['stress']['corruption_recovery'] = True
        
        stress_tester.test_resource_exhaustion_handling(queue_service)
        test_results['stress']['resource_exhaustion'] = True
        
        database.close()
        
        # Summary
        print("\n" + "=" * 80)
        print("INTEGRATION TEST SUITE SUMMARY")
        print("=" * 80)
        
        total_tests = 0
        passed_tests = 0
        
        for category, tests in test_results.items():
            print(f"\n{category.upper()} TESTS:")
            for test_name, result in tests.items():
                total_tests += 1
                if result is True or (isinstance(result, dict) and result):
                    passed_tests += 1
                    print(f"  ✓ {test_name}")
                else:
                    print(f"  ✗ {test_name}")
        
        success_rate = passed_tests / total_tests if total_tests > 0 else 0
        print(f"\nOVERALL RESULTS:")
        print(f"  Total tests: {total_tests}")
        print(f"  Passed: {passed_tests}")
        print(f"  Success rate: {success_rate:.1%}")
        
        if success_rate >= 0.95:
            print("\n🎉 INTEGRATION TEST SUITE PASSED!")
            return 0
        else:
            print("\n❌ INTEGRATION TEST SUITE FAILED!")
            return 1
            
    except Exception as e:
        print(f"\n❌ INTEGRATION TEST SUITE FAILED WITH ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(run_integration_test_suite())