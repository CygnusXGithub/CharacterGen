from typing import Optional, Dict, Any, List
from datetime import datetime
import logging
from PyQt6.QtCore import pyqtSignal

from .base import StateManagerBase
from ..models.ui import (
    UIState, FieldState, DialogInfo, StatusInfo,
    TabType, DialogType, StatusLevel
)
from ..errors import ErrorHandler, StateError, ErrorCategory, ErrorLevel

class UIStateManager(StateManagerBase):
    """Manages UI state and interactions"""
    
    # Additional signals
    tab_changed = pyqtSignal(TabType)
    field_expanded = pyqtSignal(str, bool)
    field_focused = pyqtSignal(str, bool)
    dialog_requested = pyqtSignal(DialogInfo)
    dialog_closed = pyqtSignal(DialogType)
    status_updated = pyqtSignal(StatusInfo)
    loading_changed = pyqtSignal(bool)

    def __init__(self, error_handler: ErrorHandler):
        super().__init__()
        self.error_handler = error_handler
        self.logger = logging.getLogger(__name__)
        self._initialize_state()

    def _initialize_state(self):
        """Initialize empty UI state"""
        self._state = UIState()

    def switch_tab(self, tab: TabType):
        """Switch current tab"""
        try:
            with self.operation('switch_tab', {'tab': tab.name}):
                if tab != self._state.current_tab:
                    self._state.current_tab = tab
                    self.tab_changed.emit(tab)
                    self.state_changed.emit('current_tab', tab)
        except Exception as e:
            self.error_handler.handle_error(
                error=e,
                category=ErrorCategory.UI,
                level=ErrorLevel.ERROR,
                context={'operation': 'switch_tab', 'tab': tab.name}
            )

    def set_field_state(self, field_name: str, updates: Dict[str, Any]):
        """Update field state"""
        try:
            with self.operation('update_field_state', {'field': field_name}):
                if field_name not in self._state.field_states:
                    self._state.field_states[field_name] = FieldState()

                field_state = self._state.field_states[field_name]
                
                # Update provided fields
                for key, value in updates.items():
                    if hasattr(field_state, key):
                        setattr(field_state, key, value)
                
                # Handle special states
                if 'is_expanded' in updates:
                    if updates['is_expanded']:
                        if field_name not in self._state.expanded_fields:
                            self._state.expanded_fields.append(field_name)
                    else:
                        if field_name in self._state.expanded_fields:
                            self._state.expanded_fields.remove(field_name)
                    self.field_expanded.emit(field_name, updates['is_expanded'])

                if 'is_focused' in updates:
                    if updates['is_focused']:
                        if self._state.focused_field and self._state.focused_field != field_name:
                            self._clear_focus(self._state.focused_field)
                        self._state.focused_field = field_name
                    elif self._state.focused_field == field_name:
                        self._state.focused_field = None
                    self.field_focused.emit(field_name, updates['is_focused'])

                # Update last modified if content changed
                if 'content' in updates:
                    field_state.last_modified = datetime.now()
                    field_state.is_modified = True

                self.state_changed.emit('field_state', {
                    'field': field_name,
                    'updates': updates
                })

        except Exception as e:
            self.error_handler.handle_error(
                error=e,
                category=ErrorCategory.UI,
                level=ErrorLevel.ERROR,
                context={'operation': 'set_field_state', 'field': field_name}
            )

    def show_dialog(self, dialog_info: DialogInfo):
        """Show a dialog"""
        try:
            with self.operation('show_dialog', {'type': dialog_info.dialog_type.name}):
                self._state.dialog_stack.append(dialog_info)
                self.dialog_requested.emit(dialog_info)
                self.state_changed.emit('dialog_stack', self._state.dialog_stack)
        except Exception as e:
            self.error_handler.handle_error(
                error=e,
                category=ErrorCategory.UI,
                level=ErrorLevel.ERROR,
                context={'operation': 'show_dialog', 'dialog_type': dialog_info.dialog_type.name}
            )

    def close_dialog(self, dialog_type: Optional[DialogType] = None):
        """Close the top dialog or a specific dialog type"""
        try:
            with self.operation('close_dialog'):
                if not self._state.dialog_stack:
                    return

                if dialog_type:
                    # Remove specific dialog type
                    self._state.dialog_stack = [
                        d for d in self._state.dialog_stack 
                        if d.dialog_type != dialog_type
                    ]
                else:
                    # Remove top dialog
                    dialog = self._state.dialog_stack.pop()
                    dialog_type = dialog.dialog_type

                self.dialog_closed.emit(dialog_type)
                self.state_changed.emit('dialog_stack', self._state.dialog_stack)
        except Exception as e:
            self.error_handler.handle_error(
                error=e,
                category=ErrorCategory.UI,
                level=ErrorLevel.ERROR,
                context={'operation': 'close_dialog'}
            )

    def show_status(self, message: str, level: StatusLevel, duration: int = 5000):
        """Show status message"""
        try:
            with self.operation('show_status'):
                status = StatusInfo(
                    message=message,
                    level=level,
                    duration=duration
                )
                self._state.status_message = status
                self.status_updated.emit(status)
                self.state_changed.emit('status_message', status)
        except Exception as e:
            self.error_handler.handle_error(
                error=e,
                category=ErrorCategory.UI,
                level=ErrorLevel.ERROR,
                context={'operation': 'show_status'}
            )

    def set_loading(self, is_loading: bool):
        """Set loading state"""
        try:
            with self.operation('set_loading', {'loading': is_loading}):
                if self._state.is_loading != is_loading:
                    self._state.is_loading = is_loading
                    self.loading_changed.emit(is_loading)
                    self.state_changed.emit('is_loading', is_loading)
        except Exception as e:
            self.error_handler.handle_error(
                error=e,
                category=ErrorCategory.UI,
                level=ErrorLevel.ERROR,
                context={'operation': 'set_loading'}
            )

    def handle_character_state_change(self, key: str, value: Any):
        """Handle character state changes"""
        try:
            if key == 'field_updated':
                field_name = value['field']
                self.set_field_state(field_name, {
                    'content': value['value'],
                    'is_modified': True
                })
        except Exception as e:
            self.error_handler.handle_error(
                error=e,
                category=ErrorCategory.UI,
                level=ErrorLevel.ERROR,
                context={'operation': 'handle_character_state_change'}
            )

    def _clear_focus(self, field_name: str):
        """Clear focus from a field"""
        self.set_field_state(field_name, {'is_focused': False})

    def get_field_state(self, field_name: str) -> Optional[FieldState]:
        """Get state for a specific field"""
        return self._state.field_states.get(field_name)