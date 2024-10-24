from typing import Dict, Optional
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QMessageBox
from PyQt6.QtCore import pyqtSignal

from ...core.enums import FieldName
from ...core.models import PromptTemplate, PromptSet
from ...core.exceptions import PromptLoadError, PromptSaveError
from ...services.prompt_service import PromptService
from ..widgets.base_prompt_widgets import BasePromptsContainer

class BasePromptsTab(QWidget):
    """Tab for managing base prompts"""
    prompt_set_loaded = pyqtSignal(PromptSet)  # Emitted when a new prompt set is loaded
    
    def __init__(self, prompt_service: PromptService, parent=None):
        super().__init__(parent)
        self.prompt_service = prompt_service
        self._init_ui()
        self._connect_signals()
        self._load_available_sets()
    
    def _init_ui(self):
        layout = QVBoxLayout()
        
        # Create base prompts container
        self.prompts_container = BasePromptsContainer()
        layout.addWidget(self.prompts_container)
        
        self.setLayout(layout)
    
    def _connect_signals(self):
        """Connect signal handlers"""
        # Connect load/save signals from container
        self.prompts_container.load_save.load_clicked.connect(self._handle_load)
        self.prompts_container.load_save.refresh_clicked.connect(self._load_available_sets)
        self.prompts_container.save_requested.connect(self._handle_save)
    
    def _load_available_sets(self):
        """Load list of available prompt sets"""
        try:
            sets = self.prompt_service.list_prompt_sets()
            self.prompts_container.update_available_sets(sets)
        except PromptLoadError as e:
            QMessageBox.warning(
                self,
                "Load Error",
                f"Error loading prompt sets: {str(e)}"
            )
    
    def _handle_load(self, name: str):
        """Handle loading of a prompt set"""
        if not name:
            return
            
        try:
            prompt_set = self.prompt_service.load_prompt_set(name)
            
            # Update UI with loaded prompts
            self.prompts_container.set_prompts({
                field: template.text
                for field, template in prompt_set.templates.items()
            })
            
            self.prompts_container.set_orders({
                field: template.generation_order
                for field, template in prompt_set.templates.items()
            })
            
            # Emit signal that prompt set was loaded
            self.prompt_set_loaded.emit(prompt_set)
            
        except PromptLoadError as e:
            QMessageBox.warning(
                self,
                "Load Error",
                f"Error loading prompt set '{name}': {str(e)}"
            )
    
    def _handle_save(self, name: str, prompts: Dict[FieldName, str], 
                    orders: Dict[FieldName, int]):
        """Handle saving of prompt set"""
        try:
            # Create new prompt set
            prompt_set = self.prompt_service.create_prompt_set(name)
            
            # Add templates
            for field in FieldName:
                if field in prompts and prompts[field].strip():
                    prompt_set.templates[field] = PromptTemplate(
                        text=prompts[field],
                        field=field,
                        generation_order=orders.get(field, 0)
                    )
            
            # Validate prompt set
            if not prompt_set.validate():
                raise ValueError("Invalid prompt dependencies")
            
            # Save prompt set
            self.prompt_service.save_prompt_set(prompt_set)
            
            # Refresh available sets
            self._load_available_sets()
            
            QMessageBox.information(
                self,
                "Success",
                f"Prompt set '{name}' saved successfully"
            )
            
        except Exception as e:
            QMessageBox.warning(
                self,
                "Save Error",
                f"Error saving prompt set: {str(e)}"
            )
    
    def get_current_prompts(self) -> Dict[FieldName, str]:
        """Get current prompt texts"""
        return self.prompts_container.get_prompts()
    
    def get_current_orders(self) -> Dict[FieldName, int]:
        """Get current generation orders"""
        return self.prompts_container.get_orders()
