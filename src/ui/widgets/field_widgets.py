from typing import Optional, List, Dict, Any
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QPushButton, QLabel, QCheckBox, QFrame,
    QSplitter, QSpacerItem, QSizePolicy, QSpinBox
)
from PyQt6.QtCore import Qt, pyqtSignal

from ...core.enums import FieldName, GenerationMode, UIMode
from ..widgets.common import EditableField

class BaseFieldWidget(QWidget):
    """Base class for field editing widgets with common functionality"""
    input_changed = pyqtSignal(str)
    output_changed = pyqtSignal(str)
    regen_requested = pyqtSignal()
    regen_with_deps_requested = pyqtSignal()

    def __init__(self, field: FieldName, parent=None):
        super().__init__(parent)
        self.field = field
        self._init_base_ui()

    def _init_base_ui(self):
        """Initialize common UI elements"""
        self.layout = QVBoxLayout()
        
        # Header with field name and controls
        self.header = self._create_header()
        self.layout.addWidget(self.header)
        
        # Editor container (implementation varies by subclass)
        self.editor_container = self._create_editor_container()
        self.layout.addWidget(self.editor_container)
        
        self.setLayout(self.layout)

    def _create_header(self) -> QWidget:
        """Create header with common controls"""
        header = QWidget()
        header_layout = QHBoxLayout()
        
        # Field label
        label = QLabel(self.field.value.replace('_', ' ').title())
        header_layout.addWidget(label)
        
        # Regeneration buttons
        self.regen_btn = QPushButton("🔄")
        self.regen_btn.setToolTip("Regenerate this field")
        self.regen_btn.setFixedWidth(30)
        self.regen_btn.clicked.connect(self.regen_requested.emit)
        
        self.regen_deps_btn = QPushButton("🔄+")
        self.regen_deps_btn.setToolTip("Regenerate this field and its dependents")
        self.regen_deps_btn.setFixedWidth(30)
        self.regen_deps_btn.clicked.connect(self.regen_with_deps_requested.emit)
        
        header_layout.addWidget(self.regen_btn)
        header_layout.addWidget(self.regen_deps_btn)
        header_layout.addStretch()
        
        header.setLayout(header_layout)
        return header

    def _create_editor_container(self) -> QWidget:
        """Create editor container (implemented by subclasses)"""
        raise NotImplementedError

    def _create_text_edit(self, placeholder: str = "") -> QTextEdit:
        """Create a standardized text edit widget"""
        text_edit = QTextEdit()
        text_edit.setAcceptRichText(False)
        text_edit.setPlaceholderText(placeholder)
        text_edit.setMinimumHeight(100)
        text_edit.document().documentLayout().documentSizeChanged.connect(
            lambda: self._adjust_height(text_edit)
        )
        return text_edit

    def _adjust_height(self, text_edit: QTextEdit):
        """Standard height adjustment for text editors"""
        doc_size = text_edit.document().size()
        margins = text_edit.contentsMargins()
        height = int(doc_size.height() + margins.top() + margins.bottom() + 10)
        text_edit.setMinimumHeight(min(max(100, height), 400))

    def get_input(self) -> str:
        """Get input text"""
        if hasattr(self, 'input'):
            return self.input.toPlainText()
        return ""

    def set_input(self, text: str):
        """Set input text without triggering signals"""
        if hasattr(self, 'input'):
            self.input.blockSignals(True)
            self.input.setPlainText(text)
            self.input.blockSignals(False)

class CompactFieldWidget(BaseFieldWidget):
    """Compact view of field for main window"""
    focus_changed = pyqtSignal(FieldName, bool)

    def _init_base_ui(self):
        """Override to customize layout spacing"""
        super()._init_base_ui()
        # Reduce spacing between header and editor
        self.layout.setSpacing(5)  # Reduce from default
        self.layout.setContentsMargins(5, 5, 5, 5)  # Consistent small margins

    def _create_header(self) -> QWidget:
        header = super()._create_header()
        header_layout = header.layout()
        header_layout.setContentsMargins(0, 0, 0, 0)  # Remove header margins
        
        # Add focus toggle
        focus_btn = QPushButton("🔍")
        focus_btn.setToolTip("Toggle field focus")
        focus_btn.setFixedWidth(30)
        focus_btn.clicked.connect(
            lambda: self.focus_changed.emit(self.field, True)
        )
        header_layout.insertWidget(header_layout.count() - 1, focus_btn)
        
        return header

    def _create_editor_container(self) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)  # Remove container margins
        layout.setSpacing(5)  # Consistent spacing
        
        self.input = self._create_text_edit(f"Enter {self.field.value}...")
        self.input.textChanged.connect(
            lambda: self.input_changed.emit(self.input.toPlainText())
        )
        layout.addWidget(self.input)
        
        container.setLayout(layout)
        return container
    
    def get_input(self) -> str:
        """Get input text"""
        return self.input.toPlainText()

    def set_input(self, text: str):
        """Set input text without triggering signals"""
        self.input.blockSignals(True)
        self.input.setPlainText(text)
        self.input.blockSignals(False)

class ExpandedFieldWidget(BaseFieldWidget):
    """Expanded view of field for focused editing"""
    def _create_header(self) -> QWidget:
        """Override header creation for a more compact layout"""
        header = QWidget()
        header_layout = QHBoxLayout()
        # Reduce margins
        header_layout.setContentsMargins(5, 5, 5, 5)
        header_layout.setSpacing(5)
        
        # Field label with more compact styling
        label = QLabel(self.field.value.replace('_', ' ').title())
        header_layout.addWidget(label)
        
        # Regeneration buttons in a more compact layout
        self.regen_btn = QPushButton("🔄")
        self.regen_btn.setToolTip("Regenerate this field")
        self.regen_btn.setFixedWidth(30)
        self.regen_btn.clicked.connect(self.regen_requested.emit)
        
        self.regen_deps_btn = QPushButton("🔄+")
        self.regen_deps_btn.setToolTip("Regenerate this field and its dependents")
        self.regen_deps_btn.setFixedWidth(30)
        self.regen_deps_btn.clicked.connect(self.regen_with_deps_requested.emit)
        
        # Add buttons with minimal spacing
        header_layout.addWidget(self.regen_btn)
        header_layout.addWidget(self.regen_deps_btn)
        header_layout.addStretch()
        
        header.setLayout(header_layout)
        header.setFixedHeight(40)  # Constrain header height
        return header

    def _create_editor_container(self) -> QWidget:
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Input section
        input_container = QWidget()
        input_layout = QVBoxLayout(input_container)
        input_layout.setContentsMargins(5, 5, 5, 5)  # Reduce margins
        input_layout.setSpacing(5)  # Reduce spacing
        
        input_header = QLabel("Input")
        input_header.setStyleSheet("font-weight: bold;")
        input_layout.addWidget(input_header)
        
        self.input = self._create_text_edit(f"Enter {self.field.value}...")
        input_layout.addWidget(self.input)
        splitter.addWidget(input_container)
        
        # Output section
        output_container = QWidget()
        output_layout = QVBoxLayout(output_container)
        output_layout.setContentsMargins(5, 5, 5, 5)  # Reduce margins
        output_layout.setSpacing(5)  # Reduce spacing
        
        output_header = QLabel("Output")
        output_header.setStyleSheet("font-weight: bold;")
        output_layout.addWidget(output_header)
        
        self.output = self._create_text_edit("Generated output will appear here...")
        output_layout.addWidget(self.output)
        splitter.addWidget(output_container)
        
        # Set equal sizes
        splitter.setSizes([1, 1])
        return splitter

    def _init_base_ui(self):
        """Override to customize layout for expanded view"""
        super()._init_base_ui()
        # Reduce overall margins
        self.layout.setContentsMargins(5, 5, 5, 5)
        self.layout.setSpacing(5)

    def set_input(self, text: str):
        """Update input text without triggering signals"""
        self.input.blockSignals(True)
        self.input.setPlainText(text)
        self.input.blockSignals(False)

    def set_output(self, text: str):
        """Update output text without triggering signals"""
        self.output.blockSignals(True)
        self.output.setPlainText(text)
        self.output.blockSignals(False)

class MessageExampleWidget(CompactFieldWidget):
    append_requested = pyqtSignal(FieldName)
    
    def __init__(self, parent=None):
        super().__init__(FieldName.MES_EXAMPLE, parent)
        self._add_append_controls()
    
    def _add_append_controls(self):
        """Add controls for appending examples"""
        append_layout = QHBoxLayout()
        append_btn = QPushButton("Append More Examples")
        append_btn.clicked.connect(lambda: self.append_requested.emit(self.field))
        append_layout.addWidget(append_btn)
        self.layout.addLayout(append_layout)

class FirstMessageWidget(CompactFieldWidget):
    greeting_requested = pyqtSignal(FieldName)
    
    def __init__(self, parent=None):
        super().__init__(FieldName.FIRST_MES, parent)
        self._add_greeting_controls()
    
    def _add_greeting_controls(self):
        """Add controls for alternate greetings"""
        greeting_layout = QHBoxLayout()
        greeting_btn = QPushButton("Add Alternate Greeting")
        greeting_btn.clicked.connect(
            lambda: self.greeting_requested.emit(self.field)
        )
        greeting_layout.addWidget(greeting_btn)
        self.layout.addLayout(greeting_layout)

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

class FieldViewManager:
    def __init__(self):
        """Initialize field view manager"""
        self.active_views = {}  # Add this initialization

    def toggle_field_focus(self, 
                          field: FieldName,
                          input_text: str = "",
                          output_text: str = "",
                          input_widget=None,
                          output_widget=None,
                          regen_callback=None,
                          regen_deps_callback=None) -> None:
        if field in self.active_views and self.active_views[field].isVisible():
            self.active_views[field].close()
            self.active_views.pop(field)
        else:
            # Create expanded view
            view = ExpandedFieldWidget(field)
            
            # Set initial texts
            view.set_input(input_text)
            view.set_output(output_text)
            
            # Connect signals
            if input_widget:
                view.input_changed.connect(lambda t: input_widget.set_input(t))
                input_widget.input_changed.connect(view.set_input)
            
            if output_widget:
                view.output_changed.connect(lambda t: output_widget.setPlainText(t))
                output_widget.textChanged.connect(
                    lambda: view.set_output(output_widget.toPlainText())
                )
            
            if regen_callback:
                view.regen_requested.connect(regen_callback)
            
            if regen_deps_callback:
                view.regen_with_deps_requested.connect(regen_deps_callback)
            
            # Show in window
            view.setWindowFlags(Qt.WindowType.Window)
            view.setWindowTitle(f"Editing: {field.value}")
            view.resize(800, 600)
            view.show()
            
            self.active_views[field] = view

    def handle_view_closed(self, field: FieldName):
        """Handle view closure from window system"""
        if field in self.active_views:
            self.active_views.pop(field)
    
    def close_all(self):
        """Close all expanded views"""
        for view in list(self.active_views.values()):
            view.close()
        self.active_views.clear()
