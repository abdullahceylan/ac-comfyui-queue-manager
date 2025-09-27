"""
Simple integration tests for ComfyUI Queue Manager menu functionality.
Tests that don't rely on complex imports.
"""

import sys
import unittest
from pathlib import Path

# Add the current directory to Python path for imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))


class TestMenuIntegrationSimple(unittest.TestCase):
    """Simple test cases for menu integration functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.web_dir = current_dir / "web"
        self.init_file = current_dir / "__init__.py"

    def test_init_file_exists(self):
        """Test that __init__.py exists."""
        assert self.init_file.exists(), "__init__.py should exist"

    def test_init_file_has_node_mappings(self):
        """Test that __init__.py contains node mappings."""
        if self.init_file.exists():
            with self.init_file.open(encoding="utf-8") as f:
                content = f.read()

            assert "NODE_CLASS_MAPPINGS" in content
            assert "NODE_DISPLAY_NAME_MAPPINGS" in content
            assert "QueueManagerNode" in content

    def test_init_file_has_web_configuration(self):
        """Test that __init__.py contains web configuration."""
        if self.init_file.exists():
            with self.init_file.open(encoding="utf-8") as f:
                content = f.read()

            assert "WEB_DIRECTORY" in content
            assert "WEB_EXTENSIONS" in content
            assert "./web" in content

    def test_init_file_has_menu_extension_function(self):
        """Test that __init__.py contains menu extension function."""
        if self.init_file.exists():
            with self.init_file.open(encoding="utf-8") as f:
                content = f.read()

            assert "register_menu_extension" in content
            assert "def register_menu_extension" in content

    def test_web_extension_files_exist(self):
        """Test that web extension files exist."""
        required_files = [
            "queue_manager_menu.js",
            "index.html",
            "queue_manager.js",
            "styles.css",
        ]

        for filename in required_files:
            file_path = self.web_dir / filename
            assert file_path.exists(), f"Required file {filename} should exist"

    def test_extension_file_has_comfyui_integration(self):
        """Test that extension file has ComfyUI integration."""
        extension_file = self.web_dir / "queue_manager_menu.js"

        if extension_file.exists():
            with extension_file.open(encoding="utf-8") as f:
                content = f.read()

            assert "app.registerExtension" in content
            assert "QueueManager" in content
            assert "openQueueManager" in content

    def test_extension_file_has_menu_functionality(self):
        """Test that extension file has menu functionality."""
        extension_file = self.web_dir / "queue_manager_menu.js"

        if extension_file.exists():
            with extension_file.open(encoding="utf-8") as f:
                content = f.read()

            assert "addMenuIntegration" in content
            assert "createMenuButton" in content
            assert "findMenuContainer" in content

    def test_extension_file_has_window_management(self):
        """Test that extension file has window management."""
        extension_file = self.web_dir / "queue_manager_menu.js"

        if extension_file.exists():
            with extension_file.open(encoding="utf-8") as f:
                content = f.read()

            assert "window.open" in content
            assert "openAsPopup" in content
            assert "openAsTab" in content

    def test_requirements_coverage(self):
        """Test that requirements 1.1 and 1.2 are covered."""
        extension_file = self.web_dir / "queue_manager_menu.js"

        if extension_file.exists():
            with extension_file.open(encoding="utf-8") as f:
                content = f.read()

            # Requirement 1.1: Menu access
            assert "Queue Manager" in content

            # Requirement 1.2: Interface opening
            assert "openQueueManager" in content
            assert "window.open" in content

    def test_error_handling_present(self):
        """Test that error handling is present."""
        extension_file = self.web_dir / "queue_manager_menu.js"

        if extension_file.exists():
            with extension_file.open(encoding="utf-8") as f:
                content = f.read()

            assert "try" in content
            assert "catch" in content
            assert "console.error" in content


if __name__ == "__main__":
    unittest.main()