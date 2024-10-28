from typing import Dict, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QMessageBox, QLabel
)
from PyQt6.QtCore import pyqtSignal

from ...core.enums import (
    FieldName, OperationType, StatusLevel,
    ValidationLevel, EventType
)
from ...core.models import PromptTemplate, PromptSet
from ...core.exceptions import (
    PromptLoadError, PromptSaveError,
    TagError, MismatchedTagError, ValidationError
)
from ...core.managers import (
    UIStateManager,
    SettingsManager
)
from ...services.prompt_service import PromptService
from ..widgets.base_prompt_widgets import BasePromptsContainer

class BasePromptsTab(QWidget):
    """Tab for managing base prompts"""
    
    # Signals
    operation_requested = pyqtSignal(OperationType, dict)  # Operation type and parameters
    prompt_set_loaded = pyqtSignal(PromptSet)             # When a new prompt set is loaded
    status_update = pyqtSignal(str, int)         # Status message and level
    
    def __init__(self, 
                 prompt_service: PromptService,
                 ui_manager: UIStateManager,
                 settings_manager: SettingsManager,
                 parent=None):
        super().__init__(parent)
        self.prompt_service = prompt_service
        self.ui_manager = ui_manager
        self.settings_manager = settings_manager
        self.current_set: Optional[PromptSet] = None
        self.is_updating = False
        self._init_ui()
        self._connect_signals()
        self._load_available_sets()
    
    def _init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Header section
        header = QWidget()
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        title = QLabel("Base Prompts")
        font = title.font()
        font.setBold(True)
        font.setPointSize(12)
        title.setFont(font)
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        header.setLayout(header_layout)
        layout.addWidget(header)
        
        # Create base prompts container
        self.prompts_container = BasePromptsContainer(
            self.prompt_service,
            self.ui_manager,
            self.settings_manager
        )
        layout.addWidget(self.prompts_container)
        
        self.setLayout(layout)
    
    def _connect_signals(self):
        """Connect signal handlers"""
        # Connect load/save signals from container
        self.prompts_container.save_requested.connect(self._handle_save)
        
        # Connect validation signals
        self.prompts_container.prompt_validated.connect(self._handle_validation_result)
        
        # Connect UI manager signals
        self.ui_manager.status_message.connect(self._handle_status_message)
    
    def _load_available_sets(self):
        """Load list of available prompt sets"""
        try:
            sets = self.prompt_service.list_prompt_sets()
            self.prompts_container.update_available_sets(sets)
            self.status_update.emit("Prompt sets loaded", StatusLevel.INFO)
            
        except PromptLoadError as e:
            self.status_update.emit(f"Error loading prompt sets: {str(e)}", StatusLevel.ERROR)
            QMessageBox.warning(
                self,
                "Load Error",
                f"Error loading prompt sets: {str(e)}"
            )
    
    def _handle_save(self, name: str, prompts: Dict[FieldName, str], 
                    orders: Dict[FieldName, int]):
        """Handle saving of prompt set"""
        if not name:
            self.status_update.emit("Please enter a name for the prompt set", StatusLevel.WARNING)
            return
            
        try:
            # Create new prompt set
            prompt_set = self.prompt_service.create_prompt_set(name)
            
            # Add templates
            for field in FieldName:
                if field in prompts and prompts[field].strip():
                    try:
                        # Validate template first
                        warnings = self.prompt_service._validate_template_text(prompts[field])
                        if warnings:
                            self.status_update.emit(
                                f"Warnings in {field.value}: {', '.join(warnings)}", 
                                StatusLevel.WARNING
                            )
                        
                        prompt_set.templates[field] = PromptTemplate(
                            text=prompts[field],
                            field=field,
                            generation_order=orders.get(field, -1)
                        )
                    except TagError as e:
                        raise ValidationError(f"Error in {field.value}: {str(e)}")
            
            # Validate prompt set
            if not prompt_set.validate():
                raise ValidationError("Invalid prompt dependencies")
            
            # Save prompt set
            self.prompt_service.save_prompt_set(prompt_set)
            
            # Update UI
            self._load_available_sets()
            self.current_set = prompt_set
            
            # Emit signals
            self.prompt_set_loaded.emit(prompt_set)
            self.status_update.emit(f"Saved prompt set: {name}", StatusLevel.SUCCESS)
            
        except Exception as e:
            self.status_update.emit(f"Error saving prompt set: {str(e)}", StatusLevel.ERROR)
            QMessageBox.warning(
                self,
                "Save Error",
                f"Error saving prompt set: {str(e)}"
            )
    
    def _handle_validation_result(self, field: FieldName, 
                                is_valid: bool, message: str):
        """Handle validation results"""
        level = ValidationLevel.PASS if is_valid else ValidationLevel.ERROR
        self.status_update.emit(
            f"Validation {field.value}: {message}",
            StatusLevel.INFO if is_valid else StatusLevel.ERROR
        )
    
    def _handle_status_message(self, message: str, level: StatusLevel):
        """Handle status message updates"""
        # Convert StatusLevel to int for the signal
        level_value = {
            StatusLevel.INFO: 0,
            StatusLevel.SUCCESS: 1,
            StatusLevel.WARNING: 2,
            StatusLevel.ERROR: 3
        }.get(level, 0)
        self.status_update.emit(message, level_value)
    
    def get_current_prompts(self) -> Dict[FieldName, str]:
        """Get current prompt texts"""
        return self.prompts_container.get_prompts()
    
    def get_current_orders(self) -> Dict[FieldName, int]:
        """Get current generation orders"""
        return self.prompts_container.get_orders()
    
    def clear_all(self):
        """Clear all prompts"""
        self.prompts_container.clear_all()
        self.current_set = None
        self.status_update.emit("Cleared all prompts", StatusLevel.INFO)
    
    def closeEvent(self, event):
        """Handle tab closing"""
        if self.prompts_container.prompt_save_if_modified():
            self.status_update.emit("Base prompts tab closed", StatusLevel.INFO)
            event.accept()
        else:
            event.ignore()