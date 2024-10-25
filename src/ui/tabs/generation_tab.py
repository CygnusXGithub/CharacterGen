from typing import Dict, Optional
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QMessageBox, QFileDialog, QPushButton, QLabel,
    QTextEdit, QComboBox, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal

from ...core.enums import FieldName, GenerationMode, CardFormat, SaveMode
from ...core.models import CharacterData, GenerationContext, GenerationCallbacks, GenerationResult
from ...core.exceptions import (
    GenerationError, CharacterLoadError, CharacterSaveError
)
from ...services.character_service import CharacterService
from ...services.generation_service import GenerationService
from ..widgets.field_widgets import (
    FieldInputWidget, MessageExampleWidget,
    FirstMessageWidget, FieldViewManager,AlternateGreetingsWidget
)
from ..widgets.common import LoadSaveWidget, DragDropFrame, StatusBar

class GenerationTab(QWidget):
    def __init__(self, 
                 character_service: CharacterService,
                 generation_service: GenerationService,
                 parent=None):
        super().__init__(parent)
        self.character_service = character_service
        self.generation_service = generation_service
        self.field_view_manager = FieldViewManager()
        self.current_character: Optional[CharacterData] = None
        # Initialize dictionaries
        self.input_widgets = {}
        self.output_texts = {}
        
        self._init_ui()
        self._connect_signals()
        self._load_available_characters()
    
    def _init_ui(self):
        layout = QVBoxLayout()
        
        # Add character management controls
        mgmt_layout = QHBoxLayout()
        
        # Load/save controls
        self.load_save = LoadSaveWidget(
            save_label="Character Name:",
            load_label="Load Character:"
        )
        mgmt_layout.addWidget(self.load_save)
        
        # Save format selection
        self.format_selector = QComboBox()
        self.format_selector.addItems([f.value for f in CardFormat])
        mgmt_layout.addWidget(QLabel("Save as:"))
        mgmt_layout.addWidget(self.format_selector)
        
        # Image button
        self.image_btn = QPushButton("Add Image")
        self.image_btn.clicked.connect(self._handle_image_selection)
        mgmt_layout.addWidget(self.image_btn)

        layout.addLayout(mgmt_layout)

        # ---------- End Management Controls ---------- #
        
        # Create main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left side - Input fields
        input_widget = QWidget()
        input_layout = QVBoxLayout(input_widget)
        input_layout.setSpacing(10)
        
        # Create scroll area for inputs
        input_scroll = QScrollArea()
        input_scroll.setWidgetResizable(True)
        
        # Create container for inputs
        input_container = QWidget()
        input_container_layout = QVBoxLayout(input_container)
        input_container_layout.setSpacing(10)
        
        # Add input widgets to container
        for field in FieldName:
            if field == FieldName.MES_EXAMPLE:
                widget = MessageExampleWidget()
            elif field == FieldName.FIRST_MES:
                widget = FirstMessageWidget()
            else:
                widget = FieldInputWidget(field)
            
            self.input_widgets[field] = widget
            input_container_layout.addWidget(widget)
        
        # Add buttons
        self.generate_btn = QPushButton("Generate All")
        self.generate_btn.clicked.connect(self._handle_generate_all)
        input_container_layout.addWidget(self.generate_btn)
        
        save_btn = QPushButton("Save Character")
        save_btn.clicked.connect(self._handle_save_character)
        input_container_layout.addWidget(save_btn)
        
        # Add stretch at the end
        input_container_layout.addStretch()
        
        # Set scroll widget
        input_scroll.setWidget(input_container)
        input_layout.addWidget(input_scroll)
        
        # ------------ End Input Fields ------------- #

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
        

        for field in FieldName:
            # Create a container for each field
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
            text_edit.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Minimum
            )
            text_edit.document().documentLayout().documentSizeChanged.connect(
                self._create_height_adjuster(text_edit)
            )
            self.output_texts[field] = text_edit
            field_layout.addWidget(text_edit)
            
            output_container_layout.addWidget(field_container)
            
            # Add alternate greetings widget immediately after first_mes
            if field == FieldName.FIRST_MES:
                self.alt_greetings_widget = AlternateGreetingsWidget()
                # Set the widget to match field container's layout
                self.alt_greetings_widget.setContentsMargins(0, 0, 0, 0)
                self.alt_greetings_widget.setSizePolicy(
                    QSizePolicy.Policy.Expanding,
                    QSizePolicy.Policy.Minimum
                )
                self.alt_greetings_widget.greeting_added.connect(
                    lambda: self._handle_new_greeting(FieldName.FIRST_MES)
                )
                self.alt_greetings_widget.greeting_deleted.connect(self._handle_greeting_deleted)
                self.alt_greetings_widget.greeting_regenerated.connect(self._handle_greeting_regenerated)
                output_container_layout.addWidget(self.alt_greetings_widget)

        # Add stretch at the end
        output_container_layout.addStretch()
        
        # Set scroll widget
        output_scroll.setWidget(output_container)
        output_layout.addWidget(output_scroll)

        # ------------ End Output Fields ------------- #
        
        # Add widgets to splitter
        splitter.addWidget(input_widget)
        splitter.addWidget(output_widget)
        
        # Set initial splitter sizes
        splitter.setSizes([500, 500])
        
        layout.addWidget(splitter)
        self.setLayout(layout)

        layout.addWidget(splitter)
    
        # Add status bar at the bottom
        self.status_bar = StatusBar()
        layout.addWidget(self.status_bar)
        
        self.setLayout(layout)
    
    def _connect_signals(self):
        """Connect signal handlers"""
        # Connect load/save signals
        self.load_save.load_clicked.connect(self._handle_load_character)
        self.load_save.refresh_clicked.connect(self._load_available_characters)
        self.load_save.save_clicked.connect(
            lambda name: self._handle_save_character(name)
        )
        
        # Connect input widget signals
        for field, widget in self.input_widgets.items():
            widget.regen_requested.connect(
                lambda f=field: self._handle_single_regen(f)
            )
            widget.regen_with_deps_requested.connect(
                lambda f=field: self._handle_regen_with_deps(f)
            )
            widget.focus_changed.connect(self._handle_field_focus)
            
            if isinstance(widget, MessageExampleWidget):
                widget.append_requested.connect(self._handle_append_example)
            elif isinstance(widget, FirstMessageWidget):
                widget.greeting_requested.connect(self._handle_new_greeting)
    
    def _create_height_adjuster(self, text_edit: QTextEdit):
        """Create a closure for height adjustment"""
        def adjust():
            # Calculate document height
            doc_size = text_edit.document().size()
            margins = text_edit.contentsMargins()
            height = int(doc_size.height() + margins.top() + margins.bottom() + 10)
            
            # Set height with limits
            text_edit.setMinimumHeight(min(max(100, height), 400))
            
            # Force parent widget to update layout
            parent = text_edit.parent()
            if parent:
                parent.updateGeometry()
        return adjust

    def _load_available_characters(self):
        """Load list of available characters"""
        try:
            characters = self.character_service.list_characters()
            self.load_save.update_items(characters)
            
        except CharacterLoadError as e:
            QMessageBox.warning(
                self,
                "Load Error",
                f"Error loading characters: {str(e)}"
            )
    
    def _handle_load_character(self, name: str):
        """Handle loading of a character"""
        if not name:
            return
                
        try:
            self.current_character = self.character_service.load(name)
            
            # Update UI
            self._update_output_displays(self.current_character.fields)
            
            # Load alternate greetings
            if self.current_character.alternate_greetings:
                self.alt_greetings_widget.set_greetings(self.current_character.alternate_greetings)
            else:
                self.alt_greetings_widget.set_greetings([])  # Clear if no greetings
            
            self.status_bar.set_status(f"Loaded character: {name}")
            
        except CharacterLoadError as e:
            QMessageBox.warning(
                self,
                "Load Error",
                f"Error loading character '{name}': {str(e)}"
            )
    
    def _handle_save_character(self, name: Optional[str] = None):
        """Handle saving of character"""
        # Get name from the save name input field at the top
        name = self.load_save.save_name.text().strip()
        
        if not name:
            QMessageBox.warning(
                self,
                "Save Error",
                "Please enter a character name"
            )
            return
        
        try:
            # Create or update character data
            if not self.current_character:
                self.current_character = self.character_service.create_character(name)
            
            # Update character name
            self.current_character.name = name
            
            # Update fields
            for field, text_edit in self.output_texts.items():
                self.current_character.fields[field] = text_edit.toPlainText()
            
            # Update alternate greetings
            self.current_character.alternate_greetings = self.alt_greetings_widget.greetings
            
            # Save character
            format = CardFormat(self.format_selector.currentText())
            saved_path = self.character_service.save(
                self.current_character,
                format=format,
                mode=SaveMode.OVERWRITE
            )
            
            # Refresh available characters
            self._load_available_characters()
            
            self.status_bar.set_status(f"Saved character to: {saved_path}")
            
        except CharacterSaveError as e:
            QMessageBox.warning(
                self,
                "Save Error",
                f"Error saving character: {str(e)}"
            )
    
    def _handle_image_selection(self):
        """Handle image selection"""
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Select Image",
            "",
            "Image Files (*.png *.jpg *.jpeg)"
        )
        
        if file_name:
            try:
                from PIL import Image
                image = Image.open(file_name)
                
                if self.current_character:
                    self.current_character.image_data = image
                    self.status_bar.set_status("Image added successfully")
                    
            except Exception as e:
                QMessageBox.warning(
                    self,
                    "Image Error",
                    f"Error loading image: {str(e)}"
                )
    
    def _handle_generate_all(self):
        """Handle generation of all fields"""
        try:
            # Get the first field in the generation order
            ordered_fields = self.generation_service._get_ordered_fields()
            if not ordered_fields:
                raise GenerationError("No fields with generation order defined")
                
            first_field = ordered_fields[0]
            
            # Create context for the first field and generate all from there
            context = self._create_generation_context(first_field)
            callbacks = self._create_callbacks()
            
            # Special handling for name field when in direct mode
            if (first_field == FieldName.NAME and 
                context.generation_mode == GenerationMode.DIRECT):
                self._handle_generation_result(
                    first_field,
                    GenerationResult(
                        field=first_field,
                        content=context.user_input
                    )
                )
                
            results = self.generation_service.generate_field_with_deps(
                context, callbacks
            )
            
            if any(isinstance(result.error, Exception) for result in results.values()):
                return
                        
        except Exception as e:
            QMessageBox.critical(
                self,
                "Generation Error",
                f"Error during generation: {str(e)}"
            )
    
    def _handle_single_regen(self, field: FieldName):
        """Handle regeneration of a single field"""
        try:
            context = self._create_generation_context(field)
            callbacks = self._create_callbacks()
            
            # Handle direct mode for name field
            if (field == FieldName.NAME and 
                context.generation_mode == GenerationMode.DIRECT):
                self._handle_generation_result(
                    field,
                    GenerationResult(
                        field=field,
                        content=context.user_input
                    )
                )
                return
            
            result = self.generation_service.generate_field(context)
            self._handle_generation_result(field, result)
            
        except Exception as e:
            self._handle_generation_error(field, e)
    
    def _handle_regen_with_deps(self, field: FieldName):
        """Handle regeneration of a field and its dependents"""
        try:
            context = self._create_generation_context(field)
            callbacks = self._create_callbacks()
            
            # Handle direct mode for name field
            if (field == FieldName.NAME and 
                context.generation_mode == GenerationMode.DIRECT):
                self._handle_generation_result(
                    field,
                    GenerationResult(
                        field=field,
                        content=context.user_input
                    )
                )
            
            results = self.generation_service.generate_field_with_deps(
                context, callbacks
            )
            
            # Results are handled by callbacks
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Generation Error",
                f"Error during generation: {str(e)}"
            )
    
    def _handle_append_example(self, field: FieldName):
        """Handle appending a new message example"""
        try:
            if not self.current_character:
                raise GenerationError("No character loaded")
            
            # Get current output text
            current_text = self.output_texts[FieldName.MES_EXAMPLE].toPlainText()
            
            # Use current prompt input for generation
            input_text = self.input_widgets[FieldName.MES_EXAMPLE].get_input()
            
            # Create specialized callbacks that won't overwrite existing text
            callbacks = GenerationCallbacks(
                on_start=lambda field: self.status_bar.set_status(
                    "Generating additional examples..."
                ),
                on_progress=None,  # Don't update the main field
                on_result=None,    # We'll handle the result manually
                on_error=lambda field, error: self._handle_generation_error(
                    field, error
                )
            )
            
            new_example = self.generation_service.append_message_example(
                self.current_character,
                input_text,
                callbacks
            )
            
            if new_example:
                # Append to existing examples
                updated_text = (current_text + "\n\n" + new_example 
                            if current_text.strip() else new_example)
                self.output_texts[FieldName.MES_EXAMPLE].setPlainText(updated_text)
                self.status_bar.set_status("Appended new message example")
                
        except Exception as e:
            QMessageBox.warning(
                self,
                "Generation Error",
                f"Error generating message example: {str(e)}"
            )
    
    def _handle_new_greeting(self, field: FieldName):
        """Handle generating a new alternate greeting"""
        try:
            if not self.current_character:
                raise GenerationError("No character loaded")
            
            # Create callbacks that won't affect the main first_mes field
            callbacks = GenerationCallbacks(
                on_start=lambda field: self.status_bar.set_status(
                    f"Generating alternate greeting..."
                ),
                on_progress=None,  # Don't update any fields
                on_result=lambda field, result: self.alt_greetings_widget.add_greeting(
                    result.content
                ) if not result.error else None,
                on_error=lambda field, error: self._handle_generation_error(
                    field, error
                )
            )
            
            new_greeting = self.generation_service.generate_alternate_greeting(
                self.current_character,
                callbacks
            )
            
            if new_greeting:
                self.status_bar.set_status("Added new alternate greeting")
    
            
        except Exception as e:
            QMessageBox.warning(
                self,
                "Generation Error",
                f"Error generating alternate greeting: {str(e)}"
            )
    
    def _handle_greeting_deleted(self, index: int):
        """Handle deletion of an alternate greeting"""
        if self.current_character and hasattr(self.current_character, 'alternate_greetings'):
            if 0 <= index < len(self.current_character.alternate_greetings):
                self.current_character.alternate_greetings.pop(index)
                self.status_bar.set_status("Deleted alternate greeting")

    def _handle_greeting_regenerated(self, index: int):
        """Handle regeneration of a specific alternate greeting"""
        try:
            if not self.current_character:
                raise GenerationError("No character loaded")
            
            # Initialize alternate_greetings if it doesn't exist
            if not hasattr(self.current_character, 'alternate_greetings'):
                self.current_character.alternate_greetings = []
            
            # Check if the index is valid in the widget's greetings list
            if not self.alt_greetings_widget.greetings or \
            index >= len(self.alt_greetings_widget.greetings):
                raise GenerationError("Invalid greeting index")
            
            # Create specialized callbacks that won't affect the main first_mes field
            callbacks = GenerationCallbacks(
                on_start=lambda field: self.status_bar.set_status(
                    "Regenerating alternate greeting..."
                ),
                on_progress=None,  # Don't update any fields
                on_result=None,    # Don't update any fields
                on_error=lambda field, error: self._handle_generation_error(
                    field, error
                )
            )
            
            # Use the same generation logic as new greeting
            new_greeting = self.generation_service.generate_alternate_greeting(
                self.current_character,
                callbacks
            )
            
            if new_greeting:
                # Update only the alternate greeting lists
                if index >= len(self.current_character.alternate_greetings):
                    self.current_character.alternate_greetings.extend(
                        [''] * (index - len(self.current_character.alternate_greetings) + 1)
                    )
                self.current_character.alternate_greetings[index] = new_greeting
                self.alt_greetings_widget.greetings[index] = new_greeting
                self.alt_greetings_widget._update_display()
                self.status_bar.set_status("Regenerated alternate greeting")
                
        except Exception as e:
            QMessageBox.warning(
                self,
                "Generation Error",
                f"Error regenerating greeting: {str(e)}"
            )
    
    def _handle_field_focus(self, field: FieldName, focused: bool):
        """Handle field focus changes"""
        if focused:
            self.field_view_manager.toggle_field_focus(
                field,
                input_text=self.input_widgets[field].get_input(),
                output_text=self.output_texts[field].toPlainText(),
                input_widget=self.input_widgets[field],
                output_widget=self.output_texts[field],
                regen_callback=lambda: self._handle_single_regen(field),
                regen_deps_callback=lambda: self._handle_regen_with_deps(field)
            )
        else:
            self.field_view_manager.toggle_field_focus(field)
    
    def _handle_output_change(self, field: FieldName):
        """Handle changes to output text"""
        if self.current_character:
            self.current_character.fields[field] = self.output_texts[field].toPlainText()
    
    def _update_output_displays(self, fields: Dict[FieldName, str]):
        """Update all output displays with new values"""
        for field, value in fields.items():
            if field in self.output_texts:
                self.output_texts[field].setPlainText(value)
    
    def _create_generation_context(self, field: FieldName) -> GenerationContext:
        """Create generation context for a field"""
        if not self.current_character:
            self.current_character = self.character_service.create_character(
                self.load_save.save_name.text().strip() or "Unnamed"
            )
        
        # Determine generation mode
        mode = GenerationMode.GENERATE
        if (field == FieldName.NAME and 
            field in self.input_widgets and
            hasattr(self.input_widgets[field], 'gen_mode_checkbox')):
            mode = (GenerationMode.GENERATE 
                   if self.input_widgets[field].gen_mode_checkbox.isChecked()
                   else GenerationMode.DIRECT)
        
        return GenerationContext(
            character_data=self.current_character,
            current_field=field,
            user_input=self.input_widgets[field].get_input(),
            generation_mode=mode
        )
    
    def _create_callbacks(self) -> GenerationCallbacks:
        """Create generation callbacks"""
        return GenerationCallbacks(
            on_start=lambda field: self.status_bar.set_status(
                f"Generating {field.value}..."
            ),
            on_progress=lambda field, status: self.output_texts[field].setPlainText(
                status
            ),
            on_result=lambda field, result: self._handle_generation_result(
                field, result
            ),
            on_error=lambda field, error: self._handle_generation_error(
                field, error
            )
        )
    
    def _handle_generation_result(self, field: FieldName, result: GenerationResult):
        """Handle successful generation"""
        self.output_texts[field].setPlainText(result.content)
        if self.current_character:
            self.current_character.fields[field] = result.content
        
        self.status_bar.set_status(
            f"Generated {field.value} in {result.attempts} attempts"
        )
    
    def _handle_generation_error(self, field: FieldName, error: Exception):
        """Handle generation error"""
        self.output_texts[field].setPlainText(f"Error: {str(error)}")
        self.status_bar.set_status(f"Error generating {field.value}")
        QMessageBox.warning(
            self,
            "Generation Error",
            f"Error generating {field.value}: {str(error)}"
        )
    
    def dragEnterEvent(self, event):
        """Handle drag enter events for file dropping"""
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()
    
    def dropEvent(self, event):
        """Handle file drop events"""
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        for file_path in files:
            if file_path.lower().endswith(('.json', '.png')):
                self._handle_dropped_file(file_path)
        event.accept()
    
    def _handle_dropped_file(self, file_path: str):
        """Handle dropped character file"""
        try:
            # Extract file name without extension
            name = Path(file_path).stem
            
            # Load the character
            self.current_character = self.character_service.load(file_path)
            
            # Update UI
            self.load_save.save_name.setText(name)
            self._update_output_displays(self.current_character.fields)
            
            # Refresh character list
            self._load_available_characters()
            
            self.status_bar.set_status(f"Loaded character from: {file_path}")
            
        except Exception as e:
            QMessageBox.warning(
                self,
                "Load Error",
                f"Error loading dropped file: {str(e)}"
            )
    
    def closeEvent(self, event):
        """Handle tab closing"""
        # Close any open field views
        self.field_view_manager.close_all()
        event.accept()
    
    def clear_all(self):
        """Clear all inputs and outputs"""
        # Clear input widgets
        for widget in self.input_widgets.values():
            widget.set_input("")
        
        # Clear output texts
        for text_edit in self.output_texts.values():
            text_edit.clear()
        
        # Reset current character
        self.current_character = None
        
        # Clear save name
        self.load_save.save_name.clear()
        
        # Update status
        self.status_bar.set_status("Cleared all fields")
    
    def is_modified(self) -> bool:
        """Check if any outputs have been modified"""
        if not self.current_character:
            return any(text_edit.toPlainText() for text_edit in self.output_texts.values())
        
        # Compare current outputs with character data
        for field, text_edit in self.output_texts.items():
            if text_edit.toPlainText() != self.current_character.fields.get(field, ""):
                return True
        
        return False
    
    def prompt_save_if_modified(self) -> bool:
        """Prompt to save if there are modifications"""
        if self.is_modified():
            reply = QMessageBox.question(
                self,
                "Save Changes?",
                "There are unsaved changes. Would you like to save them?",
                QMessageBox.StandardButton.Yes | 
                QMessageBox.StandardButton.No | 
                QMessageBox.StandardButton.Cancel
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self._handle_save_character()
                return True
            elif reply == QMessageBox.StandardButton.Cancel:
                return False
        
        return True