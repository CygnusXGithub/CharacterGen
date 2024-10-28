from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
import yaml
import logging

from .exceptions import InvalidConfigError, ConfigError

@dataclass
class ApiConfig:
    """API-related configuration"""
    url: str
    key: Optional[str] = None
    timeout: int = 420
    max_retries: int = 3
    retry_delay: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            'url': self.url,
            'key': self.key,
            'timeout': self.timeout,
            'max_retries': self.max_retries,
            'retry_delay': self.retry_delay
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ApiConfig':
        return cls(
            url=data.get('url', ''),
            key=data.get('key'),
            timeout=data.get('timeout', 420),
            max_retries=data.get('max_retries', 3),
            retry_delay=data.get('retry_delay', 1)
        )

@dataclass
class GenerationConfig:
    """Generation-related settings"""
    max_tokens: int = 2048
    auto_save: bool = False
    auto_save_interval: int = 300

    def to_dict(self) -> Dict[str, Any]:
        return {
            'max_tokens': self.max_tokens,
            'auto_save': self.auto_save,
            'auto_save_interval': self.auto_save_interval
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GenerationConfig':
        return cls(
            max_tokens=data.get('max_tokens', 2048),
            auto_save=data.get('auto_save', False),
            auto_save_interval=data.get('auto_save_interval', 300)
        )

@dataclass
class UserConfig:
    """User-related settings"""
    creator_name: str = "Anonymous"
    default_save_format: str = "json"
    save_path: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            'creator_name': self.creator_name,
            'default_save_format': self.default_save_format,
            'save_path': self.save_path
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserConfig':
        return cls(
            creator_name=data.get('creator_name', 'Anonymous'),
            default_save_format=data.get('default_save_format', 'json'),
            save_path=data.get('save_path', '')
        )

@dataclass
class UIConfig:
    """UI-related settings"""
    theme: str = "light"
    font_size: int = 10
    show_status_bar: bool = True
    show_toolbar: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            'theme': self.theme,
            'font_size': self.font_size,
            'show_status_bar': self.show_status_bar,
            'show_toolbar': self.show_toolbar
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UIConfig':
        return cls(
            theme=data.get('theme', 'light'),
            font_size=data.get('font_size', 10),
            show_status_bar=data.get('show_status_bar', True),
            show_toolbar=data.get('show_toolbar', True)
        )

@dataclass
class PathConfig:
    """File path configuration"""
    base_dir: Path = field(default_factory=lambda: Path.cwd())
    character_dir: str = "data/characters"
    prompt_dir: str = "data/base_prompts"
    config_dir: str = "data/config"
    logs_dir: str = "data/logs"
    
    def __post_init__(self):
        """Initialize paths after creation"""
        self.characters_dir = self.base_dir / self.character_dir
        self.base_prompts_dir = self.base_dir / self.prompt_dir
        self.config_dir = self.base_dir / self.config_dir
        self.logs_dir = self.base_dir / self.logs_dir
        
        # Create directories
        for directory in [
            self.characters_dir,
            self.base_prompts_dir,
            self.config_dir,
            self.logs_dir
        ]:
            directory.mkdir(parents=True, exist_ok=True)

    def to_dict(self) -> Dict[str, str]:
        return {
            'base_dir': str(self.base_dir),
            'character_dir': self.character_dir,
            'prompt_dir': self.prompt_dir,
            'config_dir': self.config_dir,
            'logs_dir': self.logs_dir
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PathConfig':
        return cls(
            base_dir=Path(data.get('base_dir', str(Path.cwd()))),
            character_dir=data.get('character_dir', 'data/characters'),
            prompt_dir=data.get('prompt_dir', 'data/base_prompts'),
            config_dir=data.get('config_dir', 'data/config'),
            logs_dir=data.get('logs_dir', 'data/logs')
        )

@dataclass
class WindowConfig:
    """Window state configuration"""
    geometry: Optional[bytes] = None
    state: Optional[bytes] = None
    size: Tuple[int, int] = (1024, 768)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'geometry': self.geometry,
            'state': self.state,
            'size': {'width': self.size[0], 'height': self.size[1]}
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WindowConfig':
        size_data = data.get('size', {})
        return cls(
            geometry=data.get('geometry'),
            state=data.get('state'),
            size=(
                size_data.get('width', 1024),
                size_data.get('height', 768)
            )
        )

@dataclass
class DebugConfig:
    """Debug settings"""
    logging_level: str = "INFO"
    enable_console_logging: bool = True
    enable_file_logging: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            'logging_level': self.logging_level,
            'enable_console_logging': self.enable_console_logging,
            'enable_file_logging': self.enable_file_logging
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DebugConfig':
        return cls(
            logging_level=data.get('logging_level', 'INFO'),
            enable_console_logging=data.get('enable_console_logging', True),
            enable_file_logging=data.get('enable_file_logging', True)
        )

@dataclass
class AppConfig:
    """Main application configuration"""
    api: ApiConfig
    generation: GenerationConfig
    user: UserConfig
    ui: UIConfig
    paths: PathConfig
    window: WindowConfig
    debug: DebugConfig
    recent_files: List[str] = field(default_factory=list)
    
    @classmethod
    def load(cls, config_path: Path) -> 'AppConfig':
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                data = yaml.safe_load(f)
            
            return cls(
                api=ApiConfig.from_dict(data.get('api', {})),
                generation=GenerationConfig.from_dict(data.get('generation', {})),
                user=UserConfig.from_dict(data.get('user', {})),
                ui=UIConfig.from_dict(data.get('ui', {})),
                paths=PathConfig.from_dict(data.get('paths', {})),
                window=WindowConfig.from_dict(data.get('window', {})),
                debug=DebugConfig.from_dict(data.get('debug', {})),
                recent_files=data.get('recent_files', [])
            )
            
        except yaml.YAMLError as e:
            raise InvalidConfigError(f"Error parsing config file: {str(e)}")
        except Exception as e:
            raise ConfigError(f"Error loading configuration: {str(e)}")
    
    def save(self, config_path: Path) -> None:
        """Save current configuration to YAML file"""
        try:
            config_data = {
                'api': self.api.to_dict(),
                'generation': self.generation.to_dict(),
                'user': self.user.to_dict(),
                'ui': self.ui.to_dict(),
                'paths': self.paths.to_dict(),
                'window': self.window.to_dict(),
                'debug': self.debug.to_dict(),
                'recent_files': self.recent_files
            }
            
            with open(config_path, 'w') as f:
                yaml.safe_dump(config_data, f, default_flow_style=False)
                
        except Exception as e:
            raise ConfigError(f"Error saving configuration: {str(e)}")

# Global configuration instance
_config: Optional[AppConfig] = None

def get_config() -> AppConfig:
    """Get the global configuration instance"""
    global _config
    if _config is None:
        config_path = Path("data/config/config.yaml")
        if not config_path.exists():
            raise ConfigError("Configuration file not found")
        _config = AppConfig.load(config_path)
    return _config

def set_config(config: AppConfig) -> None:
    """Set the global configuration instance"""
    global _config
    _config = config