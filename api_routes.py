"""
Flask API routes for the ComfyUI Queue Manager web interface.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from flask import Flask, jsonify, request, send_from_directory
from werkzeug.exceptions import BadRequest, NotFound

from error_handler import ErrorHandler, create_error_response, with_api_error_handling
from exceptions import APIError, NotFoundError, QueueManagerError, ValidationError
from logging_config import get_logger
from models import QueueFilter, QueueStatus
from performance_monitor import get_performance_monitor, time_function
from queue_service import QueueService

logger = get_logger("api_routes")


class QueueManagerAPI:
    """Flask API for queue management operations."""

    def __init__(self, queue_service: QueueService | None = None):
        """Initialize the API with a queue service.
        
        Args:
            queue_service: Queue service instance. If None, creates a new one.
        """
        self.app = Flask(__name__, static_folder='web', static_url_path='/static')
        self.queue_service = queue_service or QueueService()
        
        # Configure Flask
        self.app.config['JSON_SORT_KEYS'] = False
        self.app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True
        
        # Register routes
        self._register_routes()
        self._register_error_handlers()
        
        logger.info("Queue Manager API initialized")

    def _register_routes(self) -> None:
        """Register all API routes."""
        # Health check endpoints
        self.app.route('/health', methods=['GET'])(self.health_check)
        self.app.route('/health/detailed', methods=['GET'])(self.detailed_health_check)
        self.app.route('/health/metrics', methods=['GET'])(self.health_metrics)
        
        # Static files
        self.app.route('/', methods=['GET'])(self.serve_index)
        self.app.route('/index.html', methods=['GET'])(self.serve_index)
        
        # Queue management endpoints
        self.app.route('/api/queue/items', methods=['GET'])(self.get_queue_items)
        self.app.route('/api/queue/items', methods=['POST'])(self.add_queue_item)
        self.app.route('/api/queue/items/<item_id>', methods=['GET'])(self.get_queue_item)
        self.app.route('/api/queue/items/<item_id>', methods=['PUT'])(self.update_queue_item)
        self.app.route('/api/queue/items/<item_id>', methods=['DELETE'])(self.delete_queue_item)
        self.app.route('/api/queue/items/bulk', methods=['DELETE'])(self.bulk_delete_items)
        self.app.route('/api/queue/items/filter', methods=['POST'])(self.filter_queue_items)
        self.app.route('/api/queue/search', methods=['GET'])(self.search_queue_items)
        
        # Control endpoints
        self.app.route('/api/queue/status', methods=['GET'])(self.get_queue_status)
        self.app.route('/api/queue/pause', methods=['POST'])(self.pause_queue)
        self.app.route('/api/queue/resume', methods=['POST'])(self.resume_queue)
        self.app.route('/api/queue/archive', methods=['POST'])(self.archive_items)
        self.app.route('/api/queue/restore', methods=['POST'])(self.restore_items)
        self.app.route('/api/queue/export', methods=['POST'])(self.export_queue)
        self.app.route('/api/queue/import', methods=['POST'])(self.import_queue)
        self.app.route('/api/queue/config', methods=['GET'])(self.get_queue_config)
        self.app.route('/api/queue/config', methods=['PUT'])(self.update_queue_config)

    def _register_error_handlers(self) -> None:
        """Register error handlers for the Flask app."""
        
        @self.app.errorhandler(QueueManagerError)
        def handle_queue_manager_error(error: QueueManagerError) -> tuple[dict[str, Any], int]:
            """Handle queue manager errors."""
            ErrorHandler.log_error(error, context={"handler": "flask_error_handler"})
            
            # Determine HTTP status code
            if isinstance(error, APIError):
                status_code = error.details.get('status_code', 500)
            elif isinstance(error, ValidationError):
                status_code = 400
            elif isinstance(error, NotFoundError):
                status_code = 404
            else:
                status_code = 500
            
            return create_error_response(error), status_code

        @self.app.errorhandler(BadRequest)
        def handle_bad_request(error: BadRequest) -> tuple[dict[str, Any], int]:
            """Handle bad request errors."""
            logger.warning(f"Bad request: {error}")
            validation_error = ValidationError(
                str(error.description) or "Bad request",
                details={"werkzeug_error": str(error)}
            )
            return create_error_response(validation_error), 400

        @self.app.errorhandler(NotFound)
        def handle_not_found(error: NotFound) -> tuple[dict[str, Any], int]:
            """Handle not found errors."""
            not_found_error = NotFoundError(
                "The requested resource was not found",
                details={"werkzeug_error": str(error)}
            )
            return create_error_response(not_found_error), 404

        @self.app.errorhandler(Exception)
        def handle_generic_error(error: Exception) -> tuple[dict[str, Any], int]:
            """Handle generic errors."""
            logger.error(f"Unexpected error: {error}", exc_info=True)
            
            # Convert to structured error
            api_error = APIError(
                "An unexpected error occurred",
                status_code=500,
                details={"original_error": str(error)},
                cause=error
            )
            
            return create_error_response(api_error, include_traceback=False), 500

    @with_api_error_handling(endpoint="/health", method="GET")
    @time_function("api.health_check")
    def health_check(self) -> dict[str, Any]:
        """Health check endpoint."""
        # Test queue service connectivity
        queue_state = self.queue_service.get_queue_state()
        
        return {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'queue_state': queue_state.value,
            'version': '1.0.0'
        }
    
    @with_api_error_handling(endpoint="/health/detailed", method="GET")
    @time_function("api.detailed_health_check")
    def detailed_health_check(self) -> dict[str, Any]:
        """Detailed health check endpoint with comprehensive diagnostics."""
        from health_check import get_health_check_manager
        import asyncio
        
        # Get health check manager and run all checks
        health_manager = get_health_check_manager()
        
        # Run health checks in a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            results = loop.run_until_complete(health_manager.run_all_checks())
            overall_health = health_manager.get_overall_health()
        finally:
            loop.close()
        
        return overall_health
    
    @with_api_error_handling(endpoint="/health/metrics", method="GET")
    @time_function("api.health_metrics")
    def health_metrics(self) -> dict[str, Any]:
        """Health metrics endpoint with performance data."""
        perf_monitor = get_performance_monitor()
        
        # Get metrics summary for the last hour
        since = datetime.utcnow() - timedelta(hours=1)
        metrics_summary = perf_monitor.get_metrics_summary(since)
        
        # Get operation statistics
        operation_stats = perf_monitor.get_operation_stats()
        
        # Get health status
        health_status = perf_monitor.get_health_status()
        
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'health_status': health_status,
            'metrics_summary': metrics_summary,
            'operation_stats': operation_stats
        }

    def serve_index(self) -> str:
        """Serve the main index.html file."""
        try:
            return send_from_directory(self.app.static_folder, 'index.html')
        except Exception as e:
            logger.error(f"Failed to serve index.html: {e}")
            return jsonify({
                'error': 'Failed to serve index page',
                'message': str(e)
            }), 500

    def _validate_json_request(self) -> dict[str, Any]:
        """Validate and parse JSON request data."""
        if not request.is_json:
            raise ValidationError("Request must be JSON", field="content_type")
        
        try:
            data = request.get_json()
            if data is None:
                raise ValidationError("Invalid JSON data", field="request_body")
            return data
        except Exception as e:
            raise ValidationError(f"Failed to parse JSON: {e}", field="request_body", cause=e)

    def _parse_queue_filter(self, params: dict[str, Any]) -> QueueFilter:
        """Parse queue filter parameters from request."""
        filter_criteria = QueueFilter()
        
        # Parse status filter
        if 'status' in params:
            status_values = params['status']
            if isinstance(status_values, str):
                status_values = [status_values]
            
            try:
                filter_criteria.status = [QueueStatus(status) for status in status_values]
            except ValueError as e:
                raise ValidationError(f"Invalid status value: {e}", field="status", value=status_values)
        
        # Parse workflow name filter
        if 'workflow_name' in params:
            workflow_name = params['workflow_name']
            if not isinstance(workflow_name, str):
                raise ValidationError("Workflow name must be a string", field="workflow_name", value=workflow_name)
            filter_criteria.workflow_name = workflow_name
        
        # Parse search term
        if 'search' in params:
            search_term = params['search']
            if not isinstance(search_term, str):
                raise ValidationError("Search term must be a string", field="search", value=search_term)
            filter_criteria.search_term = search_term
        
        # Parse date range
        if 'date_from' in params or 'date_to' in params:
            try:
                date_from = None
                date_to = None
                
                if 'date_from' in params:
                    date_from = datetime.fromisoformat(params['date_from'])
                
                if 'date_to' in params:
                    date_to = datetime.fromisoformat(params['date_to'])
                
                if date_from and date_to:
                    if date_from > date_to:
                        raise ValidationError("date_from must be before date_to", field="date_range")
                    filter_criteria.date_range = (date_from, date_to)
                    
            except ValueError as e:
                raise ValidationError(f"Invalid date format: {e}", field="date_range", cause=e)
        
        return filter_criteria

    def run(self, host: str = '127.0.0.1', port: int = 5000, debug: bool = False) -> None:
        """Run the Flask development server.
        
        Args:
            host: Host to bind to
            port: Port to bind to
            debug: Enable debug mode
        """
        logger.info(f"Starting Queue Manager API server on {host}:{port}")
        self.app.run(host=host, port=port, debug=debug)

    def get_queue_items(self) -> dict[str, Any]:
        """Get all queue items with optional status filtering."""
        try:
            # Parse query parameters
            status_param = request.args.get('status')
            status = None
            
            if status_param:
                try:
                    status = QueueStatus(status_param)
                except ValueError:
                    raise BadRequest(f"Invalid status: {status_param}")
            
            # Get items from service
            items = self.queue_service.get_queue_items(status)
            
            return {
                'items': [item.to_dict() for item in items],
                'count': len(items),
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except QueueServiceError as e:
            logger.error(f"Failed to get queue items: {e}")
            raise

    def add_queue_item(self) -> tuple[dict[str, Any], int]:
        """Add a new workflow to the queue."""
        try:
            data = self._validate_json_request()
            
            # Validate required fields
            if 'workflow_data' not in data:
                raise BadRequest("Missing required field: workflow_data")
            
            workflow_data = data['workflow_data']
            workflow_name = data.get('workflow_name', '')
            
            # Add to queue
            item_id = self.queue_service.add_workflow(workflow_data, workflow_name)
            
            # Get the created item
            item = self.queue_service.get_queue_item(item_id)
            if not item:
                raise QueueServiceError("Failed to retrieve created item")
            
            return {
                'item': item.to_dict(),
                'message': 'Workflow added to queue successfully',
                'timestamp': datetime.utcnow().isoformat()
            }, 201
            
        except QueueServiceError as e:
            logger.error(f"Failed to add queue item: {e}")
            raise

    def get_queue_item(self, item_id: str) -> dict[str, Any]:
        """Get a specific queue item by ID."""
        try:
            if not item_id:
                raise BadRequest("Item ID is required")
            
            item = self.queue_service.get_queue_item(item_id)
            if not item:
                raise NotFound(f"Queue item {item_id} not found")
            
            return {
                'item': item.to_dict(),
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except QueueServiceError as e:
            logger.error(f"Failed to get queue item {item_id}: {e}")
            raise

    def update_queue_item(self, item_id: str) -> dict[str, Any]:
        """Update a queue item's status and related fields."""
        try:
            if not item_id:
                raise BadRequest("Item ID is required")
            
            data = self._validate_json_request()
            
            # Validate status if provided
            status = None
            if 'status' in data:
                try:
                    status = QueueStatus(data['status'])
                except ValueError:
                    raise BadRequest(f"Invalid status: {data['status']}")
            
            error_message = data.get('error_message')
            result_data = data.get('result_data')
            
            # Update the item
            if status:
                success = self.queue_service.update_item_status(
                    item_id, status, error_message, result_data
                )
            else:
                # If no status provided, just check that item exists
                item = self.queue_service.get_queue_item(item_id)
                if not item:
                    raise NotFound(f"Queue item {item_id} not found")
                success = True
            
            if not success:
                raise QueueServiceError("Failed to update queue item")
            
            # Get updated item
            updated_item = self.queue_service.get_queue_item(item_id)
            
            return {
                'item': updated_item.to_dict() if updated_item else None,
                'message': 'Queue item updated successfully',
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except QueueServiceError as e:
            logger.error(f"Failed to update queue item {item_id}: {e}")
            raise

    def delete_queue_item(self, item_id: str) -> dict[str, Any]:
        """Delete a specific queue item."""
        try:
            if not item_id:
                raise BadRequest("Item ID is required")
            
            # Check if item exists
            item = self.queue_service.get_queue_item(item_id)
            if not item:
                raise NotFound(f"Queue item {item_id} not found")
            
            # Delete the item
            success = self.queue_service.delete_items([item_id])
            if not success:
                raise QueueServiceError("Failed to delete queue item")
            
            return {
                'message': f'Queue item {item_id} deleted successfully',
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except QueueServiceError as e:
            logger.error(f"Failed to delete queue item {item_id}: {e}")
            raise

    def bulk_delete_items(self) -> dict[str, Any]:
        """Delete multiple queue items."""
        try:
            data = self._validate_json_request()
            
            if 'item_ids' not in data:
                raise BadRequest("Missing required field: item_ids")
            
            item_ids = data['item_ids']
            if not isinstance(item_ids, list):
                raise BadRequest("item_ids must be a list")
            
            if not item_ids:
                raise BadRequest("item_ids cannot be empty")
            
            # Delete the items
            success = self.queue_service.delete_items(item_ids)
            if not success:
                raise QueueServiceError("Failed to delete some queue items")
            
            return {
                'message': f'Successfully deleted {len(item_ids)} queue items',
                'deleted_count': len(item_ids),
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except QueueServiceError as e:
            logger.error(f"Failed to bulk delete queue items: {e}")
            raise

    def filter_queue_items(self) -> dict[str, Any]:
        """Filter queue items based on criteria."""
        try:
            data = self._validate_json_request()
            
            # Parse filter criteria
            filter_criteria = self._parse_queue_filter(data)
            
            # Apply filter
            items = self.queue_service.filter_items(filter_criteria)
            
            return {
                'items': [item.to_dict() for item in items],
                'count': len(items),
                'filter': filter_criteria.to_dict(),
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except QueueServiceError as e:
            logger.error(f"Failed to filter queue items: {e}")
            raise

    def search_queue_items(self) -> dict[str, Any]:
        """Search queue items using a query string."""
        try:
            query = request.args.get('q', '').strip()
            if not query:
                raise BadRequest("Search query parameter 'q' is required")
            
            # Perform search
            items = self.queue_service.search_items(query)
            
            return {
                'items': [item.to_dict() for item in items],
                'count': len(items),
                'query': query,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except QueueServiceError as e:
            logger.error(f"Failed to search queue items: {e}")
            raise

    def get_queue_status(self) -> dict[str, Any]:
        """Get the current queue processing status."""
        try:
            queue_state = self.queue_service.get_queue_state()
            config = self.queue_service.get_config()
            
            # Get queue statistics
            all_items = self.queue_service.get_queue_items()
            stats = {
                'total': len(all_items),
                'pending': len([item for item in all_items if item.status == QueueStatus.PENDING]),
                'running': len([item for item in all_items if item.status == QueueStatus.RUNNING]),
                'completed': len([item for item in all_items if item.status == QueueStatus.COMPLETED]),
                'failed': len([item for item in all_items if item.status == QueueStatus.FAILED]),
                'archived': len([item for item in all_items if item.status == QueueStatus.ARCHIVED])
            }
            
            return {
                'queue_state': queue_state.value,
                'statistics': stats,
                'config': config.to_dict(),
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except QueueServiceError as e:
            logger.error(f"Failed to get queue status: {e}")
            raise

    def pause_queue(self) -> dict[str, Any]:
        """Pause queue processing."""
        try:
            success = self.queue_service.pause_queue()
            if not success:
                raise QueueServiceError("Failed to pause queue")
            
            return {
                'message': 'Queue processing paused successfully',
                'queue_state': 'paused',
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except QueueServiceError as e:
            logger.error(f"Failed to pause queue: {e}")
            raise

    def resume_queue(self) -> dict[str, Any]:
        """Resume queue processing."""
        try:
            success = self.queue_service.resume_queue()
            if not success:
                raise QueueServiceError("Failed to resume queue")
            
            return {
                'message': 'Queue processing resumed successfully',
                'queue_state': 'running',
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except QueueServiceError as e:
            logger.error(f"Failed to resume queue: {e}")
            raise

    def archive_items(self) -> dict[str, Any]:
        """Archive queue items."""
        try:
            data = self._validate_json_request()
            
            if 'item_ids' not in data:
                raise BadRequest("Missing required field: item_ids")
            
            item_ids = data['item_ids']
            if not isinstance(item_ids, list):
                raise BadRequest("item_ids must be a list")
            
            if not item_ids:
                raise BadRequest("item_ids cannot be empty")
            
            # Archive the items
            success = self.queue_service.archive_items(item_ids)
            if not success:
                raise QueueServiceError("Failed to archive some items")
            
            return {
                'message': f'Successfully archived {len(item_ids)} items',
                'archived_count': len(item_ids),
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except QueueServiceError as e:
            logger.error(f"Failed to archive items: {e}")
            raise

    def restore_items(self) -> dict[str, Any]:
        """Restore archived queue items."""
        try:
            data = self._validate_json_request()
            
            if 'item_ids' not in data:
                raise BadRequest("Missing required field: item_ids")
            
            item_ids = data['item_ids']
            if not isinstance(item_ids, list):
                raise BadRequest("item_ids must be a list")
            
            if not item_ids:
                raise BadRequest("item_ids cannot be empty")
            
            # Restore the items
            success = self.queue_service.restore_items(item_ids)
            if not success:
                raise QueueServiceError("Failed to restore some items")
            
            return {
                'message': f'Successfully restored {len(item_ids)} items',
                'restored_count': len(item_ids),
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except QueueServiceError as e:
            logger.error(f"Failed to restore items: {e}")
            raise

    def export_queue(self) -> dict[str, Any]:
        """Export queue items."""
        try:
            data = self._validate_json_request()
            
            # Get optional item IDs to export
            item_ids = data.get('item_ids')
            if item_ids is not None and not isinstance(item_ids, list):
                raise BadRequest("item_ids must be a list")
            
            # Export the queue
            export_data = self.queue_service.export_queue(item_ids)
            
            return {
                'message': 'Queue exported successfully',
                'export_data': export_data,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except QueueServiceError as e:
            logger.error(f"Failed to export queue: {e}")
            raise

    def import_queue(self) -> dict[str, Any]:
        """Import queue items."""
        try:
            data = self._validate_json_request()
            
            if 'queue_data' not in data:
                raise BadRequest("Missing required field: queue_data")
            
            queue_data = data['queue_data']
            merge = data.get('merge', True)  # Default to merge mode
            
            if not isinstance(merge, bool):
                raise BadRequest("merge must be a boolean")
            
            # Import the queue
            success = self.queue_service.import_queue(queue_data, merge)
            if not success:
                raise QueueServiceError("Failed to import queue data")
            
            return {
                'message': 'Queue imported successfully',
                'merge_mode': merge,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except QueueServiceError as e:
            logger.error(f"Failed to import queue: {e}")
            raise

    def get_queue_config(self) -> dict[str, Any]:
        """Get the current queue configuration."""
        try:
            config = self.queue_service.get_config()
            
            return {
                'config': config.to_dict(),
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except QueueServiceError as e:
            logger.error(f"Failed to get queue config: {e}")
            raise

    def update_queue_config(self) -> dict[str, Any]:
        """Update the queue configuration."""
        try:
            data = self._validate_json_request()
            
            # Get current config and update with provided values
            current_config = self.queue_service.get_config()
            
            # Update config fields if provided
            if 'queue_state' in data:
                try:
                    from models import QueueState
                    current_config.queue_state = QueueState(data['queue_state'])
                except ValueError:
                    raise BadRequest(f"Invalid queue_state: {data['queue_state']}")
            
            if 'max_concurrent_workflows' in data:
                max_concurrent = data['max_concurrent_workflows']
                if not isinstance(max_concurrent, int) or max_concurrent < 1:
                    raise BadRequest("max_concurrent_workflows must be a positive integer")
                current_config.max_concurrent_workflows = max_concurrent
            
            if 'auto_archive_completed' in data:
                if not isinstance(data['auto_archive_completed'], bool):
                    raise BadRequest("auto_archive_completed must be a boolean")
                current_config.auto_archive_completed = data['auto_archive_completed']
            
            if 'auto_archive_days' in data:
                auto_archive_days = data['auto_archive_days']
                if not isinstance(auto_archive_days, int) or auto_archive_days < 1:
                    raise BadRequest("auto_archive_days must be a positive integer")
                current_config.auto_archive_days = auto_archive_days
            
            # Update the configuration
            success = self.queue_service.update_config(current_config)
            if not success:
                raise QueueServiceError("Failed to update queue configuration")
            
            return {
                'message': 'Queue configuration updated successfully',
                'config': current_config.to_dict(),
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except QueueServiceError as e:
            logger.error(f"Failed to update queue config: {e}")
            raise

    def get_app(self) -> Flask:
        """Get the Flask app instance for integration with other servers."""
        return self.app