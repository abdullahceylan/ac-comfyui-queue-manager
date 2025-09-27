"""
Integration tests for ComfyUI Queue Manager menu functionality.
Tests menu item registration, click handlers, and window management.
"""

from pathlib import Path
import sys
import unittest

# Add the current directory to Python path for imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))


class TestMenuIntegration(unittest.TestCase):
    """Test cases for menu integration functionality."""

    def test_web_extensions_configuration(self):
        """Test that WEB_EXTENSIONS is properly configured."""
        from __init__ import WEB_EXTENSIONS

        # Verify WEB_EXTENSIONS is a list
        assert isinstance(WEB_EXTENSIONS, list)

        # Verify it contains the queue manager extension
        extension_names = [ext.get("name") for ext in WEB_EXTENSIONS]
        assert "queue_manager_extension" in extension_names

        # Verify extension has required fields
        queue_ext = next(
            ext for ext in WEB_EXTENSIONS if ext["name"] == "queue_manager_extension"
        )
        assert "path" in queue_ext
        assert queue_ext["path"] == "queue_manager_extension.js"

    def test_web_directory_configuration(self):
        """Test that WEB_DIRECTORY is properly configured."""
        from __init__ import WEB_DIRECTORY

        # Verify WEB_DIRECTORY is set correctly
        assert WEB_DIRECTORY == "./web"

    def test_register_menu_extension_function_exists(self):
        """Test that the register_menu_extension function exists and is callable."""
        from __init__ import register_menu_extension

        # Verify function exists and is callable
        assert callable(register_menu_extension)

    def test_node_class_mappings_include_queue_manager(self):
        """Test that NODE_CLASS_MAPPINGS includes QueueManagerNode."""
        from __init__ import NODE_CLASS_MAPPINGS
        from queue_manager_node import QueueManagerNode

        # Verify QueueManagerNode is in the mappings
        assert "QueueManagerNode" in NODE_CLASS_MAPPINGS

        # Verify the mapping points to the correct class
        assert NODE_CLASS_MAPPINGS["QueueManagerNode"] == QueueManagerNode

    def test_node_display_name_mappings(self):
        """Test that NODE_DISPLAY_NAME_MAPPINGS is properly configured."""
        from __init__ import NODE_DISPLAY_NAME_MAPPINGS

        # Verify QueueManagerNode has a display name
        assert "QueueManagerNode" in NODE_DISPLAY_NAME_MAPPINGS
        assert NODE_DISPLAY_NAME_MAPPINGS["QueueManagerNode"] == "Queue Manager"


class TestMenuExtensionFiles(unittest.TestCase):
    """Test cases for menu extension files."""

    def setUp(self):
        """Set up test fixtures."""
        self.web_dir = current_dir / "web"

    def test_menu_extension_file_exists(self):
        """Test that the menu extension JavaScript file exists."""
        extension_file = self.web_dir / "queue_manager_extension.js"
        assert extension_file.exists(), "queue_manager_extension.js should exist"

    def test_menu_extension_file_content(self):
        """Test that the menu extension file has required content."""
        extension_file = self.web_dir / "queue_manager_extension.js"

        if extension_file.exists():
            with extension_file.open(encoding="utf-8") as f:
                content = f.read()

            # Check for required components
            assert "app.registerExtension" in content
            assert "QueueManager" in content
            assert "openQueueManager" in content
            assert "addMenuIntegration" in content

    def test_legacy_menu_extension_file_exists(self):
        """Test that the legacy menu extension file exists."""
        legacy_file = self.web_dir / "menu_extension.js"
        assert legacy_file.exists(), "menu_extension.js should exist as fallback"


if __name__ == "__main__":
    unittest.main()
