/**
 * ComfyUI Queue Manager Extension
 * Registers the Queue Manager with ComfyUI's extension system
 */

import { app } from "/scripts/app.js";
import { api } from "/scripts/api.js";

// Extension name
const EXTENSION_NAME = "QueueManager";

// Queue Manager state
let queueManagerState = {
  window: null,
  tab: null,
  isOpen: false,
  menuButton: null,
};

/**
 * Queue Manager ComfyUI Extension
 */
app.registerExtension({
  name: EXTENSION_NAME,

  async init(app) {
    console.log(`[${EXTENSION_NAME}] Initializing extension`);

    // Initialize queue manager integration
    this.initializeQueueManager();
  },

  async setup(app) {
    console.log(`[${EXTENSION_NAME}] Setting up extension`);

    // Add menu integration
    this.addMenuIntegration();

    // Set up keyboard shortcuts
    this.setupKeyboardShortcuts();
  },

  async beforeRegisterNodeDef(nodeType, nodeData, app) {
    // Hook into Queue Manager node registration
    if (nodeData.name === "QueueManagerNode") {
      console.log(`[${EXTENSION_NAME}] Queue Manager node detected`);

      // Add custom functionality to the node if needed
      const onNodeCreated = nodeType.prototype.onNodeCreated;
      nodeType.prototype.onNodeCreated = function () {
        if (onNodeCreated) {
          onNodeCreated.apply(this, arguments);
        }

        // Add queue manager specific functionality
        this.addWidget("button", "Open Queue Manager", null, () => {
          openQueueManager();
        });
      };
    }
  },

  /**
   * Initialize Queue Manager integration
   */
  initializeQueueManager() {
    // Check if Queue Manager API is available
    this.checkQueueManagerAPI();

    // Set up event listeners
    this.setupEventListeners();
  },

  /**
   * Add menu integration to ComfyUI
   */
  addMenuIntegration() {
    try {
      // Wait for ComfyUI menu to be ready
      const addMenuButton = () => {
        const menuContainer = this.findMenuContainer();
        if (menuContainer) {
          this.createMenuButton(menuContainer);
        } else {
          // Retry after a short delay
          setTimeout(addMenuButton, 500);
        }
      };

      // Add menu button when DOM is ready
      if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", addMenuButton);
      } else {
        addMenuButton();
      }
    } catch (error) {
      console.error(
        `[${EXTENSION_NAME}] Failed to add menu integration:`,
        error,
      );
    }
  },

  /**
   * Find ComfyUI's menu container
   */
  findMenuContainer() {
    // Try multiple selectors to find the menu
    const selectors = [
      ".comfy-menu",
      "#comfy-menu",
      ".menu",
      ".comfy-menu-btns",
      ".comfyui-menu",
    ];

    for (const selector of selectors) {
      const container = document.querySelector(selector);
      if (container) {
        return container;
      }
    }

    // Try to find by looking for existing menu buttons
    const existingButtons = document.querySelectorAll("button");
    for (const button of existingButtons) {
      if (
        button.textContent.includes("Queue") ||
        button.textContent.includes("Settings") ||
        button.className.includes("comfy")
      ) {
        return button.parentElement;
      }
    }

    return null;
  },

  /**
   * Create the Queue Manager menu button
   */
  createMenuButton(container) {
    if (queueManagerState.menuButton) {
      return; // Already created
    }

    const button = document.createElement("button");
    button.textContent = "📋 Queue Manager";
    button.title = "Open Queue Manager";
    button.className = "comfy-menu-btns queue-manager-btn";

    // Style the button to match ComfyUI's theme
    button.style.cssText = `
            background: var(--comfy-menu-bg, #333);
            color: var(--comfy-menu-text, #fff);
            border: 1px solid var(--comfy-menu-border, #555);
            padding: 4px 8px;
            margin: 2px;
            cursor: pointer;
            border-radius: 3px;
            font-size: 12px;
            transition: background-color 0.2s;
        `;

    // Add hover effects
    button.addEventListener("mouseenter", () => {
      button.style.backgroundColor = "var(--comfy-menu-hover-bg, #555)";
    });

    button.addEventListener("mouseleave", () => {
      button.style.backgroundColor = "var(--comfy-menu-bg, #333)";
    });

    // Add click handler
    button.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      openQueueManager();
    });

    // Insert button into menu
    container.appendChild(button);
    queueManagerState.menuButton = button;

    console.log(`[${EXTENSION_NAME}] Menu button added successfully`);
  },

  /**
   * Set up keyboard shortcuts
   */
  setupKeyboardShortcuts() {
    document.addEventListener("keydown", (e) => {
      // Ctrl+Shift+Q to open Queue Manager
      if (e.ctrlKey && e.shiftKey && e.key === "Q") {
        e.preventDefault();
        openQueueManager();
      }
    });
  },

  /**
   * Set up event listeners
   */
  setupEventListeners() {
    // Listen for window close events
    window.addEventListener("beforeunload", () => {
      if (queueManagerState.window && !queueManagerState.window.closed) {
        queueManagerState.window.close();
      }
    });
  },

  /**
   * Check if Queue Manager API is available
   */
  async checkQueueManagerAPI() {
    try {
      const response = await fetch("/queue/status");
      if (response.ok) {
        console.log(`[${EXTENSION_NAME}] Queue Manager API is available`);
        return true;
      }
    } catch (error) {
      console.warn(
        `[${EXTENSION_NAME}] Queue Manager API not available:`,
        error,
      );
    }
    return false;
  },
});

/**
 * Open the Queue Manager interface
 */
function openQueueManager() {
  try {
    // Check if already open
    if (queueManagerState.window && !queueManagerState.window.closed) {
      queueManagerState.window.focus();
      return;
    }

    // Determine the best way to open
    if (canOpenPopup()) {
      openAsPopup();
    } else {
      openAsTab();
    }
  } catch (error) {
    console.error(`[${EXTENSION_NAME}] Failed to open Queue Manager:`, error);
    showNotification("Failed to open Queue Manager", "error");
  }
}

/**
 * Check if popup windows can be opened
 */
function canOpenPopup() {
  try {
    const test = window.open("", "_blank", "width=1,height=1");
    if (test) {
      test.close();
      return true;
    }
  } catch (error) {
    // Popup blocked
  }
  return false;
}

/**
 * Open Queue Manager as popup window
 */
function openAsPopup() {
  const features = [
    "width=1200",
    "height=800",
    "left=100",
    "top=100",
    "resizable=yes",
    "scrollbars=yes",
    "status=no",
    "menubar=no",
    "toolbar=no",
  ].join(",");

  const url = getQueueManagerUrl();
  queueManagerState.window = window.open(url, "QueueManager", features);

  if (queueManagerState.window) {
    queueManagerState.window.focus();
    queueManagerState.isOpen = true;

    // Handle window close
    const checkClosed = setInterval(() => {
      if (queueManagerState.window.closed) {
        queueManagerState.isOpen = false;
        queueManagerState.window = null;
        clearInterval(checkClosed);
      }
    }, 1000);

    console.log(`[${EXTENSION_NAME}] Opened as popup window`);
  } else {
    openAsTab();
  }
}

/**
 * Open Queue Manager as new tab
 */
function openAsTab() {
  const url = getQueueManagerUrl();
  queueManagerState.tab = window.open(url, "_blank");

  if (queueManagerState.tab) {
    queueManagerState.tab.focus();
    queueManagerState.isOpen = true;
    console.log(`[${EXTENSION_NAME}] Opened as new tab`);
  } else {
    showNotification(
      "Failed to open Queue Manager. Please check popup blocker settings.",
      "error",
    );
  }
}

/**
 * Get the Queue Manager URL
 */
function getQueueManagerUrl() {
  const baseUrl = window.location.origin;
  return `${baseUrl}/extensions/comfyui-queue-manager/index.html`;
}

/**
 * Show notification to user
 */
function showNotification(message, type = "info") {
  const notification = document.createElement("div");
  notification.className = `queue-manager-notification ${type}`;
  notification.textContent = message;

  const colors = {
    info: "#2196F3",
    success: "#4CAF50",
    warning: "#FF9800",
    error: "#f44336",
  };

  notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${colors[type] || colors.info};
        color: white;
        padding: 12px 20px;
        border-radius: 4px;
        z-index: 10000;
        font-size: 14px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.3);
        max-width: 300px;
        word-wrap: break-word;
    `;

  document.body.appendChild(notification);

  // Auto-remove after 5 seconds
  setTimeout(() => {
    if (document.body.contains(notification)) {
      document.body.removeChild(notification);
    }
  }, 5000);

  // Click to dismiss
  notification.addEventListener("click", () => {
    if (document.body.contains(notification)) {
      document.body.removeChild(notification);
    }
  });
}

// Export for external access
window.QueueManagerExtension = {
  openQueueManager,
  getState: () => queueManagerState,
  showNotification,
};

console.log(`[${EXTENSION_NAME}] Extension loaded successfully`);
