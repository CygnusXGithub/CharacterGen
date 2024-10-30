from enum import Enum, auto
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass, field
from datetime import datetime
import traceback
import logging

from .types import (
    CharacterGenError,
    ValidationError,
    FileOperationError,
    StateError,
    ConfigError,
    GenerationError
)

class ErrorLevel(Enum):
    """Error severity levels"""
    INFO = auto()
    WARNING = auto()
    ERROR = auto()
    CRITICAL = auto()

class ErrorCategory(Enum):
    """Categories of errors"""
    STATE = auto()
    FILE = auto()
    GENERATION = auto()
    VALIDATION = auto()
    NETWORK = auto()
    UI = auto()
    CONFIG = auto()

@dataclass
class ErrorInfo:
    """Detailed error information"""
    error_type: str
    message: str
    category: ErrorCategory
    level: ErrorLevel
    timestamp: datetime = field(default_factory=datetime.now)
    context: Dict[str, Any] = field(default_factory=dict)
    traceback: Optional[str] = None
    can_recover: bool = False
    recovery_action: Optional[Callable] = None

class ErrorHandler:
    """Centralized error handling"""

    def __init__(self):
        self.logger = logging.getLogger('ErrorHandler')
        self._error_history: List[ErrorInfo] = []
        self._recovery_handlers: Dict[str, Callable] = {}
        
    def handle_error(self, 
                    error: Exception,
                    category: ErrorCategory,
                    level: ErrorLevel = ErrorLevel.ERROR,
                    context: Optional[Dict[str, Any]] = None) -> ErrorInfo:
        """Handle an error and return error information"""
        
        # Create error info
        error_info = ErrorInfo(
            error_type=error.__class__.__name__,
            message=str(error),
            category=category,
            level=level,
            context=context or {},
            traceback=traceback.format_exc(),
            can_recover=self._has_recovery_handler(error.__class__.__name__)
        )
        
        # Add recovery action if available
        if error_info.can_recover:
            error_info.recovery_action = self._get_recovery_handler(
                error.__class__.__name__
            )
        
        # Log error
        self._log_error(error_info)
        
        # Store in history
        self._error_history.append(error_info)
        
        # Attempt recovery if possible
        if error_info.can_recover:
            try:
                error_info.recovery_action(error_info)
            except Exception as e:
                self.logger.error(f"Recovery failed: {str(e)}")
        
        return error_info

    def register_recovery_handler(self, 
                                error_type: str, 
                                handler: Callable[[ErrorInfo], None]):
        """Register a recovery handler for an error type"""
        self._recovery_handlers[error_type] = handler

    def _has_recovery_handler(self, error_type: str) -> bool:
        """Check if a recovery handler exists"""
        return error_type in self._recovery_handlers

    def _get_recovery_handler(self, error_type: str) -> Optional[Callable]:
        """Get recovery handler for error type"""
        return self._recovery_handlers.get(error_type)

    def _log_error(self, error_info: ErrorInfo):
        """Log error with appropriate level"""
        log_message = (
            f"{error_info.error_type}: {error_info.message}\n"
            f"Category: {error_info.category.name}\n"
            f"Context: {error_info.context}"
        )
        
        if error_info.level == ErrorLevel.CRITICAL:
            self.logger.critical(log_message, exc_info=True)
        elif error_info.level == ErrorLevel.ERROR:
            self.logger.error(log_message, exc_info=True)
        elif error_info.level == ErrorLevel.WARNING:
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)

    def get_error_history(self, 
                         category: Optional[ErrorCategory] = None,
                         level: Optional[ErrorLevel] = None) -> List[ErrorInfo]:
        """Get filtered error history"""
        filtered = self._error_history
        
        if category:
            filtered = [e for e in filtered if e.category == category]
        
        if level:
            filtered = [e for e in filtered if e.level == level]
            
        return filtered