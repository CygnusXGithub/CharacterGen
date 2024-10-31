class CharacterGenError(Exception):
    """Base exception for all application errors"""
    pass

class ValidationError(CharacterGenError):
    """Raised when validation fails"""
    pass

class FileOperationError(CharacterGenError):
    """Raised when file operations fail"""
    pass

class StateError(CharacterGenError):
    """Raised when state operations fail"""
    pass

class ConfigError(CharacterGenError):
    """Raised when configuration operations fail"""
    pass

class GenerationError(CharacterGenError):
    """Raised when generation operations fail"""
    pass