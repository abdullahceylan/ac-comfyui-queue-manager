"""
Unit tests for the configuration manager.
"""

import json
import tempfile
import unittest
from pathlib import Path

from config_manager import ConfigurationManager
from database import SQLiteDatabase
from models import QueueConfig, QueueState


class TestConfigurationManager(unittest.TestCase):
    """Test cases for ConfigurationManager class."""

    def setUp(self):
        """Set up test database and configuration manager."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_config.db"
        self.db = SQLiteDatabase(self.db_path)
        self.assertTrue(self.db.initialize())
        self.config_manager = ConfigurationManager(self.db)

    def tearDown(self):
        """Clean up test database."""
        self.db.close()
        if self.db_path.exists():
            self.db_path.unlink()

    def test_get_default_config(self):
        """Test getting default configuration."""
        config = self.config_manager.get_config()
        
        self.assertEqual(config.queue_state, QueueState.RUNNING)
        self.assertEqual(config.max_concurrent_workflows, 1)
        self.assertFalse(config.auto_archive_completed)
        self.assertEqual(config.auto_archive_days, 30)

    def test_update_config(self):
        """Test updating configuration."""
        new_config = QueueConfig(
            queue_state=QueueState.PAUSED,
            max_concurrent_workflows=3,
            auto_archive_completed=True,
            auto_archive_days=7
        )
        
        self.assertTrue(self.config_manager.update_config(new_config))
        
        # Verify configuration was updated
        retrieved_config = self.config_manager.get_config()
        self.assertEqual(retrieved_config.queue_state, QueueState.PAUSED)
        self.assertEqual(retrieved_config.max_concurrent_workflows, 3)
        self.assertTrue(retrieved_config.auto_archive_completed)
        self.assertEqual(retrieved_config.auto_archive_days, 7)

    def test_queue_state_operations(self):
        """Test queue state management."""
        # Initially running
        self.assertEqual(self.config_manager.get_queue_state(), QueueState.RUNNING)
        self.assertFalse(self.config_manager.is_queue_paused())
        
        # Pause queue
        self.assertTrue(self.config_manager.pause_queue())
        self.assertEqual(self.config_manager.get_queue_state(), QueueState.PAUSED)
        self.assertTrue(self.config_manager.is_queue_paused())
        
        # Resume queue
        self.assertTrue(self.config_manager.resume_queue())
        self.assertEqual(self.config_manager.get_queue_state(), QueueState.RUNNING)
        self.assertFalse(self.config_manager.is_queue_paused())

    def test_max_concurrent_workflows(self):
        """Test max concurrent workflows setting."""
        # Default value
        self.assertEqual(self.config_manager.get_max_concurrent_workflows(), 1)
        
        # Set new value
        self.assertTrue(self.config_manager.set_max_concurrent_workflows(5))
        self.assertEqual(self.config_manager.get_max_concurrent_workflows(), 5)
        
        # Test invalid value
        self.assertFalse(self.config_manager.set_max_concurrent_workflows(0))
        self.assertFalse(self.config_manager.set_max_concurrent_workflows(-1))
        # Value should remain unchanged
        self.assertEqual(self.config_manager.get_max_concurrent_workflows(), 5)

    def test_auto_archive_settings(self):
        """Test auto-archive settings."""
        # Default values
        enabled, days = self.config_manager.get_auto_archive_settings()
        self.assertFalse(enabled)
        self.assertEqual(days, 30)
        
        # Set new values
        self.assertTrue(self.config_manager.set_auto_archive_settings(True, 14))
        enabled, days = self.config_manager.get_auto_archive_settings()
        self.assertTrue(enabled)
        self.assertEqual(days, 14)
        
        # Test invalid days value
        self.assertFalse(self.config_manager.set_auto_archive_settings(True, 0))
        self.assertFalse(self.config_manager.set_auto_archive_settings(True, -1))
        # Values should remain unchanged
        enabled, days = self.config_manager.get_auto_archive_settings()
        self.assertTrue(enabled)
        self.assertEqual(days, 14)

    def test_user_preferences(self):
        """Test user preferences management."""
        # Initially empty
        prefs = self.config_manager.get_user_preferences()
        self.assertEqual(prefs, {})
        
        # Set preferences
        test_prefs = {
            "theme": "dark",
            "auto_refresh": True,
            "refresh_interval": 5000,
            "columns": ["name", "status", "created_at"]
        }
        self.assertTrue(self.config_manager.set_user_preferences(test_prefs))
        
        # Verify preferences
        retrieved_prefs = self.config_manager.get_user_preferences()
        self.assertEqual(retrieved_prefs, test_prefs)

    def test_individual_user_preference(self):
        """Test individual user preference operations."""
        # Test getting non-existent preference with default
        value = self.config_manager.get_user_preference("theme", "light")
        self.assertEqual(value, "light")
        
        # Set individual preference
        self.assertTrue(self.config_manager.set_user_preference("theme", "dark"))
        value = self.config_manager.get_user_preference("theme")
        self.assertEqual(value, "dark")
        
        # Set another preference
        self.assertTrue(self.config_manager.set_user_preference("auto_refresh", True))
        
        # Verify both preferences exist
        prefs = self.config_manager.get_user_preferences()
        self.assertEqual(prefs["theme"], "dark")
        self.assertTrue(prefs["auto_refresh"])

    def test_reset_to_defaults(self):
        """Test resetting configuration to defaults."""
        # Modify configuration
        self.config_manager.pause_queue()
        self.config_manager.set_max_concurrent_workflows(10)
        self.config_manager.set_auto_archive_settings(True, 7)
        
        # Reset to defaults
        self.assertTrue(self.config_manager.reset_to_defaults())
        
        # Verify defaults
        config = self.config_manager.get_config()
        self.assertEqual(config.queue_state, QueueState.RUNNING)
        self.assertEqual(config.max_concurrent_workflows, 1)
        self.assertFalse(config.auto_archive_completed)
        self.assertEqual(config.auto_archive_days, 30)

    def test_export_config(self):
        """Test configuration export."""
        # Set some configuration
        self.config_manager.pause_queue()
        self.config_manager.set_max_concurrent_workflows(3)
        self.config_manager.set_user_preference("theme", "dark")
        
        # Export configuration
        exported = self.config_manager.export_config()
        
        # Verify export structure
        self.assertIn("queue_config", exported)
        self.assertIn("user_preferences", exported)
        self.assertIn("version", exported)
        
        # Verify queue config
        queue_config = exported["queue_config"]
        self.assertEqual(queue_config["queue_state"], "paused")
        self.assertEqual(queue_config["max_concurrent_workflows"], 3)
        
        # Verify user preferences
        user_prefs = exported["user_preferences"]
        self.assertEqual(user_prefs["theme"], "dark")

    def test_import_config(self):
        """Test configuration import."""
        # Prepare import data
        import_data = {
            "queue_config": {
                "queue_state": "paused",
                "max_concurrent_workflows": 5,
                "auto_archive_completed": True,
                "auto_archive_days": 14
            },
            "user_preferences": {
                "theme": "dark",
                "auto_refresh": False
            },
            "version": "1.0"
        }
        
        # Import configuration
        self.assertTrue(self.config_manager.import_config(import_data))
        
        # Verify imported configuration
        config = self.config_manager.get_config()
        self.assertEqual(config.queue_state, QueueState.PAUSED)
        self.assertEqual(config.max_concurrent_workflows, 5)
        self.assertTrue(config.auto_archive_completed)
        self.assertEqual(config.auto_archive_days, 14)
        
        # Verify imported preferences
        prefs = self.config_manager.get_user_preferences()
        self.assertEqual(prefs["theme"], "dark")
        self.assertFalse(prefs["auto_refresh"])

    def test_config_persistence(self):
        """Test that configuration persists across manager instances."""
        # Set configuration
        self.config_manager.pause_queue()
        self.config_manager.set_max_concurrent_workflows(7)
        self.config_manager.set_user_preference("theme", "dark")
        
        # Create new configuration manager with same database
        new_config_manager = ConfigurationManager(self.db)
        
        # Verify configuration persisted
        config = new_config_manager.get_config()
        self.assertEqual(config.queue_state, QueueState.PAUSED)
        self.assertEqual(config.max_concurrent_workflows, 7)
        
        prefs = new_config_manager.get_user_preferences()
        self.assertEqual(prefs["theme"], "dark")

    def test_cache_invalidation(self):
        """Test configuration cache invalidation."""
        # Load initial config
        config1 = self.config_manager.get_config()
        self.assertEqual(config1.queue_state, QueueState.RUNNING)
        
        # Modify database directly (bypassing cache)
        self.db.set_config("queue_state", "paused")
        
        # Config should still be cached
        config2 = self.config_manager.get_config()
        self.assertEqual(config2.queue_state, QueueState.RUNNING)
        
        # Invalidate cache
        self.config_manager.invalidate_cache()
        
        # Now should get updated config
        config3 = self.config_manager.get_config()
        self.assertEqual(config3.queue_state, QueueState.PAUSED)

    def test_invalid_json_handling(self):
        """Test handling of invalid JSON in preferences."""
        # Set invalid JSON directly in database
        self.db.set_config("user_preferences", "invalid json {")
        
        # Should return empty dict and not crash
        prefs = self.config_manager.get_user_preferences()
        self.assertEqual(prefs, {})

    def test_partial_import(self):
        """Test importing partial configuration."""
        # Import only queue config
        import_data = {
            "queue_config": {
                "queue_state": "paused",
                "max_concurrent_workflows": 2
            }
        }
        
        self.assertTrue(self.config_manager.import_config(import_data))
        
        config = self.config_manager.get_config()
        self.assertEqual(config.queue_state, QueueState.PAUSED)
        self.assertEqual(config.max_concurrent_workflows, 2)
        
        # Import only user preferences
        import_data = {
            "user_preferences": {
                "theme": "light"
            }
        }
        
        self.assertTrue(self.config_manager.import_config(import_data))
        
        prefs = self.config_manager.get_user_preferences()
        self.assertEqual(prefs["theme"], "light")


if __name__ == "__main__":
    unittest.main()