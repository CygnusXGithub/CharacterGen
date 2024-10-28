from typing import Any, Dict, Optional
from pathlib import Path
import json
import logging
from PyQt6.QtCore import QObject, QSettings, pyqtSignal

class SettingsManager(QObject):
    """Manages application settings and configuration"""
    
    settings_updated = pyqtSignal()  # Emitted when any settings change
    settings_loaded = pyqtSignal()   # Emitted when settings are loaded
    settings_error = pyqtSignal(str) # Emitted on settings errors
    
    def __init__(self):
        super().__init__()
        self.settings = QSettings("CharacterGen", "CharacterGenerator")
        
        # Default settings
        self.defaults = {
            "window": {
                "geometry": None,
                "state": None,
                "size": {"width": 1024, "height": 768},
            },
            "api": {
                "url": "http://127.0.0.1:5000/v1/chat/completions",
                "key": "",
                "timeout": 420,
                "max_retries": 3,
                "retry_delay": 1,
            },
            "generation": {
                "max_tokens": 2048,
                "auto_save": False,
                "auto_save_interval": 300,
            },
            "user": {
                "creator_name": "Anonymous",
                "default_save_format": "json",
                "save_path": "",
            },
            "ui": {
                "theme": "light",
                "font_size": 10,
                "show_status_bar": True,
                "show_toolbar": True,
            },
            "paths": {
                "base_dir": "",
                "character_dir": "data/characters",
                "prompt_dir": "data/base_prompts",
                "config_dir": "data/config",
                "logs_dir": "data/logs"
            },
            "recent_files": []  # This should be a list, not a dict
        }
        
        # Load or initialize settings
        self._ensure_settings()
    
    def _ensure_settings(self):
        """Ensure all default settings exist"""
        try:
            # Check if settings file exists
            if not self.settings.contains("initialized"):
                self._initialize_settings()
            
            # Validate existing settings
            self._validate_settings()
            
        except Exception as e:
            logging.error(f"Error ensuring settings: {str(e)}")
            self.settings_error.emit(f"Error loading settings: {str(e)}")
    
    def _initialize_settings(self):
        """Initialize settings with defaults"""
        try:
            # First try to load from config file
            config_path = Path("data/config/config.yaml")
            if config_path.exists():
                import yaml
                with open(config_path, 'r') as f:
                    config_data = yaml.safe_load(f)
                    
                # Load config data into QSettings
                for category, values in config_data.items():
                    if isinstance(values, dict):
                        for key, value in values.items():
                            setting_key = f"{category}/{key}"
                            self.settings.setValue(setting_key, value)
                    elif category == "recent_files":
                        self.settings.setValue(category, values)
            
            # Then ensure all defaults exist
            for category, values in self.defaults.items():
                if isinstance(values, dict):
                    for key, value in values.items():
                        setting_key = f"{category}/{key}"
                        if not self.settings.contains(setting_key):
                            self.settings.setValue(setting_key, value)
                elif category == "recent_files" and not self.settings.contains(category):
                    self.settings.setValue(category, [])
            
            self.settings.setValue("initialized", True)
            self.settings_loaded.emit()
                
        except Exception as e:
            logging.error(f"Error initializing settings: {str(e)}")
            self.settings_error.emit(f"Error initializing settings: {str(e)}")
    
    def _validate_settings(self):
        """Validate and repair settings if needed"""
        try:
            for category, values in self.defaults.items():
                if isinstance(values, dict):
                    for key, default_value in values.items():
                        setting_key = f"{category}/{key}"
                        
                        # Check if setting exists
                        if not self.settings.contains(setting_key):
                            self.settings.setValue(setting_key, default_value)
                            continue
                        
                        # Get current value
                        current_value = self.settings.value(setting_key)
                        
                        # Handle special cases
                        if category == "window" and key == "size":
                            if not isinstance(current_value, dict):
                                self.settings.setValue(setting_key, default_value)
                        else:
                            # Validate type matches default
                            if current_value is not None and not isinstance(current_value, type(default_value)):
                                try:
                                    # Attempt type conversion
                                    converted_value = type(default_value)(current_value)
                                    self.settings.setValue(setting_key, converted_value)
                                except (ValueError, TypeError):
                                    # Reset to default if conversion fails
                                    self.settings.setValue(setting_key, default_value)
                elif category == "recent_files":
                    # Handle recent_files as a special case since it's a list
                    current_value = self.settings.value(category, [])
                    if not isinstance(current_value, list):
                        self.settings.setValue(category, [])
            
        except Exception as e:
            logging.error(f"Error validating settings: {str(e)}")
            self.settings_error.emit(f"Error validating settings: {str(e)}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get setting value with dot notation (e.g., 'api.url')"""
        try:
            # Convert dot notation to slash notation
            setting_key = key.replace('.', '/')
            
            # Get value with default
            if default is None:
                # Find default in our defaults structure
                parts = key.split('.')
                current = self.defaults
                for part in parts:
                    if part not in current:
                        return None
                    current = current[part]
                default = current
            
            # Get the value from settings
            value = self.settings.value(setting_key, default)
            
            # Type conversion based on default type
            if default is not None:
                if isinstance(default, bool):
                    # Handle boolean values specially
                    return bool(value) if isinstance(value, str) else bool(value)
                elif isinstance(default, int):
                    return int(value) if value else 0
                elif isinstance(default, float):
                    return float(value) if value else 0.0
                elif isinstance(default, list):
                    return value if isinstance(value, list) else []
                elif isinstance(default, dict):
                    return value if isinstance(value, dict) else {}
            
            return value
            
        except Exception as e:
            logging.error(f"Error getting setting {key}: {str(e)}")
            return default
    
    def set(self, key: str, value: Any):
        """Set setting value with dot notation"""
        try:
            # Convert dot notation to slash notation
            setting_key = key.replace('.', '/')
            
            # Set value in QSettings
            self.settings.setValue(setting_key, value)
            
            # Save to config file
            self.save_to_config_file()
            
            self.settings_updated.emit()
            
        except Exception as e:
            logging.error(f"Error setting {key}: {str(e)}")
            self.settings_error.emit(f"Error saving setting: {str(e)}")
    
    def save_to_config_file(self):
        """Save current settings to config.yaml file"""
        try:
            config_path = Path("data/config/config.yaml")
            settings_dict = {
                "api": {
                    "url": self.get("api.url"),
                    "key": self.get("api.key"),
                    "timeout": self.get("api.timeout"),
                    "max_retries": self.get("api.max_retries"),
                    "retry_delay": self.get("api.retry_delay"),
                },
                "generation": {
                    "max_tokens": self.get("generation.max_tokens"),
                    "auto_save": self.get("generation.auto_save"),
                    "auto_save_interval": self.get("generation.auto_save_interval"),
                },
                "user": {
                    "creator_name": self.get("user.creator_name"),
                    "default_save_format": self.get("user.default_save_format"),
                    "save_path": self.get("user.save_path"),
                },
                "ui": {
                    "theme": self.get("ui.theme"),
                    "font_size": self.get("ui.font_size"),
                    "show_status_bar": self.get("ui.show_status_bar"),
                    "show_toolbar": self.get("ui.show_toolbar"),
                },
                "paths": {
                    "base_dir": self.get("paths.base_dir"),
                    "character_dir": self.get("paths.character_dir"),
                    "prompt_dir": self.get("paths.prompt_dir"),
                    "config_dir": self.get("paths.config_dir"),
                    "logs_dir": self.get("paths.logs_dir")
                },
                "recent_files": self.get("recent_files"),
                "window": {
                    "size": self.get("window.size")
                }
            }

            import yaml
            with open(config_path, 'w') as f:
                yaml.safe_dump(settings_dict, f, default_flow_style=False)

        except Exception as e:
            logging.error(f"Error saving to config file: {str(e)}")
            self.settings_error.emit(f"Error saving to config file: {str(e)}")

    def get_all(self) -> Dict[str, Any]:
        """Get all settings as dictionary"""
        try:
            settings_dict = {}
            
            for category, values in self.defaults.items():
                settings_dict[category] = {}
                for key in values.keys():
                    setting_key = f"{category}/{key}"
                    settings_dict[category][key] = self.settings.value(
                        setting_key,
                        self.defaults[category][key]
                    )
            
            return settings_dict
            
        except Exception as e:
            logging.error(f"Error getting all settings: {str(e)}")
            return dict(self.defaults)
    
    def reset_all(self):
        """Reset all settings to defaults"""
        try:
            self.settings.clear()
            self._initialize_settings()
            self.settings_updated.emit()
            
        except Exception as e:
            logging.error(f"Error resetting settings: {str(e)}")
            self.settings_error.emit(f"Error resetting settings: {str(e)}")
    
    def save_window_state(self, window):
        """Save window geometry and state"""
        try:
            self.settings.setValue("window/geometry", window.saveGeometry())
            self.settings.setValue("window/state", window.saveState())
            
        except Exception as e:
            logging.error(f"Error saving window state: {str(e)}")
            self.settings_error.emit(f"Error saving window state: {str(e)}")
    
    def restore_window_state(self, window) -> bool:
        """Restore window geometry and state"""
        try:
            geometry = self.settings.value("window/geometry")
            state = self.settings.value("window/state")
            
            if geometry and state:
                window.restoreGeometry(geometry)
                window.restoreState(state)
                return True
            return False
            
        except Exception as e:
            logging.error(f"Error restoring window state: {str(e)}")
            return False
    
    def add_recent_file(self, file_path: str):
        """Add file to recent files list"""
        try:
            recent_files = self.get("recent_files", [])
            
            # Remove if already exists
            if file_path in recent_files:
                recent_files.remove(file_path)
            
            # Add to start of list
            recent_files.insert(0, file_path)
            
            # Keep only last 10
            recent_files = recent_files[:10]
            
            self.set("recent_files", recent_files)
            
        except Exception as e:
            logging.error(f"Error adding recent file: {str(e)}")
    
    def get_recent_files(self) -> list:
        """Get list of recent files"""
        return self.get("recent_files", [])
    
    def clear_recent_files(self):
        """Clear recent files list"""
        self.set("recent_files", [])
    
    def export_settings(self, file_path: str):
        """Export settings to JSON file"""
        try:
            settings_dict = self.get_all()
            with open(file_path, 'w') as f:
                json.dump(settings_dict, f, indent=4)
                
        except Exception as e:
            logging.error(f"Error exporting settings: {str(e)}")
            self.settings_error.emit(f"Error exporting settings: {str(e)}")
    
    def import_settings(self, file_path: str):
        """Import settings from JSON file"""
        try:
            with open(file_path, 'r') as f:
                settings_dict = json.load(f)
            
            # Validate and import settings
            for category, values in settings_dict.items():
                if category in self.defaults:
                    for key, value in values.items():
                        if key in self.defaults[category]:
                            setting_key = f"{category}/{key}"
                            self.settings.setValue(setting_key, value)
            
            self.settings_updated.emit()
            
        except Exception as e:
            logging.error(f"Error importing settings: {str(e)}")
            self.settings_error.emit(f"Error importing settings: {str(e)}")

    def saveGeometry(self, window) -> None:
        """Save window geometry"""
        try:
            self.set("window.geometry", window.saveGeometry())
        except Exception as e:
            logging.error(f"Error saving window geometry: {str(e)}")
    
    def saveState(self, window) -> None:
        """Save window state"""
        try:
            self.set("window.state", window.saveState())
        except Exception as e:
            logging.error(f"Error saving window state: {str(e)}")
    
    def restoreGeometry(self, window) -> bool:
        """Restore window geometry"""
        try:
            geometry = self.get("window.geometry")
            if geometry:
                return window.restoreGeometry(geometry)
            return False
        except Exception as e:
            logging.error(f"Error restoring window geometry: {str(e)}")
            return False
    
    def restoreState(self, window) -> bool:
        """Restore window state"""
        try:
            state = self.get("window.state")
            if state:
                return window.restoreState(state)
            return False
        except Exception as e:
            logging.error(f"Error restoring window state: {str(e)}")
            return False