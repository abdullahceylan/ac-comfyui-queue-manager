"""
Tests for the Flask API routes.
"""

import json
import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone

from api_routes import QueueManagerAPI
from models import QueueItem, QueueState, QueueStatus
from queue_service import QueueService, QueueServiceError


class TestQueueManagerAPI:
    """Test cases for the QueueManagerAPI class."""

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

    def test_api_initialization(self, mock_queue_service):
        """Test API initialization."""
        api = QueueManagerAPI(queue_service=mock_queue_service)
        
        assert api.queue_service == mock_queue_service
        assert api.app is not None
        assert api.app.config['JSON_SORT_KEYS'] is False
        assert api.app.config['JSONIFY_PRETTYPRINT_REGULAR'] is True

    def test_api_initialization_without_service(self):
        """Test API initialization without providing a queue service."""
        with patch('api_routes.QueueService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            api = QueueManagerAPI()
            
            assert api.queue_service == mock_service
            mock_service_class.assert_called_once()

    def test_health_check_healthy(self, client, mock_queue_service):
        """Test health check endpoint when service is healthy."""
        mock_queue_service.get_queue_state.return_value = QueueState.RUNNING
        
        response = client.get('/health')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert data['queue_state'] == 'running'
        assert data['version'] == '1.0.0'
        assert 'timestamp' in data

    def test_health_check_unhealthy(self, client, mock_queue_service):
        """Test health check endpoint when service is unhealthy."""
        mock_queue_service.get_queue_state.side_effect = QueueServiceError("Database error")
        
        response = client.get('/health')
        
        assert response.status_code == 503
        data = json.loads(response.data)
        assert data['status'] == 'unhealthy'
        assert 'error' in data
        assert 'timestamp' in data

    def test_serve_index_success(self, client):
        """Test serving index.html successfully."""
        with patch('api_routes.send_from_directory') as mock_send:
            mock_send.return_value = "<html>Test</html>"
            
            response = client.get('/')
            
            assert response.status_code == 200
            mock_send.assert_called_once()

    def test_serve_index_alternative_route(self, client):
        """Test serving index.html via /index.html route."""
        with patch('api_routes.send_from_directory') as mock_send:
            mock_send.return_value = "<html>Test</html>"
            
            response = client.get('/index.html')
            
            assert response.status_code == 200
            mock_send.assert_called_once()

    def test_serve_index_error(self, client):
        """Test error handling when serving index.html fails."""
        with patch('api_routes.send_from_directory') as mock_send:
            mock_send.side_effect = FileNotFoundError("File not found")
            
            response = client.get('/')
            
            assert response.status_code == 500
            data = json.loads(response.data)
            assert data['error'] == 'Failed to serve index page'

    def test_error_handler_queue_service_error(self, client, mock_queue_service):
        """Test error handler for QueueServiceError."""
        mock_queue_service.get_queue_state.side_effect = QueueServiceError("Test error")
        
        response = client.get('/health')
        
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['error'] == 'Queue service error'
        assert data['message'] == 'Test error'
        assert 'timestamp' in data

    def test_error_handler_bad_request(self, client):
        """Test error handler for BadRequest."""
        # This will be tested more thoroughly when we add endpoints that validate input
        response = client.post('/nonexistent', data="invalid json", content_type='application/json')
        
        assert response.status_code == 404  # Not found takes precedence

    def test_error_handler_not_found(self, client):
        """Test error handler for NotFound."""
        response = client.get('/nonexistent')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['error'] == 'Not found'
        assert data['message'] == 'The requested resource was not found'
        assert 'timestamp' in data

    def test_validate_json_request_valid(self, api):
        """Test JSON request validation with valid data."""
        with api.app.test_request_context('/test', json={'key': 'value'}):
            data = api._validate_json_request()
            assert data == {'key': 'value'}

    def test_validate_json_request_not_json(self, api):
        """Test JSON request validation with non-JSON request."""
        with api.app.test_request_context('/test', data='not json'):
            with pytest.raises(Exception):  # BadRequest
                api._validate_json_request()

    def test_validate_json_request_invalid_json(self, api):
        """Test JSON request validation with invalid JSON."""
        with api.app.test_request_context('/test', data='{"invalid": json}', content_type='application/json'):
            with pytest.raises(Exception):  # BadRequest
                api._validate_json_request()

    def test_parse_queue_filter_empty(self, api):
        """Test parsing empty filter parameters."""
        filter_criteria = api._parse_queue_filter({})
        
        assert filter_criteria.status is None
        assert filter_criteria.workflow_name is None
        assert filter_criteria.search_term is None
        assert filter_criteria.date_range is None

    def test_parse_queue_filter_status_single(self, api):
        """Test parsing single status filter."""
        filter_criteria = api._parse_queue_filter({'status': 'pending'})
        
        assert filter_criteria.status == [QueueStatus.PENDING]

    def test_parse_queue_filter_status_multiple(self, api):
        """Test parsing multiple status filters."""
        filter_criteria = api._parse_queue_filter({'status': ['pending', 'running']})
        
        assert filter_criteria.status == [QueueStatus.PENDING, QueueStatus.RUNNING]

    def test_parse_queue_filter_status_invalid(self, api):
        """Test parsing invalid status filter."""
        with pytest.raises(Exception):  # BadRequest
            api._parse_queue_filter({'status': 'invalid_status'})

    def test_parse_queue_filter_workflow_name(self, api):
        """Test parsing workflow name filter."""
        filter_criteria = api._parse_queue_filter({'workflow_name': 'test_workflow'})
        
        assert filter_criteria.workflow_name == 'test_workflow'

    def test_parse_queue_filter_search(self, api):
        """Test parsing search term filter."""
        filter_criteria = api._parse_queue_filter({'search': 'test search'})
        
        assert filter_criteria.search_term == 'test search'

    def test_parse_queue_filter_date_range(self, api):
        """Test parsing date range filter."""
        date_from = '2023-01-01T00:00:00'
        date_to = '2023-12-31T23:59:59'
        
        filter_criteria = api._parse_queue_filter({
            'date_from': date_from,
            'date_to': date_to
        })
        
        assert filter_criteria.date_range is not None
        assert filter_criteria.date_range[0] == datetime.fromisoformat(date_from)
        assert filter_criteria.date_range[1] == datetime.fromisoformat(date_to)

    def test_parse_queue_filter_date_range_invalid(self, api):
        """Test parsing invalid date range filter."""
        with pytest.raises(Exception):  # BadRequest
            api._parse_queue_filter({'date_from': 'invalid_date'})

    def test_get_app(self, api):
        """Test getting the Flask app instance."""
        app = api.get_app()
        assert app == api.app

    @patch('api_routes.logger')
    def test_logging_on_initialization(self, mock_logger, mock_queue_service):
        """Test that initialization logs are created."""
        QueueManagerAPI(queue_service=mock_queue_service)
        mock_logger.info.assert_called_with("Queue Manager API initialized")

    @patch('api_routes.logger')
    def test_logging_on_health_check_failure(self, mock_logger, client, mock_queue_service):
        """Test that health check failures are logged."""
        error_msg = "Database connection failed"
        mock_queue_service.get_queue_state.side_effect = Exception(error_msg)
        
        client.get('/health')
        
        mock_logger.error.assert_called()

    def test_flask_config(self, api):
        """Test Flask configuration settings."""
        assert api.app.config['JSON_SORT_KEYS'] is False
        assert api.app.config['JSONIFY_PRETTYPRINT_REGULAR'] is True
        assert api.app.static_folder == 'web'
        assert api.app.static_url_path == '/static'


class TestQueueManagerAPIIntegration:
    """Integration tests for the QueueManagerAPI."""

    @pytest.fixture
    def real_api(self):
        """Create a real API instance with mocked dependencies."""
        with patch('api_routes.QueueService') as mock_service_class:
            mock_service = Mock()
            mock_service.get_queue_state.return_value = QueueState.RUNNING
            mock_service_class.return_value = mock_service
            
            api = QueueManagerAPI()
            return api, mock_service

    def test_full_health_check_flow(self, real_api):
        """Test the complete health check flow."""
        api, mock_service = real_api
        client = api.app.test_client()
        
        response = client.get('/health')
        
        assert response.status_code == 200
        mock_service.get_queue_state.assert_called_once()

    def test_static_file_serving_setup(self, real_api):
        """Test that static file serving is properly configured."""
        api, _ = real_api
        
        # Check that static folder is configured
        assert api.app.static_folder == 'web'
        assert api.app.static_url_path == '/static'
        
        # Check that routes are registered
        rules = [rule.rule for rule in api.app.url_map.iter_rules()]
        assert '/' in rules
        assert '/index.html' in rules
        assert '/health' in rules