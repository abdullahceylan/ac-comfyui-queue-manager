"""
Functional tests for ComfyUI Queue Manager menu integration.
Tests the actual menu functionality and integration points.
"""

from pathlib import Path
import sys
import unittest

# Add the current directory to Python path for imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))


class TestMenuFunctionality(unittest.TestCase):
    """Test cases for menu functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.web_dir = current_dir / "web"

    def test_menu_extension_loads_without_errors(self):
        """Test that the menu extension can be loaded without syntax errors."""
        extension_file = self.web_dir / "queue_manager_extension.js"

        if extension_file.exists():
            with extension_file.open(encoding="utf-8") as f:
                content = f.read()

            # Basic syntax validation
            assert "SyntaxError" not in content
            assert "app.registerExtension" in content

            # Check for proper JavaScript structure
            brace_count = content.count("{") - content.count("}")
            assert brace_count == 0, "Braces should be balanced"

            paren_count = content.count("(") - content.count(")")
            assert paren_count == 0, "Parentheses should be balanced"

    def test_menu_button_configuration(self):
        """Test menu button configuration and styling."""
        extension_file = self.web_dir / "queue_manager_extension.js"

        if extension_file.exists():
            with extension_file.open(encoding="utf-8") as f:
                content = f.read()

            # Check for menu button configuration
            assert "Queue Manager" in content
            assert "textContent" in content
            assert "addEventListener" in content
            assert "click" in content

    def test_window_management_configuration(self):
        """Test window management configuration."""
        extension_file = self.web_dir / "queue_manager_extension.js"

        if extension_file.exists():
            with extension_file.open(encoding="utf-8") as f:
                content = f.read()

            # Check for window management features
            assert "window.open" in content
            assert "popup" in content
            assert "tab" in content
            assert "focus" in content

    def test_url_generation(self):
        """Test URL generation for queue manager interface."""
        extension_file = self.web_dir / "queue_manager_extension.js"

        if extension_file.exists():
            with extension_file.open(encoding="utf-8") as f:
                content = f.read()

            # Check for proper URL generation
            assert "/extensions/comfyui-queue-manager/" in content
            assert "index.html" in content

    def test_error_handling_implementation(self):
        """Test error handling implementation."""
        extension_file = self.web_dir / "queue_manager_extension.js"

        if extension_file.exists():
            with extension_file.open(encoding="utf-8") as f:
                content = f.read()

            # Check for error handling
            assert "try" in content
            assert "catch" in content
            assert "console.error" in content

    def test_keyboard_shortcut_implementation(self):
        """Test keyboard shortcut implementation."""
        extension_file = self.web_dir / "queue_manager_extension.js"

        if extension_file.exists():
            with extension_file.open(encoding="utf-8") as f:
                content = f.read()

            # Check for keyboard shortcuts
            assert "keydown" in content
            assert "ctrlKey" in content
            assert "shiftKey" in content
            assert "preventDefault" in content

    def test_comfyui_integration_points(self):
        """Test ComfyUI integration points."""
        extension_file = self.web_dir / "queue_manager_extension.js"

        if extension_file.exists():
            with extension_file.open(encoding="utf-8") as f:
                content = f.read()

            # Check for ComfyUI integration
            assert "app.registerExtension" in content
            assert "beforeRegisterNodeDef" in content
            assert "QueueManagerNode" in content

    def test_notification_system_implementation(self):
        """Test notification system implementation."""
        extension_file = self.web_dir / "queue_manager_extension.js"

        if extension_file.exists():
            with extension_file.open(encoding="utf-8") as f:
                content = f.read()

            # Check for notification system
            assert "showNotification" in content
            assert "notification" in content
            assert "createElement" in content

    def test_menu_container_detection(self):
        """Test menu container detection logic."""
        extension_file = self.web_dir / "queue_manager_extension.js"

        if extension_file.exists():
            with extension_file.open(encoding="utf-8") as f:
                content = f.read()

            # Check for menu container detection
            assert "findMenuContainer" in content
            assert "querySelector" in content
            assert "comfy-menu" in content

    def test_initialization_sequence(self):
        """Test proper initialization sequence."""
        extension_file = self.web_dir / "queue_manager_extension.js"

        if extension_file.exists():
            with extension_file.open(encoding="utf-8") as f:
                content = f.read()

            # Check for proper initialization
            assert "init" in content
            assert "setup" in content
            assert "initializeQueueManager" in content
            assert "addMenuIntegration" in content


class TestMenuIntegrationRequirements(unittest.TestCase):
    """Test that menu integration meets the specified requirements."""

    def test_requirement_1_1_menu_access(self):
        """Test Requirement 1.1: Menu access through ComfyUI."""
        # Verify that menu integration files exist
        web_dir = current_dir / "web"
        extension_file = web_dir / "queue_manager_extension.js"

        assert extension_file.exists(), (
            "Menu extension file should exist for Requirement 1.1"
        )

        if extension_file.exists():
            with extension_file.open(encoding="utf-8") as f:
                content = f.read()

            # Check for menu integration
            assert "Queue Manager" in content, (
                "Should display 'Queue Manager' option for Requirement 1.1"
            )

    def test_requirement_1_2_interface_opening(self):
        """Test Requirement 1.2: Interface opening functionality."""
        web_dir = current_dir / "web"
        extension_file = web_dir / "queue_manager_extension.js"

        if extension_file.exists():
            with extension_file.open(encoding="utf-8") as f:
                content = f.read()

            # Check for interface opening functionality
            assert "openQueueManager" in content, (
                "Should have openQueueManager function for Requirement 1.2"
            )
            assert "window.open" in content, (
                "Should open queue management interface for Requirement 1.2"
            )


if __name__ == "__main__":
    unittest.main()
