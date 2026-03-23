"""
Plugin Manager - Dynamic plugin loading and management system
"""

import importlib
import inspect
import sys
from pathlib import Path
from typing import Dict, List, Type, Any
import logging
import traceback

logger = logging.getLogger(__name__)

class PluginManager:
    """Manages loading and execution of plugins"""
    
    def __init__(self, config_manager):
        self.config = config_manager
        self.plugins: Dict[str, Any] = {}
        self.plugin_dir = Path("src/plugins")
        self.enabled = self.config.get('plugins.enabled', True)
        
        # Ensure plugin directory exists
        self.plugin_dir.mkdir(parents=True, exist_ok=True)
        
        # Create __init__.py if it doesn't exist
        init_file = self.plugin_dir / "__init__.py"
        if not init_file.exists():
            init_file.write_text("")
    
    def load_plugins(self):
        """Dynamically load all plugins from the plugins directory"""
        if not self.enabled:
            logger.info("Plugin system is disabled")
            return
        
        logger.info("Loading plugins...")
        
        # Add plugin directory to Python path
        plugin_path = str(self.plugin_dir.parent.parent)
        if plugin_path not in sys.path:
            sys.path.insert(0, plugin_path)
        
        # Find all plugin files
        plugin_files = [f for f in self.plugin_dir.glob("*.py") 
                       if not f.name.startswith("_") and f.name != "base_plugin.py"]
        
        for plugin_file in plugin_files:
            self._load_plugin_file(plugin_file)
        
        logger.info(f"Loaded {len(self.plugins)} plugins")
    
    def _load_plugin_file(self, plugin_file: Path):
        """Load a single plugin file"""
        try:
            # Import module
            module_name = f"src.plugins.{plugin_file.stem}"
            
            # Reload if already imported (for development)
            if module_name in sys.modules:
                module = importlib.reload(sys.modules[module_name])
            else:
                module = importlib.import_module(module_name)
            
            # Find plugin classes
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    name not in ['BasePlugin', 'ABC'] and
                    hasattr(obj, '__bases__') and
                    self._is_plugin_class(obj)):
                    
                    # Get plugin configuration
                    plugin_config = self.config.get(f'plugins.{name}', {})
                    
                    # Check if plugin is enabled
                    if not plugin_config.get('enabled', True):
                        logger.info(f"Plugin {name} is disabled")
                        continue
                    
                    # Instantiate plugin
                    try:
                        plugin_instance = obj(plugin_config)
                        plugin_instance.initialize()
                        self.plugins[name] = plugin_instance
                        logger.info(f" Loaded plugin: {name}")
                        
                    except Exception as e:
                        logger.error(f"Failed to initialize plugin {name}: {e}")
                        traceback.print_exc()
                        
        except Exception as e:
            logger.error(f"Failed to load plugin file {plugin_file}: {e}")
            traceback.print_exc()
    
    def _is_plugin_class(self, obj) -> bool:
        """Check if a class is a valid plugin"""
        try:
            # Check if it's a subclass of BasePlugin
            from src.plugins.base_plugin import BasePlugin
            return issubclass(obj, BasePlugin) and obj != BasePlugin
        except:
            return False
    
    def reload_plugins(self):
        """Reload all plugins (useful for development)"""
        logger.info("Reloading plugins...")
        
        # Cleanup existing plugins
        self.cleanup_all()
        self.plugins.clear()
        
        # Reload
        self.load_plugins()
    
    def get_plugin(self, name: str) -> Any:
        """Get a specific plugin by name"""
        return self.plugins.get(name)
    
    def list_plugins(self) -> List[str]:
        """Get list of loaded plugin names"""
        return list(self.plugins.keys())
    
    def trigger_intruder_detected(self, image_path: str, timestamp: str):
        """Trigger intruder detected event on all plugins"""
        for name, plugin in self.plugins.items():
            try:
                plugin.on_intruder_detected(image_path, timestamp)
            except Exception as e:
                logger.error(f"Plugin {name} error in on_intruder_detected: {e}")
    
    def trigger_unauthorized_access(self, face_data: Dict[str, Any]):
        """Trigger unauthorized access event on all plugins"""
        for name, plugin in self.plugins.items():
            try:
                plugin.on_unauthorized_access(face_data)
            except Exception as e:
                logger.error(f"Plugin {name} error in on_unauthorized_access: {e}")
    
    def trigger_system_event(self, event_type: str, data: Dict[str, Any]):
        """Trigger generic system event on all plugins"""
        for name, plugin in self.plugins.items():
            try:
                if hasattr(plugin, 'on_system_event'):
                    plugin.on_system_event(event_type, data)
            except Exception as e:
                logger.error(f"Plugin {name} error in on_system_event: {e}")
    
    def cleanup_all(self):
        """Cleanup all plugins"""
        for name, plugin in self.plugins.items():
            try:
                plugin.cleanup()
                logger.info(f"Cleaned up plugin: {name}")
            except Exception as e:
                logger.error(f"Error cleaning up plugin {name}: {e}")
    
    def get_plugin_info(self) -> List[Dict[str, Any]]:
        """Get information about all loaded plugins"""
        info = []
        
        for name, plugin in self.plugins.items():
            plugin_info = {
                'name': name,
                'enabled': plugin.enabled,
                'class': plugin.__class__.__name__,
                'module': plugin.__class__.__module__,
                'config': plugin.config
            }
            
            # Add plugin-specific info if available
            if hasattr(plugin, 'get_info'):
                plugin_info.update(plugin.get_info())
            
            info.append(plugin_info)
        
        return info
    
    def enable_plugin(self, name: str):
        """Enable a specific plugin"""
        if name in self.plugins:
            self.plugins[name].enabled = True
            self.config.set(f'plugins.{name}.enabled', True)
            logger.info(f"Enabled plugin: {name}")
    
    def disable_plugin(self, name: str):
        """Disable a specific plugin"""
        if name in self.plugins:
            self.plugins[name].enabled = False
            self.config.set(f'plugins.{name}.enabled', False)
            logger.info(f"Disabled plugin: {name}")
    
    def execute_plugin_method(self, plugin_name: str, method_name: str, *args, **kwargs):
        """Execute a specific method on a plugin"""
        plugin = self.get_plugin(plugin_name)
        
        if not plugin:
            raise ValueError(f"Plugin {plugin_name} not found")
        
        if not hasattr(plugin, method_name):
            raise ValueError(f"Plugin {plugin_name} does not have method {method_name}")
        
        method = getattr(plugin, method_name)
        return method(*args, **kwargs)