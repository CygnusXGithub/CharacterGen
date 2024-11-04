"""Core module initialization."""
from typing import Dict, Any
from pathlib import Path

# Version information
__version__ = '0.1.0'
__author__ = 'Your Name'
__license__ = 'MIT'

# Core components
from .models import *
from .services import *
from .state import *
from .errors import *

# Type aliases for better type hinting
ConfigDict = Dict[str, Any]
PathLike = Path | str

# Initialize logger
import logging
logger = logging.getLogger(__name__)

def setup_logging(log_level: str = "INFO", log_file: PathLike | None = None) -> None:
    """Setup core logging configuration."""
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    handlers = [logging.StreamHandler()]
    
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_path))
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        handlers=handlers
    )