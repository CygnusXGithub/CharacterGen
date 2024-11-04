# core/common/types.py
"""Base types and enums for the entire application."""
from enum import Enum, auto
from typing import NewType, Dict, Any, Union, TypeVar, Optional
from pathlib import Path
from datetime import datetime
from uuid import UUID

# Base Type Aliases
JsonDict = Dict[str, Any]
PathLike = Union[str, Path]
Timestamp = NewType('Timestamp', datetime)
ID = NewType('ID', UUID)

# Generic Types
T = TypeVar('T')
ModelType = TypeVar('ModelType')

class ApplicationState(Enum):
    """Global application states."""
    INITIALIZING = auto()
    READY = auto()
    ERROR = auto()
    SHUTTING_DOWN = auto()

class ValidationLevel(Enum):
    """Validation severity levels."""
    INFO = auto()
    WARNING = auto()
    ERROR = auto()

class StatusLevel(Enum):
    """Status message importance levels."""
    INFO = auto()
    SUCCESS = auto()
    WARNING = auto()
    ERROR = auto()

class GenerationStatus(Enum):
    """Status of generation operations."""
    QUEUED = auto()
    IN_PROGRESS = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()

class ChangeType(Enum):
    """Types of changes that can occur."""
    CREATED = auto()
    UPDATED = auto()
    DELETED = auto()
    GENERATED = auto()
    REGENERATED = auto()
    MANUAL_EDIT = auto()
    SYSTEM = auto()

class ResourceType(Enum):
    """Types of resources in the application."""
    CHARACTER = auto()
    PROMPT = auto()
    GENERATION = auto()
    IMAGE = auto()
    CONFIG = auto()

class ErrorCategory(Enum):
    """Categories of errors."""
    STATE = auto()
    FILE = auto()
    GENERATION = auto()
    VALIDATION = auto()
    NETWORK = auto()
    UI = auto()
    CONFIG = auto()

class ErrorLevel(Enum):
    """Error severity levels."""
    INFO = auto()
    WARNING = auto()
    ERROR = auto()
    CRITICAL = auto()

class TabType(Enum):
    """Types of available tabs."""
    EDITOR = auto()
    GENERATION = auto()
    SETTINGS = auto()
    PREVIEW = auto()

class DialogType(Enum):
    """Types of dialogs."""
    SAVE = auto()
    LOAD = auto()
    EXPORT = auto()
    SETTINGS = auto()
    CONFIRMATION = auto()
    ERROR = auto()

# Base dataclass for all models
from dataclasses import dataclass, field

@dataclass
class BaseModel:
    """Base model with common attributes."""
    id: ID = field(default_factory=UUID)
    created_at: Timestamp = field(default_factory=datetime.now)
    modified_at: Timestamp = field(default_factory=datetime.now)
    
    def to_dict(self) -> JsonDict:
        """Convert model to dictionary."""
        return {
            'id': str(self.id),
            'created_at': self.created_at.isoformat(),
            'modified_at': self.modified_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: JsonDict) -> 'BaseModel':
        """Create model from dictionary."""
        return cls(
            id=UUID(data['id']),
            created_at=datetime.fromisoformat(data['created_at']),
            modified_at=datetime.fromisoformat(data['modified_at'])
        )

# Result types for operations
@dataclass
class Result:
    """Generic result type for operations."""
    success: bool
    message: str
    data: Optional[Any] = None
    error: Optional[Exception] = None