from typing import Any, Dict, Set, Optional, List, TypeVar, Generic
from dataclasses import dataclass, field
from datetime import datetime
import threading
import asyncio
from contextlib import contextmanager
from PyQt6.QtCore import QObject, pyqtSignal
import logging

from ..common.types import Result, JsonDict
from ..errors import ErrorHandler, ErrorCategory, ErrorLevel

@dataclass
class StateChangeEvent:
    """Container for state change information"""
    key: str
    old_value: Any
    new_value: Any
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = ""
    metadata: JsonDict = field(default_factory=dict)

@dataclass 
class OperationContext:
    """Context for state operations"""
    operation_name: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: JsonDict = field(default_factory=dict)
    parent_operation: Optional[str] = None

T = TypeVar('T')

class StateManagerBase(QObject, Generic[T]):
    """Base class for all state managers"""
    
    # Core signals
    state_changed = pyqtSignal(str, object)  # (state_key, new_value)
    error_occurred = pyqtSignal(str, str)    # (error_type, message)
    operation_started = pyqtSignal(str, dict) # (operation_name, context)
    operation_completed = pyqtSignal(str, dict) # (operation_name, context)
    operation_failed = pyqtSignal(str, str, dict) # (operation_name, error, context)

    def __init__(self, error_handler: ErrorHandler):
        """Initialize state manager with error handler"""
        super().__init__()
        self.error_handler = error_handler
        self._state: Dict[str, T] = {}
        self._operation_lock = threading.RLock()  # Reentrant lock for nested operations
        self._async_lock = asyncio.Lock()  # For async operations
        self._observers: Set[str] = set()
        self._operation_stack: List[OperationContext] = []
        self._state_history: List[StateChangeEvent] = []
        self._max_history: int = 1000  # Configurable history limit
        self.logger = logging.getLogger(self.__class__.__name__)

    async def get_state(self, key: str, default: Any = None) -> Result[T]:
        """Thread-safe async state access"""
        try:
            async with self._async_lock:
                value = self._state.get(key, default)
                return Result(True, f"State retrieved: {key}", value)
        except Exception as e:
            self.error_handler.handle_error(
                e, ErrorCategory.STATE, ErrorLevel.ERROR,
                {'operation': 'get_state', 'key': key}
            )
            return Result(False, f"Failed to get state: {str(e)}", error=e)

    async def update_state(self, 
                         key: str, 
                         value: T, 
                         emit: bool = True, 
                         metadata: Optional[JsonDict] = None) -> Result:
        """Thread-safe async state update"""
        try:
            async with self._async_lock:
                old_value = self._state.get(key)
                if old_value == value:
                    return Result(True, "State unchanged")

                self._state[key] = value
                
                # Record change
                event = StateChangeEvent(
                    key=key,
                    old_value=old_value,
                    new_value=value,
                    source=self._get_current_operation(),
                    metadata=metadata or {}
                )
                await self._record_state_change(event)
                
                if emit:
                    self.state_changed.emit(key, value)
                
                return Result(True, "State updated successfully")

        except Exception as e:
            self.error_handler.handle_error(
                e, ErrorCategory.STATE, ErrorLevel.ERROR,
                {'operation': 'update_state', 'key': key}
            )
            return Result(False, f"Failed to update state: {str(e)}", error=e)

    async def batch_update(self, 
                          updates: Dict[str, T], 
                          emit: bool = True,
                          metadata: Optional[JsonDict] = None) -> Result:
        """Perform multiple state updates atomically"""
        try:
            async with self._async_lock:
                # Store old values
                old_values = {
                    key: self._state.get(key) 
                    for key in updates
                }
                
                # Apply all updates
                for key, value in updates.items():
                    self._state[key] = value
                    
                    # Record each change
                    event = StateChangeEvent(
                        key=key,
                        old_value=old_values[key],
                        new_value=value,
                        source=self._get_current_operation(),
                        metadata=metadata or {}
                    )
                    await self._record_state_change(event)
                
                # Emit changes if requested
                if emit:
                    for key, value in updates.items():
                        self.state_changed.emit(key, value)
                
                return Result(True, "Batch update completed successfully")

        except Exception as e:
            # Rollback on error
            self._state.update(old_values)
            self.error_handler.handle_error(
                e, ErrorCategory.STATE, ErrorLevel.ERROR,
                {'operation': 'batch_update'}
            )
            return Result(False, f"Batch update failed: {str(e)}", error=e)

    @contextmanager
    def operation(self, 
                 name: str, 
                 metadata: Optional[JsonDict] = None):
        """Context manager for operations with error handling"""
        try:
            context = OperationContext(
                operation_name=name,
                metadata=metadata or {},
                parent_operation=self._get_current_operation()
            )
            self._operation_stack.append(context)
            self.operation_started.emit(name, context.metadata)
            yield context
            self._operation_stack.pop()
            self.operation_completed.emit(name, context.metadata)
            
        except Exception as e:
            self._operation_stack.pop()
            self.operation_failed.emit(name, str(e), context.metadata)
            self.error_handler.handle_error(
                e, ErrorCategory.STATE, ErrorLevel.ERROR,
                {'operation': 'operation_context', 'name': name}
            )
            raise

    async def _record_state_change(self, event: StateChangeEvent) -> None:
        """Record state change in history"""
        self._state_history.append(event)
        
        # Trim history if needed
        while len(self._state_history) > self._max_history:
            self._state_history.pop(0)

    def _get_current_operation(self) -> str:
        """Get the name of the current operation"""
        return self._operation_stack[-1].operation_name if self._operation_stack else ""

    async def get_state_history(self, 
                              key: Optional[str] = None, 
                              limit: Optional[int] = None) -> Result[List[StateChangeEvent]]:
        """Get state change history, optionally filtered by key"""
        try:
            async with self._async_lock:
                history = self._state_history
                
                if key:
                    history = [event for event in history if event.key == key]
                if limit:
                    history = history[-limit:]
                    
                return Result(True, "History retrieved successfully", history)
                
        except Exception as e:
            self.error_handler.handle_error(
                e, ErrorCategory.STATE, ErrorLevel.ERROR,
                {'operation': 'get_history', 'key': key}
            )
            return Result(False, f"Failed to get history: {str(e)}", error=e)

    async def clear_history(self) -> Result:
        """Clear state change history"""
        try:
            async with self._async_lock:
                self._state_history.clear()
                return Result(True, "History cleared successfully")
        except Exception as e:
            self.error_handler.handle_error(
                e, ErrorCategory.STATE, ErrorLevel.ERROR,
                {'operation': 'clear_history'}
            )
            return Result(False, f"Failed to clear history: {str(e)}", error=e)

    def get_current_operation_context(self) -> Optional[OperationContext]:
        """Get the current operation context"""
        return self._operation_stack[-1] if self._operation_stack else None