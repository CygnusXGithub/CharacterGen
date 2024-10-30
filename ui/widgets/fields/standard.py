from typing import Optional, Any, Dict
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QFrame,
    QSizePolicy, QTextEdit, QPlainTextEdit
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QIcon

from ..content_edit import EditableContentWidget
from ..validation import ValidationDisplay, ValidationSeverity
from core.state import UIStateManager

class StandardField(EditableContentWidget):
    """Standard field component with full feature set"""
    
    # Additional signals
    help_requested = pyqtSignal()
    generate_requested = pyqtSignal()
    clear_requested = pyqtSignal()
    
    def __init__(
        self,
        ui_manager: UIStateManager,
        field_name: str,
        label: str = "",
        placeholder: str = "",
        multiline: bool = True,
        help_text: str = "",
        required: bool = False,
        parent: Optional[QWidget] = None
    ):
        self.label_text = label or field_name.replace('_', ' ').title()
        self.help_text = help_text
        self.required = required
        
        super().__init__(
            ui_manager=ui_manager,
            field_name=field_name,
            parent=parent,
            multiline=multiline,
            placeholder_text=placeholder
        )
        
        self._setup_field_styling()

    def _setup_content_ui(self):
        """Setup the complete field UI"""
        # Header layout (label + buttons)
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)
        
        # Field label with required indicator
        label_text = f"{self.label_text} *" if self.required else self.label_text
        self._label = QLabel(label_text)
        self._label.setObjectName("field_label")
        header_layout.addWidget(self._label)
        
        # Spacer
        header_layout.addStretch()
        
        # Action buttons
        self._setup_buttons(header_layout)
        self._content_layout.addLayout(header_layout)
        
        # Help text if provided
        if self.help_text:
            help_label = QLabel(self.help_text)
            help_label.setObjectName("help_text")
            help_label.setWordWrap(True)
            help_label.setStyleSheet("""
                QLabel {
                    color: #7f8c8d;
                    font-size: 11px;
                    margin-bottom: 4px;
                }
            """)
            self._content_layout.addWidget(help_label)
        
        # Editor
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
        
        self._editor.setObjectName("field_editor")
        self._editor.setPlaceholderText(self.placeholder_text)
        self._content_layout.addWidget(self._editor)
        
        # Validation display
        self._validation_display = ValidationDisplay(self)
        self._content_layout.addWidget(self._validation_display)
        self._validation_display.hide()

    def _setup_buttons(self, layout: QHBoxLayout):
        """Setup action buttons"""
        button_list = []
        
        # Help button (only if help text exists)
        if self.help_text:
            help_button = QPushButton("?")
            help_button.setObjectName("help_button")
            help_button.setToolTip("Show help")
            help_button.clicked.connect(self.help_requested.emit)
            button_list.append(help_button)
        
        # Generate button
        generate_button = QPushButton("Generate")
        generate_button.setObjectName("generate_button")
        generate_button.clicked.connect(self.generate_requested.emit)
        button_list.append(generate_button)
        
        # Clear button
        clear_button = QPushButton("Clear")
        clear_button.setObjectName("clear_button")
        clear_button.clicked.connect(self._handle_clear)
        button_list.append(clear_button)
        
        # Add and style all buttons
        for button in button_list:
            button.setFlat(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            layout.addWidget(button)

    def _setup_field_styling(self):
        """Setup field-specific styling"""
        self.setStyleSheet("""
            StandardField {
                background-color: transparent;
                border: none;
                margin: 8px 0px;
            }
            
            QLabel#field_label {
                font-weight: bold;
                font-size: 13px;
                color: #2c3e50;
            }
            
            QTextEdit#field_editor, QPlainTextEdit#field_editor {
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                padding: 8px;
                background-color: #ffffff;
                min-height: 60px;
            }
            
            QTextEdit#field_editor:focus, QPlainTextEdit#field_editor:focus {
                border-color: #3498db;
                background-color: #f8f9fa;
            }
            
            QTextEdit#field_editor:hover, QPlainTextEdit#field_editor:hover {
                border-color: #95a5a6;
            }
            
            QPushButton {
                color: #7f8c8d;
                padding: 4px 8px;
                border: none;
                border-radius: 4px;
            }
            
            QPushButton:hover {
                background-color: #ecf0f1;
                color: #2c3e50;
            }
            
            QPushButton#generate_button {
                color: #2980b9;
            }
            
            QPushButton#generate_button:hover {
                background-color: #3498db;
                color: white;
            }
        """)

    def _handle_clear(self):
        """Handle clear button click"""
        if self.get_content():  # Only emit if there's content to clear
            self.clear_requested.emit()
        self.clear_content()

    def set_generating(self, is_generating: bool):
        """Set generation state"""
        if is_generating:
            self._editor.setReadOnly(True)
            self.set_validation_state(True, "Generating...")
        else:
            self._editor.setReadOnly(False)
            self.set_validation_state(True)
        
        # Update button states
        for button in self.findChildren(QPushButton):
            button.setEnabled(not is_generating)

    def set_required(self, required: bool):
        """Set whether field is required"""
        self.required = required
        label_text = f"{self.label_text} *" if required else self.label_text
        self._label.setText(label_text)
        self._label.setProperty("required", required)
        self._label.setStyleSheet(self._label.styleSheet())

    def set_help_text(self, text: str):
        """Set help text"""
        self.help_text = text
        help_labels = [w for w in self.findChildren(QLabel) if w.objectName() == "help_text"]
        if help_labels:
            help_labels[0].setText(text)

    def is_empty(self) -> bool:
        """Check if field is empty"""
        return not bool(self.get_content().strip())

    def validate(self) -> bool:
        """Validate field content"""
        if self.required and self.is_empty():
            self.set_validation_state(False, "This field is required")
            self._validation_display.show()
            return False
        
        # Set valid state if passes validation
        self.set_validation_state(True)
        return True

    def set_content(self, content: str):
        """Set content and validate if required"""
        super().set_content(content)
        # Validate content if field is required
        if self.required:
            self.validate()
        else:
            # Clear validation state for non-required fields
            self.set_validation_state(True)

    def clear_content(self):
        """Clear content and revalidate"""
        super().clear_content()
        if self.required:
            self.validate()

    def set_validation_state(self, is_valid: bool, message: str = ""):
        """Set validation state with message"""
        super().set_validation_state(is_valid, message)
        self._is_valid = is_valid  # Ensure internal state is updated
        
        if message:
            severity = ValidationSeverity.ERROR if not is_valid else ValidationSeverity.INFO
            self._validation_display.show_message(message, severity)
            self._validation_display.show()
        else:
            self._validation_display.clear()
            self._validation_display.hide()

    def is_valid(self) -> bool:
        """Check if field is valid"""
        if self.required and self.is_empty():
            return False
        return super().is_valid()