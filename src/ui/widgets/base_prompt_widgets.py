from typing import Dict, Optional, List
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QLabel, QLineEdit, QSpinBox, QFrame,
    QPushButton, QScrollArea, QMessageBox, QSizePolicy,
    QGroupBox, QFormLayout
)
from PyQt6.QtCore import pyqtSignal, Qt
from pathlib import Path

from ...core.enums import FieldName
from ...core.models import PromptTemplate, PromptSet
from ...core.exceptions import TagError, MismatchedTagError
from ...core.managers import UIStateManager, SettingsManager
from ...services.prompt_service import PromptService
from ..widgets.common import LoadSaveWidget

class BasePromptWidget(QWidget):
    """Widget for editing a single base prompt"""
    prompt_changed = pyqtSignal(FieldName, str)  # Prompt text changed
    order_changed = pyqtSignal(FieldName, int)   # Generation order changed
    validation_requested = pyqtSignal(FieldName)  # Validation requested
    
    def __init__(self, 
                 field: FieldName,
                 ui_manager: UIStateManager,
                 settings_manager: SettingsManager,
                 parent=None):
        super().__init__(parent)
        self.field = field
        self.ui_manager = ui_manager
        self.settings_manager = settings_manager
        self.is_updating = False
        self._init_ui()
        self._connect_signals()
    
    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(5)
        
        # Header section
        header = QWidget()
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        # Field name label
        label = QLabel(f"Base Prompt for {self.field.value.title()}")
        font = label.font()
        font.setBold(True)
        label.setFont(font)
        header_layout.addWidget(label)
        
        # Add spacer
        header_layout.addStretch()
        
        # Generation order section
        order_widget = QWidget()
        order_layout = QHBoxLayout()
        order_layout.setContentsMargins(0, 0, 0, 0)
        
        order_label = QLabel("Generation Order:")
        order_layout.addWidget(order_label)
        
        self.order_input = QSpinBox()
        self.order_input.setMinimum(-1)
        self.order_input.setMaximum(99)
        self.order_input.setValue(-1)
        self.order_input.setSpecialValueText(" ")  # Show empty for -1
        self.order_input.valueChanged.connect(self._handle_order_change)
        order_layout.addWidget(self.order_input)
        
        header_layout.addLayout(order_layout)
        header.setLayout(header_layout)
        layout.addWidget(header)
        
        # Prompt editor
        self.prompt_edit = QTextEdit()
        self.prompt_edit.setAcceptRichText(False)
        self.prompt_edit.setPlaceholderText("Enter base prompt...")
        self.prompt_edit.textChanged.connect(self._handle_prompt_change)
        
        # Apply settings
        font_size = self.settings_manager.get("ui.font_size", 10)
        font = self.prompt_edit.font()
        font.setPointSize(font_size)
        self.prompt_edit.setFont(font)
        
        layout.addWidget(self.prompt_edit)
        
        # Validation button
        validate_btn = QPushButton("Validate Tags")
        validate_btn.clicked.connect(lambda: self.validation_requested.emit(self.field))
        layout.addWidget(validate_btn)
        
        self.setLayout(layout)
    
    def _connect_signals(self):
        """Connect internal signals"""
        self.settings_manager.settings_updated.connect(self._apply_settings)
    
    def _handle_prompt_change(self):
        """Handle prompt text changes"""
        if not self.is_updating:
            self.is_updating = True
            try:
                self.prompt_changed.emit(self.field, self.prompt_edit.toPlainText())
            finally:
                self.is_updating = False
    
    def _handle_order_change(self, value: int):
        """Handle order input changes"""
        if not self.is_updating:
            self.is_updating = True
            try:
                self.order_changed.emit(self.field, value)
            finally:
                self.is_updating = False
    
    def _apply_settings(self):
        """Apply updated settings"""
        font_size = self.settings_manager.get("ui.font_size", 10)
        font = self.prompt_edit.font()
        font.setPointSize(font_size)
        self.prompt_edit.setFont(font)
    
    def get_prompt(self) -> str:
        """Get prompt text"""
        return self.prompt_edit.toPlainText()
    
    def set_prompt(self, text: str):
        """Set prompt text without triggering signals"""
        self.is_updating = True
        try:
            self.prompt_edit.setPlainText(text)
        finally:
            self.is_updating = False
    
    def get_order(self) -> int:
        """Get generation order"""
        return self.order_input.value()
    
    def set_order(self, value: int):
        """Set generation order without triggering signals"""
        self.is_updating = True
        try:
            self.order_input.setValue(value)
        finally:
            self.is_updating = False
    
    def clear(self):
        """Clear all inputs"""
        self.set_prompt("")
        self.set_order(-1)

class BasePromptsContainer(QWidget):
    """Container for all base prompt widgets"""
    save_requested = pyqtSignal(str, dict, dict)  # name, prompts, orders
    prompt_validated = pyqtSignal(FieldName, bool, str)  # field, is_valid, message
    
    def __init__(self, 
                 prompt_service: PromptService,
                 ui_manager: UIStateManager,
                 settings_manager: SettingsManager,
                 parent=None):
        super().__init__(parent)
        self.prompt_service = prompt_service
        self.ui_manager = ui_manager
        self.settings_manager = settings_manager
        self.prompt_widgets: Dict[FieldName, BasePromptWidget] = {}
        self._init_ui()
        self._connect_signals()
    
    def _init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        
        # Top controls section
        controls = QWidget()
        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(0, 0, 0, 0)
        
        # Load/Save widget
        self.load_save = LoadSaveWidget(
            save_label="Prompt Set Name:",
            load_label="Load Set:"
        )
        controls_layout.addWidget(self.load_save)
        
        # Action buttons
        refresh_btn = QPushButton("🔄")
        refresh_btn.setToolTip("Refresh prompt sets")
        refresh_btn.clicked.connect(self._refresh_prompt_sets)
        controls_layout.addWidget(refresh_btn)
        
        controls.setLayout(controls_layout)
        main_layout.addWidget(controls)
        
        # Add separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        main_layout.addWidget(separator)
        
        # Create scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Container for prompt widgets
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(20)
        
        # Create widgets for each field
        for field in FieldName:
            widget = BasePromptWidget(field, self.ui_manager, self.settings_manager)
            self.prompt_widgets[field] = widget
            layout.addWidget(widget)
        
        # Add buttons at the bottom
        button_layout = QHBoxLayout()
        
        validate_all_btn = QPushButton("Validate All")
        validate_all_btn.clicked.connect(self._validate_all)
        button_layout.addWidget(validate_all_btn)
        
        clear_all_btn = QPushButton("Clear All")
        clear_all_btn.clicked.connect(self._handle_clear)
        button_layout.addWidget(clear_all_btn)
        
        layout.addLayout(button_layout)
        
        # Add stretch at the bottom
        layout.addStretch()
        
        scroll.setWidget(container)
        main_layout.addWidget(scroll)
        
        self.setLayout(main_layout)
    
    def _connect_signals(self):
        """Connect widget signals"""
        # Connect load/save signals
        self.load_save.save_clicked.connect(self._handle_save)
        self.load_save.load_clicked.connect(self._handle_load)
        
        # Connect widget signals
        for widget in self.prompt_widgets.values():
            widget.validation_requested.connect(self._validate_prompt)
    
    def _handle_save(self, name: str):
        """Handle save request"""
        if not name:
            self.ui_manager.show_status_message(
                "Please enter a name for the prompt set",
                3000
            )
            return
        
        prompts = self.get_prompts()
        orders = self.get_orders()
        
        try:
            self._validate_all_prompts(prompts)
            self.save_requested.emit(name, prompts, orders)
            self.ui_manager.show_status_message(
                f"Saved prompt set: {name}",
                3000
            )
        except TagError as e:
            QMessageBox.warning(
                self,
                "Validation Error",
                f"Error in prompts: {str(e)}"
            )
    
    def _handle_load(self, name: str):
        """Handle load request"""
        try:
            prompt_set = self.prompt_service.load_prompt_set(name)
            self.set_prompts({
                field: template.text
                for field, template in prompt_set.templates.items()
            })
            self.set_orders({
                field: template.generation_order
                for field, template in prompt_set.templates.items()
            })
            self.ui_manager.show_status_message(
                f"Loaded prompt set: {name}",
                3000
            )
        except Exception as e:
            QMessageBox.warning(
                self,
                "Load Error",
                f"Error loading prompt set: {str(e)}"
            )
    
    def _refresh_prompt_sets(self):
        """Refresh list of available prompt sets"""
        try:
            sets = self.prompt_service.list_prompt_sets()
            self.load_save.update_items(sets)
            self.ui_manager.show_status_message(
                "Refreshed prompt sets",
                3000
            )
        except Exception as e:
            QMessageBox.warning(
                self,
                "Refresh Error",
                f"Error refreshing prompt sets: {str(e)}"
            )
    
    def _validate_prompt(self, field: FieldName):
        """Validate single prompt"""
        prompt = self.prompt_widgets[field].get_prompt()
        try:
            warnings = self.prompt_service._validate_template_text(prompt)
            if warnings:
                self.prompt_validated.emit(
                    field,
                    True,
                    "Warning: " + "\n".join(warnings)
                )
            else:
                self.prompt_validated.emit(
                    field,
                    True,
                    "Prompt is valid"
                )
        except Exception as e:
            self.prompt_validated.emit(
                field,
                False,
                str(e)
            )
    
    def _validate_all(self):
        """Validate all prompts"""
        all_valid = True
        messages = []
        
        for field, widget in self.prompt_widgets.items():
            prompt = widget.get_prompt()
            if not prompt.strip():
                continue
                
            try:
                warnings = self.prompt_service._validate_template_text(prompt)
                if warnings:
                    messages.append(f"{field.value}:\n" + "\n".join(warnings))
            except Exception as e:
                all_valid = False
                messages.append(f"{field.value}: {str(e)}")
        
        if messages:
            QMessageBox.information(
                self,
                "Validation Results",
                "Results:\n\n" + "\n\n".join(messages)
            )
        else:
            QMessageBox.information(
                self,
                "Validation Success",
                "All prompts are valid"
            )
    
    def _validate_all_prompts(self, prompts: Dict[FieldName, str]) -> bool:
        """Validate all prompts before saving"""
        for field, prompt in prompts.items():
            if not prompt.strip():
                continue
            
            self.prompt_service._validate_template_text(prompt)
        return True
    
    def _handle_clear(self):
        """Handle clear all request"""
        reply = QMessageBox.question(
            self,
            "Clear Confirmation",
            "Are you sure you want to clear all prompts?",
            QMessageBox.StandardButton.Yes | 
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            for widget in self.prompt_widgets.values():
                widget.clear()
            self.ui_manager.show_status_message(
                "Cleared all prompts",
                3000
            )
    
    def get_prompts(self) -> Dict[FieldName, str]:
        """Get all prompt texts"""
        return {
            field: widget.get_prompt()
            for field, widget in self.prompt_widgets.items()
            if widget.get_prompt().strip()
        }
    
    def get_orders(self) -> Dict[FieldName, int]:
        """Get all generation orders"""
        return {
            field: widget.get_order()
            for field, widget in self.prompt_widgets.items()
            if widget.get_order() >= 0
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
    
    def get_current_template(self, field: FieldName) -> Optional[str]:
        """Get current template for field"""
        if field in self.prompt_widgets:
            return self.prompt_widgets[field].get_prompt()
        return None
    
    def is_modified(self) -> bool:
        """Check if any prompts have been modified"""
        return any(
            widget.get_prompt().strip() 
            for widget in self.prompt_widgets.values()
        )
    
    def prompt_save_if_modified(self) -> bool:
        """Prompt to save if there are modifications"""
        if self.is_modified():
            reply = QMessageBox.question(
                self,
                "Save Changes?",
                "Do you want to save the current prompt set?",
                QMessageBox.StandardButton.Yes | 
                QMessageBox.StandardButton.No |
                QMessageBox.StandardButton.Cancel
            )
            
            if reply == QMessageBox.StandardButton.Cancel:
                return False
            elif reply == QMessageBox.StandardButton.Yes:
                name = self.load_save.save_name.text().strip()
                if name:
                    self._handle_save(name)
                else:
                    QMessageBox.warning(
                        self,
                        "Save Error",
                        "Please enter a name for the prompt set"
                    )
                    return False
        
        return True

    def closeEvent(self, event):
        """Handle widget closing"""
        if not self.prompt_save_if_modified():
            event.ignore()
        else:
            event.accept()

    def keyPressEvent(self, event):
        """Handle key press events"""
        # Check for Ctrl+S
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_S:
            name = self.load_save.save_name.text().strip()
            if name:
                self._handle_save(name)
            else:
                self.ui_manager.show_status_message(
                    "Please enter a name for the prompt set",
                    3000
                )
        else:
            super().keyPressEvent(event)