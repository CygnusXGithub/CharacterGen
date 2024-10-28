from typing import Optional, Dict, List, Set
from pathlib import Path
import logging
from datetime import datetime
from PyQt6.QtCore import QObject, pyqtSignal

from ..models import CharacterData
from ..enums import FieldName, CardFormat
from ..exceptions import CharacterLoadError, CharacterSaveError
from ...services.character_service import CharacterService

class CharacterStateManager(QObject):
    """Centralized manager for character state"""
    
    version_updated = pyqtSignal(str)
    
    # Core state change signals
    character_loaded = pyqtSignal(CharacterData)  # After successful load
    character_updated = pyqtSignal(CharacterData, str)  # When any field changes (character, field_name)
    character_saved = pyqtSignal(Path)  # After successful save
    
    # Additional state signals
    modification_changed = pyqtSignal(bool)  # When modified state changes
    operation_started = pyqtSignal(str)  # General operation status
    operation_completed = pyqtSignal(str)  # Operation completion status
    operation_failed = pyqtSignal(str, str)  # Operation failures (operation, error)
    
    def __init__(self, character_service: CharacterService):
        super().__init__()
        self.character_service = character_service
        self._current_character: Optional[CharacterData] = None
        self._is_modified = False
        self._is_updating = False
        self._undo_stack: List[Dict] = []
        self._redo_stack: List[Dict] = []
        self._recent_files: List[Path] = []
        
    @property
    def current_character(self) -> Optional[CharacterData]:
        """Get current character"""
        return self._current_character
    
    @property
    def is_modified(self) -> bool:
        """Check if character has unsaved changes"""
        return self._is_modified
    
    @property
    def is_updating(self) -> bool:
        """Check if manager is currently updating state"""
        return self._is_updating
    
    def load_character(self, file_path: str) -> Optional[CharacterData]:
        """Load character from file"""
        try:
            self._is_updating = True
            self.operation_started.emit(f"Loading character from {file_path}")
            
            # Load character
            character = self.character_service.load(file_path)
            
            # Update state
            self._current_character = character
            self._is_modified = False
            self._clear_undo_redo()
            
            # Add to recent files
            self._add_recent_file(Path(file_path))
            
            # Emit signals
            self.character_loaded.emit(character)
            self.operation_completed.emit(f"Loaded character: {character.name}")
            
            return character
            
        except Exception as e:
            error_msg = f"Error loading character: {str(e)}"
            self.operation_failed.emit("load", error_msg)
            raise
        finally:
            self._is_updating = False
    
    def save_character(self, file_path: str, format: CardFormat) -> Optional[Path]:
        """Save character to file"""
        if not self._current_character:
            self.operation_failed.emit("save", "No character to save")
            return None
            
        try:
            self._is_updating = True
            self.operation_started.emit(f"Saving character to {file_path}")
            
            # Save character
            saved_path = self.character_service.export_character(
                self._current_character,
                format,
                Path(file_path).parent
            )
            
            # Update state
            self._is_modified = False
            self._add_recent_file(saved_path)
            
            # Emit signals
            self.character_saved.emit(saved_path)
            self.modification_changed.emit(False)
            self.operation_completed.emit(f"Saved character to: {saved_path}")
            
            return saved_path
            
        except Exception as e:
            error_msg = f"Error saving character: {str(e)}"
            logging.error(error_msg)
            self.operation_failed.emit("save", error_msg)
            raise
        finally:
            self._is_updating = False
    
    def update_field(self, field_name: str, value: str):
        """Update a character field"""
        if not self._current_character:
            return
            
        try:
            self._is_updating = True
            
            # Store current state for undo
            self._push_undo_state()
            
            # Update the field
            try:
                field = FieldName(field_name)
                self._current_character.fields[field] = value
            except ValueError:
                # Handle metadata fields
                if hasattr(self._current_character, field_name):
                    setattr(self._current_character, field_name, value)
            
            # Update state
            self._is_modified = True
            
            # Emit signals
            self.character_updated.emit(self._current_character, field_name)
            self.modification_changed.emit(True)
            
        finally:
            self._is_updating = False
    
    def create_new_character(self, name: str = "Unnamed") -> CharacterData:
        """Create a new character"""
        try:
            self._is_updating = True
            self.operation_started.emit("Creating new character")
            
            # Create character
            character = self.character_service.create_character(name)
            
            # Update state
            self._current_character = character
            self._is_modified = False
            self._clear_undo_redo()
            
            # Emit signals
            self.character_loaded.emit(character)
            self.operation_completed.emit("Created new character")
            
            return character
            
        except Exception as e:
            error_msg = f"Error creating character: {str(e)}"
            logging.error(error_msg)
            self.operation_failed.emit("create", error_msg)
            raise
        finally:
            self._is_updating = False
    
    def undo(self) -> bool:
        """Undo last change"""
        if not self._undo_stack:
            return False
            
        try:
            self._is_updating = True
            
            if self._current_character:
                self._redo_stack.append(self._current_character.to_dict())
            
            state = self._undo_stack.pop()
            self._current_character = CharacterData.from_dict(state)
            self.character_loaded.emit(self._current_character)
            
            return True
            
        finally:
            self._is_updating = False
    
    def redo(self) -> bool:
        """Redo last undone change"""
        if not self._redo_stack:
            return False
            
        try:
            self._is_updating = True
            
            if self._current_character:
                self._undo_stack.append(self._current_character.to_dict())
            
            state = self._redo_stack.pop()
            self._current_character = CharacterData.from_dict(state)
            self.character_loaded.emit(self._current_character)
            
            return True
            
        finally:
            self._is_updating = False
    
    def _add_recent_file(self, file_path: Path):
        """Add file to recent files list"""
        if file_path in self._recent_files:
            self._recent_files.remove(file_path)
        self._recent_files.insert(0, file_path)
        self._recent_files = self._recent_files[:10]  # Keep last 10
    
    def _push_undo_state(self):
        """Store current state for undo"""
        if self._current_character:
            self._undo_stack.append(self._current_character.to_dict())
            self._redo_stack.clear()  # Clear redo stack on new change
    
    def _clear_undo_redo(self):
        """Clear undo/redo stacks"""
        self._undo_stack.clear()
        self._redo_stack.clear()
    
    @property
    def recent_files(self) -> List[Path]:
        """Get list of recent files"""
        return self._recent_files.copy()