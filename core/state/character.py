from typing import Dict, Optional, Set, List, Any
from datetime import datetime
import asyncio
from uuid import UUID
from pathlib import Path

from .base import StateManagerBase, OperationContext
from .metadata import MetadataManager
from ..common.types import (
    Result, JsonDict, PathLike,
    ChangeType, ErrorCategory, ErrorLevel
)
from ..models.character import CharacterData
from ..models.ui import StatusLevel
from ..models.metadata import GenerationMetadata
from ..services.validation import ValidationService
from ..services.file import FileService
from ..services.generation import GenerationService, GenerationRequest
from ..errors import ErrorHandler, StateError

class CharacterStateManager(StateManagerBase[CharacterData]):
    """Manages character state and operations"""

    def __init__(self, 
                 validation_service: ValidationService,
                 file_service: FileService,
                 generation_service: GenerationService,
                 error_handler: ErrorHandler,
                 metadata_manager: MetadataManager):
        super().__init__(error_handler)
        self.validation_service = validation_service
        self.file_service = file_service
        self.generation_service = generation_service
        self.metadata_manager = metadata_manager
        
        # State tracking
        self._current_character: Optional[CharacterData] = None
        self._modified_fields: Set[str] = set()
        self._last_saved: Optional[datetime] = None
        
        # History management
        self._undo_stack: List[CharacterData] = []
        self._redo_stack: List[CharacterData] = []
        self._max_history = 50
        
        # Locks
        self._save_lock = asyncio.Lock()
        self._generation_lock = asyncio.Lock()
        self._field_locks: Dict[str, asyncio.Lock] = {}

    async def load_character(self, path: PathLike) -> Result[CharacterData]:
        """Load character from file with proper validation"""
        try:
            async with self.operation('load_character', {'path': str(path)}):
                # Clear current state first
                await self._clear_current_state()
                
                # Load character
                load_result = await self.file_service.load_character(path)
                if not load_result.success:
                    return load_result
                
                character = load_result.data
                
                # Validate character
                validation_result = await self._validate_character(character)
                if not validation_result.success:
                    return validation_result
                
                # Initialize metadata
                await self.metadata_manager.initialize_character_metadata(character.id)
                await self.metadata_manager.set_active_character(character.id)
                
                # Update state
                self._current_character = character
                self._last_saved = datetime.now()
                
                # Clear history
                self._undo_stack.clear()
                self._redo_stack.clear()
                
                # Update state and notify
                await self.update_state(
                    'current_character',
                    character,
                    metadata={'path': str(path)}
                )
                
                return Result(True, "Character loaded successfully", character)
                
        except Exception as e:
            self.error_handler.handle_error(
                e, ErrorCategory.STATE, ErrorLevel.ERROR,
                {'operation': 'load_character', 'path': str(path)}
            )
            return Result(False, f"Failed to load character: {str(e)}", error=e)

    async def save_character(self, 
                           path: Optional[PathLike] = None,
                           create_backup: bool = True) -> Result[Path]:
        """Save current character with proper locking and validation"""
        if not self._current_character:
            return Result(False, "No character to save")
            
        async with self._save_lock:
            try:
                async with self.operation('save_character', {
                    'path': str(path) if path else None,
                    'create_backup': create_backup
                }):
                    # Validate before saving
                    validation = await self._validate_character(self._current_character)
                    if not validation.success:
                        return validation
                    
                    # Get save path
                    save_path = Path(path) if path else await self._get_default_path()
                    
                    # Save character
                    save_result = await self.file_service.save_character(
                        self._current_character,
                        save_path,
                        create_backup=create_backup
                    )
                    
                    if not save_result.success:
                        return save_result
                    
                    # Update state
                    self._last_saved = datetime.now()
                    self._modified_fields.clear()
                    
                    await self.update_state(
                        'last_saved',
                        self._last_saved,
                        metadata={'path': str(save_path)}
                    )
                    
                    return Result(True, "Character saved successfully", save_path)
                    
            except Exception as e:
                self.error_handler.handle_error(
                    e, ErrorCategory.STATE, ErrorLevel.ERROR,
                    {'operation': 'save_character', 'path': str(path) if path else None}
                )
                return Result(False, f"Failed to save character: {str(e)}", error=e)

    async def update_field(self,
                          field_name: str,
                          value: str,
                          validate: bool = True) -> Result:
        """Update character field with validation and history tracking"""
        if not self._current_character:
            return Result(False, "No character loaded")
            
        # Get or create field lock
        if field_name not in self._field_locks:
            self._field_locks[field_name] = asyncio.Lock()
            
        async with self._field_locks[field_name]:
            try:
                async with self.operation('update_field', {
                    'field': field_name,
                    'validate': validate
                }):
                    # Store for undo
                    await self._push_undo_state()
                    
                    # Validate if requested
                    if validate:
                        validation = await self.validation_service.validate_field(
                            field_name,
                            value,
                            {'character_id': str(self._current_character.id)}
                        )
                        if not validation.success:
                            return validation
                    
                    # Update field
                    old_value = getattr(self._current_character, field_name)
                    setattr(self._current_character, field_name, value)
                    self._current_character.modified_at = datetime.now()
                    self._modified_fields.add(field_name)
                    
                    # Clear redo stack
                    self._redo_stack.clear()
                    
                    # Record change
                    await self.metadata_manager.record_manual_edit(field_name)
                    
                    # Update state
                    await self.update_state(
                        f'field_{field_name}',
                        value,
                        metadata={
                            'old_value': old_value,
                            'operation': 'manual_edit'
                        }
                    )
                    
                    return Result(True, "Field updated successfully")
                    
            except Exception as e:
                self.error_handler.handle_error(
                    e, ErrorCategory.STATE, ErrorLevel.ERROR,
                    {'operation': 'update_field', 'field': field_name}
                )
                return Result(False, f"Failed to update field: {str(e)}", error=e)

    async def generate_field(self,
                           field_name: str,
                           prompt_name: str,
                           context: Optional[JsonDict] = None) -> Result[str]:
        """Queue field generation with proper tracking"""
        if not self._current_character:
            return Result(False, "No character loaded")
            
        async with self._generation_lock:
            try:
                async with self.operation('generate_field', {
                    'field': field_name,
                    'prompt': prompt_name
                }):
                    # Create generation request
                    request = GenerationRequest(
                        field_name=field_name,
                        prompt_name=prompt_name,
                        character_id=str(self._current_character.id),
                        context=context or {},
                        metadata={
                            'character_name': self._current_character.name
                        }
                    )
                    
                    # Queue generation
                    generation_result = await self.generation_service.generate_field(request)
                    if not generation_result.success:
                        return generation_result
                    
                    # Mark field as pending generation
                    self._modified_fields.add(field_name)
                    
                    await self.update_state(
                        f'generation_{field_name}',
                        'pending',
                        metadata={'request_id': generation_result.data}
                    )
                    
                    return Result(True, "Generation queued successfully", generation_result.data)
                    
            except Exception as e:
                self.error_handler.handle_error(
                    e, ErrorCategory.STATE, ErrorLevel.ERROR,
                    {'operation': 'generate_field', 'field': field_name}
                )
                return Result(False, f"Failed to queue generation: {str(e)}", error=e)

    async def handle_generation_result(self,
                                     request_id: str,
                                     content: str) -> Result:
        """Handle completed generation result"""
        if not self._current_character:
            return Result(False, "No character loaded")
            
        try:
            async with self.operation('handle_generation', {'request_id': request_id}):
                # Get generation details
                status = await self.generation_service.get_generation_status(request_id)
                if not status.success:
                    return status
                
                # Update field
                field_name = status.data.field_name
                update_result = await self.update_field(field_name, content)
                if not update_result.success:
                    return update_result
                
                # Record generation in metadata
                await self.metadata_manager.record_generation(
                    field_name=field_name,
                    generation_data=status.data.metadata
                )
                
                return Result(True, "Generation result handled successfully")
                
        except Exception as e:
            self.error_handler.handle_error(
                e, ErrorCategory.STATE, ErrorLevel.ERROR,
                {'operation': 'handle_generation', 'request_id': request_id}
            )
            return Result(False, f"Failed to handle generation result: {str(e)}", error=e)

    async def undo(self) -> Result:
        """Perform undo operation"""
        if not self._undo_stack:
            return Result(False, "Nothing to undo")
            
        try:
            async with self.operation('undo'):
                # Store current state in redo stack
                if self._current_character:
                    self._redo_stack.append(self._current_character.copy())
                
                # Restore previous state
                self._current_character = self._undo_stack.pop()
                
                await self.update_state(
                    'current_character',
                    self._current_character,
                    metadata={'operation': 'undo'}
                )
                
                return Result(True, "Undo successful")
                
        except Exception as e:
            self.error_handler.handle_error(
                e, ErrorCategory.STATE, ErrorLevel.ERROR,
                {'operation': 'undo'}
            )
            return Result(False, f"Failed to undo: {str(e)}", error=e)

    async def redo(self) -> Result:
        """Perform redo operation"""
        if not self._redo_stack:
            return Result(False, "Nothing to redo")
            
        try:
            async with self.operation('redo'):
                # Store current state in undo stack
                if self._current_character:
                    self._undo_stack.append(self._current_character.copy())
                
                # Restore next state
                self._current_character = self._redo_stack.pop()
                
                await self.update_state(
                    'current_character',
                    self._current_character,
                    metadata={'operation': 'redo'}
                )
                
                return Result(True, "Redo successful")
                
        except Exception as e:
            self.error_handler.handle_error(
                e, ErrorCategory.STATE, ErrorLevel.ERROR,
                {'operation': 'redo'}
            )
            return Result(False, f"Failed to redo: {str(e)}", error=e)

    async def _validate_character(self, character: CharacterData) -> Result:
        """Validate character data"""
        try:
            # Validate required fields
            if not character.name:
                return Result(False, "Character name is required")
                
            # Validate each field
            for field_name, value in character.__dict__.items():
                if field_name.startswith('_'):
                    continue
                    
                validation = await self.validation_service.validate_field(
                    field_name,
                    value,
                    {'character_id': str(character.id)}
                )
                if not validation.success:
                    return validation
            
            return Result(True, "Character validation successful")
            
        except Exception as e:
            self.error_handler.handle_error(
                e, ErrorCategory.VALIDATION, ErrorLevel.ERROR,
                {'operation': 'validate_character'}
            )
            return Result(False, f"Character validation failed: {str(e)}", error=e)

    async def _clear_current_state(self):
        """Clear current character state"""
        self._current_character = None
        self._modified_fields.clear()
        self._last_saved = None
        self._undo_stack.clear()
        self._redo_stack.clear()

    async def _push_undo_state(self):
        """Push current state to undo stack"""
        if self._current_character:
            self._undo_stack.append(self._current_character.copy())
            while len(self._undo_stack) > self._max_history:
                self._undo_stack.pop(0)

    async def _get_default_path(self) -> Path:
        """Get default save path for current character"""
        if not self._current_character:
            raise StateError("No character loaded")
            
        safe_name = "".join(
            c for c in self._current_character.name 
            if c.isalnum() or c in (' ', '-', '_')
        ).strip().replace(' ', '_')
        
        return self.file_service.get_save_directory() / f"{safe_name}.json"

    def has_unsaved_changes(self) -> bool:
        """Check if there are unsaved changes"""
        return bool(self._modified_fields)

    def can_undo(self) -> bool:
        """Check if undo is available"""
        return bool(self._undo_stack)

    def can_redo(self) -> bool:
        """Check if redo is available"""
        return bool(self._redo_stack)

    def get_modified_fields(self) -> Set[str]:
        """Get set of modified fields"""
        return self._modified_fields.copy()