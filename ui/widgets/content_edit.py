from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTextEdit, 
    QPlainTextEdit, QLabel
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFocusEvent, QFont

from .base import ContentEditWidget
from .validation import ValidationDisplay, ValidationSeverity
from core.state import UIStateManager

class EditableContentWidget(ContentEditWidget):
    """Concrete implementation of ContentEditWidget with text editing capabilities"""
    
    def __init__(self, 
                 ui_manager: UIStateManager,
                 field_name: Optional[str] = None,
                 parent: Optional[QWidget] = None,
                 multiline: bool = True,
                 placeholder_text: str = ""):
        self.multiline = multiline
        self.placeholder_text = placeholder_text
        super().__init__(ui_manager, field_name, parent)
        
        # Initialize state tracking
        self._last_content = ""
        self._is_editing = False

    def _setup_content_ui(self):
        """Setup the content editing UI"""
        # Add label if field has name
        if self.field_name:
            self._label = QLabel(self.field_name.replace('_', ' ').title())
            self._label.setObjectName("field_label")
            self._content_layout.addWidget(self._label)
        
        # Create appropriate editor
        if self.multiline:
            self._editor = QTextEdit(self)
            self._editor.setAcceptRichText(False)
            self._editor.setTabChangesFocus(True)
            self._editor.setMinimumHeight(100)
        else:
            self._editor = QPlainTextEdit(self)
            self._editor.setMaximumHeight(30)
            self._editor.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self._editor.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            self._editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        
        # Setup editor
        self._editor.setObjectName("content_editor")
        self._editor.setPlaceholderText(self.placeholder_text)
        self._content_layout.addWidget(self._editor)
        
        # Add validation display with proper layout handling
        self._validation_display = ValidationDisplay(self)
        self._content_layout.addWidget(self._validation_display)
        self._validation_display.hide()  # Start hidden
        
        # Ensure proper sizing
        self.setMinimumHeight(100)
        self.adjustSize()
        
        # Connect signals
        self._editor.textChanged.connect(self._handle_text_changed)
        # Connect focus events directly to the editor's events
        self._editor.focusInEvent = self._handle_focus_in
        self._editor.focusOutEvent = self._handle_focus_out
        
        # Make editor focusable
        self._editor.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # Setup styling
        self._setup_editor_styling()

        # Update validation display initial state
        self._validation_display.hide()

    def focusInEvent(self, event: QFocusEvent):
        """Override focus in event"""
        super().focusInEvent(event)
        self.handle_focus_in()
        self.focus_changed.emit(True)
    
    def focusOutEvent(self, event: QFocusEvent):
        """Override focus out event"""
        super().focusOutEvent(event)
        self.handle_focus_out()
        self.focus_changed.emit(False)

    def _setup_editor_styling(self):
        """Setup editor styling"""
        self.setStyleSheet("""
            QLabel#field_label {
                font-weight: bold;
                color: #2c3e50;
                margin-bottom: 4px;
            }
            
            QTextEdit#content_editor, QPlainTextEdit#content_editor {
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                padding: 8px;
                background-color: #ffffff;
            }
            
            QTextEdit#content_editor:focus, QPlainTextEdit#content_editor:focus {
                border-color: #3498db;
                background-color: #f8f9fa;
            }
            
            QTextEdit#content_editor:hover, QPlainTextEdit#content_editor:hover {
                border-color: #95a5a6;
            }
        """)

    def get_content(self) -> str:
        """Get current content"""
        if isinstance(self._editor, QTextEdit):
            return self._editor.toPlainText()
        return self._editor.toPlainText()

    def set_content(self, content: str):
        """Set content"""
        if isinstance(self._editor, QTextEdit):
            self._editor.setPlainText(content)
        else:
            self._editor.setPlainText(content)
        self._last_content = content
        self.handle_content_change()

    def clear_content(self):
        """Clear content"""
        self._editor.clear()
        self._last_content = ""
        self._is_modified = False
        self.set_validation_state(True)

    def set_read_only(self, read_only: bool):
        """Set whether content is editable"""
        self._editor.setReadOnly(read_only)

    def set_validation_state(self, is_valid: bool, message: str = ""):
        """Set validation state with message"""
        super().set_validation_state(is_valid, message)

    def _handle_text_changed(self):
        """Handle text changes in editor"""
        current_content = self.get_content()
        if current_content != self._last_content:
            self._last_content = current_content
            self._is_modified = True
            self.handle_content_change()

    def _handle_focus_in(self, event: Optional[QFocusEvent] = None):
        """Handle editor focus in"""
        if event:
            if isinstance(self._editor, QTextEdit):
                QTextEdit.focusInEvent(self._editor, event)
            else:
                QPlainTextEdit.focusInEvent(self._editor, event)
        
        self.handle_focus_in()
        self.focus_changed.emit(True)

    def _handle_focus_out(self, event: Optional[QFocusEvent] = None):
        """Handle editor focus out"""
        if event:
            if isinstance(self._editor, QTextEdit):
                QTextEdit.focusOutEvent(self._editor, event)
            else:
                QPlainTextEdit.focusOutEvent(self._editor, event)
        
        self.handle_focus_out()
        self.focus_changed.emit(False)

    def set_font(self, font: QFont):
        """Set editor font"""
        self._editor.setFont(font)

    def set_placeholder(self, text: str):
        """Set placeholder text"""
        self._editor.setPlaceholderText(text)