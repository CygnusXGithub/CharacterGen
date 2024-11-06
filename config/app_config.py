from dataclasses import dataclass, field
from typing import Dict, Optional, List, Any
from pathlib import Path
import yaml
from datetime import datetime

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
    # Required arguments first
    api: ApiConfig
    files: FileConfig
    ui: UIConfig
    generation: GenerationConfig
    debug: DebugConfig
    # Optional arguments after
    version: str = "1.0.0"
    last_modified: datetime = field(default_factory=datetime.now)
    
    @classmethod
    def create_default(cls) -> 'AppConfig':
        """Create default configuration"""
        return cls(
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

    @classmethod
    def load(cls, config_path: Path) -> 'AppConfig':
        """Load configuration from YAML file"""
        try:
            with open(config_path) as f:
                data = yaml.safe_load(f)
            
            # Handle version upgrades if needed
            current_version = data.get('version', '1.0.0')
            if current_version != cls.version:
                data = cls._migrate_config(data, current_version)
            
            # Convert path strings to Path objects
            if 'files' in data:
                for key in ['save_dir', 'backup_dir', 'temp_dir']:
                    if key in data['files']:
                        data['files'][key] = Path(data['files'][key])
            
            return cls(
                version=current_version,
                api=ApiConfig(**data.get('api', {})),
                files=FileConfig(**data.get('files', {})),
                ui=UIConfig(**data.get('ui', {})),
                generation=GenerationConfig(**data.get('generation', {})),
                debug=DebugConfig(**data.get('debug', {}))
            )
        except Exception as e:
            raise ConfigError(f"Failed to load config: {str(e)}")

    def save(self, config_path: Path) -> None:
        """Save configuration to YAML file"""
        try:
            data = {
                'version': self.version,
                'api': self.api.__dict__,
                'files': {
                    **self.files.__dict__,
                    'save_dir': str(self.files.save_dir),
                    'backup_dir': str(self.files.backup_dir),
                    'temp_dir': str(self.files.temp_dir)
                },
                'ui': self.ui.__dict__,
                'generation': self.generation.__dict__,
                'debug': self.debug.__dict__,
                'last_modified': self.last_modified.isoformat()
            }
            
            with open(config_path, 'w') as f:
                yaml.safe_dump(data, f, default_flow_style=False)
                
        except Exception as e:
            raise ConfigError(f"Failed to save config: {str(e)}")

    @staticmethod
    def _migrate_config(data: Dict[str, Any], old_version: str) -> Dict[str, Any]:
        """Migrate configuration from older versions"""
        # Add migration logic here as needed
        return data

class ConfigError(Exception):
    """Configuration-related errors"""
    pass