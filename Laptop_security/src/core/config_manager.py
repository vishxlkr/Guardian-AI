"""
Configuration Manager - Handles all configuration loading and management
FIXED: Resolved deadlock issue in _create_directories method
"""

import yaml
import os
import json
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime
import threading

class ConfigManager:
    """Manages application configuration with thread-safe operations"""
    
    def __init__(self, config_path: str = "config\\config.yaml"):
        self.config_path = Path(config_path)
        self.config = {}
        self._lock = threading.Lock()
        self._ensure_config_exists()
        self.load_config()
        
    def _ensure_config_exists(self):
        """Create default config if it doesn't exist"""
        if not self.config_path.exists():
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            self._create_default_config()
    
    def _create_default_config(self):
        """Create default configuration file"""
        default_config = {
            'app': {
                'name': 'Personal Security Software',
                'version': '1.0.0',
                'log_level': 'INFO'
            },
            'camera': {
                'device_id': 0,
                'resolution': {'width': 640, 'height': 480},
                'fps': 30
            },
            'face_recognition': {
                'tolerance': 0.6,
                'model': 'hog'
            },
            'screen_guard': {
                'enabled': True,
                'check_interval': 0.5,
                'blur_settings': {
                    'duration': 2,
                    'radius': 25,
                    'padding': 60,
                    'opacity': 0.8
                }
            },
            'intruder_monitor': {
                'enabled': True,
                'capture_on_failed_login': True
            },
            'storage': {
                'intruder_images_dir': 'data/images/intruders',
                'authorized_faces_dir': 'data/images/authorized',
                'log_dir': 'data/logs',
                'retention_days': 30
            }
        }
        
        with open(self.config_path, 'w') as f:
            yaml.dump(default_config, f, default_flow_style=False)
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        with self._lock:
            try:
                with open(self.config_path, 'r') as f:
                    self.config = yaml.safe_load(f) or {}
                    
                # Ensure all directories exist - FIXED: No deadlock
                self._create_directories()
                
                return self.config
            except Exception as e:
                print(f"Error loading config: {e}")
                # Return empty config on error
                self.config = {}
                return self.config
    
    def save_config(self):
        """Save current configuration to file"""
        with self._lock:
            try:
                # Backup existing config
                if self.config_path.exists():
                    backup_path = self.config_path.with_suffix('.yaml.bak')
                    self.config_path.rename(backup_path)
                
                # Save new config
                with open(self.config_path, 'w') as f:
                    yaml.dump(self.config, f, default_flow_style=False, sort_keys=False)
                    
            except Exception as e:
                print(f"Error saving config: {e}")
                # Restore backup if save failed
                backup_path = self.config_path.with_suffix('.yaml.bak')
                if backup_path.exists():
                    backup_path.rename(self.config_path)
    
    def get(self, key: str, default=None) -> Any:
        """Get configuration value by dot-notation key"""
        with self._lock:
            keys = key.split('.')
            value = self.config
            
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default
                    
            return value
    
    def set(self, key: str, value: Any):
        """Set configuration value by dot-notation key"""
        with self._lock:
            keys = key.split('.')
            config = self.config
            
            # Navigate to the parent of the target key
            for k in keys[:-1]:
                if k not in config:
                    config[k] = {}
                config = config[k]
            
            # Set the value
            config[keys[-1]] = value
            
            # Auto-save
            self.save_config()
    
    def update(self, updates: Dict[str, Any]):
        """Update multiple configuration values"""
        with self._lock:
            self._deep_update(self.config, updates)
            self.save_config()
    
    def _deep_update(self, original: dict, updates: dict):
        """Recursively update nested dictionary"""
        for key, value in updates.items():
            if isinstance(value, dict) and key in original:
                self._deep_update(original[key], value)
            else:
                original[key] = value
    
    def _create_directories(self):
        """Create all required directories - FIXED: No deadlock issue"""
        # FIXED: Access config directly instead of using self.get() 
        # to avoid deadlock since we're already holding the lock
        storage_config = self.config.get('storage', {})
        
        dirs_to_create = [
            storage_config.get('intruder_images_dir', 'data/images/intruders'),
            storage_config.get('authorized_faces_dir', 'data/images/authorized'),
            storage_config.get('log_dir', 'data/logs'),
            'data/models',
            'data/backups'
        ]
        
        for dir_path in dirs_to_create:
            try:
                # Use forward slashes for cross-platform compatibility
                normalized_path = Path(str(dir_path).replace('\\', '/'))
                normalized_path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                print(f"Warning: Could not create directory {dir_path}: {e}")
                # Continue with other directories instead of failing completely
    
    def get_all(self) -> Dict[str, Any]:
        """Get entire configuration"""
        with self._lock:
            return self.config.copy()
    
    def reload(self):
        """Reload configuration from file"""
        self.load_config()
    
    def export_config(self, export_path: str):
        """Export configuration to file"""
        with self._lock:
            with open(export_path, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False)
    
    def import_config(self, import_path: str):
        """Import configuration from file"""
        try:
            with open(import_path, 'r') as f:
                new_config = yaml.safe_load(f)
                
            if new_config:
                self.config = new_config
                self.save_config()
                return True
        except Exception as e:
            print(f"Error importing config: {e}")
            return False
    
    def validate_config(self) -> Tuple[bool, List[str]]:
        """Validate configuration values"""
        errors = []
        
        # Check camera device ID
        device_id = self.get('camera.device_id')
        if not isinstance(device_id, int) or device_id < 0:
            errors.append("Invalid camera device ID")
        
        # Check face recognition tolerance
        tolerance = self.get('face_recognition.tolerance')
        if not isinstance(tolerance, (int, float)) or not 0 <= tolerance <= 1:
            errors.append("Face recognition tolerance must be between 0 and 1")
        
        # Check directories
        for key in ['storage.intruder_images_dir', 'storage.authorized_faces_dir']:
            dir_path = self.get(key)
            if not dir_path:
                errors.append(f"Missing directory configuration: {key}")
        
        return len(errors) == 0, errors