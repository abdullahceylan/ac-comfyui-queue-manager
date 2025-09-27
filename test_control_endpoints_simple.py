#!/usr/bin/env python3
"""
Simple test script to verify the control API endpoints work.
"""

import sys
import os
import json
from unittest.mock import Mock

# Add current directory to path to avoid import issues
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api_routes import QueueManagerAPI
from models import QueueItem, QueueState, QueueStatus, QueueConfig
from queue_service import QueueService, QueueServiceError


def create_sample_items():
    """Create sample queue items for testing."""
    return [
        QueueItem(
            id="item-1",
            workflow_name="Test Workflow 1",
            workflow_data={"nodes": {"1": {"class_type": "TestNode"}}},
            status=QueueStatus.PENDING
        ),
        QueueItem(
            id="item-2",
            workflow_name="Test Workflow 2",
            workflow_data={"nodes": {"1": {"class_type": "TestNode"}}},
            status=QueueStatus.RUNNING
        ),
        QueueItem(
            id="item-3",
            workflow_name="Test Workflow 3",
            workflow_data={"nodes": {"1": {"class_type": "TestNode"}}},
            status=QueueStatus.COMPLETED
        )
    ]


def test_get_queue_status():
    """Test GET /api/queue/status endpoint."""
    print("Testing GET /api/queue/status...")
    
    # Create mock service
    mock_service = Mock(spec=QueueService)
    mock_service.get_queue_state.return_value = QueueState.RUNNING
    mock_service.get_queue_items.return_value = create_sample_items()
    mock_service.get_config.return_value = QueueConfig()
    
    # Create API and client
    api = QueueManagerAPI(queue_service=mock_service)
    client = api.app.test_client()
    
    # Test endpoint
    response = client.get('/api/queue/status')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['queue_state'] == 'running'
    assert 'statistics' in data
    assert data['statistics']['total'] == 3
    assert data['statistics']['pending'] == 1
    assert data['statistics']['running'] == 1
    assert data['statistics']['completed'] == 1
    assert 'config' in data
    assert 'timestamp' in data
    
    print("✓ GET /api/queue/status test passed")


def test_pause_queue():
    """Test POST /api/queue/pause endpoint."""
    print("Testing POST /api/queue/pause...")
    
    # Create mock service
    mock_service = Mock(spec=QueueService)
    mock_service.get_queue_state.return_value = QueueState.RUNNING
    mock_service.pause_queue.return_value = True
    
    # Create API and client
    api = QueueManagerAPI(queue_service=mock_service)
    client = api.app.test_client()
    
    # Test endpoint
    response = client.post('/api/queue/pause')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['message'] == 'Queue processing paused successfully'
    assert data['queue_state'] == 'paused'
    assert 'timestamp' in data
    
    mock_service.pause_queue.assert_called_once()
    
    print("✓ POST /api/queue/pause test passed")


def test_resume_queue():
    """Test POST /api/queue/resume endpoint."""
    print("Testing POST /api/queue/resume...")
    
    # Create mock service
    mock_service = Mock(spec=QueueService)
    mock_service.get_queue_state.return_value = QueueState.PAUSED
    mock_service.resume_queue.return_value = True
    
    # Create API and client
    api = QueueManagerAPI(queue_service=mock_service)
    client = api.app.test_client()
    
    # Test endpoint
    response = client.post('/api/queue/resume')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['message'] == 'Queue processing resumed successfully'
    assert data['queue_state'] == 'running'
    assert 'timestamp' in data
    
    mock_service.resume_queue.assert_called_once()
    
    print("✓ POST /api/queue/resume test passed")


def test_archive_items():
    """Test POST /api/queue/archive endpoint."""
    print("Testing POST /api/queue/archive...")
    
    # Create mock service
    mock_service = Mock(spec=QueueService)
    mock_service.get_queue_state.return_value = QueueState.RUNNING
    mock_service.archive_items.return_value = True
    
    # Create API and client
    api = QueueManagerAPI(queue_service=mock_service)
    client = api.app.test_client()
    
    # Test data
    request_data = {
        'item_ids': ['item-1', 'item-2']
    }
    
    # Test endpoint
    response = client.post('/api/queue/archive',
                         data=json.dumps(request_data),
                         content_type='application/json')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['archived_count'] == 2
    assert 'Successfully archived' in data['message']
    assert 'timestamp' in data
    
    mock_service.archive_items.assert_called_once_with(['item-1', 'item-2'])
    
    print("✓ POST /api/queue/archive test passed")


def test_restore_items():
    """Test POST /api/queue/restore endpoint."""
    print("Testing POST /api/queue/restore...")
    
    # Create mock service
    mock_service = Mock(spec=QueueService)
    mock_service.get_queue_state.return_value = QueueState.RUNNING
    mock_service.restore_items.return_value = True
    
    # Create API and client
    api = QueueManagerAPI(queue_service=mock_service)
    client = api.app.test_client()
    
    # Test data
    request_data = {
        'item_ids': ['item-1', 'item-2']
    }
    
    # Test endpoint
    response = client.post('/api/queue/restore',
                         data=json.dumps(request_data),
                         content_type='application/json')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['restored_count'] == 2
    assert 'Successfully restored' in data['message']
    assert 'timestamp' in data
    
    mock_service.restore_items.assert_called_once_with(['item-1', 'item-2'])
    
    print("✓ POST /api/queue/restore test passed")


def test_export_queue():
    """Test POST /api/queue/export endpoint."""
    print("Testing POST /api/queue/export...")
    
    # Create mock service
    mock_service = Mock(spec=QueueService)
    mock_service.get_queue_state.return_value = QueueState.RUNNING
    mock_service.export_queue.return_value = {
        'version': '1.0',
        'items': [item.to_dict() for item in create_sample_items()],
        'config': QueueConfig().to_dict()
    }
    
    # Create API and client
    api = QueueManagerAPI(queue_service=mock_service)
    client = api.app.test_client()
    
    # Test data (export all items)
    request_data = {}
    
    # Test endpoint
    response = client.post('/api/queue/export',
                         data=json.dumps(request_data),
                         content_type='application/json')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['message'] == 'Queue exported successfully'
    assert 'export_data' in data
    assert data['export_data']['version'] == '1.0'
    assert len(data['export_data']['items']) == 3
    assert 'timestamp' in data
    
    mock_service.export_queue.assert_called_once_with(None)
    
    print("✓ POST /api/queue/export test passed")


def test_export_queue_specific_items():
    """Test POST /api/queue/export endpoint with specific items."""
    print("Testing POST /api/queue/export with specific items...")
    
    # Create mock service
    mock_service = Mock(spec=QueueService)
    mock_service.get_queue_state.return_value = QueueState.RUNNING
    mock_service.export_queue.return_value = {
        'version': '1.0',
        'items': [create_sample_items()[0].to_dict()],
        'config': QueueConfig().to_dict()
    }
    
    # Create API and client
    api = QueueManagerAPI(queue_service=mock_service)
    client = api.app.test_client()
    
    # Test data (export specific items)
    request_data = {
        'item_ids': ['item-1']
    }
    
    # Test endpoint
    response = client.post('/api/queue/export',
                         data=json.dumps(request_data),
                         content_type='application/json')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['message'] == 'Queue exported successfully'
    assert len(data['export_data']['items']) == 1
    
    mock_service.export_queue.assert_called_once_with(['item-1'])
    
    print("✓ POST /api/queue/export with specific items test passed")


def test_import_queue():
    """Test POST /api/queue/import endpoint."""
    print("Testing POST /api/queue/import...")
    
    # Create mock service
    mock_service = Mock(spec=QueueService)
    mock_service.get_queue_state.return_value = QueueState.RUNNING
    mock_service.import_queue.return_value = True
    
    # Create API and client
    api = QueueManagerAPI(queue_service=mock_service)
    client = api.app.test_client()
    
    # Test data
    queue_data = {
        'version': '1.0',
        'items': [item.to_dict() for item in create_sample_items()],
        'config': QueueConfig().to_dict()
    }
    request_data = {
        'queue_data': queue_data,
        'merge': True
    }
    
    # Test endpoint
    response = client.post('/api/queue/import',
                         data=json.dumps(request_data),
                         content_type='application/json')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['message'] == 'Queue imported successfully'
    assert data['merge_mode'] is True
    assert 'timestamp' in data
    
    mock_service.import_queue.assert_called_once_with(queue_data, True)
    
    print("✓ POST /api/queue/import test passed")


def test_get_queue_config():
    """Test GET /api/queue/config endpoint."""
    print("Testing GET /api/queue/config...")
    
    # Create mock service
    mock_service = Mock(spec=QueueService)
    mock_service.get_queue_state.return_value = QueueState.RUNNING
    mock_service.get_config.return_value = QueueConfig()
    
    # Create API and client
    api = QueueManagerAPI(queue_service=mock_service)
    client = api.app.test_client()
    
    # Test endpoint
    response = client.get('/api/queue/config')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'config' in data
    assert data['config']['queue_state'] == 'running'
    assert data['config']['max_concurrent_workflows'] == 1
    assert 'timestamp' in data
    
    mock_service.get_config.assert_called_once()
    
    print("✓ GET /api/queue/config test passed")


def test_update_queue_config():
    """Test PUT /api/queue/config endpoint."""
    print("Testing PUT /api/queue/config...")
    
    # Create mock service
    mock_service = Mock(spec=QueueService)
    mock_service.get_queue_state.return_value = QueueState.RUNNING
    mock_service.get_config.return_value = QueueConfig()
    mock_service.update_config.return_value = True
    
    # Create API and client
    api = QueueManagerAPI(queue_service=mock_service)
    client = api.app.test_client()
    
    # Test data
    request_data = {
        'max_concurrent_workflows': 2,
        'auto_archive_completed': True,
        'auto_archive_days': 7
    }
    
    # Test endpoint
    response = client.put('/api/queue/config',
                        data=json.dumps(request_data),
                        content_type='application/json')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['message'] == 'Queue configuration updated successfully'
    assert 'config' in data
    assert 'timestamp' in data
    
    mock_service.update_config.assert_called_once()
    
    print("✓ PUT /api/queue/config test passed")


def test_error_handling():
    """Test error handling in control endpoints."""
    print("Testing error handling...")
    
    # Create mock service that raises errors
    mock_service = Mock(spec=QueueService)
    mock_service.get_queue_state.return_value = QueueState.RUNNING
    mock_service.pause_queue.side_effect = QueueServiceError("Failed to pause")
    
    # Create API and client
    api = QueueManagerAPI(queue_service=mock_service)
    client = api.app.test_client()
    
    # Test endpoint with error
    response = client.post('/api/queue/pause')
    
    assert response.status_code == 500
    data = json.loads(response.data)
    assert data['error'] == 'Queue service error'
    assert data['message'] == 'Failed to pause'
    
    print("✓ Error handling test passed")


def test_validation_errors():
    """Test validation errors in control endpoints."""
    print("Testing validation errors...")
    
    # Create mock service
    mock_service = Mock(spec=QueueService)
    mock_service.get_queue_state.return_value = QueueState.RUNNING
    
    # Create API and client
    api = QueueManagerAPI(queue_service=mock_service)
    client = api.app.test_client()
    
    # Test archive endpoint with missing item_ids
    response = client.post('/api/queue/archive',
                         data=json.dumps({}),
                         content_type='application/json')
    
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['error'] == 'Bad request'
    assert 'item_ids' in data['message']
    
    # Test archive endpoint with empty item_ids
    response = client.post('/api/queue/archive',
                         data=json.dumps({'item_ids': []}),
                         content_type='application/json')
    
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['error'] == 'Bad request'
    assert 'cannot be empty' in data['message']
    
    print("✓ Validation errors test passed")


def main():
    """Run all tests."""
    print("Running Control API endpoint tests...")
    print("=" * 50)
    
    try:
        test_get_queue_status()
        test_pause_queue()
        test_resume_queue()
        test_archive_items()
        test_restore_items()
        test_export_queue()
        test_export_queue_specific_items()
        test_import_queue()
        test_get_queue_config()
        test_update_queue_config()
        test_error_handling()
        test_validation_errors()
        
        print("=" * 50)
        print("✓ All control API endpoint tests passed!")
        return 0
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())