#!/usr/bin/env python3
"""
Simple integration test to verify basic functionality.
"""

import json
import sys
import os
import tempfile

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api_routes import QueueManagerAPI
from database import SQLiteDatabase
from queue_service import QueueService
from test_fixtures import TestDataFactory


def test_simple_integration():
    """Test simple integration workflow."""
    print("Running simple integration test...")
    
    # Create database and service
    database = SQLiteDatabase(":memory:")
    database.initialize()
    queue_service = QueueService(database)
    
    # Create API
    api = QueueManagerAPI(queue_service=queue_service)
    client = api.app.test_client()
    
    # Test workflow data
    from test_fixtures import WorkflowTemplates
    workflow_data = WorkflowTemplates.SIMPLE_IMAGE_WORKFLOW.copy()
    workflow_data["name"] = "Integration Test"
    
    print("1. Adding workflow via API...")
    response = client.post('/api/queue/items',
                         data=json.dumps({
                             'workflow_name': workflow_data['name'],
                             'workflow_data': workflow_data
                         }),
                         content_type='application/json')
    
    assert response.status_code == 201, f"Expected 201, got {response.status_code}"
    response_data = json.loads(response.data)
    item_id = response_data['item']['id']
    print(f"   ✓ Created item: {item_id}")
    
    print("2. Getting workflow via API...")
    response = client.get(f'/api/queue/items/{item_id}')
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    print("   ✓ Retrieved item successfully")
    
    print("3. Updating workflow to completed...")
    response = client.put(f'/api/queue/items/{item_id}',
                        data=json.dumps({'status': 'completed'}),
                        content_type='application/json')
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    print("   ✓ Updated item status")
    
    print("4. Filtering workflows...")
    response = client.post('/api/queue/items/filter',
                         data=json.dumps({'status': ['completed']}),
                         content_type='application/json')
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    filtered_data = json.loads(response.data)
    assert len(filtered_data['items']) == 1, f"Expected 1 item, got {len(filtered_data['items'])}"
    print("   ✓ Filtered items successfully")
    
    print("5. Archiving workflow...")
    response = client.post('/api/queue/archive',
                         data=json.dumps({'item_ids': [item_id]}),
                         content_type='application/json')
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.data.decode()}"
    print("   ✓ Archived item successfully")
    
    print("6. Exporting queue...")
    response = client.post('/api/queue/export',
                         data=json.dumps({}),
                         content_type='application/json')
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    export_data = json.loads(response.data)
    print(f"   Export response: {export_data}")
    # The export might return the data in a different format
    if 'export_data' in export_data:
        actual_export = export_data['export_data']
        assert 'version' in actual_export
        assert 'items' in actual_export
    else:
        assert 'version' in export_data
        assert 'items' in export_data
    print("   ✓ Exported queue successfully")
    
    database.close()
    print("\n✅ Simple integration test PASSED!")
    return True


if __name__ == "__main__":
    try:
        test_simple_integration()
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Simple integration test FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)