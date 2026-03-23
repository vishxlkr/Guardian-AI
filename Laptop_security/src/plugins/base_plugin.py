"""
Base Plugin Class - Abstract base for all security plugins
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class BasePlugin(ABC):
    """Base class for all security system plugins"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize plugin with configuration
        
        Args:
            config: Plugin-specific configuration dictionary
        """
        self.config = config
        self.enabled = config.get('enabled', True)
        self.name = self.__class__.__name__
        self.logger = logging.getLogger(f"plugin.{self.name}")
        
    @abstractmethod
    def on_intruder_detected(self, image_path: str, timestamp: str):
        """
        Called when an intruder is detected
        
        Args:
            image_path: Path to the captured intruder image
            timestamp: ISO format timestamp of the event
        """
        pass
    
    @abstractmethod
    def on_unauthorized_access(self, face_data: Dict[str, Any]):
        """
        Called when unauthorized face is detected on screen
        
        Args:
            face_data: Dictionary containing:
                - name: Face identification (usually "Unknown")
                - location: Tuple (top, right, bottom, left)
                - timestamp: Event timestamp
                - action_taken: What action was taken (blur, lock, etc.)
        """
        pass
    
    def on_system_event(self, event_type: str, data: Dict[str, Any]):
        """
        Called for generic system events
        
        Args:
            event_type: Type of event (login, logout, lock, etc.)
            data: Event-specific data
        """
        # Default implementation - override in subclasses if needed
        self.logger.debug(f"System event: {event_type}")
    
    def initialize(self):
        """
        Initialize plugin resources
        Called after plugin is instantiated
        """
        self.logger.info(f"Plugin {self.name} initialized")
    
    def cleanup(self):
        """
        Cleanup plugin resources
        Called before plugin is destroyed
        """
        self.logger.info(f"Plugin {self.name} cleaned up")
    
    def get_info(self) -> Dict[str, Any]:
        """
        Get plugin information
        
        Returns:
            Dictionary with plugin details
        """
        return {
            'name': self.name,
            'enabled': self.enabled,
            'version': getattr(self, 'VERSION', '1.0.0'),
            'description': self.__class__.__doc__ or 'No description'
        }
    
    def is_enabled(self) -> bool:
        """Check if plugin is enabled"""
        return self.enabled
    
    def enable(self):
        """Enable the plugin"""
        self.enabled = True
        self.logger.info(f"Plugin {self.name} enabled")
    
    def disable(self):
        """Disable the plugin"""
        self.enabled = False
        self.logger.info(f"Plugin {self.name} disabled")
    
    def reload_config(self, new_config: Dict[str, Any]):
        """
        Reload plugin configuration
        
        Args:
            new_config: New configuration dictionary
        """
        self.config = new_config
        self.enabled = new_config.get('enabled', True)
        self.logger.info(f"Plugin {self.name} configuration reloaded")
    
    def _check_enabled(func):
        """Decorator to check if plugin is enabled before executing"""
        def wrapper(self, *args, **kwargs):
            if not self.enabled:
                self.logger.debug(f"Plugin {self.name} is disabled, skipping {func.__name__}")
                return None
            return func(self, *args, **kwargs)
        return wrapper