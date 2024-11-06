# core/errors/handler.py
"""Centralized error handling system."""
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass, field
from datetime import datetime
import logging
import traceback
import json
from enum import Enum, auto
from pathlib import Path
from core.errors import get_error_category, get_error_level

from .types import CharacterGenError
from ..models.ui import StatusLevel

class ErrorCategory(Enum):
    """Categories of errors"""
    STATE = auto()
    FILE = auto()
    GENERATION = auto()
    VALIDATION = auto()
    NETWORK = auto()
    UI = auto()
    CONFIG = auto()

class ErrorLevel(Enum):
    """Error severity levels"""
    INFO = auto()
    WARNING = auto()
    ERROR = auto()
    CRITICAL = auto()

@dataclass
class ErrorHandlerConfig:
    """Configuration for error handler."""
    log_dir: Path = Path("logs")
    max_history: int = 1000
    persist_errors: bool = True
    error_file: str = "errors.json"

@dataclass
class ErrorInfo:
    """Detailed error information."""
    error_type: str
    message: str
    category: ErrorCategory
    level: ErrorLevel
    timestamp: datetime = field(default_factory=datetime.now)
    context: Dict[str, Any] = field(default_factory=dict)
    traceback: Optional[str] = None
    can_recover: bool = False
    recovery_action: Optional[Callable] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to serializable dictionary."""
        return {
            'error_type': self.error_type,
            'message': self.message,
            'category': self.category.name,
            'level': self.level.name,
            'timestamp': self.timestamp.isoformat(),
            'context': self.context,
            'traceback': self.traceback,
            'can_recover': self.can_recover
        }

class ErrorHandler:
    """Centralized error handling."""

    def __init__(self, config: Optional[ErrorHandlerConfig] = None):
        self.config = config or ErrorHandlerConfig()
        self.logger = logging.getLogger('ErrorHandler')
        self._error_history: List[ErrorInfo] = []
        self._recovery_handlers: Dict[str, Callable] = {}
        self._ui_callback: Optional[Callable] = None
        
        self._setup_logging()
    
    def _setup_logging(self):
        """Configure error logging"""
        self.config.log_dir.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(
            self.config.log_dir / "errors.log",
            encoding='utf-8'
        )
        file_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        )
        self.logger.addHandler(file_handler)
        
    def set_ui_callback(self, callback: Callable[[str, StatusLevel], None]):
        """Set callback for UI notifications."""
        self._ui_callback = callback

    def handle_error(self, 
                    error: Exception,
                    category: ErrorCategory,
                    level: ErrorLevel,
                    context: Optional[Dict[str, Any]] = None,
                    show_ui: bool = True) -> ErrorInfo:
        """Handle an error and return error information."""
        error_info = self._create_error_info(error, category, level, context)
        self._log_error(error_info)
        self._store_error(error_info)
        
        if show_ui and self._ui_callback:
            status_level = self._map_error_level_to_status(level)
            self._ui_callback(str(error), status_level)
            
        if error_info.can_recover:
            self._attempt_recovery(error_info)
            
        return error_info
    
    def _create_error_info(self, 
                          error: Exception,
                          category: ErrorCategory,
                          level: ErrorLevel,
                          context: Optional[Dict[str, Any]] = None) -> ErrorInfo:
        """Create error information object."""
        return ErrorInfo(
            error_type=error.__class__.__name__,
            message=str(error),
            category=category,
            level=level,
            context=context or {},
            traceback=traceback.format_exc(),
            can_recover=self._has_recovery_handler(error.__class__.__name__)
        )

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

    def _store_error(self, error_info: ErrorInfo):
        """Store error in history and optionally persist"""
        self._error_history.append(error_info)
        
        # Trim history if needed
        while len(self._error_history) > self.config.max_history:
            self._error_history.pop(0)
            
        if self.config.persist_errors:
            self._persist_errors()

    def _persist_errors(self):
        """Persist errors to file"""
        try:
            error_file = self.config.log_dir / self.config.error_file
            errors_data = [e.to_dict() for e in self._error_history]
            
            with open(error_file, 'w') as f:
                json.dump(errors_data, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to persist errors: {e}")

    def _map_error_level_to_status(self, level: ErrorLevel) -> StatusLevel:
        """Map error level to UI status level."""
        mapping = {
            ErrorLevel.CRITICAL: StatusLevel.ERROR,
            ErrorLevel.ERROR: StatusLevel.ERROR,
            ErrorLevel.WARNING: StatusLevel.WARNING,
            ErrorLevel.INFO: StatusLevel.INFO
        }
        return mapping.get(level, StatusLevel.ERROR)

    def register_recovery_handler(self, 
                                error_type: str, 
                                handler: Callable[[ErrorInfo], None]):
        """Register a recovery handler for an error type"""
        self._recovery_handlers[error_type] = handler

    def _has_recovery_handler(self, error_type: str) -> bool:
        """Check if a recovery handler exists"""
        return error_type in self._recovery_handlers

    def _attempt_recovery(self, error_info: ErrorInfo):
        """Attempt to recover from an error"""
        try:
            handler = self._recovery_handlers.get(error_info.error_type)
            if handler:
                handler(error_info)
        except Exception as e:
            self.logger.error(f"Recovery failed: {str(e)}")

    def get_error_history(self, 
                         category: Optional[ErrorCategory] = None,
                         level: Optional[ErrorLevel] = None) -> List[ErrorInfo]:
        """Get filtered error history"""
        filtered = self._error_history[:]
        
        if category:
            filtered = [e for e in filtered if e.category == category]
        
        if level:
            filtered = [e for e in filtered if e.level == level]
            
        return filtered