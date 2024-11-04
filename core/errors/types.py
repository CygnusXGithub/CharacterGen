"""Base error types for the application."""
from typing import Optional, Any, Dict
from datetime import datetime

class CharacterGenError(Exception):
    """Base exception for all application errors."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.timestamp = datetime.now()
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary format."""
        return {
            'type': self.__class__.__name__,
            'message': self.message,
            'details': self.details,
            'timestamp': self.timestamp.isoformat()
        }

class ValidationError(CharacterGenError):
    """Raised when validation fails."""
    def __init__(self, message: str, field_name: Optional[str] = None, **kwargs):
        super().__init__(message, {'field': field_name, **kwargs})

class FileOperationError(CharacterGenError):
    """Raised when file operations fail."""
    def __init__(self, message: str, path: Optional[str] = None, **kwargs):
        super().__init__(message, {'path': path, **kwargs})

class StateError(CharacterGenError):
    """Raised when state operations fail."""
    def __init__(self, message: str, state_key: Optional[str] = None, **kwargs):
        super().__init__(message, {'state_key': state_key, **kwargs})

class ConfigError(CharacterGenError):
    """Raised when configuration operations fail."""
    def __init__(self, message: str, config_key: Optional[str] = None, **kwargs):
        super().__init__(message, {'config_key': config_key, **kwargs})

class GenerationError(CharacterGenError):
    """Raised when generation operations fail."""
    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        super().__init__(message, {'field': field, **kwargs})