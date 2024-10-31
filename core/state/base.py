from typing import Any, Dict, Set, Optional, TypeVar, Generic, List
from dataclasses import dataclass, field
from datetime import datetime
import threading
from contextlib import contextmanager
from PyQt6.QtCore import QObject, pyqtSignal
import logging


@dataclass
class StateChangeEvent:
    """Container for state change information"""
    key: str
    old_value: Any
    new_value: Any
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = ""

class StateManagerBase(QObject):
    """Base class for all state managers"""
    
    # Core signals
    state_changed = pyqtSignal(str, object)  # (state_key, new_value)
    error_occurred = pyqtSignal(str, str)    # (error_type, message)
    operation_started = pyqtSignal(str, dict) # (operation_name, context)
    operation_completed = pyqtSignal(str, dict) # (operation_name, context)
    operation_failed = pyqtSignal(str, str, dict) # (operation_name, error, context)

    def __init__(self):
        super().__init__()
        self._state: Dict[str, Any] = {}
        self._operation_lock = threading.RLock()  # Reentrant lock for nested operations
        self._observers: Set[str] = set()
        self._operation_stack: List[str] = []
        self._state_history: List[StateChangeEvent] = []
        self.logger = logging.getLogger(self.__class__.__name__)

    def get_state(self, key: str, default: Any = None) -> Any:
        """Thread-safe state access"""
        with self._operation_lock:
            return self._state.get(key, default)

    def update_state(self, key: str, value: Any, emit: bool = True) -> bool:
        """Thread-safe state update"""
        with self._operation_lock:
            old_value = self._state.get(key)
            if old_value == value:
                return False

            self._state[key] = value
            
            if emit:
                self.state_changed.emit(key, value)
            
            return True

    @contextmanager
    def operation(self, name: str, context: Optional[Dict] = None):
        """Context manager for operations"""
        context = context or {}
        try:
            self._operation_stack.append(name)
            self.operation_started.emit(name, context)
            yield
            self._operation_stack.pop()
            self.operation_completed.emit(name, context)
        except Exception as e:
            self._operation_stack.pop()
            self.operation_failed.emit(name, str(e), context)
            raise

    def batch_update(self, updates: Dict[str, Any], emit: bool = True) -> bool:
        """Perform multiple state updates atomically"""
        with self._operation_lock:
            try:
                # Store old values
                old_values = {
                    key: self._state.get(key) 
                    for key in updates
                }
                
                # Apply all updates
                for key, value in updates.items():
                    self._state[key] = value
                    
                    # Record state change
                    event = StateChangeEvent(
                        key=key,
                        old_value=old_values[key],
                        new_value=value,
                        source=self._get_current_operation()
                    )
                    self._state_history.append(event)
                
                # Emit changes if requested
                if emit:
                    for key, value in updates.items():
                        self.state_changed.emit(key, value)
                
                return True
                
            except Exception as e:
                # Rollback on error
                self._state.update(old_values)
                self.logger.error(f"Batch update failed: {str(e)}")
                self.error_occurred.emit("batch_update_error", str(e))
                return False

    def start_operation(self, name: str, context: Optional[Dict] = None):
        """Start a new operation"""
        self._operation_stack.append(name)
        self.operation_started.emit(name, context or {})

    def complete_operation(self, name: str, context: Optional[Dict] = None):
        """Complete an operation"""
        if self._operation_stack and self._operation_stack[-1] == name:
            self._operation_stack.pop()
            self.operation_completed.emit(name, context or {})

    def fail_operation(self, name: str, error: str, context: Optional[Dict] = None):
        """Mark an operation as failed"""
        if self._operation_stack and self._operation_stack[-1] == name:
            self._operation_stack.pop()
            self.operation_failed.emit(name, error, context or {})

    def _get_current_operation(self) -> str:
        """Get the name of the current operation"""
        return self._operation_stack[-1] if self._operation_stack else ""

    def clear_history(self):
        """Clear state change history"""
        with self._operation_lock:
            self._state_history.clear()

    def get_history(self, key: Optional[str] = None) -> List[StateChangeEvent]:
        """Get state change history, optionally filtered by key"""
        with self._operation_lock:
            if key is None:
                return list(self._state_history)
            return [event for event in self._state_history if event.key == key]