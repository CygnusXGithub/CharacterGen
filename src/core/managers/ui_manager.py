from typing import Optional, Dict, List, Tuple, Union
from enum import Enum
from dataclasses import dataclass
import logging
from PyQt6.QtCore import QObject, pyqtSignal, Qt, QTimer

from ..enums import FieldName, UIMode, StatusLevel

@dataclass
class FieldState:
    """State information for a field"""
    is_expanded: bool = False
    is_focused: bool = False
    mode: UIMode = UIMode.COMPACT
    scroll_position: int = 0
    original_height: Optional[int] = None

class TabType(Enum):
    """Types of tabs in the application"""
    EDITOR = "editor"
    GENERATION = "generation"
    BASE_PROMPTS = "base_prompts"

class UIStateManager(QObject):
    """Manages UI state and interactions"""
    
    # Tab state signals
    tab_changed = pyqtSignal(str)
    tab_state_changed = pyqtSignal(TabType, dict)  # Tab-specific state updates
    
    # Field state signals
    field_expanded = pyqtSignal(FieldName, bool)
    field_focused = pyqtSignal(FieldName, bool)
    field_mode_changed = pyqtSignal(FieldName, UIMode)
    
    # UI state signals
    status_message = pyqtSignal(str, int)  # message, timeout
    theme_changed = pyqtSignal(str)
    layout_changed = pyqtSignal()
    
    # Dialog signals
    dialog_requested = pyqtSignal(str, dict)  # dialog_type, parameters
    
    def __init__(self):
        super().__init__()
        self._current_tab: Optional[TabType] = None
        self._field_states: Dict[FieldName, FieldState] = {}
        self._tab_states: Dict[TabType, Dict] = {
            tab_type: {} for tab_type in TabType
        }
        self._expanded_fields: List[FieldName] = []
        self._focused_field: Optional[FieldName] = None
        self._status_message: str = ""
        self._theme: str = "light"
        self._status_timeout = QTimer()
        self._status_timeout.setSingleShot(True)
        self._status_timeout.timeout.connect(self._clear_status)
        self._current_status = ""
        self._current_status_level = StatusLevel.INFO
        
        # Initialize field states
        for field in FieldName:
            self._field_states[field] = FieldState()
    
    @property
    def current_tab(self) -> Optional[TabType]:
        """Get current active tab"""
        return self._current_tab
    
    def show_status_message(self, message: str, level: StatusLevel = StatusLevel.INFO, timeout: int = 3000):
        """Show status message with optional timeout"""
        self._current_status = message
        self._current_status_level = level
        self.status_message.emit(message, level)
        
        if timeout > 0:
            self._status_timeout.start(timeout)
    
    def _clear_status(self):
        """Clear current status message"""
        self._current_status = ""
        self._current_status_level = StatusLevel.INFO
        self.status_message.emit("", StatusLevel.INFO)
    
    def get_current_status(self) -> tuple[str, StatusLevel]:
        """Get current status message and level"""
        return self._current_status, self._current_status_level
    
    def set_current_tab(self, tab: TabType):
        """Set current active tab"""
        if self._current_tab != tab:
            self._current_tab = tab
            self.tab_changed.emit(tab.value)
    
    def toggle_field_expansion(self, field: FieldName):
        """Toggle field expansion state"""
        try:
            current_state = self._field_states[field]
            new_state = not current_state.is_expanded
            
            # Update state
            current_state.is_expanded = new_state
            
            # Update expanded fields list
            if new_state:
                if field not in self._expanded_fields:
                    self._expanded_fields.append(field)
            else:
                if field in self._expanded_fields:
                    self._expanded_fields.remove(field)
            
            # Emit signal
            self.field_expanded.emit(field, new_state)
            
        except Exception as e:
            logging.error(f"Error toggling field expansion: {str(e)}")
    
    def set_field_focus(self, field: Optional[FieldName]):
        """Set field focus"""
        try:
            # Clear previous focus
            if self._focused_field and self._focused_field != field:
                prev_state = self._field_states[self._focused_field]
                prev_state.is_focused = False
                self.field_focused.emit(self._focused_field, False)
            
            # Set new focus
            self._focused_field = field
            if field:
                current_state = self._field_states[field]
                current_state.is_focused = True
                self.field_focused.emit(field, True)
                
        except Exception as e:
            logging.error(f"Error setting field focus: {str(e)}")
    
    def set_field_mode(self, field: FieldName, mode: UIMode):
        """Set field UI mode"""
        try:
            current_state = self._field_states[field]
            if current_state.mode != mode:
                current_state.mode = mode
                self.field_mode_changed.emit(field, mode)
                
        except Exception as e:
            logging.error(f"Error setting field mode: {str(e)}")
    
    def save_field_state(self, field: FieldName, scroll_pos: int, height: int):
        """Save field state for restoration"""
        try:
            state = self._field_states[field]
            state.scroll_position = scroll_pos
            state.original_height = height
            
        except Exception as e:
            logging.error(f"Error saving field state: {str(e)}")
    
    def get_field_state(self, field: FieldName) -> FieldState:
        """Get current field state"""
        return self._field_states.get(field, FieldState())
    
    def save_tab_state(self, tab: TabType, state: dict):
        """Save tab-specific state"""
        try:
            self._tab_states[tab].update(state)
            self.tab_state_changed.emit(tab, self._tab_states[tab])
            
        except Exception as e:
            logging.error(f"Error saving tab state: {str(e)}")
    
    def get_tab_state(self, tab: TabType) -> dict:
        """Get tab-specific state"""
        return self._tab_states.get(tab, {})
    
    def show_status_message(self, message: str, level: Union[StatusLevel, int] = StatusLevel.INFO):
        """Show status message with optional timeout"""
        # Convert int to StatusLevel if needed
        if isinstance(level, int):
            level = {
                0: StatusLevel.INFO,
                1: StatusLevel.SUCCESS,
                2: StatusLevel.WARNING,
                3: StatusLevel.ERROR
            }.get(level, StatusLevel.INFO)
        
        self._current_status = message
        self._current_status_level = level
        self.status_message.emit(message, level)
    
    def set_theme(self, theme: str):
        """Set UI theme"""
        try:
            if self._theme != theme:
                self._theme = theme
                self.theme_changed.emit(theme)
                
        except Exception as e:
            logging.error(f"Error setting theme: {str(e)}")
    
    def request_dialog(self, dialog_type: str, parameters: dict = None):
        """Request dialog display"""
        try:
            self.dialog_requested.emit(dialog_type, parameters or {})
            
        except Exception as e:
            logging.error(f"Error requesting dialog: {str(e)}")
    
    def get_expanded_fields(self) -> List[FieldName]:
        """Get list of currently expanded fields"""
        return self._expanded_fields.copy()
    
    def get_focused_field(self) -> Optional[FieldName]:
        """Get currently focused field"""
        return self._focused_field
    
    def clear_field_states(self):
        """Clear all field states"""
        try:
            for field in self._field_states:
                state = self._field_states[field]
                
                if state.is_expanded:
                    state.is_expanded = False
                    self.field_expanded.emit(field, False)
                
                if state.is_focused:
                    state.is_focused = False
                    self.field_focused.emit(field, False)
                
                state.mode = UIMode.COMPACT
                state.scroll_position = 0
                state.original_height = None
            
            self._expanded_fields.clear()
            self._focused_field = None
            
        except Exception as e:
            logging.error(f"Error clearing field states: {str(e)}")
    
    def restore_field_states(self, states: Dict[FieldName, FieldState]):
        """Restore saved field states"""
        try:
            for field, state in states.items():
                if field in self._field_states:
                    self._field_states[field] = state
                    
                    if state.is_expanded:
                        if field not in self._expanded_fields:
                            self._expanded_fields.append(field)
                        self.field_expanded.emit(field, True)
                    
                    if state.is_focused:
                        self._focused_field = field
                        self.field_focused.emit(field, True)
                    
                    self.field_mode_changed.emit(field, state.mode)
                    
        except Exception as e:
            logging.error(f"Error restoring field states: {str(e)}")