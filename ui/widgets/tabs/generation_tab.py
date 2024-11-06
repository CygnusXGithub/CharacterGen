from typing import Dict, Optional, List
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame,
    QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal

from core.state import UIStateManager
from ..base import BaseWidget
from ..layout.split_view import SplitView
from ..layout.field_container import FieldContainer
from ..fields.editor import FieldEditor
from core.models.character import CharacterData

class GenerationControls(QFrame):
    """Controls for field generation"""
    
    generate_requested = pyqtSignal(str, bool)  # field_name, include_dependencies
    focus_requested = pyqtSignal(str)  # field_name
    
    def __init__(self, field_name: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.field_name = field_name
        self._setup_ui()
        self._setup_styling()

    def _setup_ui(self):
        """Setup controls UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        
        # Generate button
        gen_btn = QPushButton("Generate")
        gen_btn.setObjectName("generate_button")
        gen_btn.clicked.connect(
            lambda: self.generate_requested.emit(self.field_name, False)
        )
        layout.addWidget(gen_btn)
        
        # Generate with dependencies button
        gen_deps_btn = QPushButton("Generate + Deps")
        gen_deps_btn.setObjectName("generate_deps_button")
        gen_deps_btn.clicked.connect(
            lambda: self.generate_requested.emit(self.field_name, True)
        )
        layout.addWidget(gen_deps_btn)
        
        # Focus button
        focus_btn = QPushButton("Focus")
        focus_btn.setObjectName("focus_button")
        focus_btn.clicked.connect(
            lambda: self.focus_requested.emit(self.field_name)
        )
        layout.addWidget(focus_btn)

    def _setup_styling(self):
        """Setup controls styling"""
        self.setStyleSheet("""
            GenerationControls {
                background: transparent;
                border: none;
            }
            
            QPushButton {
                padding: 4px 8px;
                border: 1px solid #dcdcdc;
                border-radius: 4px;
                min-width: 80px;
            }
            
            QPushButton#generate_button {
                background-color: #3498db;
                color: white;
                border-color: #2980b9;
            }
            
            QPushButton#generate_button:hover {
                background-color: #2980b9;
            }
            
            QPushButton#generate_deps_button {
                background-color: #2ecc71;
                color: white;
                border-color: #27ae60;
            }
            
            QPushButton#generate_deps_button:hover {
                background-color: #27ae60;
            }
            
            QPushButton#focus_button:hover {
                background-color: #f5f5f5;
            }
        """)

class InputPanel(BaseWidget):
    """Panel for generation inputs"""
    
    input_changed = pyqtSignal(str, str)  # field_name, content
    generate_requested = pyqtSignal(str, bool)  # field_name, include_dependencies
    focus_requested = pyqtSignal(str)  # field_name
    
    def __init__(self, ui_manager: UIStateManager, parent: Optional[QWidget] = None):
        self._inputs: Dict[str, FieldEditor] = {}
        self._controls: Dict[str, GenerationControls] = {}
        super().__init__(ui_manager, parent)

    def _setup_ui(self):
        """Setup input panel UI"""
        # Create scroll area
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._layout.addWidget(scroll)
        
        # Create content widget
        content = QWidget()
        self._content_layout = QVBoxLayout(content)
        self._content_layout.setContentsMargins(16, 16, 16, 16)
        self._content_layout.setSpacing(16)
        
        scroll.setWidget(content)
        
        # Add standard fields
        self._add_field("name", "Name")
        self._add_field("description", "Description")
        self._add_field("personality", "Personality")
        self._add_field("first_mes", "First Message")
        self._add_field("mes_example", "Message Example")
        
        # Add alternate greeting button
        alt_greet_btn = QPushButton("Add Alternate Greeting")
        alt_greet_btn.clicked.connect(self._add_alternate_greeting)
        self._content_layout.addWidget(alt_greet_btn)
        
        self._content_layout.addStretch()

    def _add_field(self, field_name: str, label: str):
        """Add input field with controls"""
        # Container for field + controls
        container = QFrame()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # Add controls
        controls = GenerationControls(field_name, container)
        controls.generate_requested.connect(self.generate_requested.emit)
        controls.focus_requested.connect(self.focus_requested.emit)
        self._controls[field_name] = controls
        layout.addWidget(controls)
        
        # Add field
        field = FieldEditor(
            ui_manager=self.ui_manager,
            field_name=field_name,
            label=label,
            parent=container
        )
        field.field_changed.connect(self.input_changed.emit)
        self._inputs[field_name] = field
        layout.addWidget(field)
        
        self._content_layout.addWidget(container)

    def _add_alternate_greeting(self):
        """Handle alternate greeting button click"""
        self.generate_requested.emit("first_mes", False)  # Generate new alternate greeting

    def get_input_content(self, field_name: str) -> str:
        """Get content of input field"""
        if field_name in self._inputs:
            return self._inputs[field_name].get_content()
        return ""

    def set_input_content(self, field_name: str, content: str):
        """Set content of input field"""
        if field_name in self._inputs:
            self._inputs[field_name].set_content(content)

class OutputPanel(BaseWidget):
    """Panel for generation outputs"""
    
    def __init__(self, ui_manager: UIStateManager, parent: Optional[QWidget] = None):
        self._outputs: Dict[str, FieldEditor] = {}
        super().__init__(ui_manager, parent)

    def _setup_ui(self):
        """Setup output panel UI"""
        # Create scroll area
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._layout.addWidget(scroll)
        
        # Create content widget
        content = QWidget()
        self._content_layout = QVBoxLayout(content)
        self._content_layout.setContentsMargins(16, 16, 16, 16)
        self._content_layout.setSpacing(16)
        
        scroll.setWidget(content)
        
        # Add output fields
        self._add_field("name", "Name")
        self._add_field("description", "Description")
        self._add_field("personality", "Personality")
        self._add_field("first_mes", "First Message")
        self._add_field("mes_example", "Message Example")
        
        # Add browse controls for first_mes
        self._add_browse_controls("first_mes")
        
        self._content_layout.addStretch()

    def _add_field(self, field_name: str, label: str):
        """Add output field"""
        field = FieldEditor(
            ui_manager=self.ui_manager,
            field_name=f"{field_name}_output",
            label=f"{label} Output",
            parent=self
        )
        field.set_read_only(True)
        self._outputs[field_name] = field
        self._content_layout.addWidget(field)

    def _add_browse_controls(self, field_name: str):
        """Add browse controls for fields with multiple versions"""
        if field_name not in self._outputs:
            return
            
        controls = QFrame()
        layout = QHBoxLayout(controls)
        
        prev_btn = QPushButton("←")
        prev_btn.clicked.connect(lambda: self._browse_version(field_name, -1))
        layout.addWidget(prev_btn)
        
        self._version_label = QLabel("1/1")
        layout.addWidget(self._version_label)
        
        next_btn = QPushButton("→")
        next_btn.clicked.connect(lambda: self._browse_version(field_name, 1))
        layout.addWidget(next_btn)
        
        layout.addStretch()
        
        # Insert before the next field
        field_idx = self._content_layout.indexOf(self._outputs[field_name])
        self._content_layout.insertWidget(field_idx + 1, controls)

    def _browse_version(self, field_name: str, delta: int):
        """Browse between versions of a field"""
        # TODO: Implement version browsing
        pass

    def set_output_content(self, field_name: str, content: str):
        """Set content of output field"""
        if field_name in self._outputs:
            self._outputs[field_name].set_content(content)

class GenerationTab(BaseWidget):
    """Tab for character content generation"""
    
    generation_requested = pyqtSignal(str, bool)  # field_name, include_dependencies
    field_focused = pyqtSignal(str)  # field_name
    
    def __init__(self, ui_manager: UIStateManager, parent: Optional[QWidget] = None):
        super().__init__(ui_manager, parent)

    def _setup_ui(self):
        """Setup generation tab UI"""
        # Create split view
        self._split_view = SplitView(
            ui_manager=self.ui_manager,
            left_title="Input",
            right_title="Output",
            parent=self
        )
        self._layout.addWidget(self._split_view)
        
        # Create panels
        self._input_panel = InputPanel(self.ui_manager)
        self._output_panel = OutputPanel(self.ui_manager)
        
        # Set panel content
        self._split_view.set_left_content(self._input_panel)
        self._split_view.set_right_content(self._output_panel)
        
        # Connect signals
        self._input_panel.generate_requested.connect(self.generation_requested.emit)
        self._input_panel.focus_requested.connect(self.field_focused.emit)
        self._input_panel.input_changed.connect(self._handle_input_change)

    def _handle_input_change(self, field_name: str, content: str):
        """Handle input field changes"""
        # Update output in real-time
        self._output_panel.set_output_content(field_name, content)

    def update_character(self, character: Optional[CharacterData]):
        """Update displayed character data"""
        if character:
            # Update input and output fields
            for field_name in ['name', 'description', 'personality', 'first_mes', 'mes_example']:
                if hasattr(character, field_name):
                    content = str(getattr(character, field_name, ""))
                    self._input_panel.set_input_content(field_name, content)
                    self._output_panel.set_output_content(field_name, content)
        else:
            # Clear all fields
            for field_name in self._input_panel._inputs:
                self._input_panel.set_input_content(field_name, "")
                self._output_panel.set_output_content(field_name, "")

    def get_field_content(self, field_name: str, input_field: bool = True) -> str:
        """Get content of a field"""
        if input_field:
            return self._input_panel.get_input_content(field_name)
        return self._output_panel._outputs[field_name].get_content() if field_name in self._output_panel._outputs else ""