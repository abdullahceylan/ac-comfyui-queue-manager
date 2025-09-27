/**
 * Simplified ComfyUI Queue Manager Frontend JavaScript
 * Basic version for testing
 */

console.log("Queue Manager JavaScript loaded successfully");

class SimpleQueueManager {
    constructor() {
        this.apiBase = '/queue';
        this.queueItems = [];
        console.log("SimpleQueueManager initialized");
    }

    init() {
        console.log("SimpleQueueManager init called");
        this.bindEvents();
        this.loadMockData();
    }

    bindEvents() {
        const pauseBtn = document.getElementById('pause-resume-btn');
        if (pauseBtn) {
            pauseBtn.addEventListener('click', () => {
                console.log('Pause/Resume clicked');
            });
        }

        const refreshBtn = document.getElementById('refresh-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                console.log('Refresh clicked');
                this.loadMockData();
            });
        }
    }

    loadMockData() {
        console.log("Loading mock data");
        this.queueItems = [
            {
                id: 'test-1',
                workflow_name: 'Test Workflow',
                status: 'pending',
                created_at: new Date().toISOString()
            }
        ];
        this.renderItems();
    }

    renderItems() {
        const container = document.getElementById('queue-items');
        if (!container) {
            console.error('Queue items container not found');
            return;
        }

        if (this.queueItems.length === 0) {
            container.innerHTML = '<div class="empty-state"><h3>No queue items</h3></div>';
            return;
        }

        container.innerHTML = this.queueItems.map(item => `
            <div class="queue-item ${item.status}">
                <h4>${item.workflow_name}</h4>
                <p>Status: ${item.status}</p>
                <p>Created: ${new Date(item.created_at).toLocaleString()}</p>
            </div>
        `).join('');
    }
}

// Initialize when DOM is ready
let simpleQueueManager;
document.addEventListener('DOMContentLoaded', () => {
    console.log("DOM loaded, initializing SimpleQueueManager");
    simpleQueueManager = new SimpleQueueManager();
    simpleQueueManager.init();
});

// Export for global access
window.simpleQueueManager = simpleQueueManager;