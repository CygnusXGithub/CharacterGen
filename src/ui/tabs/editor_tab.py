from typing import Optional, List
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QTextEdit, QPushButton, QFrame,
    QScrollArea, QGroupBox, QFormLayout, QFileDialog,
    QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QImage
from pathlib import Path
from PIL import Image
from PIL.ImageQt import ImageQt

from ...core.enums import FieldName, CardField
from ...core.models import CharacterData
from ..widgets.field_widgets import AlternateGreetingsWidget

class ImageFrame(QLabel):
    """Frame for displaying and handling character image"""
    image_changed = pyqtSignal(Image.Image)
    
    def __init__(self):
        super().__init__()
        self.setMinimumSize(300, 400)
        self.setMaximumSize(300, 400)
        self.setFrameShape(QFrame.Shape.Box)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setAcceptDrops(True)
        self._init_placeholder()
        
    def _init_placeholder(self):
        """Set placeholder text/image"""
        self.setText("Drop image here\nor click to upload")
        self.setStyleSheet("""
            QLabel {
                background-color: #2b2b2b;
                border: 2px dashed #666;
                color: #666;
            }
        """)
    
    def mousePressEvent(self, event):
        """Handle click to upload image"""
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Select Image", "", 
            "Images (*.png *.jpg *.jpeg)"
        )
        if file_name:
            self._load_image(file_name)
    
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()
    
    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        for file_path in files:
            if file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
                self._load_image(file_path)
                break
    
    def _load_image(self, file_path: str):
        """Load and display image"""
        try:
            image = Image.open(file_path)
            # Resize image maintaining aspect ratio
            image.thumbnail((300, 400))
            # Convert to QPixmap and display
            qimage = ImageQt(image)
            pixmap = QPixmap.fromImage(qimage)
            self.setPixmap(pixmap)
            # Emit the PIL Image
            self.image_changed.emit(image)
        except Exception as e:
            # TODO: Show error message
            pass

class EditorField(QWidget):
    """Field widget with label and optional token counter"""
    value_changed = pyqtSignal(str)
    
    def __init__(self, label: str, multiline: bool = True, parent=None):
        super().__init__(parent)
        self._init_ui(label, multiline)
    
    def _init_ui(self, label: str, multiline: bool):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Header with label and token counter
        header = QHBoxLayout()
        header.addWidget(QLabel(label))
        self.token_label = QLabel("0 characters, 0 tokens")
        self.token_label.setStyleSheet("color: #666;")
        header.addStretch()
        header.addWidget(self.token_label)
        layout.addLayout(header)
        
        # Text editor
        if multiline:
            self.editor = QTextEdit()
            self.editor.setMinimumHeight(100)
            self.editor.textChanged.connect(
                lambda: self.value_changed.emit(self.editor.toPlainText())
            )
        else:
            self.editor = QLineEdit()
            self.editor.textChanged.connect(self.value_changed.emit)
        
        layout.addWidget(self.editor)
        self.setLayout(layout)
    
    def set_text(self, text: str):
        """Set editor text"""
        if isinstance(self.editor, QTextEdit):
            self.editor.setPlainText(text)
        else:
            self.editor.setText(text)
    
    def get_text(self) -> str:
        """Get editor text"""
        if isinstance(self.editor, QTextEdit):
            return self.editor.toPlainText()
        return self.editor.text()
    
    def update_tokens(self, chars: int, tokens: int):
        """Update token counter"""
        self.token_label.setText(f"{chars} characters, {tokens} tokens")

class EditorTab(QWidget):
    """Character editor tab"""
    character_updated = pyqtSignal(CharacterData, str)  # When character data is modified (character, field_name)
    
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.current_character: Optional[CharacterData] = None
        self.fields: dict[str, EditorField] = {}
        self.is_updating = False
        self._init_ui()
    
    def _init_ui(self):
        layout = QHBoxLayout()
        
        # Left side - Image
        left_panel = QVBoxLayout()
        self.image_frame = ImageFrame()
        self.image_frame.image_changed.connect(self._handle_image_changed)
        left_panel.addWidget(self.image_frame)
        left_panel.addStretch()
        layout.addLayout(left_panel)
        
        # Right side - Fields
        right_panel = QVBoxLayout()
        
        # Create scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Container for fields
        container = QWidget()
        form_layout = QVBoxLayout(container)
        
        # Main Info group
        main_group = QGroupBox("Main Info")
        main_layout = QFormLayout()
        
        # Top row (Name, Version, Creator)
        top_row = QHBoxLayout()
        
        self.fields['name'] = EditorField("Name", multiline=False)
        top_row.addWidget(self.fields['name'])
        
        self.fields['version'] = EditorField("Version", multiline=False)
        self.fields['version'].set_text("1.0.0")
        top_row.addWidget(self.fields['version'])
        
        self.fields['creator'] = EditorField("Creator", multiline=False)
        self.fields['creator'].set_text(self.config.user.creator_name)
        top_row.addWidget(self.fields['creator'])
        
        main_layout.addRow("", top_row)
        
        # Generated Fields
        for field in FieldName:
            if field != FieldName.NAME:  # Skip name as it's already handled
                self.fields[field.value] = EditorField(field.value.replace('_', ' ').title())
                main_layout.addRow("", self.fields[field.value])
        
        main_group.setLayout(main_layout)
        form_layout.addWidget(main_group)
        
        # First Message with alternate greetings
        msg_group = QGroupBox("Messages")
        msg_layout = QVBoxLayout()
        
        if 'first_mes' in self.fields:
            msg_layout.addWidget(self.fields['first_mes'])
        
        self.alt_greetings = AlternateGreetingsWidget()
        msg_layout.addWidget(self.alt_greetings)
        
        msg_group.setLayout(msg_layout)
        form_layout.addWidget(msg_group)
        
        # Additional fields (metadata)
        additional_group = QGroupBox("Additional Settings")
        additional_layout = QVBoxLayout()
        
        # Add metadata-only fields
        metadata_fields = [
            field for field in CardField 
            if field.value not in [f.value for f in FieldName]
        ]
        
        for field in metadata_fields:
            self.fields[field.value] = EditorField(
                field.value.replace('_', ' ').title(),
                multiline=True  # Most metadata fields benefit from multiline
            )
            additional_layout.addWidget(self.fields[field.value])
        
        # Tags field
        self.fields['tags'] = EditorField("Tags", multiline=False)
        additional_layout.addWidget(self.fields['tags'])
        
        additional_group.setLayout(additional_layout)
        form_layout.addWidget(additional_group)
        
        # Set container as scroll area widget
        scroll.setWidget(container)
        right_panel.addWidget(scroll)
        
        layout.addLayout(right_panel, stretch=1)
        self.setLayout(layout)
        
        # Signal connections at the bottom:
        for field_name, widget in self.fields.items():
            if isinstance(widget.editor, QTextEdit):
                widget.editor.textChanged.connect(
                    lambda name=field_name: self._handle_editor_changed(name)
                )
            else:
                # Use textChanged for QLineEdit too
                widget.editor.textChanged.connect(
                    lambda text, name=field_name: self._handle_editor_changed(name)
                )

    def _handle_editor_changed(self, field_name: str):
        """Handle changes in editor fields"""
        if self.is_updating or not self.current_character:
            return
                
        self.is_updating = True
        try:
            value = self.fields[field_name].get_text()
            
            # Handle different field types
            if field_name in ['version', 'creator']:
                setattr(self.current_character, field_name, value)
                print(f"EditorTab: Emitting update for field {field_name}")
                self.character_updated.emit(self.current_character, field_name)
            elif field_name == 'name':
                setattr(self.current_character, field_name, value)
                self.current_character.fields[FieldName(field_name)] = value
                print(f"EditorTab: Emitting update for field {field_name}")
                self.character_updated.emit(self.current_character, field_name)
            elif field_name == 'tags':
                self.current_character.tags = [
                    tag.strip() for tag in value.split(',') if tag.strip()
                ]
                print(f"EditorTab: Emitting update for field {field_name}")
                self.character_updated.emit(self.current_character, field_name)
            else:
                # Try as FieldName first, then CardField
                try:
                    self.current_character.fields[FieldName(field_name)] = value
                    print(f"EditorTab: Emitting update for field {field_name}")
                    self.character_updated.emit(self.current_character, field_name)
                except ValueError:
                    try:
                        self.current_character.fields[CardField(field_name)] = value
                        self.character_updated.emit(self.current_character, field_name)
                    except ValueError:
                        pass
        finally:
            self.is_updating = False

    
    def _handle_image_changed(self, image: Image.Image):
        """Handle image upload/change"""
        if self.current_character:
            self.current_character.image_data = image
            self.character_updated.emit(self.current_character)
    
    def set_initial_character(self, character: CharacterData):
        """Set initial character data without emitting updates"""
        print(f"EditorTab: Setting initial character {character.name}")
        self.is_updating = True
        try:
            self.current_character = character
            
            # Update all fields
            for field in FieldName:
                if field.value in self.fields:
                    self.fields[field.value].set_text(character.fields.get(field, ''))
            
            # Update metadata fields
            for field in CardField:
                if field.value not in [f.value for f in FieldName]:
                    if field.value in self.fields:
                        self.fields[field.value].set_text(character.fields.get(field, ''))
            
            # Update alternate greetings
            if hasattr(self, 'alt_greetings'):
                self.alt_greetings.set_greetings(character.alternate_greetings)
                    
            # Update image
            if character.image_data:
                qimage = ImageQt(character.image_data)
                self.image_frame.setPixmap(QPixmap.fromImage(qimage))
            else:
                self.image_frame._init_placeholder()
        finally:
            self.is_updating = False

    def handle_external_update(self, character: CharacterData, updated_field: str):
        """Handle updates from other tabs"""
        if self.is_updating:
            return
            
        self.is_updating = True
        try:
            self.current_character = character
            
            # If specific field updated and not a full update
            if updated_field and updated_field != "all":
                if updated_field in self.fields:
                    self.fields[updated_field].set_text(
                        character.fields.get(FieldName(updated_field), '')
                    )
            else:
                # Full update
                for field in FieldName:
                    if field.value in self.fields:
                        self.fields[field.value].set_text(character.fields.get(field, ''))
        finally:
            self.is_updating = False