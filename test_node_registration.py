"""
Integration tests for ComfyUI custom node registration.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add the current directory to Python path
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))


class TestNodeRegistration(unittest.TestCase):
    """Test ComfyUI custom node registration."""

    def test_node_class_mappings_exist(self):
        """Test that NODE_CLASS_MAPPINGS is properly defined."""
        import __init__ as init_module
        NODE_CLASS_MAPPINGS = init_module.NODE_CLASS_MAPPINGS
        
        self.assertIsInstance(NODE_CLASS_MAPPINGS, dict)
        self.assertIn("QueueManagerNode", NODE_CLASS_MAPPINGS)
        
        # Verify the class is importable
        node_class = NODE_CLASS_MAPPINGS["QueueManagerNode"]
        self.assertTrue(hasattr(node_class, "INPUT_TYPES"))
        self.assertTrue(hasattr(node_class, "process"))

    def test_node_display_name_mappings_exist(self):
        """Test that NODE_DISPLAY_NAME_MAPPINGS is properly defined."""
        import __init__ as init_module
        NODE_DISPLAY_NAME_MAPPINGS = init_module.NODE_DISPLAY_NAME_MAPPINGS
        
        self.assertIsInstance(NODE_DISPLAY_NAME_MAPPINGS, dict)
        self.assertIn("QueueManagerNode", NODE_DISPLAY_NAME_MAPPINGS)
        self.assertEqual(NODE_DISPLAY_NAME_MAPPINGS["QueueManagerNode"], "Queue Manager")

    def test_web_directory_defined(self):
        """Test that WEB_DIRECTORY is properly defined."""
        import __init__ as init_module
        WEB_DIRECTORY = init_module.WEB_DIRECTORY
        
        self.assertIsInstance(WEB_DIRECTORY, str)
        self.assertEqual(WEB_DIRECTORY, "./web")

    def test_metadata_defined(self):
        """Test that extension metadata is properly defined."""
        import __init__ as init_module
        __version__ = init_module.__version__
        __author__ = init_module.__author__
        __description__ = init_module.__description__
        
        self.assertIsInstance(__version__, str)
        self.assertIsInstance(__author__, str)
        self.assertIsInstance(__description__, str)
        
        # Verify version format
        version_parts = __version__.split(".")
        self.assertEqual(len(version_parts), 3)
        for part in version_parts:
            self.assertTrue(part.isdigit())

    def test_initialization_success(self):
        """Test successful initialization of queue manager system."""
        # Test that the initialization function exists and can be called
        import __init__ as init_module
        
        # The function should exist
        self.assertTrue(hasattr(init_module, 'initialize_queue_manager'))
        self.assertTrue(callable(init_module.initialize_queue_manager))
        
        # Test that it returns a boolean (success or failure)
        result = init_module.initialize_queue_manager()
        self.assertIsInstance(result, bool)

    def test_node_class_structure(self):
        """Test that the QueueManagerNode class has the required structure."""
        from queue_manager_node import QueueManagerNode
        
        # Test class methods exist
        self.assertTrue(hasattr(QueueManagerNode, "INPUT_TYPES"))
        self.assertTrue(hasattr(QueueManagerNode, "IS_CHANGED"))
        self.assertTrue(hasattr(QueueManagerNode, "VALIDATE_INPUTS"))
        
        # Test class attributes exist
        self.assertTrue(hasattr(QueueManagerNode, "RETURN_TYPES"))
        self.assertTrue(hasattr(QueueManagerNode, "RETURN_NAMES"))
        self.assertTrue(hasattr(QueueManagerNode, "FUNCTION"))
        self.assertTrue(hasattr(QueueManagerNode, "CATEGORY"))
        self.assertTrue(hasattr(QueueManagerNode, "DESCRIPTION"))
        
        # Test attribute values
        self.assertEqual(QueueManagerNode.FUNCTION, "process")
        self.assertEqual(QueueManagerNode.CATEGORY, "Queue Management")
        self.assertIsInstance(QueueManagerNode.RETURN_TYPES, tuple)
        self.assertIsInstance(QueueManagerNode.RETURN_NAMES, tuple)

    def test_input_types_structure(self):
        """Test that INPUT_TYPES returns the correct structure."""
        from queue_manager_node import QueueManagerNode
        
        input_types = QueueManagerNode.INPUT_TYPES()
        
        self.assertIsInstance(input_types, dict)
        self.assertIn("required", input_types)
        self.assertIn("optional", input_types)
        
        # Test optional inputs
        optional = input_types["optional"]
        self.assertIn("workflow_name", optional)
        self.assertIn("auto_queue", optional)
        self.assertIn("priority", optional)
        self.assertIn("tags", optional)
        
        # Test input type definitions
        self.assertEqual(optional["workflow_name"][0], "STRING")
        self.assertEqual(optional["auto_queue"][0], "BOOLEAN")
        self.assertEqual(optional["priority"][0], "INT")

    def test_node_instantiation(self):
        """Test that the node can be instantiated."""
        from queue_manager_node import QueueManagerNode
        
        node = QueueManagerNode()
        self.assertIsInstance(node, QueueManagerNode)
        self.assertIsNone(node._queue_service)

    def test_validate_inputs(self):
        """Test input validation."""
        from queue_manager_node import QueueManagerNode
        
        # Test valid inputs
        self.assertTrue(QueueManagerNode.VALIDATE_INPUTS(
            workflow_name="Test Workflow",
            auto_queue=True,
            priority=5,
            tags="tag1,tag2"
        ))
        
        # Test invalid priority
        self.assertFalse(QueueManagerNode.VALIDATE_INPUTS(
            priority=15  # Out of range
        ))
        
        self.assertFalse(QueueManagerNode.VALIDATE_INPUTS(
            priority=-15  # Out of range
        ))
        
        # Test invalid workflow name type
        self.assertFalse(QueueManagerNode.VALIDATE_INPUTS(
            workflow_name=123  # Should be string
        ))

    def test_is_changed_returns_nan(self):
        """Test that IS_CHANGED returns NaN to always execute."""
        from queue_manager_node import QueueManagerNode
        import math
        
        result = QueueManagerNode.IS_CHANGED()
        self.assertTrue(math.isnan(result))

    def test_get_node_info(self):
        """Test that get_node_info returns proper metadata."""
        from queue_manager_node import QueueManagerNode
        
        info = QueueManagerNode.get_node_info()
        
        self.assertIsInstance(info, dict)
        self.assertEqual(info["name"], "QueueManagerNode")
        self.assertEqual(info["display_name"], "Queue Manager")
        self.assertEqual(info["category"], "Queue Management")
        self.assertIn("description", info)
        self.assertIn("version", info)
        self.assertIn("author", info)
        self.assertIn("input_types", info)
        self.assertIn("return_types", info)
        self.assertIn("return_names", info)


class TestNodeProcessing(unittest.TestCase):
    """Test node processing functionality."""

    def setUp(self):
        """Set up test fixtures."""
        from queue_manager_node import QueueManagerNode
        self.node = QueueManagerNode()

    def test_process_with_auto_queue_disabled(self):
        """Test processing with auto_queue disabled."""
        result = self.node.process(
            workflow_name="Test Workflow",
            auto_queue=False
        )
        
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        
        queue_item_id, queued_successfully = result
        self.assertIsInstance(queue_item_id, str)
        self.assertFalse(queued_successfully)

    @patch('queue_service.QueueService')
    @patch('database.SQLiteDatabase')
    def test_process_with_auto_queue_enabled(self, mock_database, mock_queue_service):
        """Test processing with auto_queue enabled."""
        # Mock successful queue service
        mock_db_instance = MagicMock()
        mock_database.return_value = mock_db_instance
        
        mock_qs_instance = MagicMock()
        mock_qs_instance.add_workflow.return_value = "test-queue-id"
        mock_queue_service.return_value = mock_qs_instance
        
        # Set the queue service directly
        self.node._queue_service = mock_qs_instance
        
        result = self.node.process(
            workflow_name="Test Workflow",
            auto_queue=True,
            priority=5,
            tags="tag1,tag2"
        )
        
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        
        queue_item_id, queued_successfully = result
        self.assertEqual(queue_item_id, "test-queue-id")
        self.assertTrue(queued_successfully)
        
        # Verify queue service was called with correct data
        mock_qs_instance.add_workflow.assert_called_once()
        call_args = mock_qs_instance.add_workflow.call_args[0][0]
        self.assertEqual(call_args["name"], "Test Workflow")
        self.assertEqual(call_args["priority"], 5)
        self.assertEqual(call_args["tags"], ["tag1", "tag2"])

    def test_get_queue_status_without_service(self):
        """Test getting queue status when service is not available."""
        # Mock the queue_service property to return None
        with patch.object(type(self.node), 'queue_service', new_callable=lambda: property(lambda self: None)):
            result = self.node.get_queue_status()
            
            self.assertIsInstance(result, dict)
            self.assertIn("error", result)
            self.assertEqual(result["error"], "Queue service not available")


if __name__ == "__main__":
    unittest.main()