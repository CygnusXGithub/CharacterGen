from typing import Optional, Dict, Any
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QPushButton, QLabel, QCheckBox, QFrame,
    QSplitter, QSpacerItem, QSizePolicy, QSpinBox
)
from PyQt6.QtCore import Qt, pyqtSignal

from ...core.enums import FieldName, GenerationMode, UIMode
from ..widgets.common import EditableField

class FieldInputWidget(QWidget):
    """Enhanced field input widget with generation controls"""
    regen_requested = pyqtSignal(FieldName)  # Single regeneration
    regen_with_deps_requested = pyqtSignal(FieldName)  # Regeneration with dependents
    input_changed = pyqtSignal(FieldName, str)  # Input text changed
    mode_changed = pyqtSignal(FieldName, GenerationMode)  # Generation mode changed
    focus_changed = pyqtSignal(FieldName, bool)  # Field focus changed
    
    def __init__(self, field: FieldName, parent=None):
        super().__init__(parent)
        self.field = field
        self.ui_mode = UIMode.COMPACT
        self._init_ui()
        
    def _init_ui(self):
        layout = QVBoxLayout()
        
        # Header
        header = QHBoxLayout()
        
        # Field label
        label = QLabel(self.field.value.replace('_', ' ').title())
        header.addWidget(label)
        
        # Generation mode checkbox for name field
        if self.field == FieldName.NAME:
            self.gen_mode_checkbox = QCheckBox("Generate")
            self.gen_mode_checkbox.setChecked(True)
            self.gen_mode_checkbox.stateChanged.connect(self._handle_mode_change)
            header.addWidget(self.gen_mode_checkbox)
        
        # Focus toggle button
        focus_btn = QPushButton("🔍")
        focus_btn.setToolTip("Toggle field focus")
        focus_btn.setFixedWidth(30)
        focus_btn.clicked.connect(self._toggle_focus)
        header.addWidget(focus_btn)
        
        header.addStretch()
        layout.addLayout(header)
        
        # Input area
        input_layout = QHBoxLayout()
        
        # Input text area
        self.input = QTextEdit()
        self.input.setPlaceholderText(f"Enter {self.field.value}...")
        self.input.setAcceptRichText(False)
        self.input.document().documentLayout().documentSizeChanged.connect(
            lambda: self._adjust_height(self.input)
        )
        # Set minimum height
        self.input.setMinimumHeight(100)
        # Allow growing but start at minimum
        self.input.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Minimum
        )
        input_layout.addWidget(self.input)
        
        # Generation buttons
        button_layout = QVBoxLayout()
        
        # Single regeneration button
        regen_btn = QPushButton("🔄")
        regen_btn.setToolTip("Regenerate this field")
        regen_btn.setFixedWidth(30)
        regen_btn.clicked.connect(lambda: self.regen_requested.emit(self.field))
        button_layout.addWidget(regen_btn)
        
        # Regenerate with dependencies button
        regen_deps_btn = QPushButton("🔄+")
        regen_deps_btn.setToolTip("Regenerate this field and its dependents")
        regen_deps_btn.setFixedWidth(30)
        regen_deps_btn.clicked.connect(
            lambda: self.regen_with_deps_requested.emit(self.field)
        )
        button_layout.addWidget(regen_deps_btn)
        
        input_layout.addLayout(button_layout)
        layout.addLayout(input_layout)
        
        self.setLayout(layout)
    
    def _handle_input_change(self):
        """Handle input text changes"""
        text = self.input.toPlainText()
        self.input_changed.emit(self.field, text)
    
    def _handle_mode_change(self, state):
        """Handle generation mode changes"""
        mode = GenerationMode.GENERATE if state else GenerationMode.DIRECT
        self.mode_changed.emit(self.field, mode)
    
    def _toggle_focus(self):
        """Toggle field focus mode"""
        self.ui_mode = (UIMode.EXPANDED if self.ui_mode == UIMode.COMPACT 
                       else UIMode.COMPACT)
        self._update_ui_mode()
        self.focus_changed.emit(self.field, self.ui_mode == UIMode.EXPANDED)
    
    def _update_ui_mode(self):
        """Update UI based on current mode"""
        if self.ui_mode == UIMode.EXPANDED:
            self.input.setMaximumHeight(16777215)  # Remove height limit
            self.input.setMinimumHeight(200)
        else:
            self.input.setMaximumHeight(100)
            self.input.setMinimumHeight(60)
    
    def get_input(self) -> str:
        """Get input text"""
        return self.input.toPlainText()
    
    def set_input(self, text: str):
        """Set input text"""
        self.input.setPlainText(text)

    def _adjust_height(self, text_edit: QTextEdit):
        """Adjust height to fit content with minimum height"""
        doc_size = text_edit.document().size()
        margins = text_edit.contentsMargins()
        height = int(doc_size.height() + margins.top() + margins.bottom() + 10)
        text_edit.setMinimumHeight(min(max(100, height), 400))

class MessageExampleWidget(FieldInputWidget):
    """Specialized widget for message examples with append functionality"""
    append_requested = pyqtSignal(FieldName, str)  # Request to append new example
    
    def __init__(self, parent=None):
        super().__init__(FieldName.MES_EXAMPLE, parent)
        self._add_append_controls()
    
    def _add_append_controls(self):
        """Add controls for appending examples"""
        append_layout = QHBoxLayout()
        
        # Context input for new example
        self.context_input = QTextEdit()
        self.context_input.setPlaceholderText("Enter context for new example...")
        self.context_input.setMaximumHeight(60)
        append_layout.addWidget(self.context_input)
        
        # Append button
        append_btn = QPushButton("Add Example")
        append_btn.clicked.connect(self._handle_append)
        append_layout.addWidget(append_btn)
        
        # Add to main layout
        self.layout().addLayout(append_layout)
    
    def _handle_append(self):
        """Handle append example request"""
        context = self.context_input.toPlainText()
        self.append_requested.emit(self.field, context)
        self.context_input.clear()

class FirstMessageWidget(FieldInputWidget):
    """Specialized widget for first message with alternate greeting support"""
    greeting_requested = pyqtSignal(FieldName)  # Request new alternate greeting
    
    def __init__(self, parent=None):
        super().__init__(FieldName.FIRST_MES, parent)
        self._add_greeting_controls()
        
    def _add_greeting_controls(self):
        """Add controls for alternate greetings"""
        greeting_layout = QHBoxLayout()
        
        # Add alternate greeting button
        greeting_btn = QPushButton("Add Alternate Greeting")
        greeting_btn.clicked.connect(
            lambda: self.greeting_requested.emit(self.field)
        )
        greeting_layout.addWidget(greeting_btn)
        
        # Add to main layout
        self.layout().addLayout(greeting_layout)

class ExpandedFieldView(QWidget):
    """Expanded view for focused fields"""
    def __init__(self, 
                 field: FieldName,
                 input_text: str = "",
                 output_text: str = "",
                 parent=None):
        super().__init__(parent)
        self.field = field
        self._init_ui(input_text, output_text)
    
    def _init_ui(self, input_text: str, output_text: str):
        layout = QVBoxLayout()
        
        # Header
        header = QHBoxLayout()
        header.addWidget(QLabel(f"Editing: {self.field.value}"))
        header.addStretch()
        
        # Close button
        close_btn = QPushButton("×")
        close_btn.setFixedWidth(30)
        close_btn.clicked.connect(self.close)
        header.addWidget(close_btn)
        
        layout.addLayout(header)
        
        # Splitter for input/output
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Input section
        input_widget = QWidget()
        input_layout = QVBoxLayout(input_widget)
        input_layout.addWidget(QLabel("Input"))
        self.input_edit = QTextEdit(input_text)
        input_layout.addWidget(self.input_edit)
        splitter.addWidget(input_widget)
        
        # Output section
        output_widget = QWidget()
        output_layout = QVBoxLayout(output_widget)
        output_layout.addWidget(QLabel("Output"))
        self.output_edit = QTextEdit(output_text)
        output_layout.addWidget(self.output_edit)
        splitter.addWidget(output_widget)
        
        layout.addWidget(splitter)
        self.setLayout(layout)

class FieldViewManager:
    """Manages expanded field views"""
    def __init__(self):
        self.active_views: Dict[FieldName, ExpandedFieldView] = {}
    
    def toggle_field_focus(self, 
                          field: FieldName,
                          input_text: str = "",
                          output_text: str = "") -> None:
        """Toggle expanded view for a field"""
        if field in self.active_views:
            self.active_views[field].close()
            del self.active_views[field]
        else:
            view = ExpandedFieldView(field, input_text, output_text)
            self.active_views[field] = view
            view.show()
    
    def close_all(self):
        """Close all expanded views"""
        for view in self.active_views.values():
            view.close()
        self.active_views.clear()
