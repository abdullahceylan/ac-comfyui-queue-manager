/**
 * ComfyUI Queue Manager Frontend JavaScript
 * Handles the user interface interactions and API communication
 */

class QueueManager {
    constructor() {
        this.apiBase = '/queue';
        this.queueItems = [];
        this.selectedItems = new Set();
        this.queueState = 'running';
        
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadQueueItems();
        this.updateQueueState();
    }

    bindEvents() {
        // Control buttons
        document.getElementById('pause-resume-btn').addEventListener('click', () => {
            this.toggleQueueState();
        });
        
        document.getElementById('refresh-btn').addEventListener('click', () => {
            this.loadQueueItems();
        });

        // Bulk actions
        document.getElementById('archive-selected-btn').addEventListener('click', () => {
            this.archiveSelected();
        });
        
        document.getElementById('delete-selected-btn').addEventListener('click', () => {
            this.deleteSelected();
        });

        // Filters
        document.getElementById('search-input').addEventListener('input', (e) => {
            this.filterItems();
        });
        
        document.getElementById('status-filter').addEventListener('change', (e) => {
            this.filterItems();
        });
    }

    async loadQueueItems() {
        try {
            this.showLoading();
            // Placeholder for API call - will be implemented in later tasks
            // const response = await fetch(`${this.apiBase}/items`);
            // this.queueItems = await response.json();
            
            // Mock data for now
            this.queueItems = [];
            this.renderQueueItems();
        } catch (error) {
            console.error('Failed to load queue items:', error);
            this.showError('Failed to load queue items');
        }
    }

    async updateQueueState() {
        try {
            // Placeholder for API call - will be implemented in later tasks
            // const response = await fetch(`${this.apiBase}/status`);
            // const data = await response.json();
            // this.queueState = data.state;
            
            this.updatePauseResumeButton();
        } catch (error) {
            console.error('Failed to update queue state:', error);
        }
    }

    async toggleQueueState() {
        try {
            const newState = this.queueState === 'running' ? 'paused' : 'running';
            // Placeholder for API call - will be implemented in later tasks
            // await fetch(`${this.apiBase}/${newState}`, { method: 'POST' });
            
            this.queueState = newState;
            this.updatePauseResumeButton();
        } catch (error) {
            console.error('Failed to toggle queue state:', error);
        }
    }

    updatePauseResumeButton() {
        const btn = document.getElementById('pause-resume-btn');
        if (this.queueState === 'running') {
            btn.textContent = 'Pause';
            btn.className = 'btn btn-warning';
        } else {
            btn.textContent = 'Resume';
            btn.className = 'btn btn-primary';
        }
    }

    renderQueueItems() {
        const container = document.getElementById('queue-items');
        
        if (this.queueItems.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <h3>No queue items</h3>
                    <p>Queue items will appear here when workflows are added to the queue.</p>
                </div>
            `;
            return;
        }

        container.innerHTML = this.queueItems.map(item => this.renderQueueItem(item)).join('');
        this.bindItemEvents();
    }

    renderQueueItem(item) {
        const createdAt = new Date(item.created_at).toLocaleString();
        const updatedAt = new Date(item.updated_at).toLocaleString();
        
        return `
            <div class="queue-item ${item.status}" data-id="${item.id}">
                <div class="queue-item-header">
                    <div>
                        <input type="checkbox" class="checkbox item-checkbox" data-id="${item.id}">
                        <span class="queue-item-title">${item.workflow_name || 'Unnamed Workflow'}</span>
                    </div>
                    <span class="queue-item-status status-${item.status}">${item.status}</span>
                </div>
                
                <div class="queue-item-meta">
                    <span>Created: ${createdAt}</span>
                    <span>Updated: ${updatedAt}</span>
                    <span>ID: ${item.id}</span>
                </div>
                
                ${item.error_message ? `<div class="error-message">${item.error_message}</div>` : ''}
                
                <div class="queue-item-actions">
                    ${this.getItemActions(item)}
                </div>
            </div>
        `;
    }

    getItemActions(item) {
        const actions = [];
        
        if (item.status === 'archived') {
            actions.push('<button class="btn btn-secondary restore-btn" data-id="' + item.id + '">Restore</button>');
        } else {
            actions.push('<button class="btn btn-warning archive-btn" data-id="' + item.id + '">Archive</button>');
        }
        
        if (item.status === 'pending' || item.status === 'failed') {
            actions.push('<button class="btn btn-primary retry-btn" data-id="' + item.id + '">Retry</button>');
        }
        
        actions.push('<button class="btn btn-danger delete-btn" data-id="' + item.id + '">Delete</button>');
        
        return actions.join('');
    }

    bindItemEvents() {
        // Checkbox selection
        document.querySelectorAll('.item-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
                const itemId = e.target.dataset.id;
                if (e.target.checked) {
                    this.selectedItems.add(itemId);
                } else {
                    this.selectedItems.delete(itemId);
                }
            });
        });

        // Individual item actions
        document.querySelectorAll('.archive-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.archiveItem(e.target.dataset.id);
            });
        });

        document.querySelectorAll('.restore-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.restoreItem(e.target.dataset.id);
            });
        });

        document.querySelectorAll('.delete-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.deleteItem(e.target.dataset.id);
            });
        });

        document.querySelectorAll('.retry-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.retryItem(e.target.dataset.id);
            });
        });
    }

    filterItems() {
        const searchTerm = document.getElementById('search-input').value.toLowerCase();
        const statusFilter = document.getElementById('status-filter').value;
        
        document.querySelectorAll('.queue-item').forEach(item => {
            const title = item.querySelector('.queue-item-title').textContent.toLowerCase();
            const status = item.classList.contains('pending') ? 'pending' :
                          item.classList.contains('running') ? 'running' :
                          item.classList.contains('completed') ? 'completed' :
                          item.classList.contains('failed') ? 'failed' :
                          item.classList.contains('archived') ? 'archived' : '';
            
            const matchesSearch = !searchTerm || title.includes(searchTerm);
            const matchesStatus = !statusFilter || status === statusFilter;
            
            item.style.display = matchesSearch && matchesStatus ? 'block' : 'none';
        });
    }

    async archiveSelected() {
        if (this.selectedItems.size === 0) {
            alert('Please select items to archive');
            return;
        }
        
        try {
            // Placeholder for API call - will be implemented in later tasks
            console.log('Archiving items:', Array.from(this.selectedItems));
            this.selectedItems.clear();
            this.loadQueueItems();
        } catch (error) {
            console.error('Failed to archive items:', error);
        }
    }

    async deleteSelected() {
        if (this.selectedItems.size === 0) {
            alert('Please select items to delete');
            return;
        }
        
        if (!confirm('Are you sure you want to delete the selected items?')) {
            return;
        }
        
        try {
            // Placeholder for API call - will be implemented in later tasks
            console.log('Deleting items:', Array.from(this.selectedItems));
            this.selectedItems.clear();
            this.loadQueueItems();
        } catch (error) {
            console.error('Failed to delete items:', error);
        }
    }

    async archiveItem(itemId) {
        try {
            // Placeholder for API call - will be implemented in later tasks
            console.log('Archiving item:', itemId);
            this.loadQueueItems();
        } catch (error) {
            console.error('Failed to archive item:', error);
        }
    }

    async restoreItem(itemId) {
        try {
            // Placeholder for API call - will be implemented in later tasks
            console.log('Restoring item:', itemId);
            this.loadQueueItems();
        } catch (error) {
            console.error('Failed to restore item:', error);
        }
    }

    async deleteItem(itemId) {
        if (!confirm('Are you sure you want to delete this item?')) {
            return;
        }
        
        try {
            // Placeholder for API call - will be implemented in later tasks
            console.log('Deleting item:', itemId);
            this.loadQueueItems();
        } catch (error) {
            console.error('Failed to delete item:', error);
        }
    }

    async retryItem(itemId) {
        try {
            // Placeholder for API call - will be implemented in later tasks
            console.log('Retrying item:', itemId);
            this.loadQueueItems();
        } catch (error) {
            console.error('Failed to retry item:', error);
        }
    }

    showLoading() {
        document.getElementById('queue-items').innerHTML = `
            <div class="loading">
                <p>Loading queue items...</p>
            </div>
        `;
    }

    showError(message) {
        document.getElementById('queue-items').innerHTML = `
            <div class="empty-state">
                <h3>Error</h3>
                <p>${message}</p>
            </div>
        `;
    }
}

// Initialize the queue manager when the page loads
document.addEventListener('DOMContentLoaded', () => {
    new QueueManager();
});