from typing import Dict, Optional, List
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea, 
    QFrame, QSizePolicy, QSpacerItem
)
from PyQt6.QtCore import Qt, pyqtSignal

from core.state import UIStateManager
from ..base import BaseWidget
from ..fields.editor import FieldEditor

class FieldContainer(BaseWidget):
    """Container for organizing and managing multiple fields"""
    
    field_changed = pyqtSignal(str, str)  # field_name, new_value
    generate_requested = pyqtSignal(str)  # field_name
    save_requested = pyqtSignal()

    def __init__(self, ui_manager: UIStateManager, parent: Optional[QWidget] = None):
        self._fields: Dict[str, FieldEditor] = {}
        super().__init__(ui_manager, parent)

    def _setup_ui(self):
        """Setup container UI"""
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        # Create scroll area
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._layout.addWidget(scroll)

        # Create content widget
        content = QWidget()
        self._content_layout = QVBoxLayout(content)
        self._content_layout.setContentsMargins(16, 16, 16, 16)
        self._content_layout.setSpacing(16)
        
        # Add stretch at the end
        self._content_layout.addStretch()
        
        scroll.setWidget(content)

    def _setup_styling(self):
        """Setup container styling"""
        self.setStyleSheet("""
            FieldContainer {
                background-color: #ffffff;
            }
            
            QScrollArea {
                background-color: transparent;
            }
            
            QWidget#content {
                background-color: transparent;
            }
        """)

    def add_field(self, 
                  field_name: str,
                  label: str = "",
                  help_text: str = "",
                  multiline: bool = True,
                  required: bool = False) -> FieldEditor:
        """Add a new field to the container"""
        # Create field editor
        field = FieldEditor(
            ui_manager=self.ui_manager,
            field_name=field_name,
            label=label,
            help_text=help_text,
            multiline=multiline,
            required=required,
            parent=self
        )

        # Connect signals
        field.field_changed.connect(
            lambda name, value: self.field_changed.emit(name, value)
        )
        field.generate_requested.connect(
            lambda name: self.generate_requested.emit(name)
        )
        field.save_requested.connect(self.save_requested.emit)

        # Add to layout before stretch
        self._content_layout.insertWidget(self._content_layout.count() - 1, field)
        
        # Store reference
        self._fields[field_name] = field
        
        return field

    def get_field(self, field_name: str) -> Optional[FieldEditor]:
        """Get field by name"""
        return self._fields.get(field_name)

    def remove_field(self, field_name: str) -> bool:
        """Remove field from container"""
        if field_name not in self._fields:
            return False

        field = self._fields.pop(field_name)
        self._content_layout.removeWidget(field)
        field.deleteLater()
        return True

    def clear_fields(self):
        """Remove all fields"""
        for field_name in list(self._fields.keys()):
            self.remove_field(field_name)

    def get_modified_fields(self) -> List[str]:
        """Get list of modified field names"""
        return [name for name, field in self._fields.items() 
                if field.has_unsaved_changes()]

    def validate_fields(self) -> bool:
        """Validate all fields"""
        return all(field.is_valid() for field in self._fields.values())