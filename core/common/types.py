"""Base types and enums for the entire application."""
from enum import Enum, auto
from typing import (
    NewType, Dict, Any, Union, TypeVar, Optional, 
    Generic, List, Type, Callable
)
from pathlib import Path
from datetime import datetime
from uuid import UUID
from dataclasses import dataclass, field
import asyncio

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

@dataclass
class Result(Generic[T]):
    """Generic result type for operations."""
    success: bool
    message: str
    data: Optional[T] = None
    error: Optional[Exception] = None
    metadata: JsonDict = field(default_factory=dict)

    @classmethod
    def from_error(cls, error: Exception, context: Optional[Dict] = None) -> 'Result[T]':
        """Create Result from exception with optional context."""
        return cls(
            success=False,
            message=str(error),
            error=error,
            metadata=context or {}
        )

    @classmethod
    def success(cls, message: str = "Operation successful", data: Optional[T] = None) -> 'Result[T]':
        """Create successful Result."""
        return cls(True, message, data)

    @classmethod
    def failure(cls, message: str, error: Optional[Exception] = None) -> 'Result[T]':
        """Create failure Result."""
        return cls(False, message, error=error)

    def ensure_type(self, expected_type: Type[T]) -> 'Result[T]':
        """Ensure Result data is of expected type."""
        if not self.success or self.data is None:
            return self
        if not isinstance(self.data, expected_type):
            return Result(False, f"Expected {expected_type.__name__}, got {type(self.data).__name__}")
        return self

    async def ensure_success(self) -> 'Result[T]':
        """Raise exception if Result is failure, otherwise return self."""
        if not self.success:
            if self.error:
                raise self.error
            raise RuntimeError(self.message)
        return self

    def map(self, func: Callable[[T], Any]) -> 'Result[Any]':
        """Map successful Result data through function."""
        if not self.success or self.data is None:
            return self
        try:
            return Result(
                True,
                self.message,
                func(self.data),
                metadata=self.metadata
            )
        except Exception as e:
            return Result.from_error(e)

    def bind(self, func: Callable[[T], 'Result[Any]']) -> 'Result[Any]':
        """Chain Result operations."""
        if not self.success or self.data is None:
            return self
        try:
            return func(self.data)
        except Exception as e:
            return Result.from_error(e)

@dataclass
class AsyncLock:
    """Named async lock with tracking."""
    name: str
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    last_acquired: Optional[datetime] = None
    last_released: Optional[datetime] = None
    
    async def acquire(self, timeout: float = 30.0) -> Result[bool]:
        """Acquire lock with timeout."""
        try:
            async with asyncio.timeout(timeout):
                await self.lock.acquire()
                self.last_acquired = datetime.now()
                return Result.success("Lock acquired", True)
        except asyncio.TimeoutError:
            return Result.failure(f"Lock acquisition timeout after {timeout}s")
        except Exception as e:
            return Result.from_error(e)
    
    def release(self) -> None:
        """Release lock."""
        self.lock.release()
        self.last_released = datetime.now()

@dataclass
class OperationContext:
    """Context for tracking operations."""
    name: str
    metadata: JsonDict = field(default_factory=dict)
    start_time: datetime = field(default_factory=datetime.now)
    complete_time: Optional[datetime] = None
    error: Optional[Exception] = None
    
    @property
    def duration_ms(self) -> Optional[float]:
        """Get operation duration in milliseconds."""
        if not self.complete_time:
            return None
        return (self.complete_time - self.start_time).total_seconds() * 1000
    
    def complete(self, error: Optional[Exception] = None) -> None:
        """Mark operation as complete."""
        self.complete_time = datetime.now()
        self.error = error
        self.metadata['duration_ms'] = self.duration_ms

class DataValidationError(Exception):
    """Raised when data validation fails."""
    pass

class ResourceNotFoundError(Exception):
    """Raised when a required resource is not found."""
    pass

class OperationTimeoutError(Exception):
    """Raised when an operation times out."""
    pass

class InvalidStateError(Exception):
    """Raised when operation is invalid for current state."""
    pass