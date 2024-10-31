from typing import Dict, Any, Optional, Set
from pathlib import Path
import yaml
import json
import logging
from datetime import datetime

from .base import StateManagerBase
from ..errors import ErrorHandler, ConfigError, ErrorCategory, ErrorLevel
from config.app_config import (
    AppConfig, ApiConfig, FileConfig, 
    UIConfig, GenerationConfig, DebugConfig
)

class ConfigurationManager(StateManagerBase):
    """Manages application configuration and settings"""
    
    def __init__(self, 
                 config_path: Path,
                 error_handler: ErrorHandler):
        super().__init__()
        self.config_path = config_path
        self.error_handler = error_handler
        self.logger = logging.getLogger(__name__)
        
        # Runtime configuration storage
        self._runtime_config: Dict[str, Any] = {}
        self._modified_settings: Set[str] = set()
        
        # Load initial configuration
        self._load_configuration()
        
        # Track last save
        self._last_saved: Optional[datetime] = None

    @property
    def config(self) -> AppConfig:
        """Get current configuration"""
        return self._state.get('config')

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get configuration setting using dot notation"""
        try:
            parts = key.split('.')
            current = self.config
            
            for part in parts:
                if hasattr(current, part):
                    current = getattr(current, part)
                else:
                    return default
                    
            return current
        except Exception as e:
            self.error_handler.handle_error(
                error=e,
                category=ErrorCategory.CONFIG,
                level=ErrorLevel.WARNING,
                context={'operation': 'get_setting', 'key': key}
            )
            return default

    async def update_setting(self, key: str, value: Any, save: bool = True) -> bool:
        """Update configuration setting"""
        try:
            with self.operation('update_setting', {'key': key}):
                # Parse the dot notation path
                parts = key.split('.')
                current = self.config
                
                # Navigate to the correct config object
                for part in parts[:-1]:
                    if hasattr(current, part):
                        current = getattr(current, part)
                    else:
                        raise ConfigError(f"Invalid configuration path: {key}")
                
                # Update the value
                if hasattr(current, parts[-1]):
                    setattr(current, parts[-1], value)
                    self._modified_settings.add(key)
                    
                    # Auto-save if requested
                    if save:
                        await self.save_configuration()
                    
                    # Emit change
                    self.state_changed.emit('config_updated', {
                        'key': key,
                        'value': value
                    })
                    return True
                else:
                    raise ConfigError(f"Invalid configuration key: {key}")
                    
        except Exception as e:
            self.error_handler.handle_error(
                error=e,
                category=ErrorCategory.CONFIG,
                level=ErrorLevel.ERROR,
                context={'operation': 'update_setting', 'key': key}
            )
            return False

    def set_runtime_config(self, key: str, value: Any):
        """Set runtime-only configuration value"""
        try:
            self._runtime_config[key] = value
            self.state_changed.emit('runtime_config', {
                'key': key,
                'value': value
            })
        except Exception as e:
            self.error_handler.handle_error(
                error=e,
                category=ErrorCategory.CONFIG,
                level=ErrorLevel.ERROR,
                context={'operation': 'set_runtime_config', 'key': key}
            )

    def get_runtime_config(self, key: str, default: Any = None) -> Any:
        """Get runtime configuration value"""
        return self._runtime_config.get(key, default)

    async def save_configuration(self) -> bool:
        """Save current configuration to disk"""
        try:
            with self.operation('save_configuration'):
                # Convert config to dictionary
                config_dict = {
                    'api': self.config.api.__dict__,
                    'files': {
                        **self.config.files.__dict__,
                        'save_dir': str(self.config.files.save_dir),
                        'backup_dir': str(self.config.files.backup_dir),
                        'temp_dir': str(self.config.files.temp_dir)
                    },
                    'ui': self.config.ui.__dict__,
                    'generation': self.config.generation.__dict__,
                    'debug': self.config.debug.__dict__
                }
                
                # Save to file
                with open(self.config_path, 'w') as f:
                    yaml.safe_dump(config_dict, f, default_flow_style=False)
                
                self._last_saved = datetime.now()
                self._modified_settings.clear()
                
                self.state_changed.emit('config_saved', self._last_saved)
                return True
                
        except Exception as e:
            self.error_handler.handle_error(
                error=e,
                category=ErrorCategory.CONFIG,
                level=ErrorLevel.ERROR,
                context={'operation': 'save_configuration'}
            )
            return False

    def reset_to_defaults(self) -> bool:
        """Reset configuration to defaults"""
        try:
            with self.operation('reset_configuration'):
                self._state['config'] = AppConfig(
                    api=ApiConfig(endpoint="http://localhost:5000"),
                    files=FileConfig(
                        save_dir=Path("saves"),
                        backup_dir=Path("backups"),
                        temp_dir=Path("temp")
                    ),
                    ui=UIConfig(),
                    generation=GenerationConfig(),
                    debug=DebugConfig()
                )
                self.state_changed.emit('config_reset', None)
                return True
        except Exception as e:
            self.error_handler.handle_error(
                error=e,
                category=ErrorCategory.CONFIG,
                level=ErrorLevel.ERROR,
                context={'operation': 'reset_configuration'}
            )
            return False

    def _load_configuration(self):
        """Load configuration from disk"""
        try:
            if self.config_path.exists():
                config = AppConfig.load(self.config_path)
            else:
                # Create default configuration
                config = AppConfig(
                    api=ApiConfig(endpoint="http://localhost:5000"),
                    files=FileConfig(
                        save_dir=Path("saves"),
                        backup_dir=Path("backups"),
                        temp_dir=Path("temp")
                    ),
                    ui=UIConfig(),
                    generation=GenerationConfig(),
                    debug=DebugConfig()
                )
                
            self._state['config'] = config
            self.state_changed.emit('config_loaded', config)
            
        except Exception as e:
            self.error_handler.handle_error(
                error=e,
                category=ErrorCategory.CONFIG,
                level=ErrorLevel.ERROR,
                context={'operation': 'load_configuration'}
            )
            # Load defaults on error
            self.reset_to_defaults()