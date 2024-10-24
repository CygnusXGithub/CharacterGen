from typing import Dict, Optional, List
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QLabel, QLineEdit, QSpinBox, QFrame,
    QPushButton, QScrollArea, QMessageBox
)
from PyQt6.QtCore import pyqtSignal

from ...core.enums import FieldName
from ...core.exceptions import TagError, MismatchedTagError
from ..widgets.common import EditableField, LoadSaveWidget

class BasePromptWidget(QWidget):
    """Widget for editing a single base prompt"""
    prompt_changed = pyqtSignal(FieldName, str)  # Prompt text changed
    order_changed = pyqtSignal(FieldName, int)  # Generation order changed
    
    def __init__(self, field: FieldName, parent=None):
        super().__init__(parent)
        self.field = field
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout()
        
        # Header with field name and order
        header = QHBoxLayout()
        
        # Field name label
        label = QLabel(f"Base Prompt for {self.field.value.title()}")
        header.addWidget(label)
        
        # Generation order input
        header.addWidget(QLabel("Generation Order:"))
        self.order_input = QSpinBox()
        self.order_input.setRange(0, 99)
        self.order_input.valueChanged.connect(
            lambda value: self.order_changed.emit(self.field, value)
        )
        header.addWidget(self.order_input)
        
        layout.addLayout(header)
        
        # Prompt text area
        self.prompt_edit = QTextEdit()
        self.prompt_edit.setPlaceholderText(
            "Enter base prompt...\n"
            "Available tags:\n"
            "{{input}} - User input\n"
            "{{field_name}} - Other fields\n"
            "{{if_input}}...{{/if_input}} - Conditional content"
        )
        self.prompt_edit.setAcceptRichText(False)
        self.prompt_edit.textChanged.connect(
            lambda: self.prompt_changed.emit(
                self.field, 
                self.prompt_edit.toPlainText()
            )
        )
        layout.addWidget(self.prompt_edit)
        
        # Add a help section
        help_frame = QFrame()
        help_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        help_layout = QVBoxLayout(help_frame)
        
        help_label = QLabel("Available Fields:")
        help_layout.addWidget(help_label)
        
        field_list = ", ".join(f"{{{{{f.value}}}}}" for f in FieldName)
        fields_label = QLabel(field_list)
        fields_label.setWordWrap(True)
        help_layout.addWidget(fields_label)
        
        layout.addWidget(help_frame)
        
        self.setLayout(layout)
    
    def get_prompt(self) -> str:
        """Get prompt text"""
        return self.prompt_edit.toPlainText()
    
    def set_prompt(self, text: str):
        """Set prompt text"""
        self.prompt_edit.setPlainText(text)
    
    def get_order(self) -> int:
        """Get generation order"""
        return self.order_input.value()
    
    def set_order(self, value: int):
        """Set generation order"""
        self.order_input.setValue(value)
    
    def clear(self):
        """Clear all inputs"""
        self.prompt_edit.clear()
        self.order_input.setValue(0)

class BasePromptsContainer(QWidget):
    """Container for all base prompt widgets"""
    save_requested = pyqtSignal(str, object, object)  # name, prompts, orders
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.prompt_widgets: Dict[FieldName, BasePromptWidget] = {}
        self._init_ui()
    
    def _init_ui(self):
        main_layout = QVBoxLayout()
        
        # Add load/save controls
        self.load_save = LoadSaveWidget(
            save_label="Prompt Set Name:",
            load_label="Load Set:"
        )
        self.load_save.save_clicked.connect(self._handle_save)
        main_layout.addWidget(self.load_save)
        
        # Add separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        main_layout.addWidget(separator)
        
        # Create scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        # Container for prompt widgets
        container = QWidget()
        layout = QVBoxLayout(container)
        
        # Create widgets for each field
        for field in FieldName:
            widget = BasePromptWidget(field)
            self.prompt_widgets[field] = widget
            layout.addWidget(widget)
        
        # Add buttons at the bottom
        button_layout = QHBoxLayout()
        
        # Clear button
        clear_btn = QPushButton("Clear All")
        clear_btn.clicked.connect(self._handle_clear)
        button_layout.addWidget(clear_btn)
        
        # Validate button
        validate_btn = QPushButton("Validate Tags")
        validate_btn.clicked.connect(self._handle_validate)
        button_layout.addWidget(validate_btn)
        
        layout.addLayout(button_layout)
        
        # Add container to scroll area
        scroll.setWidget(container)
        main_layout.addWidget(scroll)
        
        self.setLayout(main_layout)
    
    def _handle_save(self, name: str):
        """Handle save request"""
        if not name:
            QMessageBox.warning(
                self,
                "Save Error",
                "Please enter a name for the prompt set"
            )
            return
            
        prompts = self.get_prompts()
        orders = self.get_orders()
        
        # Validate before saving
        try:
            self._validate_prompts(prompts)
            self.save_requested.emit(name, prompts, orders)
        except TagError as e:
            QMessageBox.warning(
                self,
                "Validation Error",
                f"Error in prompts: {str(e)}"
            )
    
    def _handle_clear(self):
        """Handle clear all request"""
        reply = QMessageBox.question(
            self,
            "Clear Confirmation",
            "Are you sure you want to clear all prompts?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            for widget in self.prompt_widgets.values():
                widget.clear()
    
    def _handle_validate(self):
        """Validate all prompts"""
        try:
            self._validate_prompts(self.get_prompts())
            QMessageBox.information(
                self,
                "Validation Success",
                "All prompts are valid"
            )
        except TagError as e:
            QMessageBox.warning(
                self,
                "Validation Error",
                f"Error in prompts: {str(e)}"
            )
    
    def _validate_prompts(self, prompts: Dict[FieldName, str]) -> bool:
        """Validate prompt tags"""
        import re
        
        for field, prompt in prompts.items():
            if not prompt.strip():
                continue
                
            # Check for balanced conditional tags
            open_tags = len(re.findall(r'{{if_input}}', prompt))
            close_tags = len(re.findall(r'{{/if_input}}', prompt))
            
            if open_tags != close_tags:
                raise TagError(
                    f"Mismatched conditional tags in {field.value}: "
                    f"{open_tags} opening tags, {close_tags} closing tags"
                )
            
            # Validate field references
            field_refs = re.findall(r'{{(\w+)}}', prompt)
            for ref in field_refs:
                if ref not in ['input', 'if_input', '/if_input', 'char', 'user']:
                    try:
                        FieldName(ref)
                    except ValueError:
                        raise TagError(
                            f"Invalid field reference in {field.value}: {ref}"
                        )
        
        return True
    
    def get_prompts(self) -> Dict[FieldName, str]:
        """Get all prompt texts"""
        return {
            field: widget.get_prompt()
            for field, widget in self.prompt_widgets.items()
        }
    
    def get_orders(self) -> Dict[FieldName, int]:
        """Get all generation orders"""
        return {
            field: widget.get_order()
            for field, widget in self.prompt_widgets.items()
        }
    
    def set_prompts(self, prompts: Dict[FieldName, str]):
        """Set all prompt texts"""
        for field, text in prompts.items():
            if field in self.prompt_widgets:
                self.prompt_widgets[field].set_prompt(text)
    
    def set_orders(self, orders: Dict[FieldName, int]):
        """Set all generation orders"""
        for field, order in orders.items():
            if field in self.prompt_widgets:
                self.prompt_widgets[field].set_order(order)
    
    def update_available_sets(self, sets: List[str]):
        """Update list of available prompt sets"""
        self.load_save.update_items(sets)
    
    def clear_all(self):
        """Clear all widgets"""
        for widget in self.prompt_widgets.values():
            widget.clear()