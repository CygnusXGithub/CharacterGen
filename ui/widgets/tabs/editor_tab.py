from typing import Optional, Dict
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QScrollArea, QFrame, QSplitter,
    QPushButton, QLabel
)
from PyQt6.QtCore import Qt, pyqtSignal

from core.state import UIStateManager
from ..base import BaseWidget
from ..layout.field_container import FieldContainer
from ..image import ImageWidget
from ..fields.editor import FieldEditor
from core.models.character import CharacterData

class CharacterInfoPanel(BaseWidget):
    """Panel showing character info and stats"""
    
    refresh_requested = pyqtSignal()
    
    def __init__(self, ui_manager: UIStateManager, parent: Optional[QWidget] = None):
        super().__init__(ui_manager, parent)
        self._setup_styling()

    def _setup_ui(self):
        """Setup info panel UI"""
        self._layout.setContentsMargins(16, 16, 16, 16)
        self._layout.setSpacing(8)
        
        # Character stats
        stats_frame = QFrame(self)
        stats_frame.setObjectName("stats_frame")
        stats_layout = QVBoxLayout(stats_frame)
        
        # Add stat labels
        self._word_count = QLabel("Words: 0")
        stats_layout.addWidget(self._word_count)
        
        self._token_count = QLabel("Tokens: 0")
        stats_layout.addWidget(self._token_count)
        
        self._last_modified = QLabel("Last Modified: Never")
        stats_layout.addWidget(self._last_modified)
        
        # Add refresh button
        refresh_btn = QPushButton("Refresh Stats", self)
        refresh_btn.clicked.connect(self.refresh_requested.emit)
        stats_layout.addWidget(refresh_btn)
        
        self._layout.addWidget(stats_frame)
        self._layout.addStretch()

    def _setup_styling(self):
        """Setup panel styling"""
        self.setStyleSheet("""
            QFrame#stats_frame {
                background-color: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 4px;
                padding: 8px;
            }
            
            QLabel {
                color: #495057;
            }
        """)

    def update_stats(self, character: Optional[CharacterData] = None):
        """Update displayed stats"""
        if character:
            # Calculate stats
            total_words = sum(len(str(getattr(character, field, "")).split()) 
                            for field in ['description', 'personality', 'first_mes'])
            # Approximate token count (rough estimation)
            total_tokens = total_words * 1.3
            
            self._word_count.setText(f"Words: {total_words}")
            self._token_count.setText(f"Tokens: {int(total_tokens)}")
            self._last_modified.setText(
                f"Last Modified: {character.modified_at.strftime('%Y-%m-%d %H:%M')}"
            )
        else:
            self._word_count.setText("Words: 0")
            self._token_count.setText("Tokens: 0")
            self._last_modified.setText("Last Modified: Never")

class EditorTab(BaseWidget):
    """Main character editor interface"""
    
    character_changed = pyqtSignal(str)  # field_name
    generation_requested = pyqtSignal(str)  # field_name
    save_requested = pyqtSignal()
    
    def __init__(self, ui_manager: UIStateManager, parent: Optional[QWidget] = None):
        self._editors: Dict[str, FieldEditor] = {}
        super().__init__(ui_manager, parent)

    def _setup_ui(self):
        """Setup editor tab UI"""
        # Main layout
        self._layout.setContentsMargins(0, 0, 0, 0)
        
        # Create main splitter
        self._main_splitter = QSplitter(Qt.Orientation.Horizontal, self)
        
        # Left side (image + info)
        left_widget = QWidget(self._main_splitter)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(16, 16, 8, 16)
        
        # Image widget
        self._image_widget = ImageWidget(self.ui_manager, left_widget)
        left_layout.addWidget(self._image_widget)
        
        # Info panel
        self._info_panel = CharacterInfoPanel(self.ui_manager, left_widget)
        left_layout.addWidget(self._info_panel)
        
        # Right side (fields)
        right_widget = QWidget(self._main_splitter)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(8, 16, 16, 16)
        
        # Field container
        self._field_container = FieldContainer(self.ui_manager, right_widget)
        right_layout.addWidget(self._field_container)
        
        # Add both sides to splitter
        self._main_splitter.addWidget(left_widget)
        self._main_splitter.addWidget(right_widget)
        
        # Set initial sizes (30% left, 70% right)
        self._main_splitter.setSizes([300, 700])
        
        # Add splitter to main layout
        self._layout.addWidget(self._main_splitter)
        
        # Setup fields
        self._setup_fields()

    def _setup_fields(self):
        """Setup character fields"""
        # Basic fields
        self._add_field("name", "Name", required=True, multiline=False)
        self._add_field("description", "Description", required=True)
        
        # Personality and interactions
        self._add_field("personality", "Personality", required=True)
        self._add_field("scenario", "Scenario")
        
        # Messages
        self._add_field(
            "first_mes", 
            "First Message",
            help_text="The character's first message when starting a conversation",
            required=True
        )
        self._add_field(
            "mes_example",
            "Message Examples",
            help_text="Example messages showing the character's speech patterns"
        )
        
        # Additional fields
        self._add_field(
            "post_history_instructions",
            "Post-History Instructions",
            help_text="Instructions applied after loading chat history"
        )
        self._add_field(
            "system_prompt",
            "System Prompt",
            help_text="System-level instructions for the character"
        )
        self._add_field(
            "creator_notes",
            "Creator Notes",
            help_text="Notes about the character's creation or usage"
        )

    def _add_field(self, 
                   field_name: str,
                   label: str,
                   help_text: str = "",
                   multiline: bool = True,
                   required: bool = False):
        """Add a field to the container"""
        field = self._field_container.add_field(
            field_name=field_name,
            label=label,
            help_text=help_text,
            multiline=multiline,
            required=required
        )
        
        # Store reference
        self._editors[field_name] = field
        
        # Connect signals
        field.field_changed.connect(self.character_changed.emit)
        field.generate_requested.connect(self.generation_requested.emit)
        field.save_requested.connect(self.save_requested.emit)

    def _setup_styling(self):
        """Setup editor styling"""
        self.setStyleSheet("""
            EditorTab {
                background-color: #ffffff;
            }
            
            QSplitter::handle {
                background-color: #e9ecef;
                width: 2px;
            }
            
            QSplitter::handle:hover {
                background-color: #3498db;
            }
        """)

    def update_character(self, character: Optional[CharacterData]):
        """Update displayed character data"""
        if character:
            # Update fields
            for field_name, editor in self._editors.items():
                if hasattr(character, field_name):
                    editor.set_content(str(getattr(character, field_name, "")))
            
            # Update info panel
            self._info_panel.update_stats(character)
            
            # Update image if exists
            if character.avatar and character.avatar != "none":
                # TODO: Load avatar image
                pass
        else:
            # Clear all fields
            for editor in self._editors.values():
                editor.clear()
            self._info_panel.update_stats(None)
            self._image_widget.clear_image()

    def get_modified_fields(self) -> Dict[str, str]:
        """Get dictionary of modified fields and their values"""
        modified = {}
        for field_name, editor in self._editors.items():
            if editor.has_unsaved_changes():
                modified[field_name] = editor.get_content()
        return modified

    def validate_all(self) -> bool:
        """Validate all fields"""
        return all(editor.is_valid() for editor in self._editors.values())