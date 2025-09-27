#!/usr/bin/env python3
"""
Simple test script to verify the API routes work without pytest import issues.
"""

import sys
import os
import json
from unittest.mock import Mock

# Add current directory to path to avoid import issues
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api_routes import QueueManagerAPI
from models import QueueState, QueueStatus
from queue_service import QueueService


def test_api_initialization():
    """Test API initialization."""
    print("Testing API initialization...")
    
    # Create mock queue service
    mock_service = Mock(spec=QueueService)
    mock_service.get_queue_state.return_value = QueueState.RUNNING
    
    # Initialize API
    api = QueueManagerAPI(queue_service=mock_service)
    
    assert api.queue_service == mock_service
    assert api.app is not None
    assert api.app.config['JSON_SORT_KEYS'] is False
    assert api.app.config['JSONIFY_PRETTYPRINT_REGULAR'] is True
    
    print("✓ API initialization test passed")


def test_health_check():
    """Test health check endpoint."""
    print("Testing health check endpoint...")
    
    # Create mock queue service
    mock_service = Mock(spec=QueueService)
    mock_service.get_queue_state.return_value = QueueState.RUNNING
    
    # Initialize API
    api = QueueManagerAPI(queue_service=mock_service)
    client = api.app.test_client()
    
    # Test health check
    response = client.get('/health')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'healthy'
    assert data['queue_state'] == 'running'
    assert data['version'] == '1.0.0'
    assert 'timestamp' in data
    
    print("✓ Health check test passed")


def test_error_handling():
    """Test error handling."""
    print("Testing error handling...")
    
    # Create mock queue service that raises an error
    mock_service = Mock(spec=QueueService)
    mock_service.get_queue_state.side_effect = Exception("Database error")
    
    # Initialize API
    api = QueueManagerAPI(queue_service=mock_service)
    client = api.app.test_client()
    
    # Test health check with error
    response = client.get('/health')
    
    assert response.status_code == 503
    data = json.loads(response.data)
    assert data['status'] == 'unhealthy'
    assert 'error' in data
    assert 'timestamp' in data
    
    print("✓ Error handling test passed")


def test_not_found():
    """Test 404 error handling."""
    print("Testing 404 error handling...")
    
    # Create mock queue service
    mock_service = Mock(spec=QueueService)
    mock_service.get_queue_state.return_value = QueueState.RUNNING
    
    # Initialize API
    api = QueueManagerAPI(queue_service=mock_service)
    client = api.app.test_client()
    
    # Test non-existent endpoint
    response = client.get('/nonexistent')
    
    assert response.status_code == 404
    data = json.loads(response.data)
    assert data['error'] == 'Not found'
    assert data['message'] == 'The requested resource was not found'
    assert 'timestamp' in data
    
    print("✓ 404 error handling test passed")


def test_flask_configuration():
    """Test Flask configuration."""
    print("Testing Flask configuration...")
    
    # Create mock queue service
    mock_service = Mock(spec=QueueService)
    mock_service.get_queue_state.return_value = QueueState.RUNNING
    
    # Initialize API
    api = QueueManagerAPI(queue_service=mock_service)
    
    # Check Flask configuration
    print(f"Static folder: {api.app.static_folder}")
    print(f"Static URL path: {api.app.static_url_path}")
    assert 'web' in str(api.app.static_folder)  # Check that web is in the path
    assert api.app.static_url_path == '/static'
    
    # Check that routes are registered
    rules = [rule.rule for rule in api.app.url_map.iter_rules()]
    assert '/' in rules
    assert '/index.html' in rules
    assert '/health' in rules
    
    print("✓ Flask configuration test passed")


def main():
    """Run all tests."""
    print("Running API integration tests...")
    print("=" * 50)
    
    try:
        test_api_initialization()
        test_health_check()
        test_error_handling()
        test_not_found()
        test_flask_configuration()
        
        print("=" * 50)
        print("✓ All tests passed! Web server integration is working correctly.")
        return 0
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())