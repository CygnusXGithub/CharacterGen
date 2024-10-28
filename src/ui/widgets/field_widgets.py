from typing import Optional, Dict, Any, Callable
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QPushButton, QLabel, QCheckBox, QFrame,
    QSplitter, QSpacerItem, QSizePolicy, QSpinBox,
    QScrollArea, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QResizeEvent, QPixmap, QDragEnterEvent, QDropEvent
from PIL import Image
from PIL.ImageQt import ImageQt

from ...core.enums import FieldName, UIMode
from ...core.managers import UIStateManager, SettingsManager
from ..widgets.common import EditableField

class BaseFieldWidget(QWidget):
    """Base class for field editing widgets with common functionality"""
    input_changed = pyqtSignal(str)
    output_changed = pyqtSignal(str)
    regen_requested = pyqtSignal()
    regen_with_deps_requested = pyqtSignal()

    def __init__(self, 
                 field: FieldName, 
                 ui_manager: UIStateManager,
                 settings_manager: Optional[SettingsManager] = None,
                 parent: Optional[QWidget] = None):  # Parent parameter last
        super().__init__(parent)  # Correctly pass parent to QWidget
        self.field = field
        self.ui_manager = ui_manager
        self.settings_manager = settings_manager
        self.is_updating = False
        self._init_base_ui()
        self._connect_base_signals()

    def _init_base_ui(self):
        """Initialize common UI elements"""
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(5, 5, 5, 5)
        self.layout.setSpacing(5)
        
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
        header.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Fixed
        )
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        # Field label
        label = QLabel(self.field.value.replace('_', ' ').title())
        font = label.font()
        font.setBold(True)
        label.setFont(font)
        label.setFixedHeight(25)
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
        
        # Expand/collapse button
        self.expand_btn = QPushButton("🔍")
        self.expand_btn.setToolTip("Toggle field expansion")
        self.expand_btn.setFixedWidth(30)
        self.expand_btn.clicked.connect(self._toggle_expansion)
        
        header_layout.addWidget(self.regen_btn)
        header_layout.addWidget(self.regen_deps_btn)
        header_layout.addWidget(self.expand_btn)
        header_layout.addStretch()
        
        header.setLayout(header_layout)
        return header

    def _create_text_edit(self, placeholder: str = "") -> QTextEdit:
        """Create a standardized text edit widget"""
        text_edit = QTextEdit()
        text_edit.setAcceptRichText(False)
        text_edit.setPlaceholderText(placeholder)
        text_edit.setMinimumHeight(100)
        text_edit.document().documentLayout().documentSizeChanged.connect(
            lambda: self._adjust_height(text_edit)
        )
        
        # Apply settings if available
        if self.settings_manager:
            font_size = self.settings_manager.get("ui.font_size", 10)
            font = text_edit.font()
            font.setPointSize(font_size)
            text_edit.setFont(font)
        
        return text_edit

    def _adjust_height(self, text_edit: QTextEdit):
        """Standard height adjustment for text editors"""
        if not self.ui_manager.get_field_state(self.field).is_expanded:
            doc_size = text_edit.document().size()
            margins = text_edit.contentsMargins()
            height = int(doc_size.height() + margins.top() + margins.bottom() + 10)
            text_edit.setMinimumHeight(min(max(100, height), 400))

    def _connect_base_signals(self):
        """Connect common signals"""
        self.ui_manager.field_expanded.connect(self._handle_expansion)
        self.ui_manager.field_mode_changed.connect(self._handle_mode_change)
        
        if self.settings_manager:
            self.settings_manager.settings_updated.connect(self._apply_settings)

    def _toggle_expansion(self):
        """Toggle field expansion state"""
        self.ui_manager.toggle_field_expansion(self.field)

    def _handle_expansion(self, field: FieldName, is_expanded: bool):
        """Handle field expansion state changes"""
        if field == self.field:
            state = self.ui_manager.get_field_state(self.field)
            if is_expanded:
                if state.original_height:
                    self.setMaximumHeight(state.original_height)
                else:
                    self.setMaximumHeight(16777215)  # Qt's QWIDGETSIZE_MAX
            else:
                self.ui_manager.save_field_state(
                    self.field,
                    self.editor_container.verticalScrollBar().value(),
                    self.height()
                )
                self.setMaximumHeight(200)

    def _handle_mode_change(self, field: FieldName, mode: UIMode):
        """Handle field mode changes"""
        if field == self.field:
            self._apply_mode(mode)

    def _apply_mode(self, mode: UIMode):
        """Apply UI mode to field"""
        pass  # Implemented by subclasses

    def _apply_settings(self):
        """Apply settings updates"""
        if self.settings_manager:
            font_size = self.settings_manager.get("ui.font_size", 10)
            for text_edit in self.findChildren(QTextEdit):
                font = text_edit.font()
                font.setPointSize(font_size)
                text_edit.setFont(font)

    def get_input(self) -> str:
        """Get input text"""
        return ""  # Implemented by subclasses

    def set_input(self, text: str):
        """Set input text"""
        pass  # Implemented by subclasses

    def resizeEvent(self, event: QResizeEvent):
        """Handle resize events"""
        super().resizeEvent(event)
        if not self.ui_manager.get_field_state(self.field).is_expanded:
            scroll_value = 0
            if hasattr(self.editor_container, 'verticalScrollBar'):
                scroll_value = self.editor_container.verticalScrollBar().value()
            self.ui_manager.save_field_state(
                self.field,
                scroll_value,
                self.height()
            )

class CompactFieldWidget(BaseFieldWidget):
    """Compact view of field for main window"""
    field_focused = pyqtSignal(FieldName, bool)

    def __init__(self, 
                 field: FieldName,
                 ui_manager: UIStateManager,
                 settings_manager: Optional[SettingsManager] = None,
                 min_height: int = 100,
                 max_height: int = 300,
                 parent: Optional[QWidget] = None):
        self.min_height = min_height
        self.max_height = max_height
        super().__init__(field, ui_manager, settings_manager, parent)

    def _create_editor_container(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout()  # Changed to QVBoxLayout
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # Create input editor directly without scroll area
        self.input = QTextEdit()
        self.input.setAcceptRichText(False)
        self.input.setPlaceholderText(f"Enter {self.field.value}...")
        self.input.textChanged.connect(self._handle_input_changed)
        self.input.document().contentsChanged.connect(self._adjust_height)
        self.input.setMinimumHeight(self.min_height)
        self.input.setMaximumHeight(self.max_height)
        
        # Apply settings
        if self.settings_manager:
            font_size = self.settings_manager.get("ui.font_size", 10)
            font = self.input.font()
            font.setPointSize(font_size)
            self.input.setFont(font)
            
        layout.addWidget(self.input)
        container.setLayout(layout)
        return container

    def _adjust_height(self):
        """Adjust height based on content"""
        doc_height = self.input.document().size().height()
        margins = self.input.contentsMargins()
        needed_height = doc_height + margins.top() + margins.bottom() + 10

        new_height = max(self.min_height, min(needed_height, self.max_height))
        
        if new_height != self.input.height():
            self.input.setFixedHeight(int(new_height))

    def _handle_input_changed(self):
        """Handle input text changes"""
        if not self.is_updating:
            self.is_updating = True
            try:
                self.input_changed.emit(self.input.toPlainText())
            finally:
                self.is_updating = False

    def _apply_mode(self, mode: UIMode):
        """Apply UI mode to field"""
        if mode == UIMode.COMPACT:
            self.setMaximumHeight(200)
            self.input.setMaximumHeight(150)
        else:
            self.setMaximumHeight(16777215)  # Qt's QWIDGETSIZE_MAX
            self.input.setMaximumHeight(16777215)

    def get_input(self) -> str:
        """Get input text"""
        return self.input.toPlainText()

    def set_input(self, text: str):
        """Set input text without triggering signals"""
        self.is_updating = True
        try:
            self.input.setPlainText(text)
        finally:
            self.is_updating = False

    def focusInEvent(self, event):
        """Handle focus in events"""
        super().focusInEvent(event)
        self.field_focused.emit(self.field, True)
        self.ui_manager.set_field_focus(self.field)

    def focusOutEvent(self, event):
        """Handle focus out events"""
        super().focusOutEvent(event)
        self.field_focused.emit(self.field, False)
        if self.ui_manager.get_focused_field() == self.field:
            self.ui_manager.set_field_focus(None)

class ExpandedFieldWidget(BaseFieldWidget):
    """Expanded view of field for focused editing"""

    def _create_editor_container(self) -> QWidget:
        """Create editor container with split view"""
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Input section
        input_container = QWidget()
        input_layout = QVBoxLayout(input_container)
        input_layout.setContentsMargins(5, 5, 5, 5)
        
        input_header = QLabel("Input")
        input_header.setStyleSheet("font-weight: bold;")
        input_layout.addWidget(input_header)
        
        self.input = self._create_text_edit(f"Enter {self.field.value}...")
        self.input.textChanged.connect(self._handle_input_changed)
        input_layout.addWidget(self.input)
        
        splitter.addWidget(input_container)
        
        # Output section
        output_container = QWidget()
        output_layout = QVBoxLayout(output_container)
        output_layout.setContentsMargins(5, 5, 5, 5)
        
        output_header = QLabel("Output")
        output_header.setStyleSheet("font-weight: bold;")
        output_layout.addWidget(output_header)
        
        self.output = self._create_text_edit("Generated output will appear here...")
        self.output.textChanged.connect(self._handle_output_changed)
        output_layout.addWidget(self.output)
        
        splitter.addWidget(output_container)
        
        # Set equal sizes
        splitter.setSizes([1, 1])
        
        return splitter

    def _handle_input_changed(self):
        """Handle input text changes"""
        if not self.is_updating:
            self.is_updating = True
            try:
                self.input_changed.emit(self.input.toPlainText())
            finally:
                self.is_updating = False

    def _handle_output_changed(self):
        """Handle output text changes"""
        if not self.is_updating:
            self.is_updating = True
            try:
                self.output_changed.emit(self.output.toPlainText())
            finally:
                self.is_updating = False

    def set_input(self, text: str):
        """Update input text without triggering signals"""
        self.is_updating = True
        try:
            self.input.setPlainText(text)
        finally:
            self.is_updating = False

    def set_output(self, text: str):
        """Update output text without triggering signals"""
        self.is_updating = True
        try:
            self.output.setPlainText(text)
        finally:
            self.is_updating = False

    def _apply_mode(self, mode: UIMode):
        """Apply UI mode to field"""
        if mode == UIMode.EXPANDED:
            self.setMaximumHeight(16777215)
            self.input.setMaximumHeight(16777215)
            self.output.setMaximumHeight(16777215)
        else:
            state = self.ui_manager.get_field_state(self.field)
            if state.original_height:
                self.setMaximumHeight(state.original_height)
            else:
                self.setMaximumHeight(400)

class MessageExampleWidget(CompactFieldWidget):
    """Widget for message example field with append functionality"""
    append_requested = pyqtSignal(FieldName)
    
    def __init__(self, 
                 field: FieldName,
                 ui_manager: UIStateManager,
                 settings_manager: Optional[SettingsManager] = None,
                 min_height: int = 100,
                 max_height: int = 300,
                 parent: Optional[QWidget] = None):
        super().__init__(field, ui_manager, settings_manager, min_height, max_height, parent)
        self._add_append_controls()
    
    def _add_append_controls(self):
        """Add controls for appending examples"""
        controls = QWidget()
        layout = QHBoxLayout(controls)
        layout.setContentsMargins(0, 0, 0, 0)
        
        append_btn = QPushButton("Add Example")
        append_btn.clicked.connect(lambda: self.append_requested.emit(self.field))
        layout.addWidget(append_btn)
        
        layout.addStretch()
        
        self.layout.addWidget(controls)

class FirstMessageWidget(CompactFieldWidget):
    """Widget for first message field with greeting functionality"""
    greeting_requested = pyqtSignal(FieldName)
    
    def __init__(self, 
                 field: FieldName,
                 ui_manager: UIStateManager,
                 settings_manager: Optional[SettingsManager] = None,
                 min_height: int = 100,
                 max_height: int = 300,
                 parent: Optional[QWidget] = None):
        super().__init__(field, ui_manager, settings_manager, min_height, max_height, parent)
        self._add_greeting_controls()
    
    def _add_greeting_controls(self):
        """Add controls for alternate greetings"""
        controls = QWidget()
        layout = QHBoxLayout(controls)
        layout.setContentsMargins(0, 0, 0, 0)
        
        greeting_btn = QPushButton("Add Alternate Greeting")
        greeting_btn.clicked.connect(lambda: self.greeting_requested.emit(self.field))
        layout.addWidget(greeting_btn)
        
        layout.addStretch()
        
        self.layout.addWidget(controls)

class FieldViewManager:
    """Manages expanded field views"""
    
    def __init__(self, ui_manager: UIStateManager, settings_manager: Optional[SettingsManager] = None):
        self.ui_manager = ui_manager
        self.settings_manager = settings_manager
        self.active_views: Dict[FieldName, ExpandedFieldWidget] = {}
    
    def toggle_field_focus(self, 
                          field: FieldName,
                          input_text: str = "",
                          output_text: str = "",
                          input_widget=None,
                          output_widget=None,
                          regen_callback=None,
                          regen_deps_callback=None) -> None:
        """Toggle field focus state"""
        if field in self.active_views and self.active_views[field].isVisible():
            self._close_view(field)
        else:
            self._create_view(
                field,
                input_text,
                output_text,
                input_widget,
                output_widget,
                regen_callback,
                regen_deps_callback
            )

    def _create_view(self,
                    field: FieldName,
                    input_text: str,
                    output_text: str,
                    input_widget,
                    output_widget,
                    regen_callback,
                    regen_deps_callback) -> None:
        """Create expanded view for field"""
        # Create expanded view
        view = ExpandedFieldWidget(field, self.ui_manager, self.settings_manager)
        
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
        
        # Set up window
        view.setWindowFlags(Qt.WindowType.Window)
        view.setWindowTitle(f"Editing: {field.value}")
        
        # Apply settings
        if self.settings_manager:
            size = self.settings_manager.get(f"field_views.{field.value}.size", (800, 600))
            view.resize(*size)
            pos = self.settings_manager.get(f"field_views.{field.value}.pos", None)
            if pos:
                view.move(*pos)
        else:
            view.resize(800, 600)
        
        # Show window
        view.show()
        
        # Store reference
        self.active_views[field] = view
        
        # Update UI state
        self.ui_manager.set_field_mode(field, UIMode.EXPANDED)

    def _close_view(self, field: FieldName):
        """Close expanded view"""
        if field in self.active_views:
            view = self.active_views[field]
            
            # Save settings
            if self.settings_manager:
                self.settings_manager.set(
                    f"field_views.{field.value}.size",
                    (view.width(), view.height())
                )
                self.settings_manager.set(
                    f"field_views.{field.value}.pos",
                    (view.x(), view.y())
                )
            
            # Close view
            view.close()
            self.active_views.pop(field)
            
            # Update UI state
            self.ui_manager.set_field_mode(field, UIMode.COMPACT)

    def close_all(self):
        """Close all expanded views"""
        for field in list(self.active_views.keys()):
            self._close_view(field)

class AlternateGreetingsWidget(QWidget):
    """Widget for managing alternate greetings"""
    greeting_updated = pyqtSignal(int, str)
    greeting_deleted = pyqtSignal(int)
    greeting_regenerated = pyqtSignal(int)
    greeting_added = pyqtSignal(str)
    
    def __init__(self, 
                 ui_manager: UIStateManager, 
                 settings_manager: Optional[SettingsManager] = None, 
                 min_height: int = 100,
                 max_height: int = 300,
                 parent=None):
        super().__init__(parent)
        self.ui_manager = ui_manager
        self.settings_manager = settings_manager
        self.min_height = min_height
        self.max_height = max_height
        self.greetings = []
        self.current_index = 0
        self.is_updating = False 
        self._init_ui()
        
    def _init_ui(self):
        """Initialize UI"""
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Minimum
        )
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # Controls bar
        controls = QWidget()
        controls.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Fixed
        )
        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(5)

        # Title
        label = QLabel("Alternate Greetings")
        font = label.font()
        font.setBold(True)
        label.setFont(font)
        label.setFixedHeight(25)
        controls_layout.addWidget(label)  
        
        # Navigation group
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
        
        controls_layout.addLayout(nav_group)
        controls_layout.addStretch()
        
        # Action buttons
        self.add_btn = QPushButton("+")
        self.add_btn.setFixedWidth(30)
        self.add_btn.clicked.connect(lambda: self.greeting_added.emit(""))
        controls_layout.addWidget(self.add_btn) 
        
        self.remove_btn = QPushButton("-")
        self.remove_btn.setFixedWidth(30)
        self.remove_btn.clicked.connect(self._remove_current)
        controls_layout.addWidget(self.remove_btn) 
        
        self.regen_btn = QPushButton("🔄")
        self.regen_btn.setFixedWidth(30)
        self.regen_btn.clicked.connect(
            lambda: self.greeting_regenerated.emit(self.current_index)
        )
        controls_layout.addWidget(self.regen_btn) 
        controls.setLayout(controls_layout)  # Set the layout for controls widget
        layout.addWidget(controls)  # Add the controls widget to main layout
        
        # Text editor (remove duplicate definition)
        self.text_edit = QTextEdit()
        self.text_edit.setAcceptRichText(False)
        self.text_edit.setMinimumHeight(50)
        self.text_edit.setMaximumHeight(self.max_height - 50)  # Account for controls
        self.text_edit.document().contentsChanged.connect(self._adjust_height)
        self.text_edit.textChanged.connect(self._text_changed)
        
        if self.settings_manager:
            font_size = self.settings_manager.get("ui.font_size", 10)
            font = self.text_edit.font()
            font.setPointSize(font_size)
            self.text_edit.setFont(font)
        
        layout.addWidget(self.text_edit)
        
        self.setLayout(layout)
        self.setVisible(False)
        
        self._update_controls()
    
    def _adjust_height(self):
        """Adjust height based on content"""
        # Get the document's size
        doc_height = self.text_edit.document().size().height()
        # Add margins
        margins = self.text_edit.contentsMargins()
        needed_height = doc_height + margins.top() + margins.bottom() + 10  # extra padding
        
        # Calculate available height (account for controls)
        controls_height = 50  # Approximate height of controls
        max_text_height = self.max_height - controls_height
        min_text_height = 50
        
        # Constrain to min/max
        new_height = max(min_text_height, min(needed_height, max_text_height))
        
        # Only resize if needed
        if new_height != self.text_edit.height():
            self.text_edit.setFixedHeight(int(new_height))
            # Adjust total widget height
            self.setFixedHeight(int(new_height + controls_height))

    def update_greeting(self, index: int, text: str):
        """Update a specific greeting"""
        if self.is_updating:
            return
        
        self.is_updating = True
        try:
            if 0 <= index < len(self.greetings):
                self.greetings[index] = text
                if index == self.current_index:
                    self.text_edit.setPlainText(text)
                self._update_controls()
        finally:
            self.is_updating = False

    def delete_greeting(self, index: int):
        """Delete a specific greeting"""
        if self.is_updating:
            return
            
        self.is_updating = True
        try:
            if 0 <= index < len(self.greetings):
                self.greetings.pop(index)
                if index == self.current_index:
                    self.current_index = max(0, self.current_index - 1)
                elif index < self.current_index:
                    self.current_index -= 1
                self._update_display()
        finally:
            self.is_updating = False

    def add_greeting(self, text: str = ""):
        """Add a new greeting"""
        if self.is_updating:
            return
            
        self.is_updating = True
        try:
            self.greetings.append(text)
            self.current_index = len(self.greetings) - 1
            self._update_display()
        finally:
            self.is_updating = False
    
    def _text_changed(self):
        """Handle text changes"""
        if not self.greetings or self.is_updating:
            return
            
        self.is_updating = True
        try:
            self.greeting_updated.emit(
                self.current_index,
                self.text_edit.toPlainText()
            )
        finally:
            self.is_updating = False
    
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
    
    def _remove_current(self):
        """Remove current greeting"""
        if self.is_updating:
            return
            
        self.is_updating = True
        try:
            if self.greetings and 0 <= self.current_index < len(self.greetings):
                self.greeting_deleted.emit(self.current_index)
        finally:
            self.is_updating = False
    
    def _update_controls(self):
        """Update control states"""
        has_greetings = bool(self.greetings)
        self.setVisible(has_greetings)
        
        if has_greetings:
            self.prev_btn.setEnabled(self.current_index > 0)
            self.next_btn.setEnabled(self.current_index < len(self.greetings) - 1)
            self.counter_label.setText(f"{self.current_index + 1}/{len(self.greetings)}")
            self.remove_btn.setEnabled(True)
            self.regen_btn.setEnabled(True)
        else:
            self.remove_btn.setEnabled(False)
            self.regen_btn.setEnabled(False)
    
    def _update_display(self):
        """Update displayed greeting"""
        # Remove the is_updating check here since it's an internal operation
        try:
            if self.greetings and 0 <= self.current_index < len(self.greetings):
                self.text_edit.setPlainText(self.greetings[self.current_index])
            else:
                self.text_edit.clear()
            self._update_controls()
        except Exception as e:
            print(f"Error in _update_display: {str(e)}")  # Optional debug
    
    def set_greetings(self, greetings: list):
        """Set list of greetings"""
        if self.is_updating:
            return
            
        self.is_updating = True
        try:
            self.greetings = greetings.copy() if greetings else []  # Ensure we handle None case
            self.current_index = 0 if self.greetings else -1
            # Allow internal updates to complete
            self._update_display()
        finally:
            self.is_updating = False

class ImageFrame(QWidget):
    """Widget for displaying and managing character images"""
    
    # Signals
    image_changed = pyqtSignal(Image.Image)  # Emits when image is updated
    file_dropped = pyqtSignal(str)           # Emits path of dropped file
    
    def __init__(self, 
                 ui_manager: UIStateManager,
                 settings_manager: SettingsManager,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.ui_manager = ui_manager
        self.settings_manager = settings_manager
        self.current_image: Optional[Image.Image] = None
        self._init_ui()
        self._connect_signals()
        
        # Set up drag and drop
        self.setAcceptDrops(True)
    
    def _init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Image display
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumSize(290, 390)
        self.image_label.setMaximumSize(290, 390)
        self.image_label.setStyleSheet("""
            QLabel {
                border: 2px dashed #CCCCCC;
                border-radius: 5px;
                background-color: #F5F5F5;
            }
        """)
        layout.addWidget(self.image_label)
        
        # Controls
        controls = QHBoxLayout()
        
        self.load_btn = QPushButton("Load Image")
        self.load_btn.clicked.connect(self._load_image)
        controls.addWidget(self.load_btn)
        
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self._clear_image)
        self.clear_btn.setEnabled(False)
        controls.addWidget(self.clear_btn)
        
        layout.addLayout(controls)
        
        self.setLayout(layout)
        self._init_placeholder()
    
    def _connect_signals(self):
        """Connect signals"""
        if self.settings_manager:
            self.settings_manager.settings_updated.connect(self._apply_settings)
    
    def _init_placeholder(self):
        """Show placeholder text"""
        self.image_label.setText(
            "Drop image here\nor click Load Image"
        )
        self.clear_btn.setEnabled(False)
    
    def _load_image(self):
        """Handle image load request"""
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Load Image",
            "",
            "Image Files (*.png *.jpg *.jpeg *.gif *.bmp)"
        )
        
        if file_name:
            self._process_image_file(file_name)
    
    def _process_image_file(self, file_path: str):
        """Process loaded image file"""
        try:
            # Open and validate image
            image = Image.open(file_path)
            
            # Convert to RGB if needed
            if image.mode not in ('RGB', 'RGBA'):
                image = image.convert('RGBA')
            
            # Resize if necessary
            max_size = (800, 800)
            if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
                image.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Update display
            self._set_image(image)
            
            # Emit signal
            self.image_changed.emit(image)
            
        except Exception as e:
            QMessageBox.warning(
                self,
                "Image Load Error",
                f"Error loading image: {str(e)}"
            )
    
    def _set_image(self, image: Image.Image):
        """Set current image"""
        self.current_image = image
        
        # Convert PIL image to QPixmap
        qim = ImageQt(image)
        pixmap = QPixmap.fromImage(qim)
        
        # Scale pixmap to fit label while maintaining aspect ratio
        scaled = pixmap.scaled(
            self.image_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        
        # Update display
        self.image_label.setPixmap(scaled)
        self.clear_btn.setEnabled(True)
    
    def _clear_image(self):
        """Clear current image"""
        self.current_image = None
        self.image_label.clear()
        self._init_placeholder()
        self.image_changed.emit(None)
    
    def _apply_settings(self):
        """Apply updated settings"""
        pass  # Implement if needed
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter events"""
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()
    
    def dropEvent(self, event: QDropEvent):
        """Handle drop events"""
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        for file_path in files:
            # Only process first image
            if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                self._process_image_file(file_path)
                self.file_dropped.emit(file_path)
                break
        event.accept()
    
    def resizeEvent(self, event):
        """Handle resize events"""
        super().resizeEvent(event)
        if self.current_image:
            # Rescale current image for new size
            qim = ImageQt(self.current_image)
            pixmap = QPixmap.fromImage(qim)
            scaled = pixmap.scaled(
                self.image_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.image_label.setPixmap(scaled)
    
    def get_image(self) -> Optional[Image.Image]:
        """Get current image"""
        return self.current_image
    
    def set_image(self, image: Optional[Image.Image]):
        """Set image without triggering signals"""
        if image:
            self._set_image(image)
        else:
            self._clear_image()