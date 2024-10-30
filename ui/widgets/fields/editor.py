from typing import Optional, Dict, Any
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame,
    QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from ..base import BaseWidget
from .standard import StandardField
from core.state import UIStateManager
from core.errors import ErrorHandler, ErrorCategory, ErrorLevel

class FieldEditor(BaseWidget):
    """Main field editing component"""
    
    field_changed = pyqtSignal(str, str)  # field_name, new_value
    generate_requested = pyqtSignal(str)   # field_name
    save_requested = pyqtSignal()
    
    def __init__(self, 
                 ui_manager: UIStateManager,
                 field_name: str,
                 label: str = "",
                 help_text: str = "",
                 multiline: bool = True,
                 required: bool = False,
                 parent: Optional[QWidget] = None):
        self.field_name = field_name
        self.label = label or field_name.replace('_', ' ').title()
        self.help_text = help_text
        self.multiline = multiline
        self.required = required
        self._has_unsaved_changes = False
        super().__init__(ui_manager, parent)
        
        

    def _setup_ui(self):
        """Setup editor UI"""
        self._layout.setContentsMargins(8, 8, 8, 8)
        self._layout.setSpacing(4)
        
        # Header with actions
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        
        # Field settings button
        settings_btn = QPushButton("⚙")
        settings_btn.setObjectName("settings_button")
        settings_btn.setToolTip("Field Settings")
        settings_btn.clicked.connect(self._show_settings)
        header.addWidget(settings_btn)
        
        # Spacer
        header.addStretch()
        
        # Generate button
        self._generate_btn = QPushButton("Generate")
        self._generate_btn.setObjectName("generate_button")
        self._generate_btn.clicked.connect(
            lambda: self.generate_requested.emit(self.field_name)
        )
        header.addWidget(self._generate_btn)
        
        self._layout.addLayout(header)
        
        # Main field
        self._field = StandardField(
            ui_manager=self.ui_manager,
            field_name=self.field_name,
            label=self.label,
            help_text=self.help_text,
            multiline=self.multiline,
            required=self.required
        )
        # Connect field signals
        self._field.content_changed.connect(self._on_content_changed)
        self._field.validation_changed.connect(self._on_validation_changed)
        self._layout.addWidget(self._field)
        
        # Status bar setup
        self._status_frame = QFrame(self) 
        self._status_frame.setObjectName("status_bar")
        status_layout = QHBoxLayout() 
        status_layout.setContentsMargins(4, 2, 4, 2)
        self._status_frame.setLayout(status_layout)
        
        self._status_label = QLabel("No changes")
        self._status_label.setObjectName("status_label")
        status_layout.addWidget(self._status_label)
        
        self._save_btn = QPushButton("Save", self._status_frame)  # Explicitly set parent
        print(f"Save button created with parent: {self._save_btn.parent()}")
        self._save_btn.setObjectName("save_button")
        self._save_btn.clicked.connect(self._handle_save)
        self._save_btn.setVisible(False)
        status_layout.addWidget(self._save_btn)
        
        self._layout.addWidget(self._status_frame)
        
        self._setup_styling()

    def _setup_styling(self):
        """Setup editor styling"""
        self.setStyleSheet("""
            FieldEditor {
                background: transparent;
            }
            
            QPushButton#settings_button, QPushButton#generate_button {
                padding: 4px 8px;
                border: none;
                border-radius: 4px;
                color: #666666;
            }
            
            QPushButton#settings_button:hover, QPushButton#generate_button:hover {
                background-color: #f0f0f0;
                color: #333333;
            }
            
            QPushButton#generate_button {
                color: #2980b9;
            }
            
            QPushButton#generate_button:hover {
                background-color: #3498db;
                color: white;
            }
            
            QFrame#status_bar {
                background-color: #f8f9fa;
                border-top: 1px solid #e9ecef;
                margin-top: 4px;
            }
            
            QLabel#status_label {
                color: #666666;
                font-size: 11px;
            }
            
            QPushButton#save_button {
                padding: 2px 8px;
                border: 1px solid #2ecc71;
                border-radius: 3px;
                color: #2ecc71;
                background: transparent;
            }
            
            QPushButton#save_button:hover {
                color: white;
                background-color: #2ecc71;
            }
        """)

    def _on_content_changed(self):
        """Handle content change from field"""
        print("_on_content_changed called")
        content = self._field.get_content()
        if not self._has_unsaved_changes:
            print("Setting has_unsaved_changes to True")
            self._has_unsaved_changes = True
            print("Calling _update_status")
            self._update_status()
        self.field_changed.emit(self.field_name, content)

    def _on_validation_changed(self, is_valid: bool, message: str):
        """Handle validation change from field"""
        pass  # Store validation state if needed

    def set_content(self, content: str):
        """Set field content"""
        self._field.set_content(content)
        self._has_unsaved_changes = False
        self._update_status()

    def get_content(self) -> str:
        """Get field content"""
        return self._field.get_content()

    def set_validation_state(self, is_valid: bool, message: str = ""):
        """Set field validation state"""
        self._field.set_validation_state(is_valid, message)

    def _update_status(self):
        """Update status bar"""
        print(f"_update_status called, has_unsaved_changes: {self._has_unsaved_changes}")
        print(f"Save button exists: {self._save_btn is not None}")
        print(f"Save button parent: {self._save_btn.parent()}")
        if self._has_unsaved_changes:
            print("Updating for unsaved changes")
            self._status_label.setText("Unsaved changes")
            self._save_btn.setVisible(True)
            print(f"Save button visible after set: {self._save_btn.isVisible()}")
        else:
            self._status_label.setText("No changes")
            self._save_btn.setVisible(False)

    def _handle_save(self):
        """Handle save button click"""
        self._has_unsaved_changes = False
        self._update_status()
        self.save_requested.emit()

    def _show_settings(self):
        """Show field settings dialog"""
        # Will be implemented when we add field settings functionality
        pass

    def set_read_only(self, read_only: bool):
        """Set read-only state"""
        self._field.set_read_only(read_only)

    def is_valid(self) -> bool:
        """Check if field is valid"""
        return self._field.is_valid()

    def clear(self):
        """Clear field content"""
        self._field.clear_content()
        self._has_unsaved_changes = False
        self._update_status()