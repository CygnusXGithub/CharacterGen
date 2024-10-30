from dataclasses import dataclass, field
from typing import Dict, Optional, List
from pathlib import Path
import yaml

@dataclass
class ApiConfig:
    """API configuration"""
    endpoint: str
    api_key: Optional[str] = None
    timeout: int = 30
    retry_attempts: int = 3
    batch_size: int = 10

@dataclass
class FileConfig:
    """File handling configuration"""
    save_dir: Path
    backup_dir: Path
    temp_dir: Path
    max_backups: int = 5
    auto_save_interval: int = 300  # seconds
    auto_save_enabled: bool = True

@dataclass
class UIConfig:
    """UI configuration"""
    theme: str = "default"
    font_size: int = 12
    auto_expand_threshold: int = 1000
    max_field_height: int = 600
    show_line_numbers: bool = True

@dataclass
class GenerationConfig:
    """Generation settings"""
    max_concurrent: int = 3
    timeout: int = 30
    max_retries: int = 3
    batch_size: int = 5
    preserve_history: bool = True

@dataclass
class DebugConfig:
    """Debug settings"""
    enabled: bool = False
    log_level: str = "INFO"
    performance_logging: bool = False

@dataclass
class AppConfig:
    """Complete application configuration"""
    api: ApiConfig
    files: FileConfig
    ui: UIConfig
    generation: GenerationConfig
    debug: DebugConfig
    
    @classmethod
    def load(cls, config_path: Path) -> 'AppConfig':
        """Load configuration from YAML file"""
        try:
            with open(config_path) as f:
                data = yaml.safe_load(f)
                
            # Convert path strings to Path objects
            if 'files' in data:
                for key in ['save_dir', 'backup_dir', 'temp_dir']:
                    if key in data['files']:
                        data['files'][key] = Path(data['files'][key])
            
            return cls(
                api=ApiConfig(**data['api']),
                files=FileConfig(**data['files']),
                ui=UIConfig(**data.get('ui', {})),
                generation=GenerationConfig(**data.get('generation', {})),
                debug=DebugConfig(**data.get('debug', {}))
            )
        except Exception as e:
            raise ConfigError(f"Failed to load config: {str(e)}")

    def save(self, config_path: Path):
        """Save configuration to YAML file"""
        try:
            # Convert to dictionary
            data = {
                'api': self.api.__dict__,
                'files': {
                    **self.files.__dict__,
                    'save_dir': str(self.files.save_dir),
                    'backup_dir': str(self.files.backup_dir),
                    'temp_dir': str(self.files.temp_dir)
                },
                'ui': self.ui.__dict__,
                'generation': self.generation.__dict__,
                'debug': self.debug.__dict__
            }
            
            with open(config_path, 'w') as f:
                yaml.safe_dump(data, f, default_flow_style=False)
                
        except Exception as e:
            raise ConfigError(f"Failed to save config: {str(e)}")

class ConfigError(Exception):
    """Configuration-related errors"""
    pass