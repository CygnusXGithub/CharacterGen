from typing import Dict, Any, Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QTabWidget, QPushButton, QWidget,
    QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal

from core.state import UIStateManager
from ..dialogs.base import BaseDialog
from .panels import GeneralSettings, GenerationSettings, EditorSettings

class SettingsDialog(BaseDialog):
    """Main settings dialog"""
    
    settings_changed = pyqtSignal(dict)  # Dictionary of changed settings
    
    def __init__(self, 
                 ui_manager: UIStateManager,
                 parent: Optional[QWidget] = None):
        super().__init__(ui_manager, "Settings", parent)
        self._changed_settings: Dict[str, Any] = {}
        self._setup_dialog()
        
    def _setup_dialog(self):
        """Setup settings dialog UI"""
        # Create tab widget
        self._tabs = QTabWidget(self)
        self._tabs.setObjectName("settings_tabs")
        
        # Create settings panels
        self._general = GeneralSettings(self.ui_manager)
        self._generation = GenerationSettings(self.ui_manager)
        self._editor = EditorSettings(self.ui_manager)
        
        # Add panels to tabs
        self._tabs.addTab(self._general, "General")
        self._tabs.addTab(self._generation, "Generation")
        self._tabs.addTab(self._editor, "Editor")
        
        # Connect panel signals
        self._general.setting_changed.connect(self._handle_setting_change)
        self._generation.setting_changed.connect(self._handle_setting_change)
        self._editor.setting_changed.connect(self._handle_setting_change)
        
        # Add tabs to content
        self._content_layout.addWidget(self._tabs)
        
        # Add apply button
        self._apply_btn = QPushButton("Apply")
        self._apply_btn.setObjectName("apply_button")
        self._apply_btn.clicked.connect(self._apply_changes)
        self._apply_btn.setEnabled(False)
        
        # Add apply button to button bar
        button_layout = self._button_bar.layout()
        button_layout.insertWidget(button_layout.count() - 1, self._apply_btn)
        
        # Update styling
        self.setStyleSheet(self.styleSheet() + """
            QTabWidget#settings_tabs {
                background-color: transparent;
            }
            
            QTabWidget::pane {
                border: none;
                background-color: transparent;
            }
            
            QTabBar::tab {
                padding: 8px 16px;
                background-color: transparent;
                border: none;
                border-bottom: 2px solid transparent;
                color: #666666;
            }
            
            QTabBar::tab:hover {
                color: #2980b9;
            }
            
            QTabBar::tab:selected {
                color: #2980b9;
                border-bottom: 2px solid #2980b9;
            }
            
            QPushButton#apply_button {
                background-color: #2ecc71;
                border-color: #27ae60;
                color: white;
            }
            
            QPushButton#apply_button:hover {
                background-color: #27ae60;
            }
            
            QPushButton#apply_button:disabled {
                background-color: #bdc3c7;
                border-color: #95a5a6;
            }
        """)

    def _handle_setting_change(self, key: str, value: Any):
        """Handle setting change in any panel"""
        self._changed_settings[key] = value
        self._apply_btn.setEnabled(True)

    def _apply_changes(self):
        """Apply changed settings"""
        if self._changed_settings:
            self.settings_changed.emit(self._changed_settings)
            self._changed_settings.clear()
            self._apply_btn.setEnabled(False)

    def get_changed_settings(self) -> Dict[str, Any]:
        """Get dictionary of changed settings"""
        return self._changed_settings.copy()

    def load_settings(self, settings: Dict[str, Any]):
        """Load current settings into panels"""
        for key, value in settings.items():
            # Determine which panel the setting belongs to
            if key.startswith("editor_"):
                self._editor.set_value(key, value)
            elif key.startswith("generation_"):
                self._generation.set_value(key, value)
            else:
                self._general.set_value(key, value)

    def _handle_confirm(self):
        """Override confirm to apply changes first"""
        if self._changed_settings:
            self._apply_changes()
        super()._handle_confirm()

    def _handle_cancel(self):
        """Override cancel to warn about unsaved changes"""
        if self._changed_settings:
            # TODO: Show confirmation dialog
            pass
        super()._handle_cancel()