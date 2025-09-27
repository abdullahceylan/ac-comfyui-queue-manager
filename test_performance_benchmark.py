#!/usr/bin/env python3
"""
Performance benchmarking suite for ComfyUI Queue Manager.
Measures and reports performance metrics for various operations.
"""

import json
import os
import sys
import time
import threading
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Dict, List, Any, Callable

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import SQLiteDatabase
from queue_service import QueueService
from test_fixtures import TestDataFactory, WorkflowTemplates


class PerformanceBenchmark:
    """Performance benchmarking utility."""
    
    def __init__(self, name: str):
        self.name = name
        self.results = []
        self.start_time = None
        self.end_time = None
    
    def start(self):
        """Start timing."""
        self.start_time = time.perf_counter()
    
    def stop(self):
        """Stop timing and record result."""
        if self.start_time is None:
            raise ValueError("Benchmark not started")
        
        self.end_time = time.perf_counter()
        duration = self.end_time - self.start_time
        self.results.append(duration)
        return duration
    
    def get_statistics(self) -> Dict[str, float]:
        """Get statistical summary of results."""
        if not self.results:
            return {}
        
        return {
            'count': len(self.results),
            'total_time': sum(self.results),
            'mean': statistics.mean(self.results),
            'median': statistics.median(self.results),
            'min': min(self.results),
            'max': max(self.results),
            'stdev': statistics.stdev(self.results) if len(self.results) > 1 else 0.0
        }
    
    def reset(self):
        """Reset benchmark results."""
        self.results = []
        self.start_time = None
        self.end_time = None


class DatabasePerformanceBenchmarks:
    """Database operation performance benchmarks."""
    
    def __init__(self, database: SQLiteDatabase):
        self.database = database
        self.queue_service = QueueService(database)
    
    def benchmark_insertion_performance(self, item_counts: List[int]) -> Dict[str, Any]:
        """Benchmark item insertion performance."""
        print("Benchmarking insertion performance...")
        
        results = {}
        
        for count in item_counts:
            print(f"  Testing {count} insertions...")
            
            # Clear existing data
            existing_items = self.queue_service.get_queue_items()
            if existing_items:
                item_ids = [item.id for item in existing_items]
                self.queue_service.delete_items(item_ids)
            
            # Generate test data
            test_items = TestDataFactory.create_queue_items_batch(count)
            
            # Benchmark individual insertions
            individual_benchmark = PerformanceBenchmark(f"individual_insertion_{count}")
            
            for item in test_items:
                individual_benchmark.start()
                self.queue_service.add_workflow(
                    item.workflow_name,
                    item.workflow_data,
                    item.status
                )
                individual_benchmark.stop()
            
            # Benchmark batch retrieval after insertion
            retrieval_benchmark = PerformanceBenchmark(f"retrieval_after_insertion_{count}")
            retrieval_benchmark.start()
            retrieved_items = self.queue_service.get_queue_items()
            retrieval_benchmark.stop()
            
            individual_stats = individual_benchmark.get_statistics()
            retrieval_stats = retrieval_benchmark.get_statistics()
            
            results[count] = {
                'insertion': individual_stats,
                'retrieval': retrieval_stats,
                'items_inserted': count,
                'items_retrieved': len(retrieved_items),
                'insertion_rate': count / individual_stats['total_time'] if individual_stats['total_time'] > 0 else 0,
                'avg_insertion_time': individual_stats['mean'] * 1000,  # Convert to ms
                'retrieval_time': retrieval_stats['total_time'] * 1000  # Convert to ms
            }
            
            print(f"    Insertion rate: {results[count]['insertion_rate']:.1f} items/sec")
            print(f"    Avg insertion time: {results[count]['avg_insertion_time']:.2f} ms")
            print(f"    Retrieval time: {results[count]['retrieval_time']:.2f} ms")
        
        return results
    
    def benchmark_query_performance(self, item_count: int = 1000) -> Dict[str, Any]:
        """Benchmark various query operations."""
        print(f"Benchmarking query performance with {item_count} items...")
        
        # Setup test data
        existing_items = self.queue_service.get_queue_items()
        if existing_items:
            item_ids = [item.id for item in existing_items]
            self.queue_service.delete_items(item_ids)
        
        test_items = TestDataFactory.create_queue_items_batch(item_count)
        for item in test_items:
            self.queue_service.add_workflow(
                item.workflow_name,
                item.workflow_data,
                item.status
            )
        
        results = {}
        
        # Benchmark different query types
        query_tests = [
            ("get_all_items", lambda: self.queue_service.get_queue_items()),
            ("filter_by_status", lambda: self.queue_service.filter_items({'status': ['pending']})),
            ("filter_by_multiple_status", lambda: self.queue_service.filter_items({
                'status': ['pending', 'running', 'completed']
            })),
            ("search_by_name", lambda: self.queue_service.search_items("Test Workflow")),
            ("search_by_partial_name", lambda: self.queue_service.search_items("Workflow")),
            ("get_single_item", lambda: self.queue_service.get_queue_item(test_items[0].id)),
        ]
        
        for test_name, query_func in query_tests:
            print(f"  Testing {test_name}...")
            
            benchmark = PerformanceBenchmark(test_name)
            
            # Run query multiple times for statistical accuracy
            for _ in range(10):
                benchmark.start()
                result = query_func()
                benchmark.stop()
            
            stats = benchmark.get_statistics()
            results[test_name] = {
                'stats': stats,
                'avg_time_ms': stats['mean'] * 1000,
                'queries_per_second': 1 / stats['mean'] if stats['mean'] > 0 else 0
            }
            
            print(f"    Avg time: {results[test_name]['avg_time_ms']:.2f} ms")
            print(f"    Queries/sec: {results[test_name]['queries_per_second']:.1f}")
        
        return results
    
    def benchmark_update_performance(self, item_count: int = 500) -> Dict[str, Any]:
        """Benchmark update operations."""
        print(f"Benchmarking update performance with {item_count} items...")
        
        # Setup test data
        existing_items = self.queue_service.get_queue_items()
        if existing_items:
            item_ids = [item.id for item in existing_items]
            self.queue_service.delete_items(item_ids)
        
        test_items = TestDataFactory.create_queue_items_batch(item_count)
        item_ids = []
        for item in test_items:
            item_id = self.queue_service.add_workflow(
                item.workflow_name,
                item.workflow_data,
                item.status
            )
            item_ids.append(item_id)
        
        results = {}
        
        # Benchmark individual updates
        print("  Testing individual status updates...")
        individual_benchmark = PerformanceBenchmark("individual_updates")
        
        for item_id in item_ids[:100]:  # Test first 100 items
            individual_benchmark.start()
            self.queue_service.update_item_status(item_id, 'running')
            individual_benchmark.stop()
        
        individual_stats = individual_benchmark.get_statistics()
        results['individual_updates'] = {
            'stats': individual_stats,
            'avg_time_ms': individual_stats['mean'] * 1000,
            'updates_per_second': 1 / individual_stats['mean'] if individual_stats['mean'] > 0 else 0
        }
        
        # Benchmark bulk operations
        print("  Testing bulk operations...")
        bulk_benchmark = PerformanceBenchmark("bulk_operations")
        
        # Archive operation
        bulk_benchmark.start()
        self.queue_service.archive_items(item_ids[:50])
        bulk_benchmark.stop()
        
        # Delete operation
        bulk_benchmark.start()
        self.queue_service.delete_items(item_ids[50:100])
        bulk_benchmark.stop()
        
        bulk_stats = bulk_benchmark.get_statistics()
        results['bulk_operations'] = {
            'stats': bulk_stats,
            'avg_time_ms': bulk_stats['mean'] * 1000,
            'operations_per_second': 1 / bulk_stats['mean'] if bulk_stats['mean'] > 0 else 0
        }
        
        print(f"    Individual updates: {results['individual_updates']['avg_time_ms']:.2f} ms avg")
        print(f"    Bulk operations: {results['bulk_operations']['avg_time_ms']:.2f} ms avg")
        
        return results


class ConcurrencyBenchmarks:
    """Concurrency performance benchmarks."""
    
    def __init__(self, database: SQLiteDatabase):
        self.database = database
        self.queue_service = QueueService(database)
    
    def benchmark_concurrent_insertions(self, thread_counts: List[int], operations_per_thread: int = 50) -> Dict[str, Any]:
        """Benchmark concurrent insertion performance."""
        print("Benchmarking concurrent insertions...")
        
        results = {}
        
        for thread_count in thread_counts:
            print(f"  Testing {thread_count} threads, {operations_per_thread} ops each...")
            
            # Clear existing data
            existing_items = self.queue_service.get_queue_items()
            if existing_items:
                item_ids = [item.id for item in existing_items]
                self.queue_service.delete_items(item_ids)
            
            # Prepare test data for each thread
            thread_data = []
            for thread_id in range(thread_count):
                thread_items = TestDataFactory.create_queue_items_batch(operations_per_thread)
                thread_data.append(thread_items)
            
            def worker_thread(thread_id: int, items: List) -> Dict[str, Any]:
                """Worker function for concurrent operations."""
                thread_results = {
                    'thread_id': thread_id,
                    'operations': 0,
                    'errors': 0,
                    'start_time': time.perf_counter()
                }
                
                for item in items:
                    try:
                        self.queue_service.add_workflow(
                            f"{item.workflow_name} (T{thread_id})",
                            item.workflow_data,
                            item.status
                        )
                        thread_results['operations'] += 1
                    except Exception as e:
                        thread_results['errors'] += 1
                
                thread_results['end_time'] = time.perf_counter()
                thread_results['duration'] = thread_results['end_time'] - thread_results['start_time']
                
                return thread_results
            
            # Execute concurrent operations
            start_time = time.perf_counter()
            
            with ThreadPoolExecutor(max_workers=thread_count) as executor:
                futures = []
                for thread_id, items in enumerate(thread_data):
                    future = executor.submit(worker_thread, thread_id, items)
                    futures.append(future)
                
                thread_results = []
                for future in as_completed(futures):
                    result = future.result()
                    thread_results.append(result)
            
            total_time = time.perf_counter() - start_time
            
            # Analyze results
            total_operations = sum(r['operations'] for r in thread_results)
            total_errors = sum(r['errors'] for r in thread_results)
            success_rate = total_operations / (total_operations + total_errors) if (total_operations + total_errors) > 0 else 0
            
            results[thread_count] = {
                'thread_count': thread_count,
                'operations_per_thread': operations_per_thread,
                'total_operations': total_operations,
                'total_errors': total_errors,
                'success_rate': success_rate,
                'total_time': total_time,
                'operations_per_second': total_operations / total_time if total_time > 0 else 0,
                'thread_results': thread_results
            }
            
            print(f"    Total operations: {total_operations}")
            print(f"    Success rate: {success_rate:.2%}")
            print(f"    Operations/sec: {results[thread_count]['operations_per_second']:.1f}")
            print(f"    Total time: {total_time:.3f}s")
        
        return results
    
    def benchmark_concurrent_mixed_operations(self, thread_count: int = 10, duration_seconds: int = 30) -> Dict[str, Any]:
        """Benchmark mixed concurrent operations over time."""
        print(f"Benchmarking mixed concurrent operations ({thread_count} threads, {duration_seconds}s)...")
        
        # Setup initial data
        existing_items = self.queue_service.get_queue_items()
        if existing_items:
            item_ids = [item.id for item in existing_items]
            self.queue_service.delete_items(item_ids)
        
        # Add some initial items
        initial_items = TestDataFactory.create_queue_items_batch(100)
        initial_item_ids = []
        for item in initial_items:
            item_id = self.queue_service.add_workflow(
                item.workflow_name,
                item.workflow_data,
                item.status
            )
            initial_item_ids.append(item_id)
        
        # Shared state
        operation_counts = {
            'insertions': 0,
            'updates': 0,
            'queries': 0,
            'deletes': 0,
            'errors': 0
        }
        operation_lock = threading.Lock()
        stop_flag = threading.Event()
        
        def mixed_operations_worker(worker_id: int) -> Dict[str, Any]:
            """Worker that performs mixed operations."""
            import random
            
            local_counts = {
                'insertions': 0,
                'updates': 0,
                'queries': 0,
                'deletes': 0,
                'errors': 0
            }
            
            while not stop_flag.is_set():
                try:
                    # Randomly choose operation type
                    operation = random.choice(['insert', 'update', 'query', 'query', 'query'])  # Bias toward queries
                    
                    if operation == 'insert':
                        workflow = TestDataFactory.create_queue_item()
                        self.queue_service.add_workflow(
                            f"{workflow.workflow_name} (W{worker_id})",
                            workflow.workflow_data,
                            workflow.status
                        )
                        local_counts['insertions'] += 1
                    
                    elif operation == 'update':
                        # Get random item and update it
                        items = self.queue_service.get_queue_items()
                        if items:
                            random_item = random.choice(items)
                            self.queue_service.update_item_status(random_item.id, 'running')
                            local_counts['updates'] += 1
                    
                    elif operation == 'query':
                        # Perform various query operations
                        query_type = random.choice(['all', 'filter', 'search'])
                        
                        if query_type == 'all':
                            self.queue_service.get_queue_items()
                        elif query_type == 'filter':
                            self.queue_service.filter_items({'status': ['pending']})
                        else:
                            self.queue_service.search_items("Workflow")
                        
                        local_counts['queries'] += 1
                    
                    # Small delay to prevent overwhelming the system
                    time.sleep(0.001)
                    
                except Exception as e:
                    local_counts['errors'] += 1
            
            return local_counts
        
        # Start worker threads
        start_time = time.perf_counter()
        
        with ThreadPoolExecutor(max_workers=thread_count) as executor:
            futures = []
            for worker_id in range(thread_count):
                future = executor.submit(mixed_operations_worker, worker_id)
                futures.append(future)
            
            # Let it run for specified duration
            time.sleep(duration_seconds)
            stop_flag.set()
            
            # Collect results
            worker_results = []
            for future in as_completed(futures):
                result = future.result()
                worker_results.append(result)
        
        total_time = time.perf_counter() - start_time
        
        # Aggregate results
        total_counts = {
            'insertions': sum(r['insertions'] for r in worker_results),
            'updates': sum(r['updates'] for r in worker_results),
            'queries': sum(r['queries'] for r in worker_results),
            'deletes': sum(r['deletes'] for r in worker_results),
            'errors': sum(r['errors'] for r in worker_results)
        }
        
        total_operations = sum(total_counts.values()) - total_counts['errors']
        
        results = {
            'thread_count': thread_count,
            'duration_seconds': duration_seconds,
            'total_time': total_time,
            'operation_counts': total_counts,
            'total_operations': total_operations,
            'operations_per_second': total_operations / total_time if total_time > 0 else 0,
            'error_rate': total_counts['errors'] / (total_operations + total_counts['errors']) if (total_operations + total_counts['errors']) > 0 else 0,
            'worker_results': worker_results
        }
        
        print(f"    Total operations: {total_operations}")
        print(f"    Operations/sec: {results['operations_per_second']:.1f}")
        print(f"    Error rate: {results['error_rate']:.2%}")
        print(f"    Breakdown: {total_counts}")
        
        return results


class MemoryBenchmarks:
    """Memory usage benchmarks."""
    
    def __init__(self, database: SQLiteDatabase):
        self.database = database
        self.queue_service = QueueService(database)
    
    def benchmark_memory_usage(self, item_counts: List[int]) -> Dict[str, Any]:
        """Benchmark memory usage with different item counts."""
        print("Benchmarking memory usage...")
        
        try:
            import psutil
            import os
        except ImportError:
            print("  psutil not available, skipping memory benchmarks")
            return {}
        
        process = psutil.Process(os.getpid())
        results = {}
        
        for count in item_counts:
            print(f"  Testing memory usage with {count} items...")
            
            # Clear existing data
            existing_items = self.queue_service.get_queue_items()
            if existing_items:
                item_ids = [item.id for item in existing_items]
                self.queue_service.delete_items(item_ids)
            
            # Force garbage collection
            import gc
            gc.collect()
            
            # Measure initial memory
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # Add items and measure memory growth
            test_items = TestDataFactory.create_queue_items_batch(count)
            
            memory_samples = [initial_memory]
            
            for i, item in enumerate(test_items):
                self.queue_service.add_workflow(
                    item.workflow_name,
                    item.workflow_data,
                    item.status
                )
                
                # Sample memory every 100 items
                if (i + 1) % max(1, count // 10) == 0:
                    current_memory = process.memory_info().rss / 1024 / 1024
                    memory_samples.append(current_memory)
            
            final_memory = process.memory_info().rss / 1024 / 1024
            memory_increase = final_memory - initial_memory
            
            results[count] = {
                'item_count': count,
                'initial_memory_mb': initial_memory,
                'final_memory_mb': final_memory,
                'memory_increase_mb': memory_increase,
                'memory_per_item_kb': (memory_increase * 1024) / count if count > 0 else 0,
                'memory_samples': memory_samples
            }
            
            print(f"    Memory increase: {memory_increase:.1f} MB")
            print(f"    Memory per item: {results[count]['memory_per_item_kb']:.1f} KB")
        
        return results


def run_performance_benchmarks():
    """Run the complete performance benchmark suite."""
    print("=" * 80)
    print("COMFYUI QUEUE MANAGER - PERFORMANCE BENCHMARKS")
    print("=" * 80)
    
    # Create test database
    database = SQLiteDatabase(":memory:")
    database.initialize()
    
    all_results = {}
    
    try:
        # Database performance benchmarks
        print("\n" + "=" * 40)
        print("DATABASE PERFORMANCE BENCHMARKS")
        print("=" * 40)
        
        db_benchmarks = DatabasePerformanceBenchmarks(database)
        
        # Insertion performance
        insertion_results = db_benchmarks.benchmark_insertion_performance([10, 50, 100, 500, 1000])
        all_results['insertion_performance'] = insertion_results
        
        # Query performance
        query_results = db_benchmarks.benchmark_query_performance(1000)
        all_results['query_performance'] = query_results
        
        # Update performance
        update_results = db_benchmarks.benchmark_update_performance(500)
        all_results['update_performance'] = update_results
        
        # Concurrency benchmarks
        print("\n" + "=" * 40)
        print("CONCURRENCY BENCHMARKS")
        print("=" * 40)
        
        concurrency_benchmarks = ConcurrencyBenchmarks(database)
        
        # Concurrent insertions
        concurrent_insertion_results = concurrency_benchmarks.benchmark_concurrent_insertions([1, 2, 5, 10], 50)
        all_results['concurrent_insertions'] = concurrent_insertion_results
        
        # Mixed operations
        mixed_operations_results = concurrency_benchmarks.benchmark_concurrent_mixed_operations(10, 15)
        all_results['mixed_operations'] = mixed_operations_results
        
        # Memory benchmarks
        print("\n" + "=" * 40)
        print("MEMORY BENCHMARKS")
        print("=" * 40)
        
        memory_benchmarks = MemoryBenchmarks(database)
        memory_results = memory_benchmarks.benchmark_memory_usage([100, 500, 1000, 2000])
        all_results['memory_usage'] = memory_results
        
        # Generate summary report
        print("\n" + "=" * 80)
        print("PERFORMANCE BENCHMARK SUMMARY")
        print("=" * 80)
        
        # Insertion performance summary
        if 'insertion_performance' in all_results:
            print("\nINSERTION PERFORMANCE:")
            for count, results in all_results['insertion_performance'].items():
                print(f"  {count:4d} items: {results['insertion_rate']:6.1f} items/sec, "
                      f"{results['avg_insertion_time']:5.2f}ms avg")
        
        # Query performance summary
        if 'query_performance' in all_results:
            print("\nQUERY PERFORMANCE:")
            for query_type, results in all_results['query_performance'].items():
                print(f"  {query_type:20s}: {results['avg_time_ms']:6.2f}ms avg, "
                      f"{results['queries_per_second']:6.1f} queries/sec")
        
        # Concurrency summary
        if 'concurrent_insertions' in all_results:
            print("\nCONCURRENT INSERTION PERFORMANCE:")
            for thread_count, results in all_results['concurrent_insertions'].items():
                print(f"  {thread_count:2d} threads: {results['operations_per_second']:6.1f} ops/sec, "
                      f"{results['success_rate']:5.1%} success rate")
        
        # Memory usage summary
        if 'memory_usage' in all_results:
            print("\nMEMORY USAGE:")
            for count, results in all_results['memory_usage'].items():
                print(f"  {count:4d} items: {results['memory_increase_mb']:6.1f}MB total, "
                      f"{results['memory_per_item_kb']:5.1f}KB per item")
        
        # Save detailed results to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"performance_benchmark_results_{timestamp}.json"
        
        with open(results_file, 'w') as f:
            json.dump(all_results, f, indent=2, default=str)
        
        print(f"\nDetailed results saved to: {results_file}")
        print("\n🎉 PERFORMANCE BENCHMARKS COMPLETED!")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ PERFORMANCE BENCHMARKS FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        database.close()


if __name__ == "__main__":
    sys.exit(run_performance_benchmarks())