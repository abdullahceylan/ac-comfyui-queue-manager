#!/usr/bin/env python3
"""
Simple test script to verify the queue management API endpoints work.
"""

import sys
import os
import json
from unittest.mock import Mock

# Add current directory to path to avoid import issues
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api_routes import QueueManagerAPI
from models import QueueItem, QueueState, QueueStatus
from queue_service import QueueService, QueueServiceError


def create_sample_item():
    """Create a sample queue item for testing."""
    return QueueItem(
        id="test-item-1",
        workflow_name="Test Workflow",
        workflow_data={"nodes": {"1": {"class_type": "TestNode"}}},
        status=QueueStatus.PENDING
    )


def test_get_queue_items():
    """Test GET /api/queue/items endpoint."""
    print("Testing GET /api/queue/items...")
    
    # Create mock service
    mock_service = Mock(spec=QueueService)
    mock_service.get_queue_state.return_value = QueueState.RUNNING
    mock_service.get_queue_items.return_value = [create_sample_item()]
    
    # Create API and client
    api = QueueManagerAPI(queue_service=mock_service)
    client = api.app.test_client()
    
    # Test endpoint
    response = client.get('/api/queue/items')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['count'] == 1
    assert len(data['items']) == 1
    assert data['items'][0]['id'] == 'test-item-1'
    assert 'timestamp' in data
    
    print("✓ GET /api/queue/items test passed")


def test_get_queue_items_with_filter():
    """Test GET /api/queue/items with status filter."""
    print("Testing GET /api/queue/items with status filter...")
    
    # Create mock service
    mock_service = Mock(spec=QueueService)
    mock_service.get_queue_state.return_value = QueueState.RUNNING
    mock_service.get_queue_items.return_value = [create_sample_item()]
    
    # Create API and client
    api = QueueManagerAPI(queue_service=mock_service)
    client = api.app.test_client()
    
    # Test endpoint with status filter
    response = client.get('/api/queue/items?status=pending')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['count'] == 1
    
    # Verify the service was called with the correct status
    mock_service.get_queue_items.assert_called_with(QueueStatus.PENDING)
    
    print("✓ GET /api/queue/items with status filter test passed")


def test_add_queue_item():
    """Test POST /api/queue/items endpoint."""
    print("Testing POST /api/queue/items...")
    
    # Create mock service
    mock_service = Mock(spec=QueueService)
    mock_service.get_queue_state.return_value = QueueState.RUNNING
    mock_service.add_workflow.return_value = "test-item-1"
    mock_service.get_queue_item.return_value = create_sample_item()
    
    # Create API and client
    api = QueueManagerAPI(queue_service=mock_service)
    client = api.app.test_client()
    
    # Test data
    request_data = {
        'workflow_name': 'Test Workflow',
        'workflow_data': {'nodes': {'1': {'class_type': 'TestNode'}}}
    }
    
    # Test endpoint
    response = client.post('/api/queue/items',
                         data=json.dumps(request_data),
                         content_type='application/json')
    
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['item']['id'] == 'test-item-1'
    assert data['message'] == 'Workflow added to queue successfully'
    assert 'timestamp' in data
    
    # Verify service calls
    mock_service.add_workflow.assert_called_once_with(
        request_data['workflow_data'],
        request_data['workflow_name']
    )
    
    print("✓ POST /api/queue/items test passed")


def test_get_single_queue_item():
    """Test GET /api/queue/items/<id> endpoint."""
    print("Testing GET /api/queue/items/<id>...")
    
    # Create mock service
    mock_service = Mock(spec=QueueService)
    mock_service.get_queue_state.return_value = QueueState.RUNNING
    mock_service.get_queue_item.return_value = create_sample_item()
    
    # Create API and client
    api = QueueManagerAPI(queue_service=mock_service)
    client = api.app.test_client()
    
    # Test endpoint
    response = client.get('/api/queue/items/test-item-1')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['item']['id'] == 'test-item-1'
    assert 'timestamp' in data
    
    mock_service.get_queue_item.assert_called_once_with('test-item-1')
    
    print("✓ GET /api/queue/items/<id> test passed")


def test_update_queue_item():
    """Test PUT /api/queue/items/<id> endpoint."""
    print("Testing PUT /api/queue/items/<id>...")
    
    # Create mock service
    mock_service = Mock(spec=QueueService)
    mock_service.get_queue_state.return_value = QueueState.RUNNING
    mock_service.update_item_status.return_value = True
    
    # Create updated item
    updated_item = create_sample_item()
    updated_item.status = QueueStatus.RUNNING
    mock_service.get_queue_item.return_value = updated_item
    
    # Create API and client
    api = QueueManagerAPI(queue_service=mock_service)
    client = api.app.test_client()
    
    # Test data
    request_data = {
        'status': 'running'
    }
    
    # Test endpoint
    response = client.put('/api/queue/items/test-item-1',
                        data=json.dumps(request_data),
                        content_type='application/json')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['item']['status'] == 'running'
    assert data['message'] == 'Queue item updated successfully'
    
    mock_service.update_item_status.assert_called_once_with(
        'test-item-1', QueueStatus.RUNNING, None, None
    )
    
    print("✓ PUT /api/queue/items/<id> test passed")


def test_delete_queue_item():
    """Test DELETE /api/queue/items/<id> endpoint."""
    print("Testing DELETE /api/queue/items/<id>...")
    
    # Create mock service
    mock_service = Mock(spec=QueueService)
    mock_service.get_queue_state.return_value = QueueState.RUNNING
    mock_service.get_queue_item.return_value = create_sample_item()
    mock_service.delete_items.return_value = True
    
    # Create API and client
    api = QueueManagerAPI(queue_service=mock_service)
    client = api.app.test_client()
    
    # Test endpoint
    response = client.delete('/api/queue/items/test-item-1')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'deleted successfully' in data['message']
    assert 'timestamp' in data
    
    mock_service.delete_items.assert_called_once_with(['test-item-1'])
    
    print("✓ DELETE /api/queue/items/<id> test passed")


def test_bulk_delete_items():
    """Test DELETE /api/queue/items/bulk endpoint."""
    print("Testing DELETE /api/queue/items/bulk...")
    
    # Create mock service
    mock_service = Mock(spec=QueueService)
    mock_service.get_queue_state.return_value = QueueState.RUNNING
    mock_service.delete_items.return_value = True
    
    # Create API and client
    api = QueueManagerAPI(queue_service=mock_service)
    client = api.app.test_client()
    
    # Test data
    request_data = {
        'item_ids': ['item-1', 'item-2', 'item-3']
    }
    
    # Test endpoint
    response = client.delete('/api/queue/items/bulk',
                           data=json.dumps(request_data),
                           content_type='application/json')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['deleted_count'] == 3
    assert 'Successfully deleted' in data['message']
    
    mock_service.delete_items.assert_called_once_with(['item-1', 'item-2', 'item-3'])
    
    print("✓ DELETE /api/queue/items/bulk test passed")


def test_filter_queue_items():
    """Test POST /api/queue/items/filter endpoint."""
    print("Testing POST /api/queue/items/filter...")
    
    # Create mock service
    mock_service = Mock(spec=QueueService)
    mock_service.get_queue_state.return_value = QueueState.RUNNING
    mock_service.filter_items.return_value = [create_sample_item()]
    
    # Create API and client
    api = QueueManagerAPI(queue_service=mock_service)
    client = api.app.test_client()
    
    # Test data
    request_data = {
        'status': ['pending'],
        'workflow_name': 'Test'
    }
    
    # Test endpoint
    response = client.post('/api/queue/items/filter',
                         data=json.dumps(request_data),
                         content_type='application/json')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['count'] == 1
    assert len(data['items']) == 1
    assert 'filter' in data
    assert 'timestamp' in data
    
    print("✓ POST /api/queue/items/filter test passed")


def test_search_queue_items():
    """Test GET /api/queue/search endpoint."""
    print("Testing GET /api/queue/search...")
    
    # Create mock service
    mock_service = Mock(spec=QueueService)
    mock_service.get_queue_state.return_value = QueueState.RUNNING
    mock_service.search_items.return_value = [create_sample_item()]
    
    # Create API and client
    api = QueueManagerAPI(queue_service=mock_service)
    client = api.app.test_client()
    
    # Test endpoint
    response = client.get('/api/queue/search?q=test')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['count'] == 1
    assert data['query'] == 'test'
    assert len(data['items']) == 1
    assert 'timestamp' in data
    
    mock_service.search_items.assert_called_once_with('test')
    
    print("✓ GET /api/queue/search test passed")


def test_error_handling():
    """Test error handling in endpoints."""
    print("Testing error handling...")
    
    # Create mock service that raises errors
    mock_service = Mock(spec=QueueService)
    mock_service.get_queue_state.return_value = QueueState.RUNNING
    mock_service.get_queue_items.side_effect = QueueServiceError("Database error")
    
    # Create API and client
    api = QueueManagerAPI(queue_service=mock_service)
    client = api.app.test_client()
    
    # Test endpoint with error
    response = client.get('/api/queue/items')
    
    assert response.status_code == 500
    data = json.loads(response.data)
    assert data['error'] == 'Queue service error'
    assert data['message'] == 'Database error'
    
    print("✓ Error handling test passed")


def main():
    """Run all tests."""
    print("Running Queue Management API endpoint tests...")
    print("=" * 60)
    
    try:
        test_get_queue_items()
        test_get_queue_items_with_filter()
        test_add_queue_item()
        test_get_single_queue_item()
        test_update_queue_item()
        test_delete_queue_item()
        test_bulk_delete_items()
        test_filter_queue_items()
        test_search_queue_items()
        test_error_handling()
        
        print("=" * 60)
        print("✓ All queue management API endpoint tests passed!")
        return 0
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())