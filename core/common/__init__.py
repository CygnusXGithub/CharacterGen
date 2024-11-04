# core/common/__init__.py
"""Common types and utilities."""
from .types import (
    # Type aliases
    JsonDict, PathLike, Timestamp, ID,
    
    # Enums
    ApplicationState,
    ValidationLevel,
    StatusLevel,
    GenerationStatus,
    ChangeType,
    ResourceType,
    ErrorCategory,
    ErrorLevel,
    TabType,
    DialogType,
    
    # Base classes
    BaseModel,
    Result
)

__all__ = [
    'JsonDict', 'PathLike', 'Timestamp', 'ID',
    'ApplicationState', 'ValidationLevel', 'StatusLevel',
    'GenerationStatus', 'ChangeType', 'ResourceType',
    'ErrorCategory', 'ErrorLevel', 'TabType', 'DialogType',
    'BaseModel', 'Result'
]