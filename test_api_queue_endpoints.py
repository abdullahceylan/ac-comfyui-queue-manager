"""
Tests for queue management API endpoints.
"""

import json
import pytest
from unittest.mock import Mock
from datetime import datetime, timezone

from api_routes import QueueManagerAPI
from models import QueueItem, QueueState, QueueStatus
from queue_service import QueueService, QueueServiceError


class TestQueueManagementEndpoints:
    """Test cases for queue management API endpoints."""

    @pytest.fixture
    def mock_queue_service(self):
        """Create a mock queue service for testing."""
        service = Mock(spec=QueueService)
        service.get_queue_state.return_value = QueueState.RUNNING
        return service

    @pytest.fixture
    def api(self, mock_queue_service):
        """Create a QueueManagerAPI instance for testing."""
        return QueueManagerAPI(queue_service=mock_queue_service)

    @pytest.fixture
    def client(self, api):
        """Create a test client for the Flask app."""
        api.app.config['TESTING'] = True
        return api.app.test_client()

    @pytest.fixture
    def sample_queue_item(self):
        """Create a sample queue item for testing."""
        return QueueItem(
            id="test-item-1",
            workflow_name="Test Workflow",
            workflow_data={"nodes": {"1": {"class_type": "TestNode"}}},
            status=QueueStatus.PENDING
        )

    def test_get_queue_items_all(self, client, mock_queue_service, sample_queue_item):
        """Test getting all queue items."""
        mock_queue_service.get_queue_items.return_value = [sample_queue_item]
        
        response = client.get('/api/queue/items')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['count'] == 1
        assert len(data['items']) == 1
        assert data['items'][0]['id'] == 'test-item-1'
        assert 'timestamp' in data
        
        mock_queue_service.get_queue_items.assert_called_once_with(None)

    def test_get_queue_items_with_status_filter(self, client, mock_queue_service, sample_queue_item):
        """Test getting queue items with status filter."""
        mock_queue_service.get_queue_items.return_value = [sample_queue_item]
        
        response = client.get('/api/queue/items?status=pending')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['count'] == 1
        
        mock_queue_service.get_queue_items.assert_called_once_with(QueueStatus.PENDING)

    def test_get_queue_items_invalid_status(self, client, mock_queue_service):
        """Test getting queue items with invalid status filter."""
        response = client.get('/api/queue/items?status=invalid_status')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error'] == 'Bad request'

    def test_add_queue_item_success(self, client, mock_queue_service, sample_queue_item):
        """Test adding a new queue item successfully."""
        mock_queue_service.add_workflow.return_value = "test-item-1"
        mock_queue_service.get_queue_item.return_value = sample_queue_item
        
        request_data = {
            'workflow_name': 'Test Workflow',
            'workflow_data': {'nodes': {'1': {'class_type': 'TestNode'}}}
        }
        
        response = client.post('/api/queue/items', 
                             data=json.dumps(request_data),
                             content_type='application/json')
        
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['item']['id'] == 'test-item-1'
        assert data['message'] == 'Workflow added to queue successfully'
        assert 'timestamp' in data
        
        mock_queue_service.add_workflow.assert_called_once_with(
            request_data['workflow_data'], 
            request_data['workflow_name']
        )

    def test_add_queue_item_missing_workflow_data(self, client, mock_queue_service):
        """Test adding a queue item without workflow data."""
        request_data = {'workflow_name': 'Test Workflow'}
        
        response = client.post('/api/queue/items',
                             data=json.dumps(request_data),
                             content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error'] == 'Bad request'
        assert 'workflow_data' in data['message']

    def test_add_queue_item_invalid_json(self, client, mock_queue_service):
        """Test adding a queue item with invalid JSON."""
        response = client.post('/api/queue/items',
                             data='invalid json',
                             content_type='application/json')
        
        assert response.status_code == 400

    def test_get_queue_item_success(self, client, mock_queue_service, sample_queue_item):
        """Test getting a specific queue item successfully."""
        mock_queue_service.get_queue_item.return_value = sample_queue_item
        
        response = client.get('/api/queue/items/test-item-1')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['item']['id'] == 'test-item-1'
        assert 'timestamp' in data
        
        mock_queue_service.get_queue_item.assert_called_once_with('test-item-1')

    def test_get_queue_item_not_found(self, client, mock_queue_service):
        """Test getting a non-existent queue item."""
        mock_queue_service.get_queue_item.return_value = None
        
        response = client.get('/api/queue/items/nonexistent')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['error'] == 'Not found'

    def test_update_queue_item_status(self, client, mock_queue_service, sample_queue_item):
        """Test updating a queue item's status."""
        mock_queue_service.update_item_status.return_value = True
        updated_item = QueueItem(
            id="test-item-1",
            workflow_name="Test Workflow",
            workflow_data={"nodes": {"1": {"class_type": "TestNode"}}},
            status=QueueStatus.RUNNING
        )
        mock_queue_service.get_queue_item.return_value = updated_item
        
        request_data = {
            'status': 'running'
        }
        
        response = client.put('/api/queue/items/test-item-1',
                            data=json.dumps(request_data),
                            content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['item']['status'] == 'running'
        assert data['message'] == 'Queue item updated successfully'
        
        mock_queue_service.update_item_status.assert_called_once_with(
            'test-item-1', QueueStatus.RUNNING, None, None
        )

    def test_update_queue_item_with_error(self, client, mock_queue_service, sample_queue_item):
        """Test updating a queue item with error message."""
        mock_queue_service.update_item_status.return_value = True
        failed_item = QueueItem(
            id="test-item-1",
            workflow_name="Test Workflow",
            workflow_data={"nodes": {"1": {"class_type": "TestNode"}}},
            status=QueueStatus.FAILED,
            error_message="Test error"
        )
        mock_queue_service.get_queue_item.return_value = failed_item
        
        request_data = {
            'status': 'failed',
            'error_message': 'Test error'
        }
        
        response = client.put('/api/queue/items/test-item-1',
                            data=json.dumps(request_data),
                            content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['item']['status'] == 'failed'
        assert data['item']['error_message'] == 'Test error'

    def test_update_queue_item_invalid_status(self, client, mock_queue_service):
        """Test updating a queue item with invalid status."""
        request_data = {
            'status': 'invalid_status'
        }
        
        response = client.put('/api/queue/items/test-item-1',
                            data=json.dumps(request_data),
                            content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error'] == 'Bad request'

    def test_delete_queue_item_success(self, client, mock_queue_service, sample_queue_item):
        """Test deleting a queue item successfully."""
        mock_queue_service.get_queue_item.return_value = sample_queue_item
        mock_queue_service.delete_items.return_value = True
        
        response = client.delete('/api/queue/items/test-item-1')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'deleted successfully' in data['message']
        assert 'timestamp' in data
        
        mock_queue_service.delete_items.assert_called_once_with(['test-item-1'])

    def test_delete_queue_item_not_found(self, client, mock_queue_service):
        """Test deleting a non-existent queue item."""
        mock_queue_service.get_queue_item.return_value = None
        
        response = client.delete('/api/queue/items/nonexistent')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['error'] == 'Not found'

    def test_bulk_delete_items_success(self, client, mock_queue_service):
        """Test bulk deleting queue items successfully."""
        mock_queue_service.delete_items.return_value = True
        
        request_data = {
            'item_ids': ['item-1', 'item-2', 'item-3']
        }
        
        response = client.delete('/api/queue/items/bulk',
                               data=json.dumps(request_data),
                               content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['deleted_count'] == 3
        assert 'Successfully deleted' in data['message']
        
        mock_queue_service.delete_items.assert_called_once_with(['item-1', 'item-2', 'item-3'])

    def test_bulk_delete_items_empty_list(self, client, mock_queue_service):
        """Test bulk deleting with empty item list."""
        request_data = {
            'item_ids': []
        }
        
        response = client.delete('/api/queue/items/bulk',
                               data=json.dumps(request_data),
                               content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error'] == 'Bad request'
        assert 'cannot be empty' in data['message']

    def test_bulk_delete_items_missing_field(self, client, mock_queue_service):
        """Test bulk deleting without item_ids field."""
        request_data = {}
        
        response = client.delete('/api/queue/items/bulk',
                               data=json.dumps(request_data),
                               content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error'] == 'Bad request'
        assert 'item_ids' in data['message']

    def test_filter_queue_items_success(self, client, mock_queue_service, sample_queue_item):
        """Test filtering queue items successfully."""
        mock_queue_service.filter_items.return_value = [sample_queue_item]
        
        request_data = {
            'status': ['pending'],
            'workflow_name': 'Test'
        }
        
        response = client.post('/api/queue/items/filter',
                             data=json.dumps(request_data),
                             content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['count'] == 1
        assert len(data['items']) == 1
        assert 'filter' in data
        assert 'timestamp' in data

    def test_search_queue_items_success(self, client, mock_queue_service, sample_queue_item):
        """Test searching queue items successfully."""
        mock_queue_service.search_items.return_value = [sample_queue_item]
        
        response = client.get('/api/queue/search?q=test')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['count'] == 1
        assert data['query'] == 'test'
        assert len(data['items']) == 1
        assert 'timestamp' in data
        
        mock_queue_service.search_items.assert_called_once_with('test')

    def test_search_queue_items_missing_query(self, client, mock_queue_service):
        """Test searching queue items without query parameter."""
        response = client.get('/api/queue/search')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error'] == 'Bad request'
        assert 'query parameter' in data['message']

    def test_search_queue_items_empty_query(self, client, mock_queue_service):
        """Test searching queue items with empty query."""
        response = client.get('/api/queue/search?q=')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error'] == 'Bad request'

    def test_queue_service_error_handling(self, client, mock_queue_service):
        """Test handling of QueueServiceError."""
        mock_queue_service.get_queue_items.side_effect = QueueServiceError("Database error")
        
        response = client.get('/api/queue/items')
        
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['error'] == 'Queue service error'
        assert data['message'] == 'Database error'