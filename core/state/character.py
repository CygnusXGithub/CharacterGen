from typing import Dict, Optional, Set, List
from datetime import datetime
import asyncio
from uuid import UUID

from core.models.ui import StatusLevel

from .base import StateManagerBase
from ..models.character import CharacterData
from ..services.validation import ValidationService
from ..services.file import FileService
from ..errors import ErrorHandler, StateError, ErrorCategory, ErrorLevel

class CharacterStateManager(StateManagerBase):
    """Manages character state and operations"""

    def __init__(self, 
                 validation_service: ValidationService,
                 file_service: FileService,
                 error_handler: ErrorHandler):
        super().__init__()
        self.validation_service = validation_service
        self.file_service = file_service
        self.error_handler = error_handler
        
        # Current character state
        self._current_character: Optional[CharacterData] = None
        self._modified_fields: Set[str] = set()
        self._last_saved: Optional[datetime] = None
        
        # Undo/Redo stacks
        self._undo_stack: List[CharacterData] = []
        self._redo_stack: List[CharacterData] = []
        
        # Save lock for async operations
        self._save_lock = asyncio.Lock()

    def get_current_character(self) -> Optional[CharacterData]:
        """Get current character data"""
        return self._current_character

    async def load_character(self, character_id: UUID) -> CharacterData:
        """Load character by ID"""
        try:
            with self.operation('load_character', {'id': str(character_id)}):
                # Clear current state
                self._clear_current_state()
                
                # Load character
                character = await self.file_service.load_character(character_id)
                
                # Update state
                self._current_character = character
                self._last_saved = datetime.now()
                
                # Emit state change
                self.state_changed.emit('current_character', character)
                
                return character
                
        except Exception as e:
            self.error_handler.handle_error(
                error=e,
                category=ErrorCategory.STATE,
                level=ErrorLevel.ERROR,
                context={'operation': 'load_character', 'id': str(character_id)}
            )
            raise StateError(f"Failed to load character: {str(e)}")

    async def update_field(self, 
                         field_name: str, 
                         value: str, 
                         validate: bool = True) -> bool:
        """Update character field with optional validation"""
        try:
            with self.operation('update_field', {'field': field_name}):
                if not self._current_character:
                    raise StateError("No character loaded")
                
                # Store for undo
                self._push_undo_state()
                
                # Validate if requested
                if validate:
                    result = await self.validation_service.validate_field(
                        field_type=field_name,
                        value=value
                    )
                    if not result.is_valid:
                        self.error_occurred.emit(
                            'validation_error',
                            result.message
                        )
                        return False
                
                # Update field
                setattr(self._current_character, field_name, value)
                self._current_character.modified_at = datetime.now()
                self._modified_fields.add(field_name)
                
                # Clear redo stack
                self._redo_stack.clear()
                
                # Emit state change
                self.state_changed.emit('field_updated', {
                    'field': field_name,
                    'value': value
                })
                
                return True
                
        except Exception as e:
            self.error_handler.handle_error(
                error=e,
                category=ErrorCategory.STATE,
                level=ErrorLevel.ERROR,
                context={'operation': 'update_field', 'field': field_name}
            )
            return False

    async def save_character(self, auto_save: bool = False) -> bool:
        """Save current character"""
        if not self._current_character:
            return False
            
        async with self._save_lock:  # Prevent concurrent saves
            try:
                with self.operation('save_character', {'auto_save': auto_save}):
                    if auto_save:
                        await self.file_service.auto_save(self._current_character)
                    else:
                        await self.file_service.save_character(self._current_character)
                    
                    self._last_saved = datetime.now()
                    self._modified_fields.clear()
                    return True
                    
            except Exception as e:
                self.error_handler.handle_error(
                    error=e,
                    category=ErrorCategory.STATE,
                    level=ErrorLevel.ERROR,
                    context={'operation': 'save_character', 'auto_save': auto_save}
                )
                return False

    def has_unsaved_changes(self) -> bool:
        """Check if there are unsaved changes"""
        return len(self._modified_fields) > 0

    def can_undo(self) -> bool:
        """Check if undo is available"""
        return len(self._undo_stack) > 0

    def can_redo(self) -> bool:
        """Check if redo is available"""
        return len(self._redo_stack) > 0

    def undo(self) -> bool:
        """Perform undo operation"""
        if not self.can_undo():
            return False
            
        try:
            with self.operation('undo'):
                # Move current state to redo stack
                if self._current_character:
                    self._redo_stack.append(self._current_character)
                
                # Restore previous state
                self._current_character = self._undo_stack.pop()
                self.state_changed.emit('current_character', self._current_character)
                return True
                
        except Exception as e:
            self.error_handler.handle_error(
                error=e,
                category=ErrorCategory.STATE,
                level=ErrorLevel.ERROR,
                context={'operation': 'undo'}
            )
            return False

    def redo(self) -> bool:
        """Perform redo operation"""
        if not self.can_redo():
            return False
            
        try:
            with self.operation('redo'):
                # Move current state to undo stack
                if self._current_character:
                    self._undo_stack.append(self._current_character)
                
                # Restore next state
                self._current_character = self._redo_stack.pop()
                self.state_changed.emit('current_character', self._current_character)
                return True
                
        except Exception as e:
            self.error_handler.handle_error(
                error=e,
                category=ErrorCategory.STATE,
                level=ErrorLevel.ERROR,
                context={'operation': 'redo'}
            )
            return False

    def _clear_current_state(self):
        """Clear current character state"""
        self._current_character = None
        self._modified_fields.clear()
        self._last_saved = None
        self._undo_stack.clear()
        self._redo_stack.clear()

    def _push_undo_state(self):
        """Push current state to undo stack"""
        if self._current_character:
            self._undo_stack.append(self._current_character.copy())
            # Limit undo stack size
            while len(self._undo_stack) > 50:  # Configurable limit
                self._undo_stack.pop(0)

    async def initialize(self):
        """Initialize state manager and check for auto-saves"""
        try:
            # Check for auto-save if no character is loaded
            if not self._current_character:
                # Look for most recent auto-save
                auto_saves = list(self.file_service.config.temp_dir.glob("auto_save_*.json"))
                if auto_saves:
                    # Get most recent auto-save
                    latest_auto_save = max(auto_saves, key=lambda p: p.stat().mtime)
                    recovered_char = await self.file_service.recover_auto_save(
                        latest_auto_save.stem.replace('auto_save_', '')
                    )
                    if recovered_char:
                        self._current_character = recovered_char
                        self._modified_fields.add("*")  # Mark as modified
                        self.ui_manager.show_status(
                            "Recovered unsaved changes from auto-save",
                            StatusLevel.INFO
                        )
        except Exception as e:
            self.error_handler.handle_error(
                error=e,
                category=ErrorCategory.STATE,
                level=ErrorLevel.WARNING,
                context={'operation': 'initialize'}
            )