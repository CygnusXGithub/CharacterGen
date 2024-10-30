from typing import Optional, Any, Dict
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QFrame
from PyQt6.QtCore import pyqtSignal, Qt

from core.state import UIStateManager
from core.errors import ErrorHandler, ErrorCategory, ErrorLevel

class BaseWidget(QWidget):
    """Base class for all application widgets"""
    
    state_changed = pyqtSignal(str, object)  # Signal for state changes
    error_occurred = pyqtSignal(str, str)    # Signal for errors

    def __init__(self, 
                 ui_manager: UIStateManager,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.ui_manager = ui_manager
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        
        # Setup widget
        self._setup_ui()
        self._connect_signals()
        self._setup_styling()

    def _setup_ui(self):
        """Setup widget UI - override in subclasses"""
        pass

    def _connect_signals(self):
        """Connect signals to slots - override in subclasses"""
        pass

    def _setup_styling(self):
        """Setup widget styling"""
        self.setObjectName(self.__class__.__name__)

    def update_state(self, key: str, value: Any):
        """Update widget state"""
        try:
            self.state_changed.emit(key, value)
        except Exception as e:
            self.error_occurred.emit("state_update_error", str(e))

    def handle_error(self, error_type: str, message: str):
        """Handle widget errors"""
        self.error_occurred.emit(error_type, message)

class ContentEditWidget(BaseWidget):
    """Base class for content-editable widgets"""
    
    content_changed = pyqtSignal(str)
    focus_changed = pyqtSignal(bool)
    validation_changed = pyqtSignal(bool, str)

    def __init__(self, 
                 ui_manager: UIStateManager,
                 field_name: Optional[str] = None,
                 parent: Optional[QWidget] = None):
        self.field_name = field_name
        super().__init__(ui_manager, parent)
        
        self._is_valid = True
        self._validation_message = ""
        self._is_modified = False
        
        # Setup content frame
        self._content_frame = QFrame(self)
        self._content_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self._content_frame.setFrameShadow(QFrame.Shadow.Raised)
        self._layout.addWidget(self._content_frame)
        
        # Content layout
        self._content_layout = QVBoxLayout(self._content_frame)
        self._content_layout.setContentsMargins(8, 8, 8, 8)
        self._content_layout.setSpacing(4)
        
        self._setup_content_ui()

    def _setup_content_ui(self):
        """Setup content editing UI - override in subclasses"""
        pass

    def get_content(self) -> str:
        """Get current content - override in subclasses"""
        return ""

    def set_content(self, content: str):
        """Set content - override in subclasses"""
        pass

    def clear_content(self):
        """Clear content"""
        self.set_content("")
        self._is_modified = False

    def is_valid(self) -> bool:
        """Check if content is valid"""
        return self._is_valid

    def set_validation_state(self, is_valid: bool, message: str = ""):
        """Set validation state"""
        self._is_valid = is_valid
        self._validation_message = message
        self.validation_changed.emit(is_valid, message)
        
        # Update visual state
        self._update_validation_display()

    def _update_validation_display(self):
        """Update validation visual state"""
        if not self._is_valid:
            self._content_frame.setStyleSheet("""
                QFrame {
                    border: 1px solid #ff0000;
                    background-color: #fff0f0;
                }
            """)
        else:
            self._content_frame.setStyleSheet("")

    def handle_focus_in(self):
        """Handle widget focus in"""
        self.focus_changed.emit(True)
        if self.field_name:
            self.ui_manager.set_field_state(
                self.field_name,
                {'is_focused': True}
            )

    def handle_focus_out(self):
        """Handle widget focus out"""
        self.focus_changed.emit(False)
        if self.field_name:
            self.ui_manager.set_field_state(
                self.field_name,
                {'is_focused': False}
            )

    def handle_content_change(self):
        """Handle content changes"""
        content = self.get_content()
        self._is_modified = True
        self.content_changed.emit(content)
        
        if self.field_name:
            self.ui_manager.set_field_state(
                self.field_name,
                {
                    'content': content,
                    'is_modified': True
                }
            )

class ExpandableWidget(ContentEditWidget):
    """Base class for expandable widgets"""
    
    expanded_changed = pyqtSignal(bool)

    def __init__(self, 
                 ui_manager: UIStateManager,
                 field_name: Optional[str] = None,
                 parent: Optional[QWidget] = None):
        super().__init__(ui_manager, field_name, parent)
        self._is_expanded = False
        
        # Setup expansion handling
        self._setup_expansion()

    def _setup_expansion(self):
        """Setup expansion handling - override in subclasses"""
        pass

    def is_expanded(self) -> bool:
        """Check if widget is expanded"""
        return self._is_expanded

    def set_expanded(self, expanded: bool):
        """Set expansion state"""
        if self._is_expanded != expanded:
            self._is_expanded = expanded
            self.expanded_changed.emit(expanded)
            self._update_expansion_state()
            
            if self.field_name:
                self.ui_manager.set_field_state(
                    self.field_name,
                    {'is_expanded': expanded}
                )

    def _update_expansion_state(self):
        """Update expansion visual state - override in subclasses"""
        pass

    def toggle_expansion(self):
        """Toggle expansion state"""
        self.set_expanded(not self._is_expanded)