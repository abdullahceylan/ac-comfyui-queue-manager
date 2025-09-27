#!/usr/bin/env python3
"""
Comprehensive test runner for ComfyUI Queue Manager integration tests.
Orchestrates all test suites and generates detailed reports.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class TestResult:
    """Container for test results."""
    
    def __init__(self, name: str, success: bool, duration: float, details: Optional[Dict] = None, error: Optional[str] = None):
        self.name = name
        self.success = success
        self.duration = duration
        self.details = details or {}
        self.error = error
        self.timestamp = datetime.now()


class TestSuite:
    """Base class for test suites."""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.results: List[TestResult] = []
    
    def run(self) -> bool:
        """Run the test suite. Should be implemented by subclasses."""
        raise NotImplementedError
    
    def add_result(self, result: TestResult):
        """Add a test result."""
        self.results.append(result)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics."""
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.success)
        total_duration = sum(r.duration for r in self.results)
        
        return {
            'name': self.name,
            'description': self.description,
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': total_tests - passed_tests,
            'success_rate': passed_tests / total_tests if total_tests > 0 else 0,
            'total_duration': total_duration,
            'results': [
                {
                    'name': r.name,
                    'success': r.success,
                    'duration': r.duration,
                    'error': r.error,
                    'timestamp': r.timestamp.isoformat()
                }
                for r in self.results
            ]
        }


class UnitTestSuite(TestSuite):
    """Unit test suite runner."""
    
    def __init__(self):
        super().__init__("Unit Tests", "Individual component unit tests")
    
    def run(self) -> bool:
        """Run all unit tests."""
        print(f"Running {self.name}...")
        
        # List of unit test files
        unit_test_files = [
            "test_database.py",
            "test_queue_service.py",
            "test_api_routes.py",
            "test_archive_service.py",
            "test_filter_service.py",
            "test_import_export_service.py",
            "test_serialization_service.py",
            "test_config_manager.py",
            "test_error_handling.py",
            "test_logging_monitoring.py"
        ]
        
        all_passed = True
        
        for test_file in unit_test_files:
            if not os.path.exists(test_file):
                print(f"  Skipping {test_file} (not found)")
                continue
            
            print(f"  Running {test_file}...")
            start_time = time.time()
            
            try:
                # Run the test file
                result = subprocess.run([sys.executable, test_file], 
                                      capture_output=True, text=True, timeout=60)
                
                duration = time.time() - start_time
                success = result.returncode == 0
                
                if success:
                    print(f"    ✓ Passed ({duration:.2f}s)")
                else:
                    print(f"    ✗ Failed ({duration:.2f}s)")
                    print(f"      Error: {result.stderr}")
                    all_passed = False
                
                self.add_result(TestResult(
                    name=test_file,
                    success=success,
                    duration=duration,
                    details={'stdout': result.stdout, 'stderr': result.stderr},
                    error=result.stderr if not success else None
                ))
                
            except subprocess.TimeoutExpired:
                duration = time.time() - start_time
                print(f"    ✗ Timeout ({duration:.2f}s)")
                all_passed = False
                
                self.add_result(TestResult(
                    name=test_file,
                    success=False,
                    duration=duration,
                    error="Test timeout"
                ))
                
            except Exception as e:
                duration = time.time() - start_time
                print(f"    ✗ Error ({duration:.2f}s): {e}")
                all_passed = False
                
                self.add_result(TestResult(
                    name=test_file,
                    success=False,
                    duration=duration,
                    error=str(e)
                ))
        
        return all_passed


class IntegrationTestSuite(TestSuite):
    """Integration test suite runner."""
    
    def __init__(self):
        super().__init__("Integration Tests", "End-to-end integration tests")
    
    def run(self) -> bool:
        """Run integration tests."""
        print(f"Running {self.name}...")
        
        start_time = time.time()
        
        try:
            # Import and run integration test suite
            from test_integration_suite import run_integration_test_suite
            
            result = run_integration_test_suite()
            duration = time.time() - start_time
            success = result == 0
            
            if success:
                print(f"  ✓ Integration tests passed ({duration:.2f}s)")
            else:
                print(f"  ✗ Integration tests failed ({duration:.2f}s)")
            
            self.add_result(TestResult(
                name="integration_test_suite",
                success=success,
                duration=duration,
                details={'return_code': result}
            ))
            
            return success
            
        except Exception as e:
            duration = time.time() - start_time
            print(f"  ✗ Integration tests error ({duration:.2f}s): {e}")
            
            self.add_result(TestResult(
                name="integration_test_suite",
                success=False,
                duration=duration,
                error=str(e)
            ))
            
            return False


class PerformanceTestSuite(TestSuite):
    """Performance test suite runner."""
    
    def __init__(self):
        super().__init__("Performance Tests", "Performance and benchmarking tests")
    
    def run(self) -> bool:
        """Run performance tests."""
        print(f"Running {self.name}...")
        
        start_time = time.time()
        
        try:
            # Import and run performance benchmarks
            from test_performance_benchmark import run_performance_benchmarks
            
            result = run_performance_benchmarks()
            duration = time.time() - start_time
            success = result == 0
            
            if success:
                print(f"  ✓ Performance tests passed ({duration:.2f}s)")
            else:
                print(f"  ✗ Performance tests failed ({duration:.2f}s)")
            
            self.add_result(TestResult(
                name="performance_benchmarks",
                success=success,
                duration=duration,
                details={'return_code': result}
            ))
            
            return success
            
        except Exception as e:
            duration = time.time() - start_time
            print(f"  ✗ Performance tests error ({duration:.2f}s): {e}")
            
            self.add_result(TestResult(
                name="performance_benchmarks",
                success=False,
                duration=duration,
                error=str(e)
            ))
            
            return False


class APITestSuite(TestSuite):
    """API test suite runner."""
    
    def __init__(self):
        super().__init__("API Tests", "API endpoint and integration tests")
    
    def run(self) -> bool:
        """Run API tests."""
        print(f"Running {self.name}...")
        
        # List of API test files
        api_test_files = [
            "test_complete_api.py",
            "test_api_queue_endpoints.py",
            "test_control_endpoints_simple.py",
            "test_queue_endpoints_simple.py"
        ]
        
        all_passed = True
        
        for test_file in api_test_files:
            if not os.path.exists(test_file):
                print(f"  Skipping {test_file} (not found)")
                continue
            
            print(f"  Running {test_file}...")
            start_time = time.time()
            
            try:
                result = subprocess.run([sys.executable, test_file], 
                                      capture_output=True, text=True, timeout=120)
                
                duration = time.time() - start_time
                success = result.returncode == 0
                
                if success:
                    print(f"    ✓ Passed ({duration:.2f}s)")
                else:
                    print(f"    ✗ Failed ({duration:.2f}s)")
                    print(f"      Error: {result.stderr}")
                    all_passed = False
                
                self.add_result(TestResult(
                    name=test_file,
                    success=success,
                    duration=duration,
                    details={'stdout': result.stdout, 'stderr': result.stderr},
                    error=result.stderr if not success else None
                ))
                
            except subprocess.TimeoutExpired:
                duration = time.time() - start_time
                print(f"    ✗ Timeout ({duration:.2f}s)")
                all_passed = False
                
                self.add_result(TestResult(
                    name=test_file,
                    success=False,
                    duration=duration,
                    error="Test timeout"
                ))
                
            except Exception as e:
                duration = time.time() - start_time
                print(f"    ✗ Error ({duration:.2f}s): {e}")
                all_passed = False
                
                self.add_result(TestResult(
                    name=test_file,
                    success=False,
                    duration=duration,
                    error=str(e)
                ))
        
        return all_passed


class WorkflowTestSuite(TestSuite):
    """Workflow execution test suite runner."""
    
    def __init__(self):
        super().__init__("Workflow Tests", "Workflow execution and monitoring tests")
    
    def run(self) -> bool:
        """Run workflow tests."""
        print(f"Running {self.name}...")
        
        # List of workflow test files
        workflow_test_files = [
            "test_workflow_execution.py",
            "test_node_registration.py",
            "test_menu_integration.py",
            "test_menu_functionality.py"
        ]
        
        all_passed = True
        
        for test_file in workflow_test_files:
            if not os.path.exists(test_file):
                print(f"  Skipping {test_file} (not found)")
                continue
            
            print(f"  Running {test_file}...")
            start_time = time.time()
            
            try:
                result = subprocess.run([sys.executable, test_file], 
                                      capture_output=True, text=True, timeout=180)
                
                duration = time.time() - start_time
                success = result.returncode == 0
                
                if success:
                    print(f"    ✓ Passed ({duration:.2f}s)")
                else:
                    print(f"    ✗ Failed ({duration:.2f}s)")
                    print(f"      Error: {result.stderr}")
                    all_passed = False
                
                self.add_result(TestResult(
                    name=test_file,
                    success=success,
                    duration=duration,
                    details={'stdout': result.stdout, 'stderr': result.stderr},
                    error=result.stderr if not success else None
                ))
                
            except subprocess.TimeoutExpired:
                duration = time.time() - start_time
                print(f"    ✗ Timeout ({duration:.2f}s)")
                all_passed = False
                
                self.add_result(TestResult(
                    name=test_file,
                    success=False,
                    duration=duration,
                    error="Test timeout"
                ))
                
            except Exception as e:
                duration = time.time() - start_time
                print(f"    ✗ Error ({duration:.2f}s): {e}")
                all_passed = False
                
                self.add_result(TestResult(
                    name=test_file,
                    success=False,
                    duration=duration,
                    error=str(e)
                ))
        
        return all_passed


class TestRunner:
    """Main test runner that orchestrates all test suites."""
    
    def __init__(self):
        self.test_suites: List[TestSuite] = []
        self.start_time = None
        self.end_time = None
    
    def add_test_suite(self, test_suite: TestSuite):
        """Add a test suite to run."""
        self.test_suites.append(test_suite)
    
    def run_all(self, suite_names: Optional[List[str]] = None) -> bool:
        """Run all test suites or specified ones."""
        print("=" * 80)
        print("COMFYUI QUEUE MANAGER - COMPREHENSIVE TEST SUITE")
        print("=" * 80)
        
        self.start_time = time.time()
        
        # Filter test suites if specific ones requested
        suites_to_run = self.test_suites
        if suite_names:
            suites_to_run = [suite for suite in self.test_suites if suite.name.lower().replace(' ', '_') in suite_names]
        
        if not suites_to_run:
            print("No test suites to run!")
            return False
        
        all_passed = True
        
        for suite in suites_to_run:
            print(f"\n{'='*60}")
            print(f"{suite.name.upper()}: {suite.description}")
            print('='*60)
            
            suite_passed = suite.run()
            all_passed = all_passed and suite_passed
            
            # Print suite summary
            summary = suite.get_summary()
            print(f"\n{suite.name} Summary:")
            print(f"  Total tests: {summary['total_tests']}")
            print(f"  Passed: {summary['passed_tests']}")
            print(f"  Failed: {summary['failed_tests']}")
            print(f"  Success rate: {summary['success_rate']:.1%}")
            print(f"  Duration: {summary['total_duration']:.2f}s")
        
        self.end_time = time.time()
        
        # Generate final report
        self._generate_final_report(all_passed)
        
        return all_passed
    
    def _generate_final_report(self, all_passed: bool):
        """Generate final test report."""
        total_duration = self.end_time - self.start_time
        
        print("\n" + "=" * 80)
        print("FINAL TEST REPORT")
        print("=" * 80)
        
        # Overall statistics
        total_tests = sum(len(suite.results) for suite in self.test_suites)
        total_passed = sum(sum(1 for r in suite.results if r.success) for suite in self.test_suites)
        overall_success_rate = total_passed / total_tests if total_tests > 0 else 0
        
        print(f"\nOverall Results:")
        print(f"  Total test suites: {len(self.test_suites)}")
        print(f"  Total tests: {total_tests}")
        print(f"  Passed: {total_passed}")
        print(f"  Failed: {total_tests - total_passed}")
        print(f"  Success rate: {overall_success_rate:.1%}")
        print(f"  Total duration: {total_duration:.2f}s")
        
        # Suite breakdown
        print(f"\nSuite Breakdown:")
        for suite in self.test_suites:
            summary = suite.get_summary()
            status = "✓" if summary['failed_tests'] == 0 else "✗"
            print(f"  {status} {suite.name}: {summary['passed_tests']}/{summary['total_tests']} "
                  f"({summary['success_rate']:.1%}) in {summary['total_duration']:.2f}s")
        
        # Failed tests details
        failed_tests = []
        for suite in self.test_suites:
            for result in suite.results:
                if not result.success:
                    failed_tests.append((suite.name, result))
        
        if failed_tests:
            print(f"\nFailed Tests ({len(failed_tests)}):")
            for suite_name, result in failed_tests:
                print(f"  ✗ {suite_name}/{result.name}: {result.error or 'Unknown error'}")
        
        # Save detailed report
        self._save_detailed_report()
        
        # Final status
        if all_passed:
            print(f"\n🎉 ALL TESTS PASSED!")
            print(f"   {total_tests} tests completed successfully in {total_duration:.2f}s")
        else:
            print(f"\n❌ SOME TESTS FAILED!")
            print(f"   {total_passed}/{total_tests} tests passed ({overall_success_rate:.1%})")
    
    def _save_detailed_report(self):
        """Save detailed test report to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"test_report_{timestamp}.json"
        
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'total_duration': self.end_time - self.start_time,
            'test_suites': [suite.get_summary() for suite in self.test_suites]
        }
        
        try:
            with open(report_file, 'w') as f:
                json.dump(report_data, f, indent=2)
            print(f"\nDetailed report saved to: {report_file}")
        except Exception as e:
            print(f"\nFailed to save detailed report: {e}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run ComfyUI Queue Manager integration tests")
    parser.add_argument('--suites', nargs='*', 
                       choices=['unit_tests', 'integration_tests', 'performance_tests', 'api_tests', 'workflow_tests'],
                       help='Specific test suites to run (default: all)')
    parser.add_argument('--quick', action='store_true',
                       help='Run quick tests only (skip performance tests)')
    parser.add_argument('--performance-only', action='store_true',
                       help='Run performance tests only')
    
    args = parser.parse_args()
    
    # Create test runner
    runner = TestRunner()
    
    # Add test suites based on arguments
    if args.performance_only:
        runner.add_test_suite(PerformanceTestSuite())
    elif args.quick:
        runner.add_test_suite(UnitTestSuite())
        runner.add_test_suite(APITestSuite())
        runner.add_test_suite(IntegrationTestSuite())
    else:
        # Add all test suites
        runner.add_test_suite(UnitTestSuite())
        runner.add_test_suite(APITestSuite())
        runner.add_test_suite(WorkflowTestSuite())
        runner.add_test_suite(IntegrationTestSuite())
        if not args.quick:
            runner.add_test_suite(PerformanceTestSuite())
    
    # Run tests
    success = runner.run_all(args.suites)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())