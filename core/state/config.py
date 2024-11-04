from typing import Dict, Any, Optional, Set
from pathlib import Path
import yaml
import json
import logging
from datetime import datetime
import asyncio

from .base import StateManagerBase, OperationContext
from ..common.types import Result, JsonDict, PathLike
from ..errors import ErrorHandler, ConfigError, ErrorCategory, ErrorLevel
from config.app_config import (
    AppConfig, ApiConfig, FileConfig, 
    UIConfig, GenerationConfig, DebugConfig
)

class ConfigurationManager(StateManagerBase[AppConfig]):
    """Manages application configuration and settings"""
    
    def __init__(self, 
                 config_path: PathLike,
                 error_handler: ErrorHandler):
        super().__init__(error_handler)
        self.config_path = Path(config_path)
        
        # Runtime configuration storage
        self._runtime_config: Dict[str, Any] = {}
        self._modified_settings: Set[str] = set()
        self._config_lock = asyncio.Lock()
        self._runtime_lock = asyncio.Lock()
        
        # Load initial configuration
        asyncio.create_task(self._load_configuration())

    async def get_setting(self, key: str, default: Any = None) -> Result[Any]:
        """Get configuration setting using dot notation"""
        try:
            async with self._config_lock:
                parts = key.split('.')
                current = self._state.get('config')
                
                if not current:
                    return Result(False, "Configuration not loaded", default)
                
                for part in parts:
                    if hasattr(current, part):
                        current = getattr(current, part)
                    else:
                        return Result(True, "Setting not found", default)
                        
                return Result(True, "Setting retrieved successfully", current)
                
        except Exception as e:
            self.error_handler.handle_error(
                e, ErrorCategory.CONFIG, ErrorLevel.WARNING,
                {'operation': 'get_setting', 'key': key}
            )
            return Result(False, f"Failed to get setting: {str(e)}", default)

    async def update_setting(self, 
                           key: str, 
                           value: Any, 
                           save: bool = True) -> Result:
        """Update configuration setting"""
        try:
            async with self._config_lock:
                async with self.operation('update_setting', {
                    'key': key,
                    'save': save
                }):
                    # Parse the dot notation path
                    parts = key.split('.')
                    current = self._state.get('config')
                    
                    if not current:
                        return Result(False, "Configuration not loaded")
                    
                    # Navigate to the correct config object
                    for part in parts[:-1]:
                        if hasattr(current, part):
                            current = getattr(current, part)
                        else:
                            return Result(False, f"Invalid configuration path: {key}")
                    
                    # Update the value
                    if hasattr(current, parts[-1]):
                        # Store old value for state change
                        old_value = getattr(current, parts[-1])
                        
                        # Update value
                        setattr(current, parts[-1], value)
                        self._modified_settings.add(key)
                        
                        # Auto-save if requested
                        if save:
                            save_result = await self.save_configuration()
                            if not save_result.success:
                                return save_result
                        
                        # Notify of change
                        await self.update_state(
                            f'config_{key}',
                            value,
                            metadata={
                                'old_value': old_value,
                                'auto_saved': save
                            }
                        )
                        
                        return Result(True, "Setting updated successfully")
                    
                    return Result(False, f"Invalid configuration key: {key}")
                    
        except Exception as e:
            self.error_handler.handle_error(
                e, ErrorCategory.CONFIG, ErrorLevel.ERROR,
                {'operation': 'update_setting', 'key': key}
            )
            return Result(False, f"Failed to update setting: {str(e)}", error=e)

    async def set_runtime_config(self, 
                               key: str, 
                               value: Any) -> Result:
        """Set runtime-only configuration value"""
        try:
            async with self._runtime_lock:
                self._runtime_config[key] = value
                
                await self.update_state(
                    f'runtime_{key}',
                    value,
                    metadata={'type': 'runtime'}
                )
                
                return Result(True, "Runtime config updated successfully")
                
        except Exception as e:
            self.error_handler.handle_error(
                e, ErrorCategory.CONFIG, ErrorLevel.ERROR,
                {'operation': 'set_runtime_config', 'key': key}
            )
            return Result(False, f"Failed to set runtime config: {str(e)}", error=e)

    async def get_runtime_config(self, 
                               key: str, 
                               default: Any = None) -> Result[Any]:
        """Get runtime configuration value"""
        try:
            async with self._runtime_lock:
                value = self._runtime_config.get(key, default)
                return Result(True, "Runtime config retrieved", value)
        except Exception as e:
            self.error_handler.handle_error(
                e, ErrorCategory.CONFIG, ErrorLevel.WARNING,
                {'operation': 'get_runtime_config', 'key': key}
            )
            return Result(False, f"Failed to get runtime config: {str(e)}", default)

    async def save_configuration(self) -> Result:
        """Save current configuration to disk"""
        try:
            async with self._config_lock:
                async with self.operation('save_configuration'):
                    config = self._state.get('config')
                    if not config:
                        return Result(False, "No configuration to save")
                    
                    # Convert config to dictionary
                    config_dict = {
                        'version': config.version,
                        'last_modified': datetime.now().isoformat(),
                        'api': config.api.__dict__,
                        'files': {
                            **config.files.__dict__,
                            'save_dir': str(config.files.save_dir),
                            'backup_dir': str(config.files.backup_dir),
                            'temp_dir': str(config.files.temp_dir)
                        },
                        'ui': config.ui.__dict__,
                        'generation': config.generation.__dict__,
                        'debug': config.debug.__dict__
                    }
                    
                    # Ensure config directory exists
                    self.config_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Save to file
                    with open(self.config_path, 'w') as f:
                        yaml.safe_dump(config_dict, f, default_flow_style=False)
                    
                    # Clear modified settings
                    self._modified_settings.clear()
                    
                    # Update state
                    await self.update_state(
                        'config_saved',
                        datetime.now(),
                        metadata={'path': str(self.config_path)}
                    )
                    
                    return Result(True, "Configuration saved successfully")
                    
        except Exception as e:
            self.error_handler.handle_error(
                e, ErrorCategory.CONFIG, ErrorLevel.ERROR,
                {'operation': 'save_configuration'}
            )
            return Result(False, f"Failed to save configuration: {str(e)}", error=e)

    async def reset_to_defaults(self) -> Result:
        """Reset configuration to defaults"""
        try:
            async with self._config_lock:
                async with self.operation('reset_configuration'):
                    # Create default configuration
                    default_config = AppConfig(
                        version="1.0.0",
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
                    
                    # Update state
                    await self.update_state(
                        'config',
                        default_config,
                        metadata={'operation': 'reset'}
                    )
                    
                    # Save to disk
                    save_result = await self.save_configuration()
                    if not save_result.success:
                        return save_result
                    
                    return Result(True, "Configuration reset to defaults")
                    
        except Exception as e:
            self.error_handler.handle_error(
                e, ErrorCategory.CONFIG, ErrorLevel.ERROR,
                {'operation': 'reset_configuration'}
            )
            return Result(False, f"Failed to reset configuration: {str(e)}", error=e)

    async def _load_configuration(self) -> Result:
        """Load configuration from disk"""
        try:
            async with self._config_lock:
                if self.config_path.exists():
                    # Load from file
                    with open(self.config_path) as f:
                        config_dict = yaml.safe_load(f)
                    
                    # Create config object
                    config = AppConfig(
                        version=config_dict.get('version', '1.0.0'),
                        api=ApiConfig(**config_dict.get('api', {})),
                        files=FileConfig(
                            save_dir=Path(config_dict['files']['save_dir']),
                            backup_dir=Path(config_dict['files']['backup_dir']),
                            temp_dir=Path(config_dict['files']['temp_dir']),
                            **{k: v for k, v in config_dict['files'].items() 
                               if k not in ['save_dir', 'backup_dir', 'temp_dir']}
                        ),
                        ui=UIConfig(**config_dict.get('ui', {})),
                        generation=GenerationConfig(**config_dict.get('generation', {})),
                        debug=DebugConfig(**config_dict.get('debug', {}))
                    )
                else:
                    # Create default config
                    config = AppConfig.create_default()
                    
                # Update state
                await self.update_state(
                    'config',
                    config,
                    metadata={'loaded_from': str(self.config_path)}
                )
                
                return Result(True, "Configuration loaded successfully")
                
        except Exception as e:
            self.error_handler.handle_error(
                e, ErrorCategory.CONFIG, ErrorLevel.ERROR,
                {'operation': 'load_configuration'}
            )
            # Load defaults on error
            return await self.reset_to_defaults()

    def has_unsaved_changes(self) -> bool:
        """Check if there are unsaved changes"""
        return bool(self._modified_settings)

    def get_modified_settings(self) -> Set[str]:
        """Get set of modified settings"""
        return self._modified_settings.copy()