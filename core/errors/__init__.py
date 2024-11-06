"""Error handling module initialization."""
from typing import Dict, Any, Optional, Type

from .types import (
    CharacterGenError,
    ValidationError,
    FileOperationError,
    StateError,
    ConfigError,
    GenerationError
)

# Error registry for dynamic error handling
ERROR_REGISTRY: Dict[str, Type[CharacterGenError]] = {
    'validation': ValidationError,
    'file': FileOperationError,
    'state': StateError,
    'config': ConfigError,
    'generation': GenerationError,
}

def get_error_class(error_type: str) -> Type[CharacterGenError]:
    """Get error class by type name."""
    return ERROR_REGISTRY.get(error_type, CharacterGenError)

def get_error_category(error: Exception) -> 'ErrorCategory':
    """Get appropriate error category for exception type"""
    error_type = error.__class__.__name__
    if error_type in ERROR_REGISTRY:
        return ERROR_REGISTRY[error_type].default_category
    return ErrorCategory.STATE  # Default category

def get_error_level(error: Exception) -> 'ErrorLevel':
    """Get appropriate error level for exception type"""
    error_type = error.__class__.__name__
    if error_type in ERROR_REGISTRY:
        return ERROR_REGISTRY[error_type].default_level
    return ErrorLevel.ERROR  # Default level

from .handler import ErrorHandler, ErrorCategory, ErrorLevel, ErrorInfo

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
    'ERROR_REGISTRY',
    'get_error_category',
    'get_error_level'
]

# Add utility method for common error creation
def create_error(message: str, 
                category: ErrorCategory,
                details: Optional[Dict[str, Any]] = None) -> CharacterGenError:
    """Create appropriate error type based on category"""
    error_class = next(
        (err for err in ERROR_REGISTRY.values() 
         if err.default_category == category),
        CharacterGenError
    )
    return error_class(message, details or {})