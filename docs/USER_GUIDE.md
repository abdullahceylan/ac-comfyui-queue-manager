# ComfyUI Queue Manager - User Guide

## Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Getting Started](#getting-started)
4. [Features Overview](#features-overview)
5. [Using the Queue Manager](#using-the-queue-manager)
6. [Advanced Features](#advanced-features)
7. [Troubleshooting](#troubleshooting)
8. [FAQ](#faq)

## Introduction

The ComfyUI Queue Manager is a comprehensive workflow management system that provides persistent queue functionality, advanced filtering, archiving capabilities, and import/export features for ComfyUI workflows.

### Key Benefits

- **Persistent Queue**: Your workflows are saved and persist across ComfyUI restarts
- **Advanced Management**: Filter, search, archive, and organize your workflows
- **Import/Export**: Share workflows and backup your queue configuration
- **Real-time Monitoring**: Track workflow execution status and performance
- **Web Interface**: Modern, responsive web interface accessible from ComfyUI menu

## Installation

### Prerequisites

- ComfyUI installed and working
- Python 3.8 or higher
- Flask 2.3.0 or higher

### Installation Steps

1. **Download the Custom Node**
   ```bash
   cd ComfyUI/custom_nodes
   git clone https://github.com/abdullahceylan/ac-comfyui-queue-manager.git comfyui-queue-manager
   ```

2. **Install Dependencies**
   ```bash
   cd comfyui-queue-manager
   pip install -r requirements.txt
   ```

3. **Restart ComfyUI**
   - Close ComfyUI completely
   - Restart ComfyUI
   - The Queue Manager should appear in the menu

### Verification

1. Open ComfyUI
2. Look for "Queue Manager" in the main menu
3. Click on it to open the queue management interface
4. If you see the queue interface, installation was successful

## Getting Started

### First Launch

When you first open the Queue Manager:

1. **Access the Interface**
   - Click "Queue Manager" in the ComfyUI menu
   - A new tab/window will open with the queue interface

2. **Initial Setup**
   - The queue starts empty
   - Default settings are applied automatically
   - Database is created in the custom node directory

3. **Run Your First Workflow**
   - Create any workflow in ComfyUI
   - Execute it normally (Queue Prompt)
   - The workflow will automatically appear in the Queue Manager

### Basic Workflow

1. **Create Workflows**: Design workflows in ComfyUI as usual
2. **Execute**: Click "Queue Prompt" - workflows are automatically added to the queue
3. **Monitor**: View progress in the Queue Manager interface
4. **Manage**: Filter, search, archive, or export completed workflows

## Features Overview

### Core Features

- **Automatic Queue Management**: All workflows are automatically tracked
- **Persistent Storage**: Queue survives ComfyUI restarts
- **Status Tracking**: Monitor pending, running, completed, and failed workflows
- **Real-time Updates**: Interface updates automatically as workflows execute

### Management Features

- **Filtering**: Filter by status, date, workflow name
- **Search**: Full-text search across workflow names and data
- **Archiving**: Archive old workflows to keep queue clean
- **Bulk Operations**: Select multiple items for batch operations

### Data Features

- **Import/Export**: Save and load queue data
- **Backup/Restore**: Create backups of your workflow history
- **Configuration**: Customize queue behavior and settings

## Using the Queue Manager

### Interface Overview

The Queue Manager interface consists of several main sections:

#### 1. Header Bar
- **Queue Status**: Shows if queue is running or paused
- **Controls**: Pause/Resume queue processing
- **Statistics**: Total items, active workflows

#### 2. Filter Panel
- **Status Filter**: Filter by workflow status
- **Date Range**: Filter by creation or completion date
- **Search Box**: Search workflow names and content
- **Clear Filters**: Reset all filters

#### 3. Queue List
- **Workflow Items**: List of all workflows
- **Status Indicators**: Visual status indicators
- **Action Buttons**: Individual item actions
- **Bulk Selection**: Select multiple items

#### 4. Action Panel
- **Bulk Actions**: Archive, delete, export selected items
- **Queue Actions**: Import, export, configuration
- **System Actions**: Clear queue, reset database

### Managing Workflows

#### Viewing Workflows

1. **All Workflows**: Default view shows all workflows
2. **Filter by Status**:
   - Pending: Waiting to execute
   - Running: Currently executing
   - Completed: Successfully finished
   - Failed: Execution failed
   - Archived: Moved to archive

3. **Search Workflows**:
   - Type in search box to find specific workflows
   - Searches workflow names and metadata
   - Results update in real-time

#### Workflow Actions

**Individual Actions** (click on workflow):
- **View Details**: See full workflow information
- **Retry**: Re-queue failed workflows
- **Archive**: Move to archive
- **Delete**: Permanently remove
- **Export**: Export single workflow

**Bulk Actions** (select multiple):
- **Archive Selected**: Archive multiple workflows
- **Delete Selected**: Delete multiple workflows
- **Export Selected**: Export multiple workflows

### Queue Control

#### Pause/Resume Queue

- **Pause**: Stops processing new workflows (current ones continue)
- **Resume**: Resumes normal queue processing
- **Status**: Always visible in header

#### Queue Configuration

Access via Settings button:

- **Max Concurrent Workflows**: How many workflows run simultaneously
- **Auto-Archive**: Automatically archive completed workflows after X days
- **Retention Policy**: How long to keep workflow data
- **Performance Settings**: Optimize for your system

### Archiving System

#### What is Archiving?

Archiving moves workflows to a separate storage area:
- Keeps queue interface clean
- Preserves workflow history
- Workflows can be restored or re-run
- Archived items don't appear in main queue

#### How to Archive

**Manual Archiving**:
1. Select workflows to archive
2. Click "Archive Selected"
3. Confirm the action

**Automatic Archiving**:
1. Enable in settings
2. Set number of days
3. Completed workflows auto-archive

**Viewing Archived Items**:
1. Click "Show Archived" toggle
2. Archived items appear with different styling
3. Can be restored or permanently deleted

### Import/Export

#### Exporting Workflows

**Export All**:
1. Click "Export Queue"
2. Choose export format (JSON)
3. Save file to desired location

**Export Selected**:
1. Select specific workflows
2. Click "Export Selected"
3. Save filtered export

**Export Options**:
- Include/exclude archived items
- Include/exclude workflow data
- Include/exclude results

#### Importing Workflows

**Import Process**:
1. Click "Import Queue"
2. Select previously exported file
3. Choose import options:
   - Merge with existing queue
   - Replace entire queue
   - Import only specific statuses

**Import Validation**:
- File format is validated
- Duplicate workflows are detected
- Import summary is shown before confirmation

## Advanced Features

### API Access

The Queue Manager provides a REST API for advanced users:

**Base URL**: `http://localhost:5000/api/queue/`

**Key Endpoints**:
- `GET /items` - List all queue items
- `POST /items` - Add new workflow
- `PUT /items/{id}` - Update workflow
- `DELETE /items/{id}` - Delete workflow
- `POST /filter` - Filter workflows
- `GET /search` - Search workflows

**Example Usage**:
```bash
# Get all queue items
curl http://localhost:5000/api/queue/items

# Add new workflow
curl -X POST http://localhost:5000/api/queue/items \
  -H "Content-Type: application/json" \
  -d '{"workflow_name": "My Workflow", "workflow_data": {...}}'
```

### Database Management

#### Database Location
- Default: `custom_nodes/comfyui-queue-manager/queue_manager.db`
- SQLite database file
- Can be backed up by copying file

#### Database Maintenance
- **Backup**: Copy database file regularly
- **Cleanup**: Use built-in cleanup tools
- **Reset**: Delete database file to start fresh
- **Migration**: Automatic schema updates

### Performance Optimization

#### For Large Queues (1000+ workflows)

1. **Enable Auto-Archive**: Keep active queue small
2. **Adjust Concurrent Workflows**: Based on system resources
3. **Regular Cleanup**: Remove old failed workflows
4. **Database Optimization**: Use built-in optimization tools

#### System Requirements

- **Minimum**: 2GB RAM, 1GB disk space
- **Recommended**: 4GB RAM, 5GB disk space
- **Large Scale**: 8GB+ RAM, 10GB+ disk space

### Integration with Other Tools

#### ComfyUI Manager
- Compatible with ComfyUI Manager
- Can be installed via Manager interface
- Updates available through Manager

#### Custom Workflows
- Works with any ComfyUI workflow
- Supports custom nodes
- Handles complex workflow graphs

## Troubleshooting

### Common Issues

#### Queue Manager Not Appearing in Menu

**Possible Causes**:
- Installation incomplete
- Dependencies missing
- ComfyUI not restarted

**Solutions**:
1. Verify installation in `custom_nodes` directory
2. Check `pip install -r requirements.txt` ran successfully
3. Restart ComfyUI completely
4. Check ComfyUI console for error messages

#### Workflows Not Appearing in Queue

**Possible Causes**:
- Queue Manager not initialized
- Database connection issues
- Workflow interception disabled

**Solutions**:
1. Open Queue Manager interface first
2. Check database file permissions
3. Restart ComfyUI
4. Check console for error messages

#### Interface Not Loading

**Possible Causes**:
- Port conflict (default 5000)
- Firewall blocking connection
- Browser cache issues

**Solutions**:
1. Try different port in settings
2. Check firewall settings
3. Clear browser cache
4. Try different browser

#### Performance Issues

**Symptoms**:
- Slow interface loading
- High memory usage
- Workflow execution delays

**Solutions**:
1. Enable auto-archive
2. Reduce concurrent workflows
3. Clean up old workflows
4. Optimize database

### Error Messages

#### "Database initialization failed"
- Check file permissions in custom node directory
- Ensure disk space available
- Try deleting database file to reset

#### "Port already in use"
- Another application using port 5000
- Change port in settings
- Or stop conflicting application

#### "Workflow execution failed"
- Check ComfyUI console for details
- Verify workflow is valid
- Check for missing custom nodes

### Getting Help

#### Log Files
- Location: `custom_nodes/comfyui-queue-manager/logs/`
- Files: `queue_manager.log`, `errors.log`
- Include in support requests

#### Support Channels
- GitHub Issues: Report bugs and feature requests
- ComfyUI Discord: Community support
- Documentation: Check this guide and API docs

## FAQ

### General Questions

**Q: Does this replace ComfyUI's built-in queue?**
A: No, it enhances it. ComfyUI's queue still works normally, but workflows are also tracked in the Queue Manager for persistence and advanced management.

**Q: Will this slow down my workflows?**
A: No, the overhead is minimal. Workflows execute normally through ComfyUI's system.

**Q: Can I use this with custom nodes?**
A: Yes, it works with any ComfyUI workflow including custom nodes.

### Installation Questions

**Q: Do I need to install anything else?**
A: Just the Python dependencies listed in requirements.txt. Flask is the main requirement.

**Q: Can I install this through ComfyUI Manager?**
A: Yes, if available in the registry. Otherwise, manual installation is straightforward.

**Q: Does this work on all operating systems?**
A: Yes, it works on Windows, macOS, and Linux.

### Usage Questions

**Q: How do I backup my queue?**
A: Use the Export function to save all workflows, or copy the database file directly.

**Q: Can I share workflows with others?**
A: Yes, use the Export/Import functions to share individual workflows or entire queues.

**Q: What happens if I delete a workflow?**
A: It's permanently removed from the queue. Use Archive instead to preserve but hide workflows.

**Q: Can I run multiple ComfyUI instances?**
A: Each instance needs its own Queue Manager database. Configure different ports if running simultaneously.

### Technical Questions

**Q: Where is data stored?**
A: In a SQLite database file in the custom node directory. It's portable and can be backed up easily.

**Q: Can I access the queue from other applications?**
A: Yes, through the REST API. See the API documentation for details.

**Q: How much disk space does it use?**
A: Depends on workflow complexity and quantity. Typical usage: 1-10MB per 1000 workflows.

**Q: Is my data secure?**
A: Data is stored locally on your machine. The web interface is only accessible from localhost by default.

---

For more detailed technical information, see the [API Documentation](API_DOCUMENTATION.md) and [Developer Guide](DEVELOPER_GUIDE.md).