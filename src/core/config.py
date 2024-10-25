from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from pathlib import Path
import yaml
from .exceptions import InvalidConfigError, ConfigError

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from pathlib import Path
import yaml
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
        """Convert to dictionary for saving"""
        return {
            'API_URL': self.url,
            'API_KEY': self.key,
            'timeout': self.timeout,
            'max_retries': self.max_retries,
            'retry_delay': self.retry_delay
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ApiConfig':
        """Create instance from dictionary"""
        return cls(
            url=data.get('API_URL', ''),
            key=data.get('API_KEY'),
            timeout=data.get('timeout', 420),
            max_retries=data.get('max_retries', 3),
            retry_delay=data.get('retry_delay', 1)
        )

@dataclass
class GenerationConfig:
    """Generation-related settings"""
    max_tokens: int = 2048

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for saving"""
        return {
            'max_tokens': self.max_tokens,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GenerationConfig':
        """Create instance from dictionary"""
        return cls(
            max_tokens=data.get('max_tokens', 2048),
        )


@dataclass
class PathConfig:
    """File path configuration"""
    base_dir: Path = field(default_factory=lambda: Path.cwd())
    
    def __post_init__(self):
        self.data_dir = self.base_dir / "data"
        self.characters_dir = self.data_dir / "characters"
        self.base_prompts_dir = self.data_dir / "base_prompts"
        self.config_dir = self.data_dir / "config"
        self.logs_dir = self.data_dir / "logs"
        
        # Create directories if they don't exist
        for directory in [
            self.data_dir,
            self.characters_dir, 
            self.base_prompts_dir,
            self.config_dir,
            self.logs_dir
        ]:
            directory.mkdir(parents=True, exist_ok=True)

@dataclass
class UserConfig:
    """User-related settings"""
    creator_name: str = "Anonymous"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for saving"""
        return {
            'creator_name': self.creator_name
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserConfig':
        """Create instance from dictionary"""
        return cls(
            creator_name=data.get('creator_name', 'Anonymous')
        )

@dataclass
class AppConfig:
    """Main application configuration"""
    api: ApiConfig
    generation: GenerationConfig
    user: UserConfig
    paths: PathConfig
    
    @classmethod
    def load(cls, config_path: Path) -> 'AppConfig':
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                data = yaml.safe_load(f)
            
            # Parse configurations
            api_config = ApiConfig.from_dict(data)
            gen_data = data.get('generation', {})
            gen_config = GenerationConfig.from_dict(gen_data)
            user_data = data.get('user', {})
            user_config = UserConfig.from_dict(user_data)
            
            # Set up paths
            path_config = PathConfig(base_dir=Path(data.get('base_dir', Path.cwd())))
            
            return cls(
                api=api_config,
                generation=gen_config,
                user=user_config,
                paths=path_config
            )
            
        except yaml.YAMLError as e:
            raise InvalidConfigError(f"Error parsing config file: {str(e)}")
        except Exception as e:
            raise ConfigError(f"Error loading configuration: {str(e)}")
    
    def save(self, config_path: Path) -> None:
        """Save current configuration to YAML file"""
        try:
            config_data = {
                **self.api.to_dict(),
                'generation': self.generation.to_dict(),
                'user': self.user.to_dict(),
                'base_dir': str(self.paths.base_dir)
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
