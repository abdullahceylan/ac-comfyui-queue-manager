/**
 * ComfyUI Queue Manager Menu Extension
 * Integrates the Queue Manager into ComfyUI's menu system
 */

import { app } from "/scripts/app.js";
import { api } from "/scripts/api.js";

// Queue Manager window reference
let queueManagerWindow = null;
let queueManagerTab = null;

/**
 * Queue Manager Menu Extension
 */
class QueueManagerMenuExtension {
  constructor() {
    this.name = "QueueManager.MenuExtension";
    this.menuItem = null;
  }

  /**
   * Initialize the menu extension
   */
  init() {
    // Register menu item when ComfyUI is ready
    app.registerExtension({
      name: this.name,
      async setup() {
        // Add menu item to ComfyUI's menu
        this.addMenuItem();
      },

      async beforeRegisterNodeDef(nodeType, nodeData, app) {
        // Hook into node registration if needed
        if (nodeData.name === "QueueManagerNode") {
          // Add any node-specific menu integrations here
          console.log("[Queue Manager] Node registered:", nodeData.name);
        }
      },
    });
  }

  /**
   * Add Queue Manager menu item to ComfyUI's menu
   */
  addMenuItem() {
    try {
      // Get ComfyUI's menu container
      const menuContainer =
        document.querySelector(".comfy-menu") ||
        document.querySelector("#comfy-menu") ||
        document.querySelector(".menu");

      if (!menuContainer) {
        console.warn(
          "[Queue Manager] Could not find ComfyUI menu container, trying alternative approach",
        );
        this.addMenuItemAlternative();
        return;
      }

      // Create menu item
      const menuItem = document.createElement("button");
      menuItem.className = "comfy-menu-btns";
      menuItem.textContent = "Queue Manager";
      menuItem.title = "Open Queue Manager";
      menuItem.style.cssText = `
                background: #333;
                color: #fff;
                border: 1px solid #555;
                padding: 4px 8px;
                margin: 2px;
                cursor: pointer;
                border-radius: 3px;
                font-size: 12px;
            `;

      // Add click handler
      menuItem.addEventListener("click", () => {
        this.openQueueManager();
      });

      // Add hover effects
      menuItem.addEventListener("mouseenter", () => {
        menuItem.style.background = "#555";
      });

      menuItem.addEventListener("mouseleave", () => {
        menuItem.style.background = "#333";
      });

      // Insert menu item
      menuContainer.appendChild(menuItem);
      this.menuItem = menuItem;

      console.log("[Queue Manager] Menu item added successfully");
    } catch (error) {
      console.error("[Queue Manager] Failed to add menu item:", error);
      this.addMenuItemAlternative();
    }
  }

  /**
   * Alternative method to add menu item if standard approach fails
   */
  addMenuItemAlternative() {
    try {
      // Create a floating button as fallback
      const floatingButton = document.createElement("div");
      floatingButton.innerHTML = `
                <button id="queue-manager-floating-btn" style="
                    position: fixed;
                    top: 10px;
                    right: 10px;
                    z-index: 10000;
                    background: #4CAF50;
                    color: white;
                    border: none;
                    padding: 10px 15px;
                    border-radius: 5px;
                    cursor: pointer;
                    font-size: 12px;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.3);
                    transition: background 0.3s;
                " title="Open Queue Manager">
                    📋 Queue
                </button>
            `;

      document.body.appendChild(floatingButton);

      const button = document.getElementById("queue-manager-floating-btn");
      button.addEventListener("click", () => {
        this.openQueueManager();
      });

      button.addEventListener("mouseenter", () => {
        button.style.background = "#45a049";
      });

      button.addEventListener("mouseleave", () => {
        button.style.background = "#4CAF50";
      });

      this.menuItem = button;
      console.log("[Queue Manager] Floating menu button added as fallback");
    } catch (error) {
      console.error("[Queue Manager] Failed to add fallback menu item:", error);
    }
  }

  /**
   * Open the Queue Manager interface
   */
  openQueueManager() {
    try {
      // Check if window is already open
      if (queueManagerWindow && !queueManagerWindow.closed) {
        queueManagerWindow.focus();
        return;
      }

      // Determine the best way to open the interface
      if (this.canUsePopupWindow()) {
        this.openAsPopupWindow();
      } else {
        this.openAsTab();
      }
    } catch (error) {
      console.error("[Queue Manager] Failed to open queue manager:", error);
      this.showError("Failed to open Queue Manager");
    }
  }

  /**
   * Check if popup windows are allowed
   */
  canUsePopupWindow() {
    try {
      // Test if we can open popup windows
      const testWindow = window.open("", "_blank", "width=1,height=1");
      if (testWindow) {
        testWindow.close();
        return true;
      }
      return false;
    } catch (error) {
      return false;
    }
  }

  /**
   * Open Queue Manager as a popup window
   */
  openAsPopupWindow() {
    const windowFeatures = [
      "width=1200",
      "height=800",
      "left=100",
      "top=100",
      "resizable=yes",
      "scrollbars=yes",
      "status=no",
      "menubar=no",
      "toolbar=no",
      "location=no",
    ].join(",");

    // Get the queue manager URL
    const queueManagerUrl = this.getQueueManagerUrl();

    queueManagerWindow = window.open(
      queueManagerUrl,
      "QueueManager",
      windowFeatures,
    );

    if (queueManagerWindow) {
      queueManagerWindow.focus();

      // Handle window close
      queueManagerWindow.addEventListener("beforeunload", () => {
        queueManagerWindow = null;
      });

      console.log("[Queue Manager] Opened as popup window");
    } else {
      console.warn("[Queue Manager] Popup blocked, falling back to tab");
      this.openAsTab();
    }
  }

  /**
   * Open Queue Manager as a new tab
   */
  openAsTab() {
    const queueManagerUrl = this.getQueueManagerUrl();
    queueManagerTab = window.open(queueManagerUrl, "_blank");

    if (queueManagerTab) {
      queueManagerTab.focus();
      console.log("[Queue Manager] Opened as new tab");
    } else {
      console.error("[Queue Manager] Failed to open tab");
      this.openAsEmbedded();
    }
  }

  /**
   * Open Queue Manager as embedded iframe (fallback)
   */
  openAsEmbedded() {
    try {
      // Create modal overlay
      const overlay = document.createElement("div");
      overlay.id = "queue-manager-overlay";
      overlay.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.8);
                z-index: 10000;
                display: flex;
                justify-content: center;
                align-items: center;
            `;

      // Create iframe container
      const container = document.createElement("div");
      container.style.cssText = `
                width: 90%;
                height: 90%;
                background: white;
                border-radius: 8px;
                position: relative;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
            `;

      // Create close button
      const closeButton = document.createElement("button");
      closeButton.innerHTML = "×";
      closeButton.style.cssText = `
                position: absolute;
                top: 10px;
                right: 15px;
                background: none;
                border: none;
                font-size: 24px;
                cursor: pointer;
                z-index: 10001;
                color: #666;
            `;

      closeButton.addEventListener("click", () => {
        document.body.removeChild(overlay);
      });

      // Create iframe
      const iframe = document.createElement("iframe");
      iframe.src = this.getQueueManagerUrl();
      iframe.style.cssText = `
                width: 100%;
                height: 100%;
                border: none;
                border-radius: 8px;
            `;

      // Assemble components
      container.appendChild(closeButton);
      container.appendChild(iframe);
      overlay.appendChild(container);
      document.body.appendChild(overlay);

      // Close on overlay click
      overlay.addEventListener("click", (e) => {
        if (e.target === overlay) {
          document.body.removeChild(overlay);
        }
      });

      console.log("[Queue Manager] Opened as embedded iframe");
    } catch (error) {
      console.error(
        "[Queue Manager] Failed to open embedded interface:",
        error,
      );
      this.showError("Failed to open Queue Manager interface");
    }
  }

  /**
   * Get the Queue Manager URL
   */
  getQueueManagerUrl() {
    // Use the web directory served by ComfyUI
    const baseUrl = window.location.origin;
    return `${baseUrl}/extensions/comfyui-queue-manager/index.html`;
  }

  /**
   * Show error message
   */
  showError(message) {
    // Create simple error notification
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
            box-shadow: 0 2px 5px rgba(0,0,0,0.3);
        `;
    notification.textContent = message;

    document.body.appendChild(notification);

    // Auto-remove after 5 seconds
    setTimeout(() => {
      if (document.body.contains(notification)) {
        document.body.removeChild(notification);
      }
    }, 5000);
  }

  /**
   * Clean up resources
   */
  cleanup() {
    if (queueManagerWindow && !queueManagerWindow.closed) {
      queueManagerWindow.close();
    }

    if (this.menuItem && this.menuItem.parentNode) {
      this.menuItem.parentNode.removeChild(this.menuItem);
    }
  }
}

// Initialize the menu extension
const queueManagerMenuExtension = new QueueManagerMenuExtension();

// Auto-initialize when DOM is ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => {
    queueManagerMenuExtension.init();
  });
} else {
  queueManagerMenuExtension.init();
}

// Export for testing and external access
window.QueueManagerMenuExtension = queueManagerMenuExtension;

export default queueManagerMenuExtension;
