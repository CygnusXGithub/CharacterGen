from typing import Optional, List, Dict, Any
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

class AlternateGreetingsWidget(QWidget):
    """Widget for displaying and managing alternate greetings"""
    greeting_updated = pyqtSignal(int, str)  # Index, new text
    greeting_deleted = pyqtSignal(int)       # Index to delete
    greeting_regenerated = pyqtSignal(int)   # Index to regenerate
    greeting_added = pyqtSignal()            # Request to add new greeting
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.greetings = []
        self.current_index = 0
        self._init_ui()
    
    def _init_ui(self):
        # Set size policy to match other fields
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Minimum
        )
        
        layout = QVBoxLayout()
        # Match margins with other fields
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # Controls bar
        controls = QHBoxLayout()
        controls.addWidget(QLabel("Alternate Greetings"))
        controls.setContentsMargins(0, 0, 0, 0)
        
        # Navigation group (left side)
        nav_group = QHBoxLayout()
        
        self.prev_btn = QPushButton("←")
        self.prev_btn.setFixedWidth(30)
        self.prev_btn.clicked.connect(self._previous_greeting)
        nav_group.addWidget(self.prev_btn)
        
        self.counter_label = QLabel("0/0")
        nav_group.addWidget(self.counter_label)
        
        self.next_btn = QPushButton("→")
        self.next_btn.setFixedWidth(30)
        self.next_btn.clicked.connect(self._next_greeting)
        nav_group.addWidget(self.next_btn)
        
        controls.addLayout(nav_group)
        
        # Add stretch to separate navigation from control buttons
        controls.addStretch()
        
        # Control buttons group (right side)
        control_group = QHBoxLayout()
        
        # Add greeting button
        self.add_btn = QPushButton("+")
        self.add_btn.setFixedWidth(30)
        self.add_btn.setToolTip("Add new alternate greeting")
        self.add_btn.clicked.connect(lambda: self.greeting_added.emit())
        control_group.addWidget(self.add_btn)
        
        # Remove greeting button
        self.remove_btn = QPushButton("-")
        self.remove_btn.setFixedWidth(30)
        self.remove_btn.setToolTip("Remove current greeting")
        self.remove_btn.clicked.connect(self._remove_current_greeting)
        control_group.addWidget(self.remove_btn)
        
        # Add spacing between remove and regen buttons
        control_group.addSpacing(10)
        
        # Regenerate current greeting button
        self.regen_btn = QPushButton("🔄")
        self.regen_btn.setFixedWidth(30)
        self.regen_btn.setToolTip("Regenerate this greeting")
        self.regen_btn.clicked.connect(
            lambda: self.greeting_regenerated.emit(self.current_index)
        )
        control_group.addWidget(self.regen_btn)
        
        controls.addLayout(control_group)
        
        layout.addLayout(controls)
        
        # Text display
        self.text_edit = QTextEdit()
        self.text_edit.setAcceptRichText(False)
        self.text_edit.setMinimumHeight(60)
        self.text_edit.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Minimum
        )
        # Add the same height adjustment as other fields
        self.text_edit.document().documentLayout().documentSizeChanged.connect(
            lambda: self._adjust_height()
        )
        layout.addWidget(self.text_edit)
        
        self.setLayout(layout)
        self.setVisible(False)  # Hidden by default
        
        self._update_controls()
    
    def _adjust_height(self):
        """Adjust height to fit content"""
        doc_size = self.text_edit.document().size()
        margins = self.text_edit.contentsMargins()
        height = int(doc_size.height() + margins.top() + margins.bottom() + 10)
        self.text_edit.setMinimumHeight(min(max(100, height), 400))

    def _text_changed(self):
        """Handle text changes"""
        if self.greetings:
            self.greeting_updated.emit(
                self.current_index,
                self.text_edit.toPlainText()
            )
    
    def _previous_greeting(self):
        """Show previous greeting"""
        if self.greetings and self.current_index > 0:
            self.current_index -= 1
            self._update_display()
    
    def _next_greeting(self):
        """Show next greeting"""
        if self.greetings and self.current_index < len(self.greetings) - 1:
            self.current_index += 1
            self._update_display()
    
    def _update_controls(self):
        """Update control states"""
        has_greetings = bool(self.greetings)
        self.setVisible(has_greetings)
        if has_greetings:
            self.prev_btn.setEnabled(self.current_index > 0)
            self.next_btn.setEnabled(self.current_index < len(self.greetings) - 1)
            self.counter_label.setText(f"{self.current_index + 1}/{len(self.greetings)}")
    
    def _update_display(self):
        """Update displayed greeting"""
        if self.greetings:
            self.text_edit.blockSignals(True)
            self.text_edit.setPlainText(self.greetings[self.current_index])
            self.text_edit.blockSignals(False)
            self._update_controls()
    
    def set_greetings(self, greetings: List[str]):
        """Set the list of greetings"""
        self.greetings = greetings
        self.current_index = 0 if greetings else -1
        self._update_display()
        self._update_controls()
    
    def add_greeting(self, greeting: str):
        """Add a new greeting"""
        self.greetings.append(greeting)
        self.current_index = len(self.greetings) - 1
        self._update_display()

    def _remove_current_greeting(self):
        """Remove the current greeting"""
        if not self.greetings or self.current_index < 0 or self.current_index >= len(self.greetings):
            return
            
        self.greeting_deleted.emit(self.current_index)
        self.greetings.pop(self.current_index)
        if self.greetings:
            # Adjust current index if needed
            if self.current_index >= len(self.greetings):
                self.current_index = len(self.greetings) - 1
            self._update_display()
        else:
            self.current_index = -1
            self.setVisible(False)
        self._update_controls()
    
    def clear_greetings(self):
        """Clear all greetings"""
        self.greetings = []
        self.current_index = -1
        self._update_display()
        
class ExpandedFieldView(QWidget):
    """Expanded view for focused fields"""
    input_changed = pyqtSignal(str)  # Signal for input changes
    output_changed = pyqtSignal(str)  # Signal for output changes
    regen_requested = pyqtSignal()    # Signal for regeneration
    regen_with_deps_requested = pyqtSignal()  # Signal for regeneration with deps
    
    def __init__(self, 
                 field: FieldName,
                 input_text: str = "",
                 output_text: str = "",
                 parent=None):
        super().__init__(parent)
        self.field = field
        self._init_ui(input_text, output_text)
        self.setWindowTitle(f"Editing: {field.value}")
        # Set a reasonable default size
        self.resize(800, 600)
    
    def _init_ui(self, input_text: str, output_text: str):
        layout = QVBoxLayout()
        
        # Header
        header = QHBoxLayout()
        header.addWidget(QLabel(f"Editing: {self.field.value}"))
        
        # Add regeneration buttons
        regen_btn = QPushButton("🔄 Regenerate")
        regen_btn.clicked.connect(self.regen_requested.emit)
        header.addWidget(regen_btn)
        
        regen_deps_btn = QPushButton("🔄+ Regen with Dependencies")
        regen_deps_btn.clicked.connect(self.regen_with_deps_requested.emit)
        header.addWidget(regen_deps_btn)
        
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
        self.input_edit.textChanged.connect(
            lambda: self.input_changed.emit(self.input_edit.toPlainText())
        )
        input_layout.addWidget(self.input_edit)
        splitter.addWidget(input_widget)
        
        # Output section
        output_widget = QWidget()
        output_layout = QVBoxLayout(output_widget)
        output_layout.addWidget(QLabel("Output"))
        self.output_edit = QTextEdit(output_text)
        self.output_edit.textChanged.connect(
            lambda: self.output_changed.emit(self.output_edit.toPlainText())
        )
        output_layout.addWidget(self.output_edit)
        splitter.addWidget(output_widget)
        
        layout.addWidget(splitter)
        
        # Set equal sizes for splitter sections
        splitter.setSizes([400, 400])
        
        self.setLayout(layout)

    def update_input(self, text: str):
        """Update input text without triggering signals"""
        self.input_edit.blockSignals(True)
        self.input_edit.setPlainText(text)
        self.input_edit.blockSignals(False)
    
    def update_output(self, text: str):
        """Update output text without triggering signals"""
        self.output_edit.blockSignals(True)
        self.output_edit.setPlainText(text)
        self.output_edit.blockSignals(False)

class FieldViewManager:
    """Manages expanded field views"""
    def __init__(self):
        self.active_views: Dict[FieldName, ExpandedFieldView] = {}
    
    def toggle_field_focus(self, 
                          field: FieldName,
                          input_text: str = "",
                          output_text: str = "",
                          input_widget=None,
                          output_widget=None,
                          regen_callback=None,
                          regen_deps_callback=None) -> None:
        """Toggle expanded view for a field"""
        if field in self.active_views:
            self.active_views[field].close()
            del self.active_views[field]
        else:
            view = ExpandedFieldView(field, input_text, output_text)
            
            # Connect signals
            if input_widget:
                view.input_changed.connect(lambda t: input_widget.set_input(t))
                input_widget.input_changed.connect(view.update_input)
            
            if output_widget:
                view.output_changed.connect(lambda t: output_widget.setPlainText(t))
                output_widget.textChanged.connect(
                    lambda: view.update_output(output_widget.toPlainText())
                )
            
            if regen_callback:
                view.regen_requested.connect(regen_callback)
            
            if regen_deps_callback:
                view.regen_with_deps_requested.connect(regen_deps_callback)
            
            self.active_views[field] = view
            view.show()
    
    def close_all(self):
        """Close all expanded views"""
        for view in self.active_views.values():
            view.close()
        self.active_views.clear()
