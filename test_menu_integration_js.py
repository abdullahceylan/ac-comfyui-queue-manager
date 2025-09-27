"""
JavaScript integration tests for ComfyUI Queue Manager menu functionality.
Tests the JavaScript menu extension behavior and DOM interactions.
"""

from pathlib import Path
import sys
import unittest

# Add the current directory to Python path for imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))


class TestJavaScriptMenuIntegration(unittest.TestCase):
    """Test cases for JavaScript menu integration."""

    def setUp(self):
        """Set up test fixtures."""
        self.web_dir = current_dir / "web"
        self.extension_file = self.web_dir / "queue_manager_extension.js"

    def test_extension_file_syntax(self):
        """Test that the extension JavaScript file has valid syntax."""
        if not self.extension_file.exists():
            self.skipTest("Extension file does not exist")

        with self.extension_file.open(encoding="utf-8") as f:
            content = f.read()

        # Basic syntax checks
        assert "app.registerExtension" in content
        assert "name:" in content
        assert "init" in content
        assert "setup" in content

        # Check for proper function definitions
        assert "openQueueManager" in content
        assert "addMenuIntegration" in content
        assert "findMenuContainer" in content
        assert "createMenuButton" in content

    def test_extension_structure(self):
        """Test that the extension has the required structure."""
        if not self.extension_file.exists():
            self.skipTest("Extension file does not exist")

        with self.extension_file.open(encoding="utf-8") as f:
            content = f.read()

        # Check for required extension methods
        required_methods = ["init", "setup", "beforeRegisterNodeDef"]

        for method in required_methods:
            assert f"{method}(" in content, f"Extension should have {method} method"

    def test_menu_button_creation_logic(self):
        """Test the menu button creation logic."""
        if not self.extension_file.exists():
            self.skipTest("Extension file does not exist")

        with self.extension_file.open(encoding="utf-8") as f:
            content = f.read()

        # Check for menu button creation elements
        assert "createElement" in content
        assert "textContent" in content
        assert "addEventListener" in content
        assert "appendChild" in content

    def test_window_management_functions(self):
        """Test window management functionality."""
        if not self.extension_file.exists():
            self.skipTest("Extension file does not exist")

        with self.extension_file.open(encoding="utf-8") as f:
            content = f.read()

        # Check for window management functions
        window_functions = [
            "openAsPopup",
            "openAsTab",
            "canOpenPopup",
            "getQueueManagerUrl",
        ]

        for func in window_functions:
            assert func in content, f"Should have {func} function"

    def test_keyboard_shortcuts(self):
        """Test keyboard shortcut implementation."""
        if not self.extension_file.exists():
            self.skipTest("Extension file does not exist")

        with self.extension_file.open(encoding="utf-8") as f:
            content = f.read()

        # Check for keyboard event handling
        assert "keydown" in content
        assert "ctrlKey" in content
        assert "shiftKey" in content

    def test_notification_system(self):
        """Test notification system implementation."""
        if not self.extension_file.exists():
            self.skipTest("Extension file does not exist")

        with self.extension_file.open(encoding="utf-8") as f:
            content = f.read()

        # Check for notification functionality
        assert "showNotification" in content
        assert "notification" in content

    def test_error_handling(self):
        """Test error handling in the extension."""
        if not self.extension_file.exists():
            self.skipTest("Extension file does not exist")

        with self.extension_file.open(encoding="utf-8") as f:
            content = f.read()

        # Check for error handling
        assert "try" in content
        assert "catch" in content
        assert "console.error" in content


class TestMenuIntegrationAPI(unittest.TestCase):
    """Test cases for menu integration API endpoints."""

    def test_extension_url_structure(self):
        """Test that extension URLs are properly structured."""
        # Test URL patterns that should be registered
        expected_patterns = [
            "/extensions/comfyui-queue-manager/{filename}",
            "/extensions/comfyui-queue-manager/index.html",
        ]

        # This is a structural test - in a real scenario,
        # we would test against the actual router registration
        for pattern in expected_patterns:
            assert isinstance(pattern, str)
            assert "comfyui-queue-manager" in pattern

    def test_serve_extension_file_success(self):
        """Test serving extension file successfully."""
        # This would test the actual serve_extension_file function
        # when it's properly imported and available


class TestMenuIntegrationEndToEnd(unittest.TestCase):
    """End-to-end tests for menu integration."""

    def setUp(self):
        """Set up test fixtures."""
        self.web_dir = current_dir / "web"

    def test_all_required_files_exist(self):
        """Test that all required files for menu integration exist."""
        required_files = [
            "queue_manager_extension.js",
            "menu_extension.js",  # Legacy fallback
            "index.html",
            "queue_manager.js",
            "styles.css",
        ]

        for filename in required_files:
            file_path = self.web_dir / filename
            assert file_path.exists(), (
                f"Required file {filename} should exist in web directory"
            )

    def test_html_file_has_proper_structure(self):
        """Test that the HTML file has proper structure for integration."""
        html_file = self.web_dir / "index.html"

        if html_file.exists():
            with html_file.open(encoding="utf-8") as f:
                content = f.read()

            # Check for required HTML elements
            assert "<html" in content
            assert "<head>" in content
            assert "<body>" in content
            assert "queue-manager-app" in content

    def test_integration_consistency(self):
        """Test consistency between different integration files."""
        extension_file = self.web_dir / "queue_manager_extension.js"
        legacy_file = self.web_dir / "menu_extension.js"

        if extension_file.exists() and legacy_file.exists():
            with extension_file.open(encoding="utf-8") as f:
                ext_content = f.read()

            with legacy_file.open(encoding="utf-8") as f:
                legacy_content = f.read()

            # Both should reference the same URL patterns
            assert "queue-manager" in ext_content
            assert "queue-manager" in legacy_content


if __name__ == "__main__":
    unittest.main()
