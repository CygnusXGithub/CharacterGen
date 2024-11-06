from typing import Optional, List
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame,
    QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal

from ..editor import FieldEditor
from core.state import UIStateManager

class MessageExample(QFrame):
    """Individual message example with controls"""
    
    removed = pyqtSignal()
    moved = pyqtSignal(int)  # Delta position
    
    def __init__(self, content: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("message_example")
        self._content = content
        self._setup_ui()

    def _setup_ui(self):
        """Setup example UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Message content
        self._content_label = QLabel(self._content)
        self._content_label.setWordWrap(True)
        layout.addWidget(self._content_label)
        
        # Controls
        controls = QHBoxLayout()
        
        move_up = QPushButton("↑")
        move_up.clicked.connect(lambda: self.moved.emit(-1))
        controls.addWidget(move_up)
        
        move_down = QPushButton("↓")
        move_down.clicked.connect(lambda: self.moved.emit(1))
        controls.addWidget(move_down)
        
        controls.addStretch()
        
        remove_btn = QPushButton("Remove")
        remove_btn.setObjectName("remove_button")
        remove_btn.clicked.connect(self.removed.emit)
        controls.addWidget(remove_btn)
        
        layout.addLayout(controls)
        
        self.setStyleSheet("""
            QFrame#message_example {
                background-color: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 4px;
                margin: 4px 0px;
            }
            
            QPushButton {
                padding: 4px 8px;
                border: 1px solid #dcdcdc;
                border-radius: 4px;
            }
            
            QPushButton:hover {
                background-color: #f5f5f5;
            }
            
            QPushButton#remove_button {
                border-color: #e74c3c;
                color: #e74c3c;
            }
            
            QPushButton#remove_button:hover {
                background-color: #e74c3c;
                color: white;
            }
        """)

class MessageExampleField(FieldEditor):
    """Field for managing multiple message examples"""
    
    example_added = pyqtSignal(str)
    example_removed = pyqtSignal(int)
    examples_reordered = pyqtSignal()
    
    def __init__(self, 
                 ui_manager: UIStateManager,
                 parent: Optional[QWidget] = None):
        super().__init__(
            ui_manager=ui_manager,
            field_name="mes_example",
            label="Message Examples",
            help_text="Examples of the character's messages. Add multiple examples to show speech patterns.",
            parent=parent
        )
        self._examples: List[str] = []
        self._setup_examples_ui()

    def _setup_examples_ui(self):
        """Setup examples list UI"""
        # Create scroll area for examples
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        # Container for examples
        self._examples_container = QWidget()
        self._examples_layout = QVBoxLayout(self._examples_container)
        scroll.setWidget(self._examples_container)
        
        # Add example button
        add_btn = QPushButton("Add Example")
        add_btn.setObjectName("add_button")
        add_btn.clicked.connect(self._add_example)
        
        # Add to layout
        self._content_layout.addWidget(scroll)
        self._content_layout.addWidget(add_btn)
        
        # Additional styling
        add_btn.setStyleSheet("""
            QPushButton#add_button {
                padding: 8px;
                border: 1px solid #2ecc71;
                border-radius: 4px;
                color: #2ecc71;
                margin-top: 8px;
            }
            
            QPushButton#add_button:hover {
                background-color: #2ecc71;
                color: white;
            }
        """)

    def _add_example(self):
        """Add current content as new example"""
        content = self.get_content()
        if content.strip():
            self._examples.append(content)
            self._update_examples()
            self.example_added.emit(content)
            self.clear_content()

    def _create_example_widget(self, content: str, index: int) -> MessageExample:
        """Create widget for message example"""
        example = MessageExample(content)
        example.removed.connect(lambda: self._remove_example(index))
        example.moved.connect(lambda d: self._move_example(index, d))
        return example

    def _remove_example(self, index: int):
        """Remove example at index"""
        if 0 <= index < len(self._examples):
            self._examples.pop(index)
            self._update_examples()
            self.example_removed.emit(index)

    def _move_example(self, index: int, delta: int):
        """Move example up or down"""
        new_index = index + delta
        if 0 <= new_index < len(self._examples):
            self._examples[index], self._examples[new_index] = \
                self._examples[new_index], self._examples[index]
            self._update_examples()
            self.examples_reordered.emit()

    def _update_examples(self):
        """Update examples display"""
        # Clear current examples
        while self._examples_layout.count():
            item = self._examples_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Add examples
        for i, content in enumerate(self._examples):
            example = self._create_example_widget(content, i)
            self._examples_layout.addWidget(example)
        
        self._examples_layout.addStretch()

    def set_examples(self, examples: List[str]):
        """Set list of examples"""
        self._examples = examples.copy()
        self._update_examples()

    def get_examples(self) -> List[str]:
        """Get list of examples"""
        return self._examples.copy()

    def clear_examples(self):
        """Clear all examples"""
        self._examples.clear()
        self._update_examples()