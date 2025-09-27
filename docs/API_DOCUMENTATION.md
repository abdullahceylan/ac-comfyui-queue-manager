# ComfyUI Queue Manager - API Documentation

## Overview

The ComfyUI Queue Manager provides a comprehensive REST API for programmatic access to queue management functionality. The API follows RESTful conventions and returns JSON responses.

**Base URL**: `http://localhost:5000/api/queue/`

**Content Type**: All requests should use `application/json`

## Authentication

Currently, the API does not require authentication as it runs locally. In future versions, authentication may be added for remote access.

## Response Format

All API responses follow a consistent format:

### Success Response
```json
{
  "status": "success",
  "data": { ... },
  "message": "Operation completed successfully",
  "timestamp": "2025-09-27T16:52:03.302158Z"
}
```

### Error Response
```json
{
  "status": "error",
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request data",
    "details": { ... }
  },
  "timestamp": "2025-09-27T16:52:03.302158Z"
}
```

## Endpoints

### Health Check

#### GET /health
Check API health status.

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2025-09-27T16:52:03.302158Z",
  "queue_state": "running",
  "version": "1.0.0"
}
```

### Queue Items

#### GET /api/queue/items
Get all queue items with optional filtering.

**Query Parameters**:
- `status` (optional): Filter by status (`pending`, `running`, `completed`, `failed`, `archived`)

**Example**:
```bash
curl "http://localhost:5000/api/queue/items?status=pending"
```

**Response**:
```json
{
  "items": [
    {
      "id": "uuid-string",
      "workflow_name": "My Workflow",
      "workflow_data": { ... },
      "status": "pending",
      "created_at": "2025-09-27T16:52:03.302158Z",
      "updated_at": "2025-09-27T16:52:03.302158Z",
      "started_at": null,
      "completed_at": null,
      "error_message": null,
      "result_data": null
    }
  ],
  "count": 1,
  "timestamp": "2025-09-27T16:52:03.302158Z"
}
```

#### POST /api/queue/items
Add a new workflow to the queue.

**Request Body**:
```json
{
  "workflow_name": "My New Workflow",
  "workflow_data": {
    "nodes": [ ... ],
    "links": [ ... ],
    "workflow": { ... }
  }
}
```

**Response**:
```json
{
  "item": {
    "id": "new-uuid-string",
    "workflow_name": "My New Workflow",
    "status": "pending",
    ...
  },
  "message": "Workflow added to queue successfully",
  "timestamp": "2025-09-27T16:52:03.302158Z"
}
```

#### GET /api/queue/items/{item_id}
Get a specific queue item by ID.

**Parameters**:
- `item_id`: UUID of the queue item

**Response**:
```json
{
  "item": {
    "id": "uuid-string",
    "workflow_name": "My Workflow",
    ...
  },
  "timestamp": "2025-09-27T16:52:03.302158Z"
}
```

#### PUT /api/queue/items/{item_id}
Update a queue item's status and related fields.

**Request Body**:
```json
{
  "status": "completed",
  "result_data": {
    "output": "success",
    "execution_time": 45.2
  },
  "error_message": null
}
```

**Response**:
```json
{
  "item": {
    "id": "uuid-string",
    "status": "completed",
    "result_data": { ... },
    ...
  },
  "message": "Queue item updated successfully",
  "timestamp": "2025-09-27T16:52:03.302158Z"
}
```

#### DELETE /api/queue/items/{item_id}
Delete a specific queue item.

**Response**:
```json
{
  "message": "Queue item uuid-string deleted successfully",
  "timestamp": "2025-09-27T16:52:03.302158Z"
}
```

#### DELETE /api/queue/items/bulk
Delete multiple queue items.

**Request Body**:
```json
{
  "item_ids": ["uuid-1", "uuid-2", "uuid-3"]
}
```

**Response**:
```json
{
  "message": "Successfully deleted 3 queue items",
  "deleted_count": 3,
  "timestamp": "2025-09-27T16:52:03.302158Z"
}
```

### Filtering and Search

#### POST /api/queue/items/filter
Filter queue items based on criteria.

**Request Body**:
```json
{
  "status": ["pending", "running"],
  "workflow_name": "My Workflow",
  "date_from": "2025-09-01T00:00:00Z",
  "date_to": "2025-09-30T23:59:59Z",
  "search": "keyword"
}
```

**Response**:
```json
{
  "items": [ ... ],
  "count": 5,
  "filter": {
    "status": ["pending", "running"],
    "workflow_name": "My Workflow",
    "date_range": ["2025-09-01T00:00:00Z", "2025-09-30T23:59:59Z"],
    "search_term": "keyword"
  },
  "timestamp": "2025-09-27T16:52:03.302158Z"
}
```

#### GET /api/queue/search
Search queue items using a query string.

**Query Parameters**:
- `q`: Search query string

**Example**:
```bash
curl "http://localhost:5000/api/queue/search?q=my%20workflow"
```

**Response**:
```json
{
  "items": [ ... ],
  "count": 3,
  "query": "my workflow",
  "timestamp": "2025-09-27T16:52:03.302158Z"
}
```

### Queue Control

#### GET /api/queue/status
Get the current queue processing status.

**Response**:
```json
{
  "queue_state": "running",
  "total_items": 25,
  "pending_items": 5,
  "running_items": 2,
  "completed_items": 15,
  "failed_items": 2,
  "archived_items": 1,
  "timestamp": "2025-09-27T16:52:03.302158Z"
}
```

#### POST /api/queue/pause
Pause queue processing.

**Response**:
```json
{
  "message": "Queue paused successfully",
  "queue_state": "paused",
  "timestamp": "2025-09-27T16:52:03.302158Z"
}
```

#### POST /api/queue/resume
Resume queue processing.

**Response**:
```json
{
  "message": "Queue resumed successfully",
  "queue_state": "running",
  "timestamp": "2025-09-27T16:52:03.302158Z"
}
```

### Archive Operations

#### POST /api/queue/archive
Archive selected queue items.

**Request Body**:
```json
{
  "item_ids": ["uuid-1", "uuid-2"]
}
```

**Response**:
```json
{
  "message": "Successfully archived 2 items",
  "archived_count": 2,
  "timestamp": "2025-09-27T16:52:03.302158Z"
}
```

#### POST /api/queue/restore
Restore archived queue items.

**Request Body**:
```json
{
  "item_ids": ["uuid-1", "uuid-2"]
}
```

**Response**:
```json
{
  "message": "Successfully restored 2 items",
  "restored_count": 2,
  "timestamp": "2025-09-27T16:52:03.302158Z"
}
```

### Import/Export

#### POST /api/queue/export
Export queue data.

**Request Body**:
```json
{
  "item_ids": ["uuid-1", "uuid-2"],  // Optional: specific items
  "include_archived": true,          // Optional: include archived items
  "format": "json"                   // Optional: export format
}
```

**Response**:
```json
{
  "export_data": {
    "version": "1.0",
    "exported_at": "2025-09-27T16:52:03.302158Z",
    "items": [ ... ],
    "config": { ... }
  },
  "message": "Queue exported successfully",
  "timestamp": "2025-09-27T16:52:03.302158Z"
}
```

#### POST /api/queue/import
Import queue data.

**Request Body**:
```json
{
  "queue_data": {
    "version": "1.0",
    "items": [ ... ],
    "config": { ... }
  },
  "merge": true,                     // Optional: merge with existing queue
  "overwrite_duplicates": false      // Optional: overwrite duplicate items
}
```

**Response**:
```json
{
  "message": "Queue imported successfully",
  "imported_count": 5,
  "skipped_count": 2,
  "timestamp": "2025-09-27T16:52:03.302158Z"
}
```

### Configuration

#### GET /api/queue/config
Get queue configuration.

**Response**:
```json
{
  "config": {
    "max_concurrent_workflows": 1,
    "auto_archive_completed": false,
    "auto_archive_days": 30,
    "queue_state": "running"
  },
  "timestamp": "2025-09-27T16:52:03.302158Z"
}
```

#### PUT /api/queue/config
Update queue configuration.

**Request Body**:
```json
{
  "max_concurrent_workflows": 2,
  "auto_archive_completed": true,
  "auto_archive_days": 7
}
```

**Response**:
```json
{
  "config": {
    "max_concurrent_workflows": 2,
    "auto_archive_completed": true,
    "auto_archive_days": 7,
    "queue_state": "running"
  },
  "message": "Configuration updated successfully",
  "timestamp": "2025-09-27T16:52:03.302158Z"
}
```

## Data Models

### QueueItem

```json
{
  "id": "string (UUID)",
  "workflow_name": "string",
  "workflow_data": "object",
  "status": "string (pending|running|completed|failed|archived)",
  "created_at": "string (ISO 8601)",
  "updated_at": "string (ISO 8601)",
  "started_at": "string (ISO 8601) | null",
  "completed_at": "string (ISO 8601) | null",
  "error_message": "string | null",
  "result_data": "object | null"
}
```

### QueueFilter

```json
{
  "status": ["string"],
  "workflow_name": "string",
  "date_range": ["string", "string"],
  "search_term": "string"
}
```

### QueueConfig

```json
{
  "max_concurrent_workflows": "integer",
  "auto_archive_completed": "boolean",
  "auto_archive_days": "integer",
  "queue_state": "string (running|paused)"
}
```

## Error Codes

### HTTP Status Codes

- `200 OK`: Request successful
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid request data
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

### Application Error Codes

- `VALIDATION_ERROR`: Request validation failed
- `NOT_FOUND_ERROR`: Requested resource not found
- `QUEUE_SERVICE_ERROR`: Queue operation failed
- `DATABASE_ERROR`: Database operation failed
- `ARCHIVE_ERROR`: Archive operation failed
- `IMPORT_EXPORT_ERROR`: Import/export operation failed

## Rate Limiting

Currently, no rate limiting is implemented. In production environments, consider implementing rate limiting based on your needs.

## Examples

### Python Examples

#### Basic Queue Operations

```python
import requests
import json

BASE_URL = "http://localhost:5000/api/queue"

# Get all queue items
response = requests.get(f"{BASE_URL}/items")
items = response.json()["items"]

# Add new workflow
workflow_data = {
    "workflow_name": "My API Workflow",
    "workflow_data": {
        "nodes": [
            {"id": "1", "type": "LoadImage", "inputs": {}},
            {"id": "2", "type": "SaveImage", "inputs": {"images": ["1", 0]}}
        ],
        "links": [["1", 0, "2", 0]]
    }
}

response = requests.post(
    f"{BASE_URL}/items",
    headers={"Content-Type": "application/json"},
    data=json.dumps(workflow_data)
)

new_item = response.json()["item"]
print(f"Created item: {new_item['id']}")

# Update item status
update_data = {
    "status": "completed",
    "result_data": {"output": "success"}
}

response = requests.put(
    f"{BASE_URL}/items/{new_item['id']}",
    headers={"Content-Type": "application/json"},
    data=json.dumps(update_data)
)

print("Item updated successfully")
```

#### Filtering and Search

```python
# Filter by status
filter_data = {
    "status": ["pending", "running"]
}

response = requests.post(
    f"{BASE_URL}/items/filter",
    headers={"Content-Type": "application/json"},
    data=json.dumps(filter_data)
)

filtered_items = response.json()["items"]

# Search workflows
response = requests.get(f"{BASE_URL}/search?q=my workflow")
search_results = response.json()["items"]
```

#### Export and Import

```python
# Export queue
export_data = {
    "include_archived": True
}

response = requests.post(
    f"{BASE_URL}/export",
    headers={"Content-Type": "application/json"},
    data=json.dumps(export_data)
)

exported_queue = response.json()["export_data"]

# Save to file
with open("queue_backup.json", "w") as f:
    json.dump(exported_queue, f, indent=2)

# Import queue
with open("queue_backup.json", "r") as f:
    queue_data = json.load(f)

import_data = {
    "queue_data": queue_data,
    "merge": True
}

response = requests.post(
    f"{BASE_URL}/import",
    headers={"Content-Type": "application/json"},
    data=json.dumps(import_data)
)

print(f"Imported {response.json()['imported_count']} items")
```

### JavaScript Examples

#### Using Fetch API

```javascript
const BASE_URL = "http://localhost:5000/api/queue";

// Get queue status
async function getQueueStatus() {
    const response = await fetch(`${BASE_URL}/status`);
    const data = await response.json();
    console.log("Queue status:", data.queue_state);
    return data;
}

// Add workflow
async function addWorkflow(workflowName, workflowData) {
    const response = await fetch(`${BASE_URL}/items`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            workflow_name: workflowName,
            workflow_data: workflowData
        })
    });
    
    const data = await response.json();
    return data.item;
}

// Filter items
async function filterItems(filters) {
    const response = await fetch(`${BASE_URL}/items/filter`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(filters)
    });
    
    const data = await response.json();
    return data.items;
}

// Usage
getQueueStatus().then(status => {
    console.log(`Queue has ${status.total_items} items`);
});

const workflow = {
    nodes: [
        {id: "1", type: "LoadImage", inputs: {}},
        {id: "2", type: "SaveImage", inputs: {images: ["1", 0]}}
    ],
    links: [["1", 0, "2", 0]]
};

addWorkflow("JS API Test", workflow).then(item => {
    console.log(`Created item: ${item.id}`);
});
```

### cURL Examples

#### Basic Operations

```bash
# Get all items
curl -X GET "http://localhost:5000/api/queue/items"

# Get pending items only
curl -X GET "http://localhost:5000/api/queue/items?status=pending"

# Add new workflow
curl -X POST "http://localhost:5000/api/queue/items" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_name": "cURL Test Workflow",
    "workflow_data": {
      "nodes": [{"id": "1", "type": "LoadImage", "inputs": {}}],
      "links": []
    }
  }'

# Update item status
curl -X PUT "http://localhost:5000/api/queue/items/ITEM_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "completed",
    "result_data": {"output": "success"}
  }'

# Delete item
curl -X DELETE "http://localhost:5000/api/queue/items/ITEM_ID"
```

#### Advanced Operations

```bash
# Filter items
curl -X POST "http://localhost:5000/api/queue/items/filter" \
  -H "Content-Type: application/json" \
  -d '{
    "status": ["completed"],
    "date_from": "2025-09-01T00:00:00Z"
  }'

# Search items
curl -X GET "http://localhost:5000/api/queue/search?q=test"

# Archive items
curl -X POST "http://localhost:5000/api/queue/archive" \
  -H "Content-Type: application/json" \
  -d '{
    "item_ids": ["uuid-1", "uuid-2"]
  }'

# Export queue
curl -X POST "http://localhost:5000/api/queue/export" \
  -H "Content-Type: application/json" \
  -d '{
    "include_archived": true
  }'

# Pause queue
curl -X POST "http://localhost:5000/api/queue/pause"

# Resume queue
curl -X POST "http://localhost:5000/api/queue/resume"
```

## WebSocket Support

Currently, the API does not support WebSocket connections. Real-time updates are handled through polling. WebSocket support may be added in future versions for real-time queue updates.

## Versioning

The API follows semantic versioning. The current version is included in health check responses. Breaking changes will increment the major version number.

## Support

For API-related issues:

1. Check this documentation
2. Verify request format and required fields
3. Check HTTP status codes and error messages
4. Report bugs on GitHub with request/response examples

---

**Related Documentation**:
- [User Guide](USER_GUIDE.md) - General usage instructions
- [Installation Guide](INSTALLATION.md) - Setup instructions
- [Developer Guide](DEVELOPER_GUIDE.md) - Development information