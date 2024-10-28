from typing import Dict, Optional, List, Set
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QMessageBox, QFileDialog, QPushButton, QLabel,
    QTextEdit, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal

from ...core.enums import (
    FieldName, GenerationMode, CardFormat, SaveMode,
    StatusLevel, UIMode, OperationType, EventType
)
from ...core.models import (
    CharacterData, GenerationContext, GenerationResult,
    GenerationCallbacks
)
from ...core.exceptions import (
    GenerationError, DependencyError
)
from ...core.managers import (
    UIStateManager, GenerationManager,
    CharacterStateManager, SettingsManager
)
from ..widgets.field_widgets import (
    CompactFieldWidget, MessageExampleWidget,
    FirstMessageWidget, AlternateGreetingsWidget
)

class GenerationTab(QWidget):
    """Tab for character generation"""
    
    # Signals
    character_updated = pyqtSignal(CharacterData, str)  # When character data is modified
    generation_requested = pyqtSignal(FieldName, str)   # When generation is requested
    status_update = pyqtSignal(str, StatusLevel)        # Status message updates
    
    def __init__(self, 
                 generation_manager: GenerationManager,
                 character_manager: CharacterStateManager,
                 ui_manager: UIStateManager,
                 settings_manager: SettingsManager,
                 parent=None):
        super().__init__(parent)
        self.generation_manager = generation_manager
        self.character_manager = character_manager
        self.ui_manager = ui_manager
        self.settings_manager = settings_manager
        
        # State tracking
        self.is_updating = False
        self.current_generation: Optional[FieldName] = None
        self.field_states: Dict[FieldName, Dict] = {}
        
        # Initialize widgets
        self.input_widgets: Dict[FieldName, CompactFieldWidget] = {}
        self.output_texts: Dict[FieldName, QTextEdit] = {}
        
        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Create main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left side - Input fields
        input_widget = QWidget()
        input_layout = QVBoxLayout(input_widget)
        input_layout.setSpacing(10)
        
        # Create scroll area for inputs
        input_scroll = QScrollArea()
        input_scroll.setWidgetResizable(True)
        input_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Create container for inputs
        input_container = QWidget()
        input_container_layout = QVBoxLayout(input_container)
        input_container_layout.setSpacing(10)
        
        # Create field widgets
        for field in FieldName:
            if field == FieldName.MES_EXAMPLE:
                self.input_widgets[field] = MessageExampleWidget(
                    field=field,
                    ui_manager=self.ui_manager,
                    settings_manager=self.settings_manager,
                    min_height=100,
                    max_height=300,
                    parent=self
                )
            elif field == FieldName.FIRST_MES:
                self.input_widgets[field] = FirstMessageWidget(
                    field=field,
                    ui_manager=self.ui_manager,
                    settings_manager=self.settings_manager,
                    min_height=100,
                    max_height=300,
                    parent=self
                )
            else:
                self.input_widgets[field] = CompactFieldWidget(
                    field=field,
                    ui_manager=self.ui_manager,
                    settings_manager=self.settings_manager,
                    min_height=100,
                    max_height=300,
                    parent=self
                )
            
            input_container_layout.addWidget(self.input_widgets[field])
        
        # Add generate button
        self.generate_btn = QPushButton("Generate All")
        self.generate_btn.clicked.connect(self._handle_generate_all)
        input_container_layout.addWidget(self.generate_btn)
        
        # Add stretch at the end
        input_container_layout.addStretch()
        
        # Set scroll widget
        input_scroll.setWidget(input_container)
        input_layout.addWidget(input_scroll)
        
        splitter.addWidget(input_widget)
        
        # Right side - Output fields
        output_widget = QWidget()
        output_layout = QVBoxLayout(output_widget)
        output_layout.setSpacing(10)
        
        # Create scroll area for outputs
        output_scroll = QScrollArea()
        output_scroll.setWidgetResizable(True)
        
        # Create container for outputs
        output_container = QWidget()
        output_container_layout = QVBoxLayout(output_container)
        output_container_layout.setSpacing(10)
        
        # Create output fields
        for field in FieldName:
            # Create field container
            field_container = QWidget()
            field_layout = QVBoxLayout(field_container)
            field_layout.setContentsMargins(0, 0, 0, 0)
            
            # Add label
            label = QLabel(f"{field.value.title()} Output:")
            field_layout.addWidget(label)
            
            # Add text edit
            text_edit = QTextEdit()
            text_edit.setAcceptRichText(False)
            text_edit.setMinimumHeight(100)
            text_edit.setMaximumHeight(300)  # Set maximum height
            text_edit.document().contentsChanged.connect(
                lambda text_edit=text_edit: self._adjust_output_height(text_edit)
            )
            text_edit.textChanged.connect(
                lambda field=field: self._handle_output_changed(field)
            )
            
            # Apply settings
            font_size = self.settings_manager.get("ui.font_size", 10)
            font = text_edit.font()
            font.setPointSize(font_size)
            text_edit.setFont(font)
            
            self.output_texts[field] = text_edit
            field_layout.addWidget(text_edit)
            
            output_container_layout.addWidget(field_container)
            
            # Add alternate greetings widget after first_mes
            if field == FieldName.FIRST_MES:
                self.alt_greetings_widget = AlternateGreetingsWidget(
                    self.ui_manager,
                    self.settings_manager
                )
                output_container_layout.addWidget(self.alt_greetings_widget)
        
        # Add stretch at the end
        output_container_layout.addStretch()
        
        # Set scroll widget
        output_scroll.setWidget(output_container)
        output_layout.addWidget(output_scroll)
        
        splitter.addWidget(output_widget)
        
        # Set initial splitter sizes
        splitter.setSizes([500, 500])
        
        layout.addWidget(splitter)
        
        self.setLayout(layout)

    def _adjust_output_height(self, text_edit: QTextEdit):
        """Adjust output field height based on content"""
        if not text_edit:
            return
            
        doc_height = text_edit.document().size().height()
        margins = text_edit.contentsMargins()
        needed_height = doc_height + margins.top() + margins.bottom() + 10

        new_height = max(100, min(needed_height, 300))
        if new_height != text_edit.height():
            text_edit.setFixedHeight(int(new_height))

    def _handle_generate_all(self):
        """Generate all fields in order"""
        # Check if we have a character to generate for
        if not self.character_manager.current_character:
            self.ui_manager.show_status_message(
                "Please create or load a character first",
                StatusLevel.WARNING
            )
            return
            
        try:
            # Get the ordered fields from the generation manager
            ordered_fields = self.generation_manager.generation_service._get_ordered_fields()
            
            # Filter out fields that don't have an order
            ordered_fields = [f for f in ordered_fields if f is not None]
            
            if not ordered_fields:
                self.ui_manager.show_status_message(
                    "No fields configured for generation order",
                    StatusLevel.WARNING
                )
                return
            
            # Collect inputs for all fields
            field_inputs = {}
            for field in ordered_fields:
                if field in self.input_widgets:
                    field_inputs[field] = self.input_widgets[field].get_input()
            
            # Create generation context
            context = GenerationContext(
                character_data=self.character_manager.current_character,
                current_field=ordered_fields[0],  # Start with first field
                field_inputs=field_inputs,
                changed_fields=set(),
                generation_mode=GenerationMode.GENERATE
            )
            
            # Show progress
            self.ui_manager.show_status_message(
                f"Starting generation for {len(ordered_fields)} fields...",
                StatusLevel.INFO
            )
            
            # Start generation
            self.generation_manager.batch_started.emit(len(ordered_fields))
            
            def on_batch_complete():
                self.ui_manager.show_status_message(
                    "Generation completed",
                    StatusLevel.SUCCESS
                )
                
            def on_batch_progress(current: int, total: int):
                self.ui_manager.show_status_message(
                    f"Generating fields: {current}/{total}",
                    StatusLevel.INFO
                )
            
            # Connect temporary progress handlers
            self.generation_manager.batch_completed.connect(on_batch_complete)
            self.generation_manager.batch_progress.connect(on_batch_progress)
            
            # Start the generation process
            self.generation_manager.generate_with_dependencies(
                ordered_fields[0],  # Start with first field
                context.field_inputs.get(ordered_fields[0], ""),
                GenerationMode.GENERATE
            )
            
        except Exception as e:
            self.ui_manager.show_status_message(
                f"Error during generation: {str(e)}",
                StatusLevel.ERROR
            )
            QMessageBox.critical(
                self,
                "Generation Error",
                f"Error during generation: {str(e)}"
            )

    def _handle_output_changed(self, field: FieldName):
        """Handle output text changes"""
        if self.is_updating:
            return
            
        self.is_updating = True
        try:
            if field in self.output_texts:
                text = self.output_texts[field].toPlainText()
                
                # Update character
                if self.character_manager.current_character:
                    self.character_manager.current_character.fields[field] = text
                    self.character_updated.emit(
                        self.character_manager.current_character,
                        field.value
                    )
        finally:
            self.is_updating = False
            
    def _handle_regenerate(self, field: FieldName):
        """Handle single field regeneration"""
        if not self.character_manager.current_character:
            return
            
        input_text = ""
        if field in self.input_widgets:
            input_text = self.input_widgets[field].get_input()
        
        self.generation_manager.generate_field(
            field,
            input_text,
            GenerationMode.GENERATE
        )
    
    def _handle_regenerate_with_deps(self, field: FieldName):
        """Handle regeneration with dependencies"""
        if not self.character_manager.current_character:
            return
            
        input_text = ""
        if field in self.input_widgets:
            input_text = self.input_widgets[field].get_input()
        
        self.generation_manager.generate_with_dependencies(
            field,
            input_text,
            GenerationMode.GENERATE
        )

    def _connect_signals(self):
        """Connect signals"""
        # Connect generation result signals
        self.generation_manager.generation_completed.connect(
            self._handle_generation_completed
        )
        self.generation_manager.generation_error.connect(
            self._handle_generation_error
        )
        
        # Connect field widgets
        for field, widget in self.input_widgets.items():
            if isinstance(widget, CompactFieldWidget):
                # Connect regeneration signals
                widget.regen_requested.connect(
                    lambda f=field: self._handle_regenerate(f)
                )
                widget.regen_with_deps_requested.connect(
                    lambda f=field: self._handle_regenerate_with_deps(f)
                )
    
    def _handle_generation_completed(self, field: FieldName, result):
        """Handle completed generation"""
        if not result.error:
            # Update output display
            if field in self.output_texts:
                self.output_texts[field].setPlainText(result.content)
            
            # Update character
            if self.character_manager.current_character:
                self.character_manager.current_character.fields[field] = result.content
                self.character_updated.emit(
                    self.character_manager.current_character,
                    field.value
                )
    
    def _handle_generation_error(self, field: FieldName, error: Exception):
        """Handle generation error"""
        self.ui_manager.show_status_message(
            f"Error generating {field.value}: {str(error)}",
            StatusLevel.ERROR
        )
        QMessageBox.warning(
            self,
            "Generation Error",
            f"Error generating {field.value}: {str(error)}"
        )

    def set_initial_character(self, character: CharacterData):
        """Set initial character data"""
        print(f"GenerationTab: Setting initial character {character.name}")
        self.is_updating = True
        try:
            # Update field input and output displays
            for field in FieldName:
                if field in self.input_widgets:
                    self.input_widgets[field].set_input('')  # Clear inputs
                    
                if field in self.output_texts and field in character.fields:
                    text_edit = self.output_texts[field]
                    content = character.fields.get(field, '')
                    if content:
                        text_edit.setPlainText(content)
                        # Force height adjustment directly
                        self._adjust_output_height(text_edit)
            
            # Update alternate greetings
            if hasattr(self, 'alt_greetings_widget'):
                if character.alternate_greetings:
                    print(f"Setting {len(character.alternate_greetings)} greetings in Gen Tab")
                    self.alt_greetings_widget.set_greetings(character.alternate_greetings)
                    # Force height adjustment
                    self.alt_greetings_widget._adjust_height()
                else:
                    self.alt_greetings_widget.set_greetings([])
                    
        finally:
            self.is_updating = False

    def handle_external_update(self, character: CharacterData, updated_field: Optional[str] = None):
        """Handle updates from other tabs"""
        if self.is_updating:
            return
                    
        self.is_updating = True
        try:
            if updated_field:
                try:
                    field = FieldName(updated_field)
                    if field in self.output_texts:
                        self.output_texts[field].setPlainText(
                            character.fields.get(field, '')
                        )
                        # Force height adjustment
                        self._adjust_output_height(self.output_texts[field])
                except ValueError:
                    pass
            else:
                self._update_output_displays(character.fields, emit_updates=False)
        finally:
            self.is_updating = False

    def _update_output_displays(self, fields: Dict[FieldName, str], emit_updates: bool = True):
        """Update all output displays"""
        if self.is_updating:
            return
                    
        self.is_updating = True
        try:
            for field, value in fields.items():
                if field in self.output_texts:
                    text_edit = self.output_texts[field]
                    text_edit.setPlainText(value)
                    # Force height adjustment directly
                    self._adjust_output_height(text_edit)
            
            if emit_updates and self.character_manager.current_character:
                self.character_updated.emit(
                    self.character_manager.current_character,
                    "all"
                )
        finally:
            self.is_updating = False

    def closeEvent(self, event):
        """Handle tab closing"""
        if self.character_manager.is_modified:
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "There are unsaved changes. Would you like to save?",
                QMessageBox.StandardButton.Yes | 
                QMessageBox.StandardButton.No |
                QMessageBox.StandardButton.Cancel
            )
            
            if reply == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
            elif reply == QMessageBox.StandardButton.Yes:
                # Switch to editor tab for saving
                self.ui_manager.set_current_tab("editor")
                event.ignore()
                return
        
        event.accept()