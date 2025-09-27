/**
 * ComfyUI Queue Manager Menu Extension
 * Follows the official ComfyUI topbar menu API
 */

import { app } from "/scripts/app.js";

// Queue Manager window reference
let queueManagerWindow = null;

/**
 * Open the Queue Manager interface
 */
function openQueueManager() {
    try {
        // Check if window is already open
        if (queueManagerWindow && !queueManagerWindow.closed) {
            queueManagerWindow.focus();
            return;
        }

        // Get the queue manager URL
        const baseUrl = window.location.origin;
        const queueManagerUrl = `${baseUrl}/extensions/comfyui-queue-manager/index.html`;

        // Try to open as popup window
        const windowFeatures = [
            "width=1200",
            "height=800", 
            "left=100",
            "top=100",
            "resizable=yes",
            "scrollbars=yes",
            "status=no",
            "menubar=no",
            "toolbar=no"
        ].join(",");

        queueManagerWindow = window.open(queueManagerUrl, "QueueManager", windowFeatures);

        if (queueManagerWindow) {
            queueManagerWindow.focus();
            console.log("[Queue Manager] Opened successfully");
        } else {
            // Fallback to new tab
            queueManagerWindow = window.open(queueManagerUrl, "_blank");
            if (queueManagerWindow) {
                queueManagerWindow.focus();
                console.log("[Queue Manager] Opened as new tab");
            } else {
                throw new Error("Failed to open Queue Manager window");
            }
        }

        // Handle window close
        const checkClosed = setInterval(() => {
            if (queueManagerWindow && queueManagerWindow.closed) {
                queueManagerWindow = null;
                clearInterval(checkClosed);
            }
        }, 1000);

    } catch (error) {
        console.error("[Queue Manager] Failed to open:", error);
        
        // Show error notification
        const notification = document.createElement("div");
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #f44336;
            color: white;
            padding: 12px 20px;
            border-radius: 4px;
            z-index: 10000;
            font-size: 14px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.3);
        `;
        notification.textContent = "Failed to open Queue Manager. Please check popup blocker settings.";
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            if (document.body.contains(notification)) {
                document.body.removeChild(notification);
            }
        }, 5000);
    }
}

/**
 * Register the Queue Manager extension using official ComfyUI API
 */
app.registerExtension({
    name: "QueueManager",
    
    // Define commands following official API
    commands: [
        {
            id: "queueManager.open",
            label: "Open Queue Manager",
            function: openQueueManager
        }
    ],
    
    // Add commands to menu following official API
    menuCommands: [
        {
            path: ["Queue"],
            commands: ["queueManager.open"]
        }
    ],

    async setup() {
        console.log("[Queue Manager] Extension registered successfully");
        
        // Set up keyboard shortcut (Ctrl+Shift+Q)
        document.addEventListener("keydown", (e) => {
            if (e.ctrlKey && e.shiftKey && e.key === "Q") {
                e.preventDefault();
                openQueueManager();
            }
        });
    },

    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        // Hook into Queue Manager node registration
        if (nodeData.name === "QueueManagerNode") {
            console.log("[Queue Manager] Node detected:", nodeData.name);
            
            // Add button widget to the node
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function() {
                if (onNodeCreated) {
                    onNodeCreated.apply(this, arguments);
                }
                
                // Add "Open Queue Manager" button to the node
                this.addWidget("button", "Open Queue Manager", null, () => {
                    openQueueManager();
                });
            };
        }
    }
});

// Clean up on page unload
window.addEventListener("beforeunload", () => {
    if (queueManagerWindow && !queueManagerWindow.closed) {
        queueManagerWindow.close();
    }
});

console.log("[Queue Manager] Menu extension loaded");