#!/usr/bin/env python3
"""
Simple debug test for API functionality.
"""

import json
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api_routes import QueueManagerAPI
from database import SQLiteDatabase
from queue_service import QueueService


def test_api_debug():
    """Debug API functionality."""
    print("Testing API functionality...")
    
    # Create database and service
    database = SQLiteDatabase(":memory:")
    database.initialize()
    queue_service = QueueService(database)
    
    # Create API
    api = QueueManagerAPI(queue_service=queue_service)
    client = api.app.test_client()
    
    # Test workflow data
    workflow_data = {
        "name": "Debug Test Workflow",
        "nodes": [
            {"id": "1", "type": "LoadImage", "inputs": {}},
            {"id": "2", "type": "SaveImage", "inputs": {"images": ["1", 0]}}
        ],
        "links": [["1", 0, "2", 0]]
    }
    
    print("1. Testing POST /api/queue/items...")
    response = client.post('/api/queue/items',
                         data=json.dumps({
                             'workflow_name': workflow_data['name'],
                             'workflow_data': workflow_data
                         }),
                         content_type='application/json')
    
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.data.decode()}")
    
    if response.status_code == 201:
        response_data = json.loads(response.data)
        print(f"   Item created: {response_data.get('item', {}).get('id', 'NO ID')}")
        
        item_id = response_data['item']['id']
        
        print(f"\n2. Testing GET /api/queue/items/{item_id}...")
        response = client.get(f'/api/queue/items/{item_id}')
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.data.decode()}")
        
        if response.status_code == 200:
            item_data = json.loads(response.data)
            print(f"   Item workflow_name: {item_data.get('item', {}).get('workflow_name', 'NO NAME')}")
    
    print("\n3. Testing GET /api/queue/items...")
    response = client.get('/api/queue/items')
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.data.decode()}")
    
    print("\n4. Testing filter...")
    response = client.post('/api/queue/items/filter',
                         data=json.dumps({'status': ['pending']}),
                         content_type='application/json')
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.data.decode()}")
    
    database.close()


if __name__ == "__main__":
    test_api_debug()