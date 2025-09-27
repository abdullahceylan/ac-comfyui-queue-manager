# ComfyUI Queue Manager - Examples and Use Cases

## Table of Contents

1. [Basic Usage Examples](#basic-usage-examples)
2. [Workflow Management](#workflow-management)
3. [Automation Scripts](#automation-scripts)
4. [Integration Examples](#integration-examples)
5. [Advanced Use Cases](#advanced-use-cases)
6. [Troubleshooting Examples](#troubleshooting-examples)

## Basic Usage Examples

### Example 1: Simple Image Processing Workflow

This example shows how to create and manage a basic image processing workflow.

**Workflow Setup**:
1. Create a workflow in ComfyUI:
   - Load Image node
   - Image processing nodes (resize, enhance, etc.)
   - Save Image node

2. Execute the workflow normally
3. View in Queue Manager

**Expected Queue Manager Behavior**:
- Workflow appears as "pending"
- Status changes to "running" during execution
- Status changes to "completed" when finished
- Results are stored and viewable

### Example 2: Batch Processing Multiple Images

**Scenario**: Process 50 images with the same workflow

**Steps**:
1. Create base workflow for single image
2. Use ComfyUI's batch processing features
3. Queue multiple executions
4. Monitor progress in Queue Manager

**Queue Manager Features Used**:
- Filter by status to see progress
- Bulk operations for completed items
- Archive processed batches

### Example 3: AI Art Generation Pipeline

**Scenario**: Generate multiple variations of an art piece

**Workflow Components**:
- Text prompt input
- Model loading
- Sampling with different seeds
- Upscaling
- Final output

**Queue Management**:
```python
# Example API usage for batch generation
import requests
import json

BASE_URL = "http://localhost:5000/api/queue"

# Base workflow template
base_workflow = {
    "nodes": [
        {"id": "1", "type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "model.safetensors"}},
        {"id": "2", "type": "CLIPTextEncode", "inputs": {"text": "a beautiful landscape", "clip": ["1", 1]}},
        {"id": "3", "type": "KSampler", "inputs": {"seed": 42, "steps": 20, "model": ["1", 0], "positive": ["2", 0]}},
        {"id": "4", "type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["1", 2]}},
        {"id": "5", "type": "SaveImage", "inputs": {"images": ["4", 0]}}
    ],
    "links": [["1", 0, "3", 0], ["1", 1, "2", 0], ["1", 2, "4", 1], ["2", 0, "3", 1], ["3", 0, "4", 0], ["4", 0, "5", 0]]
}

# Generate 10 variations with different seeds
for i in range(10):
    workflow = base_workflow.copy()
    workflow["nodes"][2]["inputs"]["seed"] = 42 + i  # Different seed for each
    
    response = requests.post(
        f"{BASE_URL}/items",
        headers={"Content-Type": "application/json"},
        data=json.dumps({
            "workflow_name": f"Art Generation Variation {i+1}",
            "workflow_data": workflow
        })
    )
    
    print(f"Queued variation {i+1}")

# Monitor progress
response = requests.get(f"{BASE_URL}/status")
status = response.json()
print(f"Queue status: {status['pending_items']} pending, {status['running_items']} running")
```

## Workflow Management

### Managing Long-Running Workflows

**Scenario**: Video processing or complex AI workflows that take hours

**Best Practices**:
1. **Monitor Progress**: Use Queue Manager to track status
2. **Resource Management**: Limit concurrent workflows
3. **Error Handling**: Set up retry mechanisms
4. **Archiving**: Archive completed long workflows

**Configuration Example**:
```python
# Set maximum concurrent workflows to 1 for resource-intensive tasks
config_update = {
    "max_concurrent_workflows": 1,
    "auto_archive_completed": True,
    "auto_archive_days": 7
}

response = requests.put(
    f"{BASE_URL}/config",
    headers={"Content-Type": "application/json"},
    data=json.dumps(config_update)
)
```

### Workflow Templates and Reuse

**Scenario**: Standardize workflows for team use

**Implementation**:
1. Create template workflows
2. Export successful workflows
3. Import templates on other systems
4. Version control workflow templates

**Export Template Example**:
```python
# Export specific successful workflows as templates
template_items = ["uuid-1", "uuid-2", "uuid-3"]  # IDs of template workflows

export_data = {
    "item_ids": template_items,
    "include_archived": False
}

response = requests.post(
    f"{BASE_URL}/export",
    headers={"Content-Type": "application/json"},
    data=json.dumps(export_data)
)

# Save as template file
with open("workflow_templates.json", "w") as f:
    json.dump(response.json()["export_data"], f, indent=2)
```

### Quality Control Workflow

**Scenario**: Review and approve generated content

**Process**:
1. Generate content with workflows
2. Filter completed items for review
3. Use custom status or tags for approval
4. Archive approved items separately

**Implementation**:
```python
# Get completed items for review
filter_data = {"status": ["completed"]}
response = requests.post(f"{BASE_URL}/items/filter", 
                        headers={"Content-Type": "application/json"},
                        data=json.dumps(filter_data))

completed_items = response.json()["items"]

# Review process (manual or automated)
approved_items = []
for item in completed_items:
    # Review logic here
    if review_item(item):  # Your review function
        approved_items.append(item["id"])

# Archive approved items
if approved_items:
    archive_data = {"item_ids": approved_items}
    requests.post(f"{BASE_URL}/archive",
                 headers={"Content-Type": "application/json"},
                 data=json.dumps(archive_data))
```

## Automation Scripts

### Daily Batch Processing Script

**Use Case**: Process daily uploads automatically

```python
#!/usr/bin/env python3
"""
Daily batch processing script for ComfyUI Queue Manager
"""

import requests
import json
import os
import glob
from datetime import datetime

BASE_URL = "http://localhost:5000/api/queue"
INPUT_DIR = "/path/to/daily/inputs"
WORKFLOW_TEMPLATE = "daily_processing_template.json"

def load_workflow_template():
    """Load workflow template from file"""
    with open(WORKFLOW_TEMPLATE, 'r') as f:
        return json.load(f)

def process_daily_batch():
    """Process all files in input directory"""
    # Get list of files to process
    image_files = glob.glob(os.path.join(INPUT_DIR, "*.jpg")) + \
                  glob.glob(os.path.join(INPUT_DIR, "*.png"))
    
    if not image_files:
        print("No files to process")
        return
    
    # Load workflow template
    template = load_workflow_template()
    
    # Queue workflows for each file
    queued_count = 0
    for image_file in image_files:
        workflow = template.copy()
        
        # Update workflow with specific file
        workflow["nodes"][0]["inputs"]["image"] = os.path.basename(image_file)
        
        # Queue the workflow
        response = requests.post(
            f"{BASE_URL}/items",
            headers={"Content-Type": "application/json"},
            data=json.dumps({
                "workflow_name": f"Daily Processing - {os.path.basename(image_file)}",
                "workflow_data": workflow
            })
        )
        
        if response.status_code == 201:
            queued_count += 1
            print(f"Queued: {os.path.basename(image_file)}")
        else:
            print(f"Failed to queue: {os.path.basename(image_file)}")
    
    print(f"Queued {queued_count} workflows for processing")

def cleanup_old_workflows():
    """Archive workflows older than 7 days"""
    from datetime import datetime, timedelta
    
    # Get all completed workflows
    response = requests.post(
        f"{BASE_URL}/items/filter",
        headers={"Content-Type": "application/json"},
        data=json.dumps({"status": ["completed"]})
    )
    
    completed_items = response.json()["items"]
    
    # Find items older than 7 days
    cutoff_date = datetime.now() - timedelta(days=7)
    old_items = []
    
    for item in completed_items:
        item_date = datetime.fromisoformat(item["completed_at"].replace('Z', '+00:00'))
        if item_date < cutoff_date:
            old_items.append(item["id"])
    
    # Archive old items
    if old_items:
        archive_data = {"item_ids": old_items}
        response = requests.post(
            f"{BASE_URL}/archive",
            headers={"Content-Type": "application/json"},
            data=json.dumps(archive_data)
        )
        print(f"Archived {len(old_items)} old workflows")

if __name__ == "__main__":
    print(f"Starting daily batch processing - {datetime.now()}")
    process_daily_batch()
    cleanup_old_workflows()
    print("Daily batch processing completed")
```

### Monitoring and Alerting Script

**Use Case**: Monitor queue health and send alerts

```python
#!/usr/bin/env python3
"""
Queue monitoring and alerting script
"""

import requests
import smtplib
from email.mime.text import MimeText
from datetime import datetime, timedelta

BASE_URL = "http://localhost:5000/api/queue"

def check_queue_health():
    """Check queue health and return status"""
    try:
        response = requests.get(f"{BASE_URL}/status", timeout=10)
        if response.status_code != 200:
            return {"healthy": False, "error": f"API returned {response.status_code}"}
        
        status = response.json()
        
        # Check for issues
        issues = []
        
        # Too many failed items
        if status["failed_items"] > 10:
            issues.append(f"High number of failed items: {status['failed_items']}")
        
        # Queue stuck (no progress in last hour)
        if status["running_items"] == 0 and status["pending_items"] > 0:
            issues.append("Queue appears stuck - pending items but none running")
        
        # Very old pending items
        response = requests.post(
            f"{BASE_URL}/items/filter",
            headers={"Content-Type": "application/json"},
            data=json.dumps({"status": ["pending"]})
        )
        
        if response.status_code == 200:
            pending_items = response.json()["items"]
            old_pending = []
            cutoff = datetime.now() - timedelta(hours=2)
            
            for item in pending_items:
                created_at = datetime.fromisoformat(item["created_at"].replace('Z', '+00:00'))
                if created_at < cutoff:
                    old_pending.append(item)
            
            if len(old_pending) > 5:
                issues.append(f"Many old pending items: {len(old_pending)}")
        
        return {
            "healthy": len(issues) == 0,
            "status": status,
            "issues": issues
        }
        
    except Exception as e:
        return {"healthy": False, "error": str(e)}

def send_alert(subject, message):
    """Send email alert"""
    # Configure your email settings
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    sender_email = "your-email@gmail.com"
    sender_password = "your-app-password"
    recipient_email = "admin@yourcompany.com"
    
    msg = MimeText(message)
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = recipient_email
    
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        print("Alert sent successfully")
    except Exception as e:
        print(f"Failed to send alert: {e}")

def main():
    """Main monitoring function"""
    health = check_queue_health()
    
    if not health["healthy"]:
        subject = "ComfyUI Queue Manager Alert"
        
        if "error" in health:
            message = f"Queue Manager health check failed: {health['error']}"
        else:
            message = f"Queue Manager issues detected:\n\n"
            for issue in health["issues"]:
                message += f"- {issue}\n"
            
            if "status" in health:
                status = health["status"]
                message += f"\nCurrent Status:\n"
                message += f"- Total items: {status['total_items']}\n"
                message += f"- Pending: {status['pending_items']}\n"
                message += f"- Running: {status['running_items']}\n"
                message += f"- Failed: {status['failed_items']}\n"
        
        send_alert(subject, message)
    else:
        print("Queue health check passed")

if __name__ == "__main__":
    main()
```

## Integration Examples

### Integration with External Systems

#### Webhook Integration

**Use Case**: Notify external systems when workflows complete

```python
import requests
import json

def setup_webhook_monitoring():
    """Monitor queue and send webhooks for completed workflows"""
    
    # Get recently completed items
    response = requests.post(
        f"{BASE_URL}/items/filter",
        headers={"Content-Type": "application/json"},
        data=json.dumps({
            "status": ["completed"],
            "date_from": (datetime.now() - timedelta(hours=1)).isoformat()
        })
    )
    
    completed_items = response.json()["items"]
    
    # Send webhook for each completed item
    webhook_url = "https://your-system.com/webhook/comfyui-completed"
    
    for item in completed_items:
        webhook_data = {
            "event": "workflow_completed",
            "workflow_id": item["id"],
            "workflow_name": item["workflow_name"],
            "completed_at": item["completed_at"],
            "result_data": item["result_data"]
        }
        
        try:
            response = requests.post(
                webhook_url,
                headers={"Content-Type": "application/json"},
                data=json.dumps(webhook_data),
                timeout=10
            )
            print(f"Webhook sent for {item['id']}: {response.status_code}")
        except Exception as e:
            print(f"Webhook failed for {item['id']}: {e}")
```

#### Database Integration

**Use Case**: Store workflow results in external database

```python
import sqlite3
import requests
import json

def sync_to_database():
    """Sync completed workflows to external database"""
    
    # Connect to external database
    conn = sqlite3.connect('workflow_results.db')
    cursor = conn.cursor()
    
    # Create table if not exists
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS workflow_results (
            id TEXT PRIMARY KEY,
            workflow_name TEXT,
            status TEXT,
            created_at TEXT,
            completed_at TEXT,
            result_data TEXT,
            synced_at TEXT
        )
    ''')
    
    # Get completed workflows not yet synced
    response = requests.post(
        f"{BASE_URL}/items/filter",
        headers={"Content-Type": "application/json"},
        data=json.dumps({"status": ["completed"]})
    )
    
    completed_items = response.json()["items"]
    
    # Check which items are already synced
    synced_count = 0
    for item in completed_items:
        cursor.execute('SELECT id FROM workflow_results WHERE id = ?', (item["id"],))
        if cursor.fetchone() is None:
            # Insert new record
            cursor.execute('''
                INSERT INTO workflow_results 
                (id, workflow_name, status, created_at, completed_at, result_data, synced_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                item["id"],
                item["workflow_name"],
                item["status"],
                item["created_at"],
                item["completed_at"],
                json.dumps(item["result_data"]),
                datetime.now().isoformat()
            ))
            synced_count += 1
    
    conn.commit()
    conn.close()
    print(f"Synced {synced_count} new workflow results to database")
```

### CI/CD Integration

**Use Case**: Automated testing of ComfyUI workflows

```yaml
# .github/workflows/test-workflows.yml
name: Test ComfyUI Workflows

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test-workflows:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        pip install requests
    
    - name: Start ComfyUI with Queue Manager
      run: |
        # Start ComfyUI in background
        python ComfyUI/main.py --headless &
        sleep 30  # Wait for startup
    
    - name: Test Workflow Execution
      run: |
        python test_workflows.py
    
    - name: Check Results
      run: |
        python check_test_results.py
```

```python
# test_workflows.py
import requests
import json
import time

BASE_URL = "http://localhost:5000/api/queue"

def test_basic_workflow():
    """Test basic image processing workflow"""
    
    workflow_data = {
        "workflow_name": "CI Test - Basic Processing",
        "workflow_data": {
            "nodes": [
                {"id": "1", "type": "LoadImage", "inputs": {"image": "test_image.png"}},
                {"id": "2", "type": "SaveImage", "inputs": {"images": ["1", 0]}}
            ],
            "links": [["1", 0, "2", 0]]
        }
    }
    
    # Queue workflow
    response = requests.post(
        f"{BASE_URL}/items",
        headers={"Content-Type": "application/json"},
        data=json.dumps(workflow_data)
    )
    
    assert response.status_code == 201
    item_id = response.json()["item"]["id"]
    
    # Wait for completion (with timeout)
    timeout = 300  # 5 minutes
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        response = requests.get(f"{BASE_URL}/items/{item_id}")
        item = response.json()["item"]
        
        if item["status"] == "completed":
            print("✓ Basic workflow test passed")
            return True
        elif item["status"] == "failed":
            print(f"✗ Basic workflow test failed: {item['error_message']}")
            return False
        
        time.sleep(5)
    
    print("✗ Basic workflow test timed out")
    return False

if __name__ == "__main__":
    success = test_basic_workflow()
    exit(0 if success else 1)
```

## Advanced Use Cases

### Multi-Stage Processing Pipeline

**Scenario**: Complex pipeline with multiple dependent stages

```python
class WorkflowPipeline:
    """Manage multi-stage workflow pipeline"""
    
    def __init__(self, base_url):
        self.base_url = base_url
        self.stages = []
    
    def add_stage(self, name, workflow_template, depends_on=None):
        """Add a stage to the pipeline"""
        self.stages.append({
            "name": name,
            "workflow_template": workflow_template,
            "depends_on": depends_on,
            "items": []
        })
    
    def execute_pipeline(self, input_data):
        """Execute the entire pipeline"""
        pipeline_id = f"pipeline_{int(time.time())}"
        
        for stage in self.stages:
            if stage["depends_on"]:
                # Wait for dependency to complete
                self.wait_for_stage_completion(stage["depends_on"])
            
            # Execute current stage
            workflow = stage["workflow_template"].copy()
            # Update workflow with input_data and previous stage results
            
            response = requests.post(
                f"{self.base_url}/items",
                headers={"Content-Type": "application/json"},
                data=json.dumps({
                    "workflow_name": f"{pipeline_id} - {stage['name']}",
                    "workflow_data": workflow
                })
            )
            
            if response.status_code == 201:
                item_id = response.json()["item"]["id"]
                stage["items"].append(item_id)
                print(f"Started stage: {stage['name']}")
    
    def wait_for_stage_completion(self, stage_name):
        """Wait for a specific stage to complete"""
        stage = next(s for s in self.stages if s["name"] == stage_name)
        
        while True:
            all_completed = True
            for item_id in stage["items"]:
                response = requests.get(f"{self.base_url}/items/{item_id}")
                item = response.json()["item"]
                
                if item["status"] not in ["completed", "failed"]:
                    all_completed = False
                    break
            
            if all_completed:
                break
            
            time.sleep(10)

# Usage example
pipeline = WorkflowPipeline(BASE_URL)

# Stage 1: Initial processing
pipeline.add_stage("preprocessing", {
    "nodes": [
        {"id": "1", "type": "LoadImage", "inputs": {}},
        {"id": "2", "type": "ImageResize", "inputs": {"image": ["1", 0]}}
    ]
})

# Stage 2: AI processing (depends on stage 1)
pipeline.add_stage("ai_processing", {
    "nodes": [
        {"id": "1", "type": "LoadProcessedImage", "inputs": {}},
        {"id": "2", "type": "AIEnhancement", "inputs": {"image": ["1", 0]}}
    ]
}, depends_on="preprocessing")

# Stage 3: Final output (depends on stage 2)
pipeline.add_stage("output", {
    "nodes": [
        {"id": "1", "type": "LoadEnhancedImage", "inputs": {}},
        {"id": "2", "type": "SaveFinalImage", "inputs": {"image": ["1", 0]}}
    ]
}, depends_on="ai_processing")

pipeline.execute_pipeline({"input_image": "source.jpg"})
```

### Resource-Aware Scheduling

**Use Case**: Optimize workflow execution based on system resources

```python
import psutil
import requests
import json
import time

class ResourceAwareScheduler:
    """Schedule workflows based on system resources"""
    
    def __init__(self, base_url):
        self.base_url = base_url
        self.max_cpu_percent = 80
        self.max_memory_percent = 85
        self.max_concurrent = 3
    
    def get_system_resources(self):
        """Get current system resource usage"""
        return {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_usage": psutil.disk_usage('/').percent
        }
    
    def can_start_workflow(self):
        """Check if system can handle another workflow"""
        resources = self.get_system_resources()
        
        # Check resource limits
        if resources["cpu_percent"] > self.max_cpu_percent:
            return False, "CPU usage too high"
        
        if resources["memory_percent"] > self.max_memory_percent:
            return False, "Memory usage too high"
        
        # Check current running workflows
        response = requests.get(f"{self.base_url}/status")
        status = response.json()
        
        if status["running_items"] >= self.max_concurrent:
            return False, "Too many concurrent workflows"
        
        return True, "Resources available"
    
    def schedule_workflows(self):
        """Main scheduling loop"""
        while True:
            # Get pending workflows
            response = requests.post(
                f"{self.base_url}/items/filter",
                headers={"Content-Type": "application/json"},
                data=json.dumps({"status": ["pending"]})
            )
            
            pending_items = response.json()["items"]
            
            if not pending_items:
                print("No pending workflows")
                time.sleep(30)
                continue
            
            # Check if we can start more workflows
            can_start, reason = self.can_start_workflow()
            
            if can_start:
                # Start highest priority workflow
                # (In this example, oldest first)
                oldest_item = min(pending_items, key=lambda x: x["created_at"])
                
                # Update status to running (this would normally be done by ComfyUI)
                response = requests.put(
                    f"{self.base_url}/items/{oldest_item['id']}",
                    headers={"Content-Type": "application/json"},
                    data=json.dumps({"status": "running"})
                )
                
                print(f"Started workflow: {oldest_item['workflow_name']}")
            else:
                print(f"Cannot start workflow: {reason}")
            
            time.sleep(10)  # Check every 10 seconds

# Usage
scheduler = ResourceAwareScheduler(BASE_URL)
scheduler.schedule_workflows()
```

## Troubleshooting Examples

### Common Issues and Solutions

#### Issue: Workflows Stuck in Pending

**Diagnosis Script**:
```python
def diagnose_stuck_workflows():
    """Diagnose why workflows are stuck in pending"""
    
    # Get pending workflows
    response = requests.post(
        f"{BASE_URL}/items/filter",
        headers={"Content-Type": "application/json"},
        data=json.dumps({"status": ["pending"]})
    )
    
    pending_items = response.json()["items"]
    
    if not pending_items:
        print("No pending workflows found")
        return
    
    print(f"Found {len(pending_items)} pending workflows")
    
    # Check for very old pending items
    old_items = []
    cutoff = datetime.now() - timedelta(hours=1)
    
    for item in pending_items:
        created_at = datetime.fromisoformat(item["created_at"].replace('Z', '+00:00'))
        if created_at < cutoff:
            old_items.append(item)
    
    if old_items:
        print(f"Found {len(old_items)} workflows pending for over 1 hour:")
        for item in old_items[:5]:  # Show first 5
            print(f"  - {item['workflow_name']} (created: {item['created_at']})")
    
    # Check queue status
    response = requests.get(f"{BASE_URL}/status")
    status = response.json()
    
    print(f"\nQueue Status:")
    print(f"  - State: {status.get('queue_state', 'unknown')}")
    print(f"  - Running: {status.get('running_items', 0)}")
    print(f"  - Pending: {status.get('pending_items', 0)}")
    
    # Recommendations
    print(f"\nRecommendations:")
    if status.get('queue_state') == 'paused':
        print("  - Queue is paused. Resume queue processing.")
    elif status.get('running_items', 0) == 0:
        print("  - No workflows running. Check ComfyUI status.")
    elif len(old_items) > 0:
        print("  - Consider restarting ComfyUI or clearing stuck workflows.")

diagnose_stuck_workflows()
```

#### Issue: High Memory Usage

**Memory Cleanup Script**:
```python
def cleanup_memory_usage():
    """Clean up queue to reduce memory usage"""
    
    # Archive old completed workflows
    cutoff_date = datetime.now() - timedelta(days=7)
    
    response = requests.post(
        f"{BASE_URL}/items/filter",
        headers={"Content-Type": "application/json"},
        data=json.dumps({"status": ["completed"]})
    )
    
    completed_items = response.json()["items"]
    old_completed = []
    
    for item in completed_items:
        completed_at = datetime.fromisoformat(item["completed_at"].replace('Z', '+00:00'))
        if completed_at < cutoff_date:
            old_completed.append(item["id"])
    
    if old_completed:
        print(f"Archiving {len(old_completed)} old completed workflows...")
        archive_data = {"item_ids": old_completed}
        response = requests.post(
            f"{BASE_URL}/archive",
            headers={"Content-Type": "application/json"},
            data=json.dumps(archive_data)
        )
        print("Archive completed")
    
    # Delete old failed workflows
    response = requests.post(
        f"{BASE_URL}/items/filter",
        headers={"Content-Type": "application/json"},
        data=json.dumps({"status": ["failed"]})
    )
    
    failed_items = response.json()["items"]
    old_failed = []
    
    for item in failed_items:
        created_at = datetime.fromisoformat(item["created_at"].replace('Z', '+00:00'))
        if created_at < cutoff_date:
            old_failed.append(item["id"])
    
    if old_failed:
        print(f"Deleting {len(old_failed)} old failed workflows...")
        delete_data = {"item_ids": old_failed}
        response = requests.delete(
            f"{BASE_URL}/items/bulk",
            headers={"Content-Type": "application/json"},
            data=json.dumps(delete_data)
        )
        print("Deletion completed")

cleanup_memory_usage()
```

#### Issue: Database Corruption

**Database Recovery Script**:
```python
def recover_database():
    """Attempt to recover from database issues"""
    
    print("Attempting database recovery...")
    
    # First, try to export current data
    try:
        response = requests.post(
            f"{BASE_URL}/export",
            headers={"Content-Type": "application/json"},
            data=json.dumps({"include_archived": True})
        )
        
        if response.status_code == 200:
            # Save backup
            backup_file = f"queue_backup_{int(time.time())}.json"
            with open(backup_file, 'w') as f:
                json.dump(response.json()["export_data"], f, indent=2)
            print(f"Backup saved to {backup_file}")
        else:
            print("Could not create backup - database may be corrupted")
    
    except Exception as e:
        print(f"Backup failed: {e}")
    
    # Instructions for manual recovery
    print("\nManual recovery steps:")
    print("1. Stop ComfyUI")
    print("2. Backup current database file: queue_manager.db")
    print("3. Delete corrupted database file")
    print("4. Restart ComfyUI (new database will be created)")
    print("5. Import backup using the web interface or API")

recover_database()
```

These examples demonstrate the flexibility and power of the ComfyUI Queue Manager for various use cases, from simple workflow management to complex automation and integration scenarios.