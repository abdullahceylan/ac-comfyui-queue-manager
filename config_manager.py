"""
Configuration management for the ComfyUI Queue Manager.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from interfaces import DatabaseInterface
from models import QueueConfig, QueueState

logger = logging.getLogger(__name__)


class ConfigurationManager:
    """Manages configuration persistence and queue state."""

    # Configuration keys
    QUEUE_STATE_KEY = "queue_state"
    MAX_CONCURRENT_KEY = "max_concurrent_workflows"
    AUTO_ARCHIVE_COMPLETED_KEY = "auto_archive_completed"
    AUTO_ARCHIVE_DAYS_KEY = "auto_archive_days"
    USER_PREFERENCES_KEY = "user_preferences"

    def __init__(self, database: DatabaseInterface):
        """Initialize the configuration manager.
        
        Args:
            database: Database interface for persistence
        """
        self.database = database
        self._config_cache: QueueConfig | None = None

    def get_config(self) -> QueueConfig:
        """Get the current queue configuration.
        
        Returns:
            Current queue configuration
        """
        if self._config_cache is None:
            self._load_config()
        return self._config_cache

    def update_config(self, config: QueueConfig) -> bool:
        """Update the queue configuration.
        
        Args:
            config: New configuration to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Save each configuration value
            success = True
            success &= self.database.set_config(
                self.QUEUE_STATE_KEY, 
                config.queue_state.value
            )
            success &= self.database.set_config(
                self.MAX_CONCURRENT_KEY, 
                str(config.max_concurrent_workflows)
            )
            success &= self.database.set_config(
                self.AUTO_ARCHIVE_COMPLETED_KEY, 
                json.dumps(config.auto_archive_completed)
            )
            success &= self.database.set_config(
                self.AUTO_ARCHIVE_DAYS_KEY, 
                str(config.auto_archive_days)
            )
            
            if success:
                self._config_cache = config
                logger.info("Configuration updated successfully")
            else:
                logger.error("Failed to update configuration")
                
            return success
            
        except Exception as e:
            logger.error(f"Error updating configuration: {e}")
            return False

    def get_queue_state(self) -> QueueState:
        """Get the current queue processing state.
        
        Returns:
            Current queue state (running or paused)
        """
        config = self.get_config()
        return config.queue_state

    def set_queue_state(self, state: QueueState) -> bool:
        """Set the queue processing state.
        
        Args:
            state: New queue state
            
        Returns:
            True if successful, False otherwise
        """
        try:
            success = self.database.set_config(self.QUEUE_STATE_KEY, state.value)
            if success and self._config_cache:
                self._config_cache.queue_state = state
                logger.info(f"Queue state changed to {state.value}")
            return success
        except Exception as e:
            logger.error(f"Error setting queue state: {e}")
            return False

    def pause_queue(self) -> bool:
        """Pause queue processing.
        
        Returns:
            True if successful, False otherwise
        """
        return self.set_queue_state(QueueState.PAUSED)

    def resume_queue(self) -> bool:
        """Resume queue processing.
        
        Returns:
            True if successful, False otherwise
        """
        return self.set_queue_state(QueueState.RUNNING)

    def is_queue_paused(self) -> bool:
        """Check if the queue is currently paused.
        
        Returns:
            True if queue is paused, False if running
        """
        return self.get_queue_state() == QueueState.PAUSED

    def get_max_concurrent_workflows(self) -> int:
        """Get the maximum number of concurrent workflows.
        
        Returns:
            Maximum concurrent workflows
        """
        config = self.get_config()
        return config.max_concurrent_workflows

    def set_max_concurrent_workflows(self, max_concurrent: int) -> bool:
        """Set the maximum number of concurrent workflows.
        
        Args:
            max_concurrent: Maximum number of concurrent workflows
            
        Returns:
            True if successful, False otherwise
        """
        if max_concurrent < 1:
            logger.warning("Max concurrent workflows must be at least 1")
            return False
            
        try:
            success = self.database.set_config(
                self.MAX_CONCURRENT_KEY, 
                str(max_concurrent)
            )
            if success and self._config_cache:
                self._config_cache.max_concurrent_workflows = max_concurrent
                logger.info(f"Max concurrent workflows set to {max_concurrent}")
            return success
        except Exception as e:
            logger.error(f"Error setting max concurrent workflows: {e}")
            return False

    def get_auto_archive_settings(self) -> tuple[bool, int]:
        """Get auto-archive settings.
        
        Returns:
            Tuple of (auto_archive_enabled, days_threshold)
        """
        config = self.get_config()
        return config.auto_archive_completed, config.auto_archive_days

    def set_auto_archive_settings(self, enabled: bool, days: int = 30) -> bool:
        """Set auto-archive settings.
        
        Args:
            enabled: Whether to enable auto-archiving
            days: Number of days after which to auto-archive completed items
            
        Returns:
            True if successful, False otherwise
        """
        if days < 1:
            logger.warning("Auto-archive days must be at least 1")
            return False
            
        try:
            success = True
            success &= self.database.set_config(
                self.AUTO_ARCHIVE_COMPLETED_KEY, 
                json.dumps(enabled)
            )
            success &= self.database.set_config(
                self.AUTO_ARCHIVE_DAYS_KEY, 
                str(days)
            )
            
            if success and self._config_cache:
                self._config_cache.auto_archive_completed = enabled
                self._config_cache.auto_archive_days = days
                logger.info(f"Auto-archive settings updated: enabled={enabled}, days={days}")
            return success
        except Exception as e:
            logger.error(f"Error setting auto-archive settings: {e}")
            return False

    def get_user_preferences(self) -> dict[str, Any]:
        """Get user preferences.
        
        Returns:
            Dictionary of user preferences
        """
        try:
            prefs_json = self.database.get_config(self.USER_PREFERENCES_KEY)
            if prefs_json:
                return json.loads(prefs_json)
            return {}
        except Exception as e:
            logger.error(f"Error getting user preferences: {e}")
            return {}

    def set_user_preferences(self, preferences: dict[str, Any]) -> bool:
        """Set user preferences.
        
        Args:
            preferences: Dictionary of user preferences
            
        Returns:
            True if successful, False otherwise
        """
        try:
            prefs_json = json.dumps(preferences)
            success = self.database.set_config(self.USER_PREFERENCES_KEY, prefs_json)
            if success:
                logger.debug("User preferences updated")
            return success
        except Exception as e:
            logger.error(f"Error setting user preferences: {e}")
            return False

    def get_user_preference(self, key: str, default: Any = None) -> Any:
        """Get a specific user preference.
        
        Args:
            key: Preference key
            default: Default value if key not found
            
        Returns:
            Preference value or default
        """
        preferences = self.get_user_preferences()
        return preferences.get(key, default)

    def set_user_preference(self, key: str, value: Any) -> bool:
        """Set a specific user preference.
        
        Args:
            key: Preference key
            value: Preference value
            
        Returns:
            True if successful, False otherwise
        """
        preferences = self.get_user_preferences()
        preferences[key] = value
        return self.set_user_preferences(preferences)

    def reset_to_defaults(self) -> bool:
        """Reset configuration to default values.
        
        Returns:
            True if successful, False otherwise
        """
        default_config = QueueConfig()
        return self.update_config(default_config)

    def export_config(self) -> dict[str, Any]:
        """Export configuration to a dictionary.
        
        Returns:
            Configuration dictionary
        """
        config = self.get_config()
        preferences = self.get_user_preferences()
        
        return {
            "queue_config": config.to_dict(),
            "user_preferences": preferences,
            "version": "1.0"
        }

    def import_config(self, config_data: dict[str, Any]) -> bool:
        """Import configuration from a dictionary.
        
        Args:
            config_data: Configuration dictionary
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Import queue configuration
            if "queue_config" in config_data:
                queue_config = QueueConfig.from_dict(config_data["queue_config"])
                if not self.update_config(queue_config):
                    return False
            
            # Import user preferences
            if "user_preferences" in config_data:
                if not self.set_user_preferences(config_data["user_preferences"]):
                    return False
            
            logger.info("Configuration imported successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error importing configuration: {e}")
            return False

    def _load_config(self) -> None:
        """Load configuration from database."""
        try:
            # Load queue state
            queue_state_str = self.database.get_config(self.QUEUE_STATE_KEY)
            queue_state = QueueState(queue_state_str) if queue_state_str else QueueState.RUNNING
            
            # Load max concurrent workflows
            max_concurrent_str = self.database.get_config(self.MAX_CONCURRENT_KEY)
            max_concurrent = int(max_concurrent_str) if max_concurrent_str else 1
            
            # Load auto-archive settings
            auto_archive_str = self.database.get_config(self.AUTO_ARCHIVE_COMPLETED_KEY)
            auto_archive = json.loads(auto_archive_str) if auto_archive_str else False
            
            auto_archive_days_str = self.database.get_config(self.AUTO_ARCHIVE_DAYS_KEY)
            auto_archive_days = int(auto_archive_days_str) if auto_archive_days_str else 30
            
            # Create configuration object
            self._config_cache = QueueConfig(
                queue_state=queue_state,
                max_concurrent_workflows=max_concurrent,
                auto_archive_completed=auto_archive,
                auto_archive_days=auto_archive_days
            )
            
            logger.debug("Configuration loaded from database")
            
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            # Fall back to defaults
            self._config_cache = QueueConfig()

    def invalidate_cache(self) -> None:
        """Invalidate the configuration cache to force reload."""
        self._config_cache = None