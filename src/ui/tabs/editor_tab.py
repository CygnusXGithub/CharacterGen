from typing import Optional, List, Dict, Any
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QTextEdit, QPushButton, QFrame,
    QScrollArea, QGroupBox, QFormLayout, QFileDialog,
    QSizePolicy, QMessageBox, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QImage, QDragEnterEvent, QDropEvent
from PIL import Image
from PIL.ImageQt import ImageQt

from ...core.enums import (
    FieldName, CardField, CardFormat, UIMode,
    StatusLevel, OperationType, ImageFormat
)
from ...core.models import CharacterData
from ...core.exceptions import CharacterLoadError, CharacterSaveError
from ...core.managers import (
    CharacterStateManager, UIStateManager,
    SettingsManager
)
from ..widgets.field_widgets import (
    EditableField, AlternateGreetingsWidget,
    ImageFrame
)

class EditorTab(QWidget):
    """Tab for editing character data"""
    
    # Signals
    character_loaded = pyqtSignal(CharacterData)         # When character is loaded
    character_updated = pyqtSignal(CharacterData, str)   # When character is modified
    status_update = pyqtSignal(str, StatusLevel)         # Status updates
    operation_requested = pyqtSignal(OperationType, dict)  # Operation requests
    
    def __init__(self,
                 character_manager: CharacterStateManager,
                 ui_manager: UIStateManager,
                 settings_manager: SettingsManager,
                 parent=None):
        super().__init__(parent)
        self.character_manager = character_manager
        self.ui_manager = ui_manager
        self.settings_manager = settings_manager
        
        # State tracking
        self.current_character: Optional[CharacterData] = None
        self.is_updating = False
        self.fields: Dict[str, EditableField] = {}
        self.current_image: Optional[Image.Image] = None
        
        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        """Initialize the user interface"""
        layout = QHBoxLayout()
        layout.setSpacing(20)
        
        # Left panel - Image and file operations
        left_panel = QVBoxLayout()
        
        # Image section
        self.image_frame = ImageFrame(
            self.ui_manager,
            self.settings_manager
        )
        self.image_frame.setMinimumSize(300, 400)
        self.image_frame.setMaximumSize(300, 400)
        left_panel.addWidget(self.image_frame)
        
        # File operation buttons
        self.load_btn = QPushButton("Load Character")
        self.load_btn.setFixedWidth(300)
        self.load_btn.clicked.connect(self._handle_load_character)
        left_panel.addWidget(self.load_btn)
        
        # Save buttons container
        save_buttons = QHBoxLayout()
        
        self.save_png_btn = QPushButton("Save as PNG")
        self.save_png_btn.setFixedWidth(145)
        self.save_png_btn.clicked.connect(
            lambda: self._handle_save_character("png")
        )
        save_buttons.addWidget(self.save_png_btn)
        
        self.save_json_btn = QPushButton("Save as JSON")
        self.save_json_btn.setFixedWidth(145)
        self.save_json_btn.clicked.connect(
            lambda: self._handle_save_character("json")
        )
        save_buttons.addWidget(self.save_json_btn)
        
        left_panel.addLayout(save_buttons)
        left_panel.addStretch()
        
        layout.addLayout(left_panel)

        # Right panel with scrollable content
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        form_container = QWidget()
        form_layout = QVBoxLayout(form_container)
        form_layout.setSpacing(20)
        
        # Main Information group
        main_group = QGroupBox("Main Information")
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Set size policy to not stretch
        main_group.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Maximum
        )
        
        # Top row for single-line fields
        top_row = QHBoxLayout()
        
        # Name field
        self.fields['name'] = EditableField(
            "Name", multiline=False,
            ui_manager=self.ui_manager,
            settings_manager=self.settings_manager,
            min_height=25,
            max_height=25
        )
        top_row.addWidget(self.fields['name'])
        
        # Version field
        self.fields['version'] = EditableField(
            "Version", multiline=False,
            ui_manager=self.ui_manager,
            settings_manager=self.settings_manager,
            min_height=25,
            max_height=25
        )
        top_row.addWidget(self.fields['version'])
        
        # Creator field
        self.fields['creator'] = EditableField(
            "Creator", multiline=False,
            ui_manager=self.ui_manager,
            settings_manager=self.settings_manager,
            min_height=25,
            max_height=25
        )
        top_row.addWidget(self.fields['creator'])
        
        main_layout.addLayout(top_row)
        
        # Multi-line fields
        multiline_fields = ['description', 'scenario', 'personality']
        for field in multiline_fields:
            self.fields[field] = EditableField(
                field.title(),
                multiline=True,
                ui_manager=self.ui_manager,
                settings_manager=self.settings_manager,
                min_height=100,
                max_height=300
            )
            main_layout.addWidget(self.fields[field])
        
        main_group.setLayout(main_layout)
        form_layout.addWidget(main_group)
        
        # Messages group
        msg_group = QGroupBox("Messages")
        msg_layout = QVBoxLayout()
        msg_layout.setSpacing(10)
        msg_layout.setContentsMargins(10, 10, 10, 10)
        
        # Set size policy to not stretch
        msg_group.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Maximum
        )
        # First message
        self.fields['first_mes'] = EditableField(
            "First Message",
            multiline=True,
            ui_manager=self.ui_manager,
            settings_manager=self.settings_manager,
            min_height=100,
            max_height=300
        )
        msg_layout.addWidget(self.fields['first_mes'])
        
        # Alternate greetings
        self.alt_greetings = AlternateGreetingsWidget(
            self.ui_manager,
            self.settings_manager,
            min_height=100,
            max_height=300
        )
        msg_layout.addWidget(self.alt_greetings)
        
        # Message examples
        self.fields['mes_example'] = EditableField(
            "Message Examples",
            multiline=True,
            ui_manager=self.ui_manager,
            settings_manager=self.settings_manager,
            min_height=100,
            max_height=300
        )
        msg_layout.addWidget(self.fields['mes_example'])
        
        msg_group.setLayout(msg_layout)
        form_layout.addWidget(msg_group)
        
        right_scroll.setWidget(form_container)
        layout.addWidget(right_scroll, stretch=1)
        
        self.setLayout(layout)
        form_layout.addStretch()
        
    def _handle_character_loaded(self, character: CharacterData):
        """Handle loaded character"""
        print(f"EditorTab: Loading character {character.name}")
        self.is_updating = True
        try:
            # Handle fields
            for field in FieldName:
                if field.value in self.fields:
                    self.fields[field.value].set_value(
                        character.fields.get(field, '')
                    )
            
            # Handle metadata
            if 'creator' in self.fields:
                self.fields['creator'].set_value(character.creator)
            if 'version' in self.fields:
                self.fields['version'].set_value(character.version)
            if 'tags' in self.fields:
                self.fields['tags'].set_value(','.join(character.tags))
            
            # Handle image
            if character.image_data:
                self.image_frame.set_image(character.image_data)
            else:
                self.image_frame._init_placeholder()
            
            # Handle alternate greetings
            if character.alternate_greetings:
                self.alt_greetings.set_greetings(character.alternate_greetings)
            else:
                self.alt_greetings.set_greetings([])
                    
        finally:
            self.is_updating = False

    def _handle_mode_change(self, field: FieldName, mode: UIMode):
        """Handle field mode changes"""
        if field.value in self.fields:
            widget = self.fields[field.value]
            
            # Update widget state based on mode
            if mode == UIMode.EXPANDED:
                # Save current state for restoration
                self.ui_manager.save_field_state(
                    field,
                    widget.verticalScrollBar().value() if hasattr(widget, 'verticalScrollBar') else 0,
                    widget.height()
                )
                widget.setMaximumHeight(16777215)  # Qt's QWIDGETSIZE_MAX
            else:
                # Restore previous state
                state = self.ui_manager.get_field_state(field)
                if state.original_height:
                    widget.setMaximumHeight(state.original_height)
                else:
                    widget.setMaximumHeight(200)  # Default compact height
                
                if hasattr(widget, 'verticalScrollBar'):
                    widget.verticalScrollBar().setValue(state.scroll_position)
            
            # Update edit state
            if hasattr(widget, 'editor'):
                widget.editor.setReadOnly(mode == UIMode.READONLY)
                
    def _handle_character_updated(self, character: CharacterData, field: str):
        """Handle character updates"""
        if self.is_updating:
            return
            
        self.is_updating = True
        try:
            if field == "image":
                if character.image_data:
                    self.image_frame.set_image(character.image_data)
            elif field == "all":
                self._handle_character_loaded(character)
            else:
                if field in self.fields:
                    if field in ['creator', 'version']:
                        self.fields[field].set_value(
                            getattr(character, field, '')
                        )
                    elif field == 'tags':
                        self.fields['tags'].set_value(','.join(character.tags))
                    else:
                        try:
                            field_enum = FieldName(field)
                            self.fields[field].set_value(
                                character.fields.get(field_enum, '')
                            )
                        except ValueError:
                            pass
        finally:
            self.is_updating = False

    def _handle_dropped_file(self, file_path: str):
        """Handle dropped files"""
        if file_path.lower().endswith(('.json', '.png')):
            try:
                character = self.character_manager.load_character(file_path)
                self._handle_character_loaded(character)
                self.character_loaded.emit(character)
                self.ui_manager.show_status_message(
                    f"Loaded character from dropped file: {file_path}",
                    StatusLevel.SUCCESS
                )
            except Exception as e:
                self.ui_manager.show_status_message(
                    f"Error loading dropped file: {str(e)}",
                    StatusLevel.ERROR
                )
                QMessageBox.critical(
                    self,
                    "Load Error",
                    f"Error loading dropped file: {str(e)}"
                )

    def _connect_signals(self):
        """Connect all signals"""
        # Connect character manager signals
        self.character_manager.character_loaded.connect(self._handle_character_loaded)
        self.character_manager.character_updated.connect(self._handle_character_updated)
        
        # Connect UI manager signals
        self.ui_manager.field_mode_changed.connect(self._handle_mode_change)
        
        # Connect image frame signals
        self.image_frame.image_changed.connect(self._handle_image_changed)
        self.image_frame.file_dropped.connect(self._handle_dropped_file)
        
        # Connect field signals
        for field_name, field_widget in self.fields.items():
            field_widget.value_changed.connect(
                lambda value, name=field_name: self._handle_field_changed(name, value)
            )

    def _handle_load_character(self):
        """Handle character load request"""
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Load Character",
            "",
            "Character Files (*.json *.png)"
        )
        
        if not file_name:
            return
            
        try:
            character = self.character_manager.load_character(file_name)
            self.set_initial_character(character)
            self.character_loaded.emit(character)
            self.status_update.emit(
                f"Loaded character: {character.name}",
                StatusLevel.SUCCESS
            )
            
        except Exception as e:
            self.status_update.emit(
                f"Error loading character: {str(e)}",
                StatusLevel.ERROR
            )
            QMessageBox.critical(
                self,
                "Load Error",
                f"Error loading character: {str(e)}"
            )

    def _handle_save_character(self, format_type: str):
        """Handle character save request"""
        if not self.current_character:
            self.status_update.emit(
                "No character to save",
                StatusLevel.WARNING
            )
            return
        
        try:
            # Update character data from fields
            self._update_character_data()
            
            # Get save location
            default_name = f"{self.current_character.name}.{format_type}"
            file_name, _ = QFileDialog.getSaveFileName(
                self,
                "Save Character",
                default_name,
                f"Character Files (*.{format_type})"
            )
            
            if not file_name:
                return
            
            # Ensure correct extension
            if not file_name.lower().endswith(f".{format_type}"):
                file_name += f".{format_type}"
            
            # Save character
            save_format = CardFormat.PNG if format_type == "png" else CardFormat.JSON
            saved_path = self.character_manager.save_character(
                file_name,
                save_format
            )
            
            self.status_update.emit(
                f"Saved character to: {saved_path}",
                StatusLevel.SUCCESS
            )
            
        except Exception as e:
            self.status_update.emit(
                f"Error saving character: {str(e)}",
                StatusLevel.ERROR
            )
            QMessageBox.critical(
                self,
                "Save Error",
                f"Error saving character: {str(e)}"
            )

    def _handle_image_changed(self, image: Image.Image):
        """Handle image changes"""
        self.current_image = image
        if self.current_character:
            self.current_character.image_data = image
            self.character_updated.emit(self.current_character, "image")
            self.status_update.emit(
                "Character image updated",
                StatusLevel.SUCCESS
            )

    def _handle_field_changed(self, field_name: str, value: str):
        """Handle field value changes"""
        if not self.is_updating and self.current_character:
            self.is_updating = True
            try:
                if field_name in ['creator', 'version']:
                    setattr(self.current_character, field_name, value)
                elif field_name == 'tags':
                    self.current_character.tags = [
                        tag.strip() for tag in value.split(',')
                        if tag.strip()
                    ]
                else:
                    try:
                        field = FieldName(field_name)
                        self.current_character.fields[field] = value
                    except ValueError:
                        try:
                            field = CardField(field_name)
                            self.current_character.fields[field] = value
                        except ValueError:
                            pass
                
                # Emit update signal for synchronization
                self.character_updated.emit(self.current_character, field_name)
                    
            finally:
                self.is_updating = False

    def _update_character_data(self):
        """Update character data from current fields"""
        if not self.current_character:
            return
        
        # Update fields
        for field in FieldName:
            if field.value in self.fields:
                self.current_character.fields[field] = self.fields[field.value].get_value()
        
        # Update metadata fields
        for field in CardField:
            if field.value not in [f.value for f in FieldName]:
                if field.value in self.fields:
                    self.current_character.fields[field] = self.fields[field.value].get_value()
        
        # Update character properties
        if 'creator' in self.fields:
            self.current_character.creator = self.fields['creator'].get_value()
        if 'version' in self.fields:
            self.current_character.version = self.fields['version'].get_value()
        if 'tags' in self.fields:
            self.current_character.tags = [
                tag.strip() for tag in self.fields['tags'].get_value().split(',')
                if tag.strip()
            ]

    def set_initial_character(self, character: CharacterData):
        """Set initial character data"""
        print(f"EditorTab: Setting initial character {character.name}")
        self.is_updating = True
        try:
            # Handle fields
            for field in FieldName:
                if field.value in self.fields:
                    self.fields[field.value].set_value(
                        character.fields.get(field, '')
                    )
            
            # Handle metadata
            if 'creator' in self.fields:
                self.fields['creator'].set_value(character.creator)
            if 'version' in self.fields:
                self.fields['version'].set_value(character.version)
            if 'tags' in self.fields:
                self.fields['tags'].set_value(','.join(character.tags))
            
            # Handle image
            if character.image_data:
                self.image_frame.set_image(character.image_data)
            else:
                self.image_frame._init_placeholder()
            
            # Handle alternate greetings
            if hasattr(self, 'alt_greetings'):  # Verify the attribute name
                print(f"Setting {len(character.alternate_greetings)} greetings in Editor Tab")  # Debug
                if character.alternate_greetings:
                    self.alt_greetings.set_greetings(character.alternate_greetings)
                else:
                    self.alt_greetings.set_greetings([])
                    
        finally:
            self.is_updating = False

    def handle_external_update(self, character: CharacterData, updated_field: str):
        """Handle updates from other tabs"""
        if self.is_updating:
            return
            
        self.is_updating = True
        try:
            self.current_character = character
            
            if updated_field == "image":
                if character.image_data:
                    qimage = ImageQt(character.image_data)
                    self.image_frame.setPixmap(QPixmap.fromImage(qimage))
                    self.current_image = character.image_data
            elif updated_field == "all":
                self.set_initial_character(character)
            else:
                if updated_field in self.fields:
                    if updated_field in ['creator', 'version']:
                        self.fields[updated_field].set_value(
                            getattr(character, updated_field, '')
                        )
                    elif updated_field == 'tags':
                        self.fields['tags'].set_value(','.join(character.tags))
                    else:
                        try:
                            field = FieldName(updated_field)
                            self.fields[updated_field].set_value(
                                character.fields.get(field, '')
                            )
                        except ValueError:
                            try:
                                field = CardField(updated_field)
                                self.fields[updated_field].set_value(
                                    character.fields.get(field, '')
                                )
                            except ValueError:
                                pass
                
        finally:
            self.is_updating = False

    def closeEvent(self, event):
        """Handle tab closing"""
        if self.character_manager.is_modified:
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "Do you want to save your changes before closing?",
                QMessageBox.StandardButton.Yes | 
                QMessageBox.StandardButton.No |
                QMessageBox.StandardButton.Cancel
            )
            
            if reply == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
            elif reply == QMessageBox.StandardButton.Yes:
                self._handle_save_character(
                    self.settings_manager.get("default_save_format", "json")
                )
        
        event.accept()