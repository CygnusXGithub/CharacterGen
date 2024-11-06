from typing import Dict, Any, List, Optional, Type, Generic, TypeVar
from dataclasses import dataclass, field
from enum import Enum, auto
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout,
    QLabel, QFrame, QPushButton,
    QSpinBox, QCheckBox, QComboBox,
    QLineEdit, QColorDialog, QHBoxLayout
)
from PyQt6.QtCore import Qt, pyqtSignal

from core.state import UIStateManager
from ..widgets.base import BaseWidget

T = TypeVar('T')

class SettingType(Enum):
    """Types of settings"""
    STRING = auto()
    INTEGER = auto()
    FLOAT = auto()
    BOOLEAN = auto()
    COLOR = auto()
    CHOICE = auto()
    PATH = auto()
    FONT = auto()

@dataclass
class SettingDefinition(Generic[T]):
    """Definition of a setting"""
    key: str
    type: SettingType
    default: T
    label: str
    description: str = ""
    choices: Optional[list] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    requires_restart: bool = False
    category: str = "General"
    metadata: Dict[str, Any] = field(default_factory=dict)

class SettingsPanel(BaseWidget):
    """Base class for settings panels"""
    
    setting_changed = pyqtSignal(str, object)  # key, new_value
    
    def __init__(self, 
                 ui_manager: UIStateManager,
                 title: str,
                 parent: Optional[QWidget] = None):
        self.title = title
        self._settings: Dict[str, SettingDefinition] = {}
        self._widgets: Dict[str, QWidget] = {}
        super().__init__(ui_manager, parent)

    def _setup_ui(self):
        """Setup settings panel UI"""
        self._layout.setContentsMargins(16, 16, 16, 16)
        self._layout.setSpacing(8)
        
        # Title
        title_label = QLabel(self.title)
        title_label.setObjectName("settings_title")
        self._layout.addWidget(title_label)
        
        # Settings form
        self._form = QFormLayout()
        self._form.setSpacing(12)
        self._form.setContentsMargins(0, 16, 0, 16)
        self._layout.addLayout(self._form)
        
        # Create widgets for settings
        self._create_settings_widgets()
        
        # Add stretch at end
        self._layout.addStretch()

    def _setup_styling(self):
        """Setup panel styling"""
        self.setStyleSheet("""
            QLabel#settings_title {
                font-size: 16px;
                font-weight: bold;
                color: #2c3e50;
                padding-bottom: 8px;
                border-bottom: 1px solid #e9ecef;
            }
            
            QLabel[isDescription="true"] {
                color: #666666;
                font-size: 11px;
            }
            
            QPushButton {
                padding: 4px 12px;
                border: 1px solid #dcdcdc;
                border-radius: 4px;
            }
            
            QPushButton:hover {
                background-color: #f5f5f5;
            }
            
            QSpinBox, QLineEdit, QComboBox {
                padding: 4px 8px;
                border: 1px solid #dcdcdc;
                border-radius: 4px;
                min-width: 120px;
            }
            
            QSpinBox:hover, QLineEdit:hover, QComboBox:hover {
                border-color: #3498db;
            }
        """)

    def _create_settings_widgets(self):
        """Create widgets for settings"""
        # Group settings by category
        categories: Dict[str, List[SettingDefinition]] = {}
        for setting in self._settings.values():
            if setting.category not in categories:
                categories[setting.category] = []
            categories[setting.category].append(setting)
        
        # Add settings by category
        for category, settings in categories.items():
            if category != "General":
                # Add category header
                label = QLabel(category)
                label.setObjectName("category_header")
                self._form.addRow(label)
            
            # Add settings
            for setting in settings:
                self._add_setting_widget(setting)

    def _add_setting_widget(self, setting: SettingDefinition):
        """Add widget for a setting"""
        # Create label with description
        label_widget = QWidget()
        label_layout = QVBoxLayout(label_widget)
        label_layout.setContentsMargins(0, 0, 0, 0)
        label_layout.setSpacing(2)
        
        # Setting label
        label = QLabel(setting.label)
        label_layout.addWidget(label)
        
        # Description if provided
        if setting.description:
            desc = QLabel(setting.description)
            desc.setProperty("isDescription", True)
            desc.setWordWrap(True)
            label_layout.addWidget(desc)
        
        # Create appropriate widget based on type
        widget = self._create_type_widget(setting)
        if widget:
            self._widgets[setting.key] = widget
            self._form.addRow(label_widget, widget)

    def _create_type_widget(self, setting: SettingDefinition) -> Optional[QWidget]:
        """Create widget based on setting type"""
        if setting.type == SettingType.BOOLEAN:
            widget = QCheckBox()
            widget.setChecked(setting.default)
            widget.stateChanged.connect(
                lambda state: self._handle_change(setting.key, bool(state))
            )
            
        elif setting.type == SettingType.INTEGER:
            widget = QSpinBox()
            if setting.min_value is not None:
                widget.setMinimum(int(setting.min_value))
            if setting.max_value is not None:
                widget.setMaximum(int(setting.max_value))
            widget.setValue(setting.default)
            widget.valueChanged.connect(
                lambda value: self._handle_change(setting.key, value)
            )
            
        elif setting.type == SettingType.CHOICE:
            widget = QComboBox()
            if setting.choices:
                widget.addItems(setting.choices)
                widget.setCurrentText(str(setting.default))
                widget.currentTextChanged.connect(
                    lambda text: self._handle_change(setting.key, text)
                )
            
        elif setting.type == SettingType.COLOR:
            widget = QPushButton()
            widget.setStyleSheet(f"background-color: {setting.default};")
            widget.clicked.connect(lambda: self._show_color_dialog(setting.key))
            
        elif setting.type == SettingType.PATH:
            layout = QHBoxLayout()
            line_edit = QLineEdit(str(setting.default))
            browse_btn = QPushButton("Browse")
            browse_btn.clicked.connect(lambda: self._show_path_dialog(setting.key))
            layout.addWidget(line_edit)
            layout.addWidget(browse_btn)
            container = QWidget()
            container.setLayout(layout)
            widget = container
            
        else:  # STRING and others
            widget = QLineEdit(str(setting.default))
            widget.textChanged.connect(
                lambda text: self._handle_change(setting.key, text)
            )
            
        return widget

    def _handle_change(self, key: str, value: Any):
        """Handle setting change"""
        if key in self._settings:
            self.setting_changed.emit(key, value)

    def _show_color_dialog(self, key: str):
        """Show color picker dialog"""
        dialog = QColorDialog(self)
        if dialog.exec():
            color = dialog.selectedColor().name()
            self._widgets[key].setStyleSheet(f"background-color: {color};")
            self._handle_change(key, color)

    def _show_path_dialog(self, key: str):
        """Show path selection dialog"""
        # TODO: Implement path selection
        pass

    def add_setting(self, setting: SettingDefinition):
        """Add a setting definition"""
        self._settings[setting.key] = setting

    def get_value(self, key: str) -> Optional[Any]:
        """Get current value of a setting"""
        if key not in self._widgets:
            return None
            
        widget = self._widgets[key]
        if isinstance(widget, QCheckBox):
            return widget.isChecked()
        elif isinstance(widget, QSpinBox):
            return widget.value()
        elif isinstance(widget, QComboBox):
            return widget.currentText()
        elif isinstance(widget, QLineEdit):
            return widget.text()
        elif isinstance(widget, QPushButton):  # Color button
            return widget.styleSheet().split(": ")[1].rstrip(";")
            
        return None

    def set_value(self, key: str, value: Any):
        """Set value of a setting"""
        if key not in self._widgets:
            return
            
        widget = self._widgets[key]
        if isinstance(widget, QCheckBox):
            widget.setChecked(bool(value))
        elif isinstance(widget, QSpinBox):
            widget.setValue(int(value))
        elif isinstance(widget, QComboBox):
            widget.setCurrentText(str(value))
        elif isinstance(widget, QLineEdit):
            widget.setText(str(value))
        elif isinstance(widget, QPushButton):  # Color button
            widget.setStyleSheet(f"background-color: {value};")