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

@dataclass
class GenerationConfig:
    """Generation-related settings"""
    max_tokens: int = 2048

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
class AppConfig:
    """Main application configuration"""
    api: ApiConfig
    generation: GenerationConfig
    paths: PathConfig
    templates: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def load(cls, config_path: Path) -> 'AppConfig':
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                data = yaml.safe_load(f)
            
            # Parse API configuration
            api_config = ApiConfig(
                url=data.get('API_URL', ''),
                key=data.get('API_KEY'),
            )
            
            # Parse generation settings
            gen_data = data.get('generation', {})
            gen_config = GenerationConfig(
                max_tokens=gen_data.get('max_tokens', 2048),
            )
            
            # Set up paths
            base_dir = Path(data.get('base_dir', Path.cwd()))
            path_config = PathConfig(base_dir=base_dir)
            
            # Load templates
            template_path = path_config.config_dir / "template.json"
            templates = {}
            if template_path.exists():
                with open(template_path, 'r') as f:
                    import json
                    templates = json.load(f)
            
            return cls(
                api=api_config,
                generation=gen_config,
                paths=path_config,
                templates=templates
            )
            
        except yaml.YAMLError as e:
            raise InvalidConfigError(f"Error parsing config file: {str(e)}")
        except Exception as e:
            raise ConfigError(f"Error loading configuration: {str(e)}")
    
    def save(self, config_path: Path) -> None:
        """Save current configuration to YAML file"""
        try:
            config_data = {
                'API_URL': self.api.url,
                'API_KEY': self.api.key,
                'generation': {
                    'max_tokens': self.generation.max_tokens,
                },
                'base_dir': str(self.paths.base_dir)
            }
            
            with open(config_path, 'w') as f:
                yaml.safe_dump(config_data, f, default_flow_style=False)
                
        except Exception as e:
            raise ConfigError(f"Error saving configuration: {str(e)}")
    
    def validate(self) -> bool:
        """Validate configuration"""
        if not self.api.url:
            raise InvalidConfigError("API URL is required")
        
        if not self.paths.base_dir.exists():
            raise InvalidConfigError(f"Base directory does not exist: {self.paths.base_dir}")
        
        if not 0 <= self.generation.temperature <= 1:
            raise InvalidConfigError("Temperature must be between 0 and 1")
        
        if not 0 <= self.generation.top_p <= 1:
            raise InvalidConfigError("Top P must be between 0 and 1")
        
        return True

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
