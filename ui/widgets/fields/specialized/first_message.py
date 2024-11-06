from typing import List, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal

from ..editor import FieldEditor
from core.state import UIStateManager

class FirstMessageField(FieldEditor):
    """Specialized field for managing first messages and alternate greetings"""
    
    alternate_added = pyqtSignal(str)  # New greeting content
    alternate_removed = pyqtSignal(int)  # Greeting index
    greeting_switched = pyqtSignal(int)  # New greeting index
    
    def __init__(self, 
                 ui_manager: UIStateManager,
                 parent: Optional[QWidget] = None):
        super().__init__(
            ui_manager=ui_manager,
            field_name="first_mes",
            label="First Message",
            help_text="The character's initial greeting. Use arrows to view alternate greetings.",
            required=True,
            parent=parent
        )
        self._alternate_greetings: List[str] = []
        self._current_index = 0
        self._setup_alternate_controls()

    def _setup_alternate_controls(self):
        """Setup controls for alternate greetings"""
        controls = QFrame(self)
        controls.setObjectName("alternate_controls")
        layout = QHBoxLayout(controls)
        layout.setContentsMargins(0, 4, 0, 4)
        
        # Navigation
        self._prev_btn = QPushButton("←")
        self._prev_btn.setObjectName("nav_button")
        self._prev_btn.clicked.connect(lambda: self._switch_greeting(-1))
        layout.addWidget(self._prev_btn)
        
        self._greeting_label = QLabel("1/1")
        self._greeting_label.setObjectName("greeting_counter")
        layout.addWidget(self._greeting_label)
        
        self._next_btn = QPushButton("→")
        self._next_btn.setObjectName("nav_button")
        self._next_btn.clicked.connect(lambda: self._switch_greeting(1))
        layout.addWidget(self._next_btn)
        
        layout.addStretch()
        
        # Add/Remove buttons
        self._add_btn = QPushButton("Add Alternate")
        self._add_btn.setObjectName("add_button")
        self._add_btn.clicked.connect(self._add_alternate)
        layout.addWidget(self._add_btn)
        
        self._remove_btn = QPushButton("Remove")
        self._remove_btn.setObjectName("remove_button")
        self._remove_btn.clicked.connect(self._remove_current)
        self._remove_btn.setVisible(False)
        layout.addWidget(self._remove_btn)
        
        # Add controls under the field
        self._content_layout.addWidget(controls)
        
        # Additional styling
        controls.setStyleSheet("""
            QFrame#alternate_controls {
                background: transparent;
                margin-top: 4px;
            }
            
            QPushButton#nav_button {
                min-width: 30px;
                padding: 4px;
                border: 1px solid #dcdcdc;
                border-radius: 4px;
            }
            
            QPushButton#nav_button:hover {
                background-color: #f5f5f5;
            }
            
            QLabel#greeting_counter {
                min-width: 50px;
                text-align: center;
                color: #666666;
            }
            
            QPushButton#add_button {
                padding: 4px 8px;
                border: 1px solid #2ecc71;
                border-radius: 4px;
                color: #2ecc71;
            }
            
            QPushButton#add_button:hover {
                background-color: #2ecc71;
                color: white;
            }
            
            QPushButton#remove_button {
                padding: 4px 8px;
                border: 1px solid #e74c3c;
                border-radius: 4px;
                color: #e74c3c;
            }
            
            QPushButton#remove_button:hover {
                background-color: #e74c3c;
                color: white;
            }
        """)
        
        self._update_controls()

    def _switch_greeting(self, delta: int):
        """Switch to another greeting"""
        if not self._alternate_greetings:
            return
            
        new_index = (self._current_index + delta) % (len(self._alternate_greetings) + 1)
        if new_index != self._current_index:
            # Save current content
            if self._current_index == 0:
                current = self.get_content()
            else:
                current = self._alternate_greetings[self._current_index - 1]
                
            # Update content
            self._current_index = new_index
            if new_index == 0:
                self.set_content(current)
            else:
                self.set_content(self._alternate_greetings[new_index - 1])
                
            self._update_controls()
            self.greeting_switched.emit(new_index)

    def _add_alternate(self):
        """Add new alternate greeting"""
        current = self.get_content()
        self._alternate_greetings.append(current)
        self._update_controls()
        self.alternate_added.emit(current)

    def _remove_current(self):
        """Remove current alternate greeting"""
        if self._current_index > 0:
            removed_idx = self._current_index - 1
            self._alternate_greetings.pop(removed_idx)
            self._current_index = 0
            self.set_content(self.get_content())
            self._update_controls()
            self.alternate_removed.emit(removed_idx)

    def _update_controls(self):
        """Update control states"""
        total = len(self._alternate_greetings) + 1
        self._greeting_label.setText(f"{self._current_index + 1}/{total}")
        
        self._prev_btn.setEnabled(total > 1)
        self._next_btn.setEnabled(total > 1)
        self._remove_btn.setVisible(self._current_index > 0)

    def set_alternate_greetings(self, greetings: List[str]):
        """Set list of alternate greetings"""
        self._alternate_greetings = greetings.copy()
        self._current_index = 0
        self._update_controls()

    def get_alternate_greetings(self) -> List[str]:
        """Get list of alternate greetings"""
        return self._alternate_greetings.copy()

    def get_all_greetings(self) -> List[str]:
        """Get main greeting plus alternates"""
        return [self.get_content()] + self._alternate_greetings