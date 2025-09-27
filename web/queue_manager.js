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
        this.updateInterval = null;
        this.currentFilters = {
            search: '',
            status: '',
            dateRange: null
        };
        
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadQueueItems();
        this.updateQueueState();
        this.startRealTimeUpdates();
    }

    bindEvents() {
        // Control buttons
        document.getElementById('pause-resume-btn').addEventListener('click', () => {
            this.toggleQueueState();
        });
        
        document.getElementById('refresh-btn').addEventListener('click', () => {
            this.loadQueueItems();
        });
        
        document.getElementById('import-export-btn').addEventListener('click', () => {
            this.showModal('import-export-modal');
        });
        
        document.getElementById('help-btn').addEventListener('click', () => {
            this.showModal('help-modal');
        });

        // Bulk actions
        document.getElementById('archive-selected-btn').addEventListener('click', () => {
            this.archiveSelected();
        });
        
        document.getElementById('delete-selected-btn').addEventListener('click', () => {
            this.deleteSelected();
        });
        
        document.getElementById('restore-selected-btn').addEventListener('click', () => {
            this.restoreSelected();
        });

        // Filters
        document.getElementById('search-input').addEventListener('input', (e) => {
            this.currentFilters.search = e.target.value;
            this.filterItems();
        });
        
        document.getElementById('status-filter').addEventListener('change', (e) => {
            this.currentFilters.status = e.target.value;
            this.filterItems();
        });
        
        // Modal events
        this.bindModalEvents();
        
        // Keyboard shortcuts
        this.bindKeyboardShortcuts();
    }
    
    bindModalEvents() {
        // Modal overlay click to close
        document.getElementById('modal-overlay').addEventListener('click', (e) => {
            if (e.target.id === 'modal-overlay') {
                this.hideModal();
            }
        });
        
        // Modal close buttons
        document.querySelectorAll('.modal-close').forEach(btn => {
            btn.addEventListener('click', () => {
                this.hideModal();
            });
        });
        
        // Tab switching
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.switchTab(e.target.dataset.tab);
            });
        });
        
        // Import/Export modal actions
        document.getElementById('export-btn').addEventListener('click', () => {
            this.exportQueue();
        });
        
        document.getElementById('import-btn').addEventListener('click', () => {
            this.importQueue();
        });
        
        // Archive modal actions
        document.getElementById('archive-confirm-btn').addEventListener('click', () => {
            this.confirmArchive();
        });
        
        // Confirmation modal
        document.getElementById('confirm-btn').addEventListener('click', () => {
            this.executeConfirmedAction();
        });
    }

    async loadQueueItems() {
        try {
            this.showLoading();
            // Placeholder for API call - will be implemented in later tasks
            // const response = await fetch(`${this.apiBase}/items`);
            // this.queueItems = await response.json();
            
            // Mock data for demonstration
            this.queueItems = this.generateMockData();
            this.renderQueueItems();
        } catch (error) {
            console.error('Failed to load queue items:', error);
            this.showError('Failed to load queue items');
        }
    }
    
    generateMockData() {
        // Generate some mock queue items for demonstration
        const statuses = ['pending', 'running', 'completed', 'failed', 'archived'];
        const workflowNames = [
            'Text to Image Generation',
            'Image Upscaling',
            'Style Transfer',
            'Background Removal',
            'Face Enhancement'
        ];
        
        const mockItems = [];
        for (let i = 0; i < 10; i++) {
            const createdAt = new Date(Date.now() - Math.random() * 86400000 * 7); // Last 7 days
            const updatedAt = new Date(createdAt.getTime() + Math.random() * 3600000); // Up to 1 hour later
            
            mockItems.push({
                id: `item-${i + 1}`,
                workflow_name: workflowNames[Math.floor(Math.random() * workflowNames.length)],
                status: statuses[Math.floor(Math.random() * statuses.length)],
                created_at: createdAt.toISOString(),
                updated_at: updatedAt.toISOString(),
                started_at: Math.random() > 0.5 ? updatedAt.toISOString() : null,
                completed_at: Math.random() > 0.7 ? new Date(updatedAt.getTime() + Math.random() * 1800000).toISOString() : null,
                error_message: Math.random() > 0.8 ? 'Sample error message for demonstration' : null,
                workflow_data: { nodes: [], connections: [] }
            });
        }
        
        return mockItems;
    }
    
    startRealTimeUpdates() {
        // Update queue items every 5 seconds
        this.updateInterval = setInterval(() => {
            this.loadQueueItems();
        }, 5000);
    }
    
    stopRealTimeUpdates() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
            this.updateInterval = null;
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
        const header = document.querySelector('header h1');
        
        if (this.queueState === 'running') {
            btn.textContent = '⏸️ Pause Queue';
            btn.className = 'btn btn-warning';
            header.style.color = '#4CAF50';
            this.showStatusIndicator('Queue is running', 'success');
        } else {
            btn.textContent = '▶️ Resume Queue';
            btn.className = 'btn btn-primary';
            header.style.color = '#ff9800';
            this.showStatusIndicator('Queue is paused', 'warning');
        }
    }
    
    showStatusIndicator(message, type) {
        // Remove existing status indicator
        const existing = document.querySelector('.status-indicator');
        if (existing) {
            existing.remove();
        }
        
        // Create new status indicator
        const indicator = document.createElement('div');
        indicator.className = `status-indicator status-${type}`;
        indicator.textContent = message;
        
        const header = document.querySelector('header');
        header.appendChild(indicator);
        
        // Auto-hide after 3 seconds
        setTimeout(() => {
            if (indicator.parentNode) {
                indicator.remove();
            }
        }, 3000);
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
        const startedAt = item.started_at ? new Date(item.started_at).toLocaleString() : null;
        const completedAt = item.completed_at ? new Date(item.completed_at).toLocaleString() : null;
        
        // Calculate duration if applicable
        let duration = '';
        if (item.started_at && item.completed_at) {
            const start = new Date(item.started_at);
            const end = new Date(item.completed_at);
            const durationMs = end - start;
            duration = this.formatDuration(durationMs);
        } else if (item.started_at && item.status === 'running') {
            const start = new Date(item.started_at);
            const now = new Date();
            const durationMs = now - start;
            duration = this.formatDuration(durationMs) + ' (running)';
        }
        
        return `
            <div class="queue-item ${item.status}" data-id="${item.id}" data-status="${item.status}">
                <div class="queue-item-header">
                    <div class="item-header-left">
                        <input type="checkbox" class="checkbox item-checkbox" data-id="${item.id}" 
                               ${this.selectedItems.has(item.id) ? 'checked' : ''}>
                        <span class="queue-item-title">${item.workflow_name || 'Unnamed Workflow'}</span>
                    </div>
                    <div class="item-header-right">
                        <span class="queue-item-status status-${item.status}">
                            ${item.status === 'running' ? '<span class="spinner"></span>' : ''}
                            ${item.status.toUpperCase()}
                        </span>
                    </div>
                </div>
                
                <div class="queue-item-meta">
                    <span><strong>Created:</strong> ${createdAt}</span>
                    <span><strong>Updated:</strong> ${updatedAt}</span>
                    ${startedAt ? `<span><strong>Started:</strong> ${startedAt}</span>` : ''}
                    ${completedAt ? `<span><strong>Completed:</strong> ${completedAt}</span>` : ''}
                    ${duration ? `<span><strong>Duration:</strong> ${duration}</span>` : ''}
                    <span><strong>ID:</strong> ${item.id}</span>
                </div>
                
                ${item.error_message ? `<div class="error-message"><strong>Error:</strong> ${item.error_message}</div>` : ''}
                
                <div class="queue-item-details" style="display: none;">
                    <h4>Workflow Data:</h4>
                    <pre>${JSON.stringify(item.workflow_data, null, 2)}</pre>
                </div>
                
                <div class="queue-item-actions">
                    <button class="btn btn-secondary toggle-details-btn" data-id="${item.id}">Show Details</button>
                    ${this.getItemActions(item)}
                </div>
            </div>
        `;
    }
    
    formatDuration(milliseconds) {
        const seconds = Math.floor(milliseconds / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);
        
        if (hours > 0) {
            return `${hours}h ${minutes % 60}m ${seconds % 60}s`;
        } else if (minutes > 0) {
            return `${minutes}m ${seconds % 60}s`;
        } else {
            return `${seconds}s`;
        }
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
                this.updateBulkActionButtons();
            });
        });

        // Toggle details
        document.querySelectorAll('.toggle-details-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.toggleItemDetails(e.target.dataset.id);
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
        
        // Item click selection (excluding buttons and checkboxes)
        document.querySelectorAll('.queue-item').forEach(item => {
            item.addEventListener('click', (e) => {
                if (!e.target.matches('button, input, .btn, .checkbox')) {
                    this.toggleItemSelection(item.dataset.id);
                }
            });
        });
    }
    
    toggleItemDetails(itemId) {
        const item = document.querySelector(`[data-id="${itemId}"]`);
        const details = item.querySelector('.queue-item-details');
        const btn = item.querySelector('.toggle-details-btn');
        
        if (details.style.display === 'none') {
            details.style.display = 'block';
            btn.textContent = 'Hide Details';
        } else {
            details.style.display = 'none';
            btn.textContent = 'Show Details';
        }
    }
    
    toggleItemSelection(itemId) {
        const checkbox = document.querySelector(`[data-id="${itemId}"].item-checkbox`);
        checkbox.checked = !checkbox.checked;
        checkbox.dispatchEvent(new Event('change'));
    }
    
    updateBulkActionButtons() {
        const archiveBtn = document.getElementById('archive-selected-btn');
        const restoreBtn = document.getElementById('restore-selected-btn');
        const deleteBtn = document.getElementById('delete-selected-btn');
        const selectedCount = this.selectedItems.size;
        
        // Count archived items in selection
        const archivedCount = Array.from(this.selectedItems).filter(itemId => {
            const item = this.queueItems.find(i => i.id === itemId);
            return item && item.status === 'archived';
        }).length;
        
        archiveBtn.disabled = selectedCount === 0;
        restoreBtn.disabled = archivedCount === 0;
        deleteBtn.disabled = selectedCount === 0;
        
        if (selectedCount > 0) {
            archiveBtn.textContent = `Archive Selected (${selectedCount})`;
            deleteBtn.textContent = `Delete Selected (${selectedCount})`;
        } else {
            archiveBtn.textContent = 'Archive Selected';
            deleteBtn.textContent = 'Delete Selected';
        }
        
        if (archivedCount > 0) {
            restoreBtn.textContent = `Restore Selected (${archivedCount})`;
        } else {
            restoreBtn.textContent = 'Restore Selected';
        }
    }

    filterItems() {
        const searchTerm = this.currentFilters.search.toLowerCase();
        const statusFilter = this.currentFilters.status;
        
        let visibleCount = 0;
        let totalCount = 0;
        
        document.querySelectorAll('.queue-item').forEach(item => {
            totalCount++;
            const title = item.querySelector('.queue-item-title').textContent.toLowerCase();
            const status = item.dataset.status;
            const itemId = item.dataset.id;
            
            // Search in multiple fields
            const searchableText = [
                title,
                itemId.toLowerCase(),
                item.querySelector('.queue-item-meta').textContent.toLowerCase()
            ].join(' ');
            
            const matchesSearch = !searchTerm || searchableText.includes(searchTerm);
            const matchesStatus = !statusFilter || status === statusFilter;
            
            const isVisible = matchesSearch && matchesStatus;
            item.style.display = isVisible ? 'block' : 'none';
            
            if (isVisible) {
                visibleCount++;
            }
        });
        
        this.updateFilterStatus(visibleCount, totalCount);
    }
    
    updateFilterStatus(visibleCount, totalCount) {
        // Update the queue header to show filter results
        const queueHeader = document.querySelector('.queue-header h2');
        if (visibleCount === totalCount) {
            queueHeader.textContent = `Queue Items (${totalCount})`;
        } else {
            queueHeader.textContent = `Queue Items (${visibleCount} of ${totalCount})`;
        }
        
        // Show/hide empty state for filtered results
        if (visibleCount === 0 && totalCount > 0) {
            this.showFilteredEmptyState();
        }
    }
    
    showFilteredEmptyState() {
        const container = document.getElementById('queue-items');
        const existingEmpty = container.querySelector('.filtered-empty-state');
        
        if (!existingEmpty) {
            const emptyState = document.createElement('div');
            emptyState.className = 'filtered-empty-state empty-state';
            emptyState.innerHTML = `
                <h3>No items match your filters</h3>
                <p>Try adjusting your search terms or status filter.</p>
                <button class="btn btn-secondary" onclick="queueManager.clearFilters()">Clear Filters</button>
            `;
            container.appendChild(emptyState);
        }
    }
    
    clearFilters() {
        document.getElementById('search-input').value = '';
        document.getElementById('status-filter').value = '';
        this.currentFilters = { search: '', status: '', dateRange: null };
        
        // Remove filtered empty state
        const filteredEmpty = document.querySelector('.filtered-empty-state');
        if (filteredEmpty) {
            filteredEmpty.remove();
        }
        
        this.filterItems();
    }

    async archiveSelected() {
        if (this.selectedItems.size === 0) {
            alert('Please select items to archive');
            return;
        }
        
        this.showModal('archive-modal');
    }

    async deleteSelected() {
        if (this.selectedItems.size === 0) {
            alert('Please select items to delete');
            return;
        }
        
        this.showConfirmation(
            'Delete Selected Items',
            `Are you sure you want to delete ${this.selectedItems.size} selected item(s)? This action cannot be undone.`,
            () => {
                try {
                    // Placeholder for API call - will be implemented in later tasks
                    console.log('Deleting items:', Array.from(this.selectedItems));
                    this.selectedItems.clear();
                    this.loadQueueItems();
                } catch (error) {
                    console.error('Failed to delete items:', error);
                }
            }
        );
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
        this.showConfirmation(
            'Restore Item',
            'Are you sure you want to restore this item to the active queue?',
            () => {
                try {
                    // Restore item (in real implementation, this would be an API call)
                    const item = this.queueItems.find(i => i.id === itemId);
                    if (item) {
                        item.status = 'pending';
                        item.restored_at = new Date().toISOString();
                        delete item.archived_at;
                        delete item.archive_options;
                    }
                    
                    this.renderQueueItems();
                    this.showStatusIndicator('Item restored successfully', 'success');
                } catch (error) {
                    console.error('Failed to restore item:', error);
                    this.showStatusIndicator('Failed to restore item', 'error');
                }
            }
        );
    }
    
    // Add bulk restore functionality
    restoreSelected() {
        if (this.selectedItems.size === 0) {
            this.showStatusIndicator('Please select items to restore', 'warning');
            return;
        }
        
        const archivedItems = Array.from(this.selectedItems).filter(itemId => {
            const item = this.queueItems.find(i => i.id === itemId);
            return item && item.status === 'archived';
        });
        
        if (archivedItems.length === 0) {
            this.showStatusIndicator('No archived items selected', 'warning');
            return;
        }
        
        this.showConfirmation(
            'Restore Selected Items',
            `Are you sure you want to restore ${archivedItems.length} archived item(s) to the active queue?`,
            () => {
                try {
                    archivedItems.forEach(itemId => {
                        const item = this.queueItems.find(i => i.id === itemId);
                        if (item) {
                            item.status = 'pending';
                            item.restored_at = new Date().toISOString();
                            delete item.archived_at;
                            delete item.archive_options;
                        }
                    });
                    
                    this.selectedItems.clear();
                    this.renderQueueItems();
                    this.updateBulkActionButtons();
                    this.showStatusIndicator(`Restored ${archivedItems.length} items`, 'success');
                } catch (error) {
                    console.error('Failed to restore items:', error);
                    this.showStatusIndicator('Failed to restore items', 'error');
                }
            }
        );
    }

    async deleteItem(itemId) {
        this.showConfirmation(
            'Delete Item',
            'Are you sure you want to delete this item? This action cannot be undone.',
            () => {
                try {
                    // Placeholder for API call - will be implemented in later tasks
                    console.log('Deleting item:', itemId);
                    this.loadQueueItems();
                } catch (error) {
                    console.error('Failed to delete item:', error);
                }
            }
        );
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
    
    // Modal management methods
    showModal(modalId) {
        document.getElementById('modal-overlay').classList.add('active');
        document.querySelectorAll('.modal').forEach(modal => {
            modal.style.display = 'none';
        });
        document.getElementById(modalId).style.display = 'block';
    }
    
    hideModal() {
        document.getElementById('modal-overlay').classList.remove('active');
        document.querySelectorAll('.modal').forEach(modal => {
            modal.style.display = 'none';
        });
    }
    
    switchTab(tabName) {
        // Update tab buttons
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
        
        // Update tab content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        document.getElementById(`${tabName}-tab`).classList.add('active');
    }
    
    showConfirmation(title, message, action) {
        document.getElementById('confirmation-title').textContent = title;
        document.getElementById('confirmation-message').textContent = message;
        this.pendingAction = action;
        this.showModal('confirmation-modal');
    }
    
    executeConfirmedAction() {
        if (this.pendingAction) {
            this.pendingAction();
            this.pendingAction = null;
        }
        this.hideModal();
    }
    
    // Enhanced import/export functionality
    exportQueue() {
        const exportAll = document.getElementById('export-all').checked;
        const exportSelected = document.getElementById('export-selected').checked;
        
        let itemsToExport = [];
        
        if (exportAll) {
            itemsToExport = this.queueItems;
        } else if (exportSelected && this.selectedItems.size > 0) {
            itemsToExport = this.queueItems.filter(item => this.selectedItems.has(item.id));
        } else {
            this.showStatusIndicator('Please select items to export or choose "Export all"', 'error');
            return;
        }
        
        if (itemsToExport.length === 0) {
            this.showStatusIndicator('No items to export', 'warning');
            return;
        }
        
        try {
            const exportData = {
                version: '1.0',
                exported_at: new Date().toISOString(),
                items: itemsToExport,
                total_items: itemsToExport.length
            };
            
            const dataStr = JSON.stringify(exportData, null, 2);
            const dataBlob = new Blob([dataStr], { type: 'application/json' });
            
            const link = document.createElement('a');
            link.href = URL.createObjectURL(dataBlob);
            link.download = `queue-export-${new Date().toISOString().split('T')[0]}.json`;
            link.click();
            
            this.showStatusIndicator(`Exported ${itemsToExport.length} items successfully`, 'success');
            this.hideModal();
        } catch (error) {
            console.error('Export failed:', error);
            this.showStatusIndicator('Export failed: ' + error.message, 'error');
        }
    }
    
    importQueue() {
        const fileInput = document.getElementById('import-file');
        const mergeImport = document.getElementById('merge-import').checked;
        
        if (!fileInput.files.length) {
            this.showStatusIndicator('Please select a file to import', 'warning');
            return;
        }
        
        const file = fileInput.files[0];
        const reader = new FileReader();
        
        reader.onload = (e) => {
            try {
                const importData = JSON.parse(e.target.result);
                
                // Validate import data structure
                if (!importData.items || !Array.isArray(importData.items)) {
                    throw new Error('Invalid file format: missing items array');
                }
                
                // Process import
                let importedCount = 0;
                let skippedCount = 0;
                
                importData.items.forEach(item => {
                    // Check for duplicates if merging
                    if (mergeImport) {
                        const exists = this.queueItems.some(existing => existing.id === item.id);
                        if (exists) {
                            skippedCount++;
                            return;
                        }
                    }
                    
                    // Add imported item (in real implementation, this would be an API call)
                    this.queueItems.push({
                        ...item,
                        id: mergeImport ? item.id : `imported-${Date.now()}-${importedCount}`,
                        imported_at: new Date().toISOString()
                    });
                    importedCount++;
                });
                
                // Update display
                this.renderQueueItems();
                
                let message = `Imported ${importedCount} items`;
                if (skippedCount > 0) {
                    message += `, skipped ${skippedCount} duplicates`;
                }
                
                this.showStatusIndicator(message, 'success');
                this.hideModal();
                
                // Clear file input
                fileInput.value = '';
                
            } catch (error) {
                console.error('Import failed:', error);
                this.showStatusIndicator('Import failed: ' + error.message, 'error');
            }
        };
        
        reader.onerror = () => {
            this.showStatusIndicator('Failed to read file', 'error');
        };
        
        reader.readAsText(file);
    }
    
    confirmArchive() {
        const withResults = document.getElementById('archive-with-results').checked;
        const compress = document.getElementById('archive-compress').checked;
        
        if (this.selectedItems.size === 0) {
            this.showStatusIndicator('No items selected for archiving', 'warning');
            return;
        }
        
        try {
            // Archive selected items (in real implementation, this would be an API call)
            const itemsToArchive = Array.from(this.selectedItems);
            
            itemsToArchive.forEach(itemId => {
                const item = this.queueItems.find(i => i.id === itemId);
                if (item) {
                    item.status = 'archived';
                    item.archived_at = new Date().toISOString();
                    item.archive_options = {
                        with_results: withResults,
                        compressed: compress
                    };
                }
            });
            
            // Clear selection and update display
            this.selectedItems.clear();
            this.renderQueueItems();
            this.updateBulkActionButtons();
            
            this.showStatusIndicator(`Archived ${itemsToArchive.length} items`, 'success');
            this.hideModal();
            
        } catch (error) {
            console.error('Archive failed:', error);
            this.showStatusIndicator('Archive failed: ' + error.message, 'error');
        }
    }
    
    bindKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Only handle shortcuts when not in input fields
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
                return;
            }
            
            switch (e.key) {
                case 'r':
                case 'R':
                    if (e.ctrlKey || e.metaKey) {
                        e.preventDefault();
                        this.loadQueueItems();
                    }
                    break;
                case ' ':
                    e.preventDefault();
                    this.toggleQueueState();
                    break;
                case 'a':
                case 'A':
                    if (e.ctrlKey || e.metaKey) {
                        e.preventDefault();
                        this.selectAllItems();
                    }
                    break;
                case 'Escape':
                    this.hideModal();
                    this.clearSelection();
                    break;
                case 'Delete':
                case 'Backspace':
                    if (this.selectedItems.size > 0) {
                        e.preventDefault();
                        this.deleteSelected();
                    }
                    break;
            }
        });
    }
    
    selectAllItems() {
        const visibleItems = document.querySelectorAll('.queue-item:not([style*="display: none"])');
        visibleItems.forEach(item => {
            const itemId = item.dataset.id;
            const checkbox = item.querySelector('.item-checkbox');
            this.selectedItems.add(itemId);
            checkbox.checked = true;
        });
        this.updateBulkActionButtons();
        this.showStatusIndicator(`Selected ${visibleItems.length} items`, 'success');
    }
    
    clearSelection() {
        this.selectedItems.clear();
        document.querySelectorAll('.item-checkbox').forEach(checkbox => {
            checkbox.checked = false;
        });
        this.updateBulkActionButtons();
    }
    
    // Cleanup method for when the component is destroyed
    destroy() {
        this.stopRealTimeUpdates();
        document.removeEventListener('keydown', this.bindKeyboardShortcuts);
    }
}

// Initialize the queue manager when the page loads
let queueManager;
document.addEventListener('DOMContentLoaded', () => {
    queueManager = new QueueManager();
});