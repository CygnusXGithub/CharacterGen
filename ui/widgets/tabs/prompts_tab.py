from typing import Dict, List, Optional, Set
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox,
    QFrame, QListWidget, QListWidgetItem,
    QSplitter, QScrollArea, QTextEdit
)
from PyQt6.QtCore import Qt, pyqtSignal

from core.state import UIStateManager
from core.models.prompts import PromptSet, PromptTemplate
from ..base import BaseWidget
from .prompt_order import PromptOrderWidget

class PromptEditor(QFrame):
    """Editor for individual prompt templates"""
    
    content_changed = pyqtSignal(str, str)  # field_name, content
    validation_requested = pyqtSignal(str)  # field_name
    
    def __init__(self, field_name: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.field_name = field_name
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup editor UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # Header
        header = QHBoxLayout()
        
        # Field name
        field_label = QLabel(self.field_name.replace('_', ' ').title())
        field_label.setObjectName("field_label")
        header.addWidget(field_label)
        
        header.addStretch()
        
        # Validate button
        validate_btn = QPushButton("Validate Tags")
        validate_btn.setObjectName("validate_button")
        validate_btn.clicked.connect(
            lambda: self.validation_requested.emit(self.field_name)
        )
        header.addWidget(validate_btn)
        
        layout.addLayout(header)
        
        # Editor
        self._editor = QTextEdit()
        self._editor.setObjectName("prompt_editor")
        self._editor.setAcceptRichText(False)
        self._editor.textChanged.connect(self._handle_change)
        layout.addWidget(self._editor)
        
        # Tag help
        help_frame = QFrame()
        help_frame.setObjectName("tag_help")
        help_layout = QVBoxLayout(help_frame)
        
        help_label = QLabel("Available Tags:")
        help_layout.addWidget(help_label)
        
        tags_text = QLabel(
            "{{char}} - Character name\n"
            "{{user}} - User name\n"
            "{{if_input}}...{{/if_input}} - Conditional block\n"
            "{{field}} - Reference other fields"
        )
        tags_text.setObjectName("tags_help")
        help_layout.addWidget(tags_text)
        
        layout.addWidget(help_frame)
        
        self._setup_styling()
        
    def _setup_styling(self):
        """Setup editor styling"""
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #dcdcdc;
                border-radius: 4px;
            }
            
            QLabel#field_label {
                font-size: 14px;
                font-weight: bold;
                color: #2c3e50;
            }
            
            QPushButton#validate_button {
                padding: 4px 12px;
                border: 1px solid #3498db;
                border-radius: 4px;
                color: #3498db;
            }
            
            QPushButton#validate_button:hover {
                background-color: #3498db;
                color: white;
            }
            
            QTextEdit#prompt_editor {
                border: 1px solid #dcdcdc;
                border-radius: 4px;
                padding: 8px;
                font-family: monospace;
            }
            
            QFrame#tag_help {
                background-color: #f8f9fa;
                padding: 8px;
                margin-top: 8px;
            }
            
            QLabel#tags_help {
                color: #666666;
                font-family: monospace;
            }
        """)
        
    def _handle_change(self):
        """Handle editor content change"""
        self.content_changed.emit(self.field_name, self._editor.toPlainText())
        
    def set_content(self, content: str):
        """Set editor content"""
        self._editor.setPlainText(content)
        
    def get_content(self) -> str:
        """Get editor content"""
        return self._editor.toPlainText()

class PromptsTab(BaseWidget):
    """Tab for managing base prompts and generation order"""
    
    prompt_saved = pyqtSignal(str)  # prompt_set_name
    prompt_changed = pyqtSignal(str, str, str)  # prompt_set_name, field_name, content
    order_changed = pyqtSignal(str, list)  # prompt_set_name, new_order
    
    def __init__(self,
                 ui_manager: UIStateManager,
                 parent: Optional[QWidget] = None):
        self._editors: Dict[str, PromptEditor] = {}
        self._current_set: Optional[str] = None
        super().__init__(ui_manager, parent)
        
    def _setup_ui(self):
        """Setup prompts tab UI"""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Toolbar
        toolbar = QFrame()
        toolbar.setObjectName("prompts_toolbar")
        toolbar_layout = QHBoxLayout(toolbar)
        
        # Prompt set selector
        self._prompt_set = QComboBox()
        self._prompt_set.setObjectName("prompt_set_selector")
        self._prompt_set.currentTextChanged.connect(self._load_prompt_set)
        toolbar_layout.addWidget(self._prompt_set)
        
        # Prompt set actions
        new_btn = QPushButton("New")
        new_btn.clicked.connect(self._new_prompt_set)
        toolbar_layout.addWidget(new_btn)
        
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._save_prompt_set)
        toolbar_layout.addWidget(save_btn)
        
        delete_btn = QPushButton("Delete")
        delete_btn.clicked.connect(self._delete_prompt_set)
        toolbar_layout.addWidget(delete_btn)
        
        toolbar_layout.addStretch()
        
        layout.addWidget(toolbar)
        
        # Main content
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left side - Editors
        editors_widget = QWidget()
        editors_layout = QVBoxLayout(editors_widget)
        
        # Scrollable editors area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        editors_container = QWidget()
        self._editors_layout = QVBoxLayout(editors_container)
        self._editors_layout.setContentsMargins(16, 16, 16, 16)
        self._editors_layout.setSpacing(16)
        
        scroll.setWidget(editors_container)
        editors_layout.addWidget(scroll)
        
        splitter.addWidget(editors_widget)
        
        # Right side - Generation order
        self._order_widget = PromptOrderWidget(self.ui_manager)
        self._order_widget.order_changed.connect(self._handle_order_change)
        splitter.addWidget(self._order_widget)
        
        # Set initial sizes (60% editors, 40% order)
        splitter.setSizes([600, 400])
        
        layout.addWidget(splitter)
        
        self._setup_styling()
        
    def _setup_styling(self):
        """Setup tab styling"""
        self.setStyleSheet("""
            QFrame#prompts_toolbar {
                background-color: #f8f9fa;
                border-bottom: 1px solid #e9ecef;
                padding: 8px 16px;
            }
            
            QComboBox#prompt_set_selector {
                min-width: 200px;
                padding: 4px 8px;
                border: 1px solid #dcdcdc;
                border-radius: 4px;
            }
            
            QPushButton {
                padding: 4px 12px;
                border: 1px solid #dcdcdc;
                border-radius: 4px;
            }
            
            QPushButton:hover {
                background-color: #f5f5f5;
            }
        """)
        
    def _setup_editors(self):
        """Setup prompt editors"""
        # Clear current editors
        while self._editors_layout.count():
            item = self._editors_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Create editors for standard fields
        fields = [
            "name",
            "description",
            "personality",
            "scenario",
            "first_mes",
            "mes_example",
            "system_prompt"
        ]
        
        for field in fields:
            editor = PromptEditor(field)
            editor.content_changed.connect(self._handle_prompt_change)
            editor.validation_requested.connect(self._validate_prompt)
            self._editors[field] = editor
            self._editors_layout.addWidget(editor)
            
        # Add stretch at end
        self._editors_layout.addStretch()
        
    def _load_prompt_set(self, name: str):
        """Load selected prompt set"""
        if not name or name == self._current_set:
            return
            
        # TODO: Load prompt set from storage
        self._current_set = name
        
    def _new_prompt_set(self):
        """Create new prompt set"""
        # TODO: Show new prompt set dialog
        pass
        
    def _save_prompt_set(self):
        """Save current prompt set"""
        if not self._current_set:
            return
            
        # TODO: Save prompt set to storage
        self.prompt_saved.emit(self._current_set)
        
    def _delete_prompt_set(self):
        """Delete current prompt set"""
        # TODO: Show confirmation dialog
        pass
        
    def _handle_prompt_change(self, field_name: str, content: str):
        """Handle prompt content change"""
        if self._current_set:
            self.prompt_changed.emit(self._current_set, field_name, content)
            
    def _handle_order_change(self, new_order: List[str]):
        """Handle generation order change"""
        if self._current_set:
            self.order_changed.emit(self._current_set, new_order)
            
    def _validate_prompt(self, field_name: str):
        """Validate prompt template"""
        if field_name not in self._editors:
            return
            
        content = self._editors[field_name].get_content()
        # TODO: Validate prompt template
        
    def load_prompts(self, prompt_sets: List[str], current: Optional[str] = None):
        """Load available prompt sets"""
        self._prompt_set.clear()
        self._prompt_set.addItems(prompt_sets)
        
        if current in prompt_sets:
            self._prompt_set.setCurrentText(current)
            
    def set_prompt_content(self, field_name: str, content: str):
        """Set content for a prompt editor"""
        if field_name in self._editors:
            self._editors[field_name].set_content(content)
            
    def update_generation_order(self, order: List[str]):
        """Update generation order display"""
        self._order_widget.set_order(order)