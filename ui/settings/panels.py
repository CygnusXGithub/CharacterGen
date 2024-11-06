from typing import Dict, Any, Optional
from pathlib import Path
from PyQt6.QtWidgets import QWidget

from .base import SettingsPanel, SettingDefinition, SettingType
from core.state import UIStateManager

class GeneralSettings(SettingsPanel):
    """General application settings"""
    
    def __init__(self, ui_manager: UIStateManager, parent: Optional[QWidget] = None):
        super().__init__(ui_manager, "General Settings", parent)
        self._define_settings()
        
    def _define_settings(self):
        """Define general settings"""
        self.add_setting(SettingDefinition(
            key="auto_save",
            type=SettingType.BOOLEAN,
            default=True,
            label="Auto Save",
            description="Automatically save changes periodically",
            category="Saving"
        ))
        
        self.add_setting(SettingDefinition(
            key="auto_save_interval",
            type=SettingType.INTEGER,
            default=300,
            label="Auto Save Interval",
            description="Seconds between auto-saves",
            min_value=60,
            max_value=3600,
            category="Saving"
        ))
        
        self.add_setting(SettingDefinition(
            key="save_path",
            type=SettingType.PATH,
            default=Path("saves"),
            label="Save Directory",
            description="Directory for character files",
            category="Saving"
        ))
        
        self.add_setting(SettingDefinition(
            key="theme",
            type=SettingType.CHOICE,
            default="Light",
            label="Theme",
            choices=["Light", "Dark", "System"],
            requires_restart=True,
            category="Appearance"
        ))

class GenerationSettings(SettingsPanel):
    """Generation-related settings"""
    
    def __init__(self, ui_manager: UIStateManager, parent: Optional[QWidget] = None):
        super().__init__(ui_manager, "Generation Settings", parent)
        self._define_settings()
        
    def _define_settings(self):
        """Define generation settings"""
        self.add_setting(SettingDefinition(
            key="max_retries",
            type=SettingType.INTEGER,
            default=3,
            label="Maximum Retries",
            description="Maximum generation retry attempts",
            min_value=0,
            max_value=10,
            category="Generation"
        ))
        
        self.add_setting(SettingDefinition(
            key="batch_size",
            type=SettingType.INTEGER,
            default=5,
            label="Batch Size",
            description="Number of generations per batch",
            min_value=1,
            max_value=20,
            category="Generation"
        ))
        
        self.add_setting(SettingDefinition(
            key="auto_regen_deps",
            type=SettingType.BOOLEAN,
            default=True,
            label="Auto-Regenerate Dependencies",
            description="Automatically regenerate dependent fields",
            category="Dependencies"
        ))

class EditorSettings(SettingsPanel):
    """Editor-specific settings"""
    
    def __init__(self, ui_manager: UIStateManager, parent: Optional[QWidget] = None):
        super().__init__(ui_manager, "Editor Settings", parent)
        self._define_settings()
        
    def _define_settings(self):
        """Define editor settings"""
        self.add_setting(SettingDefinition(
            key="font_size",
            type=SettingType.INTEGER,
            default=12,
            label="Font Size",
            description="Editor font size in points",
            min_value=8,
            max_value=24,
            category="Editor"
        ))
        
        self.add_setting(SettingDefinition(
            key="line_numbers",
            type=SettingType.BOOLEAN,
            default=True,
            label="Show Line Numbers",
            description="Display line numbers in editor",
            category="Editor"
        ))
        
        self.add_setting(SettingDefinition(
            key="highlight_color",
            type=SettingType.COLOR,
            default="#FFE9B2",
            label="Highlight Color",
            description="Color for text highlights",
            category="Colors"
        ))
        
        self.add_setting(SettingDefinition(
            key="selection_color",
            type=SettingType.COLOR,
            default="#B2D6FF",
            label="Selection Color",
            description="Color for selected text",
            category="Colors"
        ))