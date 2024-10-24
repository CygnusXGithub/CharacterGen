class CharacterGenError(Exception):
    """Base exception for all CharacterGen errors"""
    pass

# API Related Exceptions
class ApiError(CharacterGenError):
    """Base exception for API-related errors"""
    pass

class ApiTimeoutError(ApiError):
    """Raised when API request times out"""
    pass

class ApiResponseError(ApiError):
    """Raised when API returns an error response"""
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        super().__init__(f"API error {status_code}: {message}")

# File Operations Exceptions
class FileError(CharacterGenError):
    """Base exception for file operation errors"""
    pass

class CharacterLoadError(FileError):
    """Raised when loading a character file fails"""
    pass

class CharacterSaveError(FileError):
    """Raised when saving a character file fails"""
    pass

class PromptLoadError(FileError):
    """Raised when loading prompt templates fails"""
    pass

class PromptSaveError(FileError):
    """Raised when saving prompt templates fails"""
    pass

# Generation Exceptions
class GenerationError(CharacterGenError):
    """Base exception for generation-related errors"""
    pass

class DependencyError(GenerationError):
    """Raised when field dependencies are not met"""
    def __init__(self, field_name: str, missing_deps: list):
        self.field_name = field_name
        self.missing_deps = missing_deps
        super().__init__(
            f"Cannot generate {field_name}. Missing dependencies: {', '.join(missing_deps)}"
        )

class ValidationError(GenerationError):
    """Raised when validation fails"""
    pass

# Template Exceptions
class TemplateError(CharacterGenError):
    """Base exception for template-related errors"""
    pass

class TagError(TemplateError):
    """Raised when there's an error with template tags"""
    pass

class MismatchedTagError(TagError):
    """Raised when conditional tags are mismatched"""
    pass

class InvalidTagError(TagError):
    """Raised when an invalid tag is used"""
    pass

# Configuration Exceptions
class ConfigError(CharacterGenError):
    """Base exception for configuration-related errors"""
    pass

class InvalidConfigError(ConfigError):
    """Raised when configuration is invalid"""
    pass

# UI Exceptions
class UIError(CharacterGenError):
    """Base exception for UI-related errors"""
    pass

class WidgetStateError(UIError):
    """Raised when widget enters invalid state"""
    pass
