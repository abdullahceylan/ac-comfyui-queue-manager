#!/usr/bin/env python3
"""
Comprehensive test script to verify the complete API layer works correctly.
"""

import sys
import os
import json
from unittest.mock import Mock

# Add current directory to path to avoid import issues
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api_routes import QueueManagerAPI
from models import QueueItem, QueueState, QueueStatus, QueueConfig
from queue_service import QueueService


def test_complete_api_integration():
    """Test the complete API integration with all endpoints."""
    print("Testing complete API integration...")
    
    # Create mock service
    mock_service = Mock(spec=QueueService)
    mock_service.get_queue_state.return_value = QueueState.RUNNING
    
    # Create sample items
    sample_items = [
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
        )
    ]
    
    mock_service.get_queue_items.return_value = sample_items
    mock_service.get_config.return_value = QueueConfig()
    mock_service.add_workflow.return_value = "new-item-id"
    mock_service.get_queue_item.return_value = sample_items[0]
    mock_service.update_item_status.return_value = True
    mock_service.delete_items.return_value = True
    mock_service.archive_items.return_value = True
    mock_service.restore_items.return_value = True
    mock_service.pause_queue.return_value = True
    mock_service.resume_queue.return_value = True
    mock_service.filter_items.return_value = [sample_items[0]]
    mock_service.search_items.return_value = [sample_items[0]]
    mock_service.export_queue.return_value = {
        'version': '1.0',
        'items': [item.to_dict() for item in sample_items]
    }
    mock_service.import_queue.return_value = True
    mock_service.update_config.return_value = True
    
    # Create API and client
    api = QueueManagerAPI(queue_service=mock_service)
    client = api.app.test_client()
    
    # Test all endpoints
    endpoints_tested = []
    
    # 1. Health check
    response = client.get('/health')
    assert response.status_code == 200
    endpoints_tested.append("GET /health")
    
    # 2. Get queue items
    response = client.get('/api/queue/items')
    assert response.status_code == 200
    endpoints_tested.append("GET /api/queue/items")
    
    # 3. Add queue item
    response = client.post('/api/queue/items',
                         data=json.dumps({
                             'workflow_name': 'New Workflow',
                             'workflow_data': {'nodes': {'1': {'class_type': 'TestNode'}}}
                         }),
                         content_type='application/json')
    assert response.status_code == 201
    endpoints_tested.append("POST /api/queue/items")
    
    # 4. Get single queue item
    response = client.get('/api/queue/items/item-1')
    assert response.status_code == 200
    endpoints_tested.append("GET /api/queue/items/<id>")
    
    # 5. Update queue item
    response = client.put('/api/queue/items/item-1',
                        data=json.dumps({'status': 'running'}),
                        content_type='application/json')
    assert response.status_code == 200
    endpoints_tested.append("PUT /api/queue/items/<id>")
    
    # 6. Filter queue items
    response = client.post('/api/queue/items/filter',
                         data=json.dumps({'status': ['pending']}),
                         content_type='application/json')
    assert response.status_code == 200
    endpoints_tested.append("POST /api/queue/items/filter")
    
    # 7. Search queue items
    response = client.get('/api/queue/search?q=test')
    assert response.status_code == 200
    endpoints_tested.append("GET /api/queue/search")
    
    # 8. Get queue status
    response = client.get('/api/queue/status')
    assert response.status_code == 200
    endpoints_tested.append("GET /api/queue/status")
    
    # 9. Pause queue
    response = client.post('/api/queue/pause')
    assert response.status_code == 200
    endpoints_tested.append("POST /api/queue/pause")
    
    # 10. Resume queue
    response = client.post('/api/queue/resume')
    assert response.status_code == 200
    endpoints_tested.append("POST /api/queue/resume")
    
    # 11. Archive items
    response = client.post('/api/queue/archive',
                         data=json.dumps({'item_ids': ['item-1']}),
                         content_type='application/json')
    assert response.status_code == 200
    endpoints_tested.append("POST /api/queue/archive")
    
    # 12. Restore items
    response = client.post('/api/queue/restore',
                         data=json.dumps({'item_ids': ['item-1']}),
                         content_type='application/json')
    assert response.status_code == 200
    endpoints_tested.append("POST /api/queue/restore")
    
    # 13. Export queue
    response = client.post('/api/queue/export',
                         data=json.dumps({}),
                         content_type='application/json')
    assert response.status_code == 200
    endpoints_tested.append("POST /api/queue/export")
    
    # 14. Import queue
    response = client.post('/api/queue/import',
                         data=json.dumps({
                             'queue_data': {'version': '1.0', 'items': []},
                             'merge': True
                         }),
                         content_type='application/json')
    assert response.status_code == 200
    endpoints_tested.append("POST /api/queue/import")
    
    # 15. Get queue config
    response = client.get('/api/queue/config')
    assert response.status_code == 200
    endpoints_tested.append("GET /api/queue/config")
    
    # 16. Update queue config
    response = client.put('/api/queue/config',
                        data=json.dumps({'max_concurrent_workflows': 2}),
                        content_type='application/json')
    assert response.status_code == 200
    endpoints_tested.append("PUT /api/queue/config")
    
    # 17. Bulk delete items
    response = client.delete('/api/queue/items/bulk',
                           data=json.dumps({'item_ids': ['item-1', 'item-2']}),
                           content_type='application/json')
    assert response.status_code == 200
    endpoints_tested.append("DELETE /api/queue/items/bulk")
    
    # 18. Delete single item
    response = client.delete('/api/queue/items/item-1')
    assert response.status_code == 200
    endpoints_tested.append("DELETE /api/queue/items/<id>")
    
    print(f"✓ Successfully tested {len(endpoints_tested)} endpoints:")
    for endpoint in endpoints_tested:
        print(f"  - {endpoint}")
    
    return len(endpoints_tested)


def test_api_route_registration():
    """Test that all expected routes are registered."""
    print("Testing API route registration...")
    
    # Create mock service
    mock_service = Mock(spec=QueueService)
    mock_service.get_queue_state.return_value = QueueState.RUNNING
    
    # Create API
    api = QueueManagerAPI(queue_service=mock_service)
    
    # Get all registered routes
    routes = [rule.rule for rule in api.app.url_map.iter_rules()]
    
    # Expected routes
    expected_routes = [
        '/',
        '/index.html',
        '/health',
        '/api/queue/items',
        '/api/queue/items/<item_id>',
        '/api/queue/items/bulk',
        '/api/queue/items/filter',
        '/api/queue/search',
        '/api/queue/status',
        '/api/queue/pause',
        '/api/queue/resume',
        '/api/queue/archive',
        '/api/queue/restore',
        '/api/queue/export',
        '/api/queue/import',
        '/api/queue/config',
        '/static/<path:filename>'  # Flask automatically adds this for static files
    ]
    
    # Check that all expected routes are registered
    missing_routes = []
    for expected_route in expected_routes:
        if expected_route not in routes:
            missing_routes.append(expected_route)
    
    if missing_routes:
        print(f"✗ Missing routes: {missing_routes}")
        return False
    
    print(f"✓ All {len(expected_routes)} expected routes are registered")
    return True


def test_flask_configuration():
    """Test Flask application configuration."""
    print("Testing Flask configuration...")
    
    # Create mock service
    mock_service = Mock(spec=QueueService)
    mock_service.get_queue_state.return_value = QueueState.RUNNING
    
    # Create API
    api = QueueManagerAPI(queue_service=mock_service)
    
    # Check Flask configuration
    assert api.app.config['JSON_SORT_KEYS'] is False
    assert api.app.config['JSONIFY_PRETTYPRINT_REGULAR'] is True
    assert 'web' in str(api.app.static_folder)
    assert api.app.static_url_path == '/static'
    
    print("✓ Flask configuration is correct")
    return True


def main():
    """Run all comprehensive tests."""
    print("Running Comprehensive API Layer Tests...")
    print("=" * 60)
    
    try:
        # Test route registration
        if not test_api_route_registration():
            return 1
        
        # Test Flask configuration
        if not test_flask_configuration():
            return 1
        
        # Test complete API integration
        endpoints_count = test_complete_api_integration()
        
        print("=" * 60)
        print(f"✓ Complete API layer implementation verified!")
        print(f"✓ {endpoints_count} endpoints tested successfully")
        print("✓ All subtasks for task 5 'Create API layer for web interface' completed:")
        print("  - 5.1 Flask/FastAPI web server integration ✓")
        print("  - 5.2 Queue management API endpoints ✓")
        print("  - 5.3 Control API endpoints ✓")
        
        return 0
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())