"""Error handling module initialization."""
from typing import Dict, Any, Type

from .handler import ErrorHandler, ErrorCategory, ErrorLevel, ErrorInfo
from .types import (
    CharacterGenError,  # Base error class
    ValidationError,
    FileOperationError,
    StateError,
    ConfigError,
    GenerationError
)

# Type alias for error mapping
ErrorMapping = Dict[str, Type[CharacterGenError]]

# Error registry for dynamic error handling
ERROR_REGISTRY: ErrorMapping = {
    'validation': ValidationError,
    'file': FileOperationError,
    'state': StateError,
    'config': ConfigError,
    'generation': GenerationError,
}

def get_error_class(error_type: str) -> Type[CharacterGenError]:
    """Get error class by type name."""
    return ERROR_REGISTRY.get(error_type, CharacterGenError)

__all__ = [
    'ErrorHandler',
    'ErrorCategory',
    'ErrorLevel',
    'ErrorInfo',
    'CharacterGenError',
    'ValidationError',
    'FileOperationError',
    'StateError',
    'ConfigError',
    'GenerationError',
    'get_error_class',
    'ERROR_REGISTRY'
]