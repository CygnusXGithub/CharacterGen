# core/services/character_handler.py
"""Service for managing character data operations."""
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Set
from pathlib import Path
from datetime import datetime
import asyncio
import logging

from ..common.types import (
    BaseModel, JsonDict, Result,
    PathLike, ChangeType
)
from ..models.character import CharacterData, CharacterMetadata
from ..models.image import ImageData
from ..models.prompts import PromptSet
from ..errors import ErrorHandler, ErrorCategory, ErrorLevel
from .file import FileService
from .validation import ValidationService
from .generation import GenerationService, GenerationRequest
from .versioning import VersioningService

@dataclass
class CharacterOperationContext(BaseModel):
    """Context for character operations."""
    operation: str
    character_id: str
    metadata: JsonDict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

class CharacterDataHandler:
    """Handles character data operations and lifecycle management."""
    
    def __init__(self,
                 file_service: FileService,
                 validation_service: ValidationService,
                 generation_service: GenerationService,
                 versioning_service: VersioningService,
                 error_handler: ErrorHandler):
        self.file_service = file_service
        self.validation_service = validation_service
        self.generation_service = generation_service
        self.versioning_service = versioning_service
        self.error_handler = error_handler
        self.logger = logging.getLogger(__name__)
        
        # Cache management
        self._character_cache: Dict[str, CharacterData] = {}
        self._modified_fields: Dict[str, Set[str]] = {}
        self._last_saved: Dict[str, datetime] = {}
        
        # Operation locks
        self._file_lock = asyncio.Lock()
        self._operation_locks: Dict[str, asyncio.Lock] = {}

    async def load_character(self,
                           path: PathLike,
                           validate: bool = True) -> Result[CharacterData]:
        """Load character from file."""
        try:
            path = Path(path)
            async with self._file_lock:
                # Read file content
                load_result = await self.file_service.load_character(path)
                if not load_result.success:
                    return load_result
                
                character = load_result.data
                
                # Validate if requested
                if validate:
                    validation = await self._validate_character(character)
                    if not validation.success:
                        return validation
                
                # Cache character
                self._character_cache[str(character.id)] = character
                self._last_saved[str(character.id)] = datetime.now()
                
                self.logger.info(f"Character loaded: {character.name}")
                return Result(True, "Character loaded successfully", character)
                
        except Exception as e:
            self.error_handler.handle_error(
                e,
                ErrorCategory.FILE,
                ErrorLevel.ERROR,
                {'operation': 'load_character', 'path': str(path)}
            )
            return Result(False, f"Failed to load character: {str(e)}", error=e)

    async def save_character(self,
                           character: CharacterData,
                           path: Optional[PathLike] = None,
                           create_backup: bool = True) -> Result[Path]:
        """Save character to file."""
        try:
            # Get operation lock for this character
            char_id = str(character.id)
            if char_id not in self._operation_locks:
                self._operation_locks[char_id] = asyncio.Lock()
            
            async with self._operation_locks[char_id]:
                # Validate before saving
                validation = await self._validate_character(character)
                if not validation.success:
                    return validation
                
                # Determine save path
                if path is None:
                    path = self._get_default_path(character)
                
                # Record save operation
                save_context = CharacterOperationContext(
                    operation='save',
                    character_id=char_id,
                    metadata={'path': str(path)}
                )
                
                # Update metadata
                character._charactergen_metadata.update({
                    "last_saved": datetime.now().isoformat(),
                    "last_modified_with": "CharacterGen",
                    "save_path": str(path)
                })
                
                # Save character
                save_result = await self.file_service.save_character(
                    character,
                    path,
                    create_backup=create_backup
                )
                
                if not save_result.success:
                    return save_result
                
                # Update cache and state
                self._character_cache[char_id] = character
                self._last_saved[char_id] = datetime.now()
                self._modified_fields.pop(char_id, None)
                
                self.logger.info(f"Character saved: {character.name}")
                return Result(True, "Character saved successfully", save_result.data)
                
        except Exception as e:
            self.error_handler.handle_error(
                e,
                ErrorCategory.FILE,
                ErrorLevel.ERROR,
                {'operation': 'save_character', 'character': character.name}
            )
            return Result(False, f"Failed to save character: {str(e)}", error=e)

    async def generate_field(self,
                           character: CharacterData,
                           field_name: str,
                           prompt_set: PromptSet,
                           context: Optional[JsonDict] = None) -> Result[str]:
        """Generate content for a character field."""
        try:
            char_id = str(character.id)
            async with self._operation_locks.get(char_id, asyncio.Lock()):
                # Prepare generation request
                request = GenerationRequest(
                    field_name=field_name,
                    prompt_set=prompt_set,
                    input_context=context or {},
                    metadata={
                        'character_id': char_id,
                        'character_name': character.name
                    }
                )
                
                # Queue generation
                generation_result = await self.generation_service.generate_field(request)
                if not generation_result.success:
                    return generation_result
                
                # Mark field as modified
                if char_id not in self._modified_fields:
                    self._modified_fields[char_id] = set()
                self._modified_fields[char_id].add(field_name)
                
                # Record generation in version history
                await self.versioning_service.record_generation(
                    character,
                    field_name,
                    {'request_id': generation_result.data}
                )
                
                self.logger.info(f"Field generation queued: {field_name} for {character.name}")
                return generation_result
                
        except Exception as e:
            self.error_handler.handle_error(
                e,
                ErrorCategory.GENERATION,
                ErrorLevel.ERROR,
                {
                    'operation': 'generate_field',
                    'character': character.name,
                    'field': field_name
                }
            )
            return Result(False, f"Failed to generate field: {str(e)}", error=e)

    async def update_field(self,
                          character: CharacterData,
                          field_name: str,
                          value: str,
                          validate: bool = True) -> Result:
        """Update a character field."""
        try:
            char_id = str(character.id)
            async with self._operation_locks.get(char_id, asyncio.Lock()):
                # Validate if requested
                if validate:
                    validation = await self.validation_service.validate_field(
                        field_name,
                        value,
                        {'character_id': char_id}
                    )
                    if not validation.success:
                        return validation
                
                # Update field
                setattr(character, field_name, value)
                character.modified_at = datetime.now()
                
                # Mark as modified
                if char_id not in self._modified_fields:
                    self._modified_fields[char_id] = set()
                self._modified_fields[char_id].add(field_name)
                
                # Record change
                await self.versioning_service.record_manual_edit(
                    character,
                    [field_name],
                    f"Manual update to {field_name}"
                )
                
                self.logger.info(f"Field updated: {field_name} for {character.name}")
                return Result(True, "Field updated successfully")
                
        except Exception as e:
            self.error_handler.handle_error(
                e,
                ErrorCategory.STATE,
                ErrorLevel.ERROR,
                {
                    'operation': 'update_field',
                    'character': character.name,
                    'field': field_name
                }
            )
            return Result(False, f"Failed to update field: {str(e)}", error=e)

    async def _validate_character(self, character: CharacterData) -> Result:
        """Validate character data."""
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
                e,
                ErrorCategory.VALIDATION,
                ErrorLevel.ERROR,
                {'operation': 'validate_character', 'character': character.name}
            )
            return Result(False, f"Character validation failed: {str(e)}", error=e)

    def _get_default_path(self, character: CharacterData) -> Path:
        """Get default save path for character."""
        safe_name = "".join(c for c in character.name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_name = safe_name.replace(' ', '_')
        return self.file_service.get_save_directory() / f"{safe_name}.json"

    async def create_character(self, name: str) -> Result[CharacterData]:
        """Create a new character."""
        try:
            # Create character
            character = CharacterData.create_empty()
            character.name = name
            
            # Initial validation
            validation = await self._validate_character(character)
            if not validation.success:
                return validation
            
            # Cache character
            self._character_cache[str(character.id)] = character
            self._modified_fields[str(character.id)] = {'name'}
            
            self.logger.info(f"Character created: {name}")
            return Result(True, "Character created successfully", character)
            
        except Exception as e:
            self.error_handler.handle_error(
                e,
                ErrorCategory.STATE,
                ErrorLevel.ERROR,
                {'operation': 'create_character', 'name': name}
            )
            return Result(False, f"Failed to create character: {str(e)}", error=e)

    def has_unsaved_changes(self, character_id: str) -> bool:
        """Check if character has unsaved changes."""
        return character_id in self._modified_fields and bool(self._modified_fields[character_id])

    def get_modified_fields(self, character_id: str) -> Set[str]:
        """Get set of modified fields for character."""
        return self._modified_fields.get(character_id, set())

    async def handle_generation_result(self, 
                                     character_id: str,
                                     request_id: str,
                                     content: str) -> Result:
        """Handle completed generation result."""
        try:
            character = self._character_cache.get(character_id)
            if not character:
                return Result(False, f"Character not found: {character_id}")
            
            # Get generation details
            status = await self.generation_service.get_generation_status(request_id)
            if not status.success:
                return status
            
            # Update character field
            field_name = status.data.field_name
            return await self.update_field(character, field_name, content)
            
        except Exception as e:
            self.error_handler.handle_error(
                e,
                ErrorCategory.GENERATION,
                ErrorLevel.ERROR,
                {
                    'operation': 'handle_generation_result',
                    'character_id': character_id,
                    'request_id': request_id
                }
            )
            return Result(False, f"Failed to handle generation result: {str(e)}", error=e)