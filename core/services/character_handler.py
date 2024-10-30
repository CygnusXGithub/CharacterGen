import json
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID, uuid4

from ..models.character import CharacterData
from ..errors import ErrorHandler, ErrorCategory, ErrorLevel, FileOperationError
from .file import FileService
from .validation import ValidationService, ValidationError

class CharacterDataHandler:
    """Handles character data operations including load/save functionality"""
    
    def __init__(self, 
                 file_service: FileService,
                 validation_service: ValidationService,
                 error_handler: ErrorHandler):
        self.file_service = file_service
        self.validation_service = validation_service
        self.error_handler = error_handler
        
        # Cache of recently accessed characters
        self._character_cache: Dict[UUID, CharacterData] = {}
        self._modified_characters: Dict[UUID, datetime] = {}
        
        # File operation lock
        self._file_lock = asyncio.Lock()

    async def load_character(self, 
                           path: Path,
                           validate: bool = True) -> Optional[CharacterData]:
        """Load character from file"""
        try:
            async with self._file_lock:
                # Read file content
                if not path.exists():
                    raise FileOperationError(f"Character file not found: {path}")
                
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Verify format
                if 'spec' not in data or data['spec'] != 'chara_card_v2':
                    raise FileOperationError("Invalid character format")
                
                # Create character from data
                character = CharacterData.from_dict(data['data'])
                
                # Validate if requested
                if validate:
                    is_valid = await self._validate_character(character)
                    if not is_valid:
                        return None
                
                # Cache character
                self._character_cache[character.id] = character
                return character
                
        except Exception as e:
            self.error_handler.handle_error(
                error=e,
                category=ErrorCategory.FILE,
                level=ErrorLevel.ERROR,
                context={'operation': 'load_character', 'path': str(path)}
            )
            return None

    async def save_character(self, 
                           character: CharacterData,
                           path: Optional[Path] = None) -> Optional[Path]:
        """Save character to file"""
        try:
            async with self._file_lock:
                # Validate before saving
                if not await self._validate_character(character):
                    raise ValidationError("Character validation failed")
                
                # Determine save path
                if path is None:
                    path = self._get_default_path(character)
                
                # Ensure directory exists
                self.file_service.ensure_directory(path.parent)
                
                # Update metadata
                character._charactergen_metadata.update({
                    "version": "1.0",
                    "created_with": "CharacterGen",
                    "last_modified_with": "CharacterGen",
                    "last_modified": datetime.now().isoformat()
                })
                
                # Convert to dict and save
                data = character.to_dict()  # This now includes proper JSON-serializable metadata
                
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                # Update cache and modified state
                self._character_cache[character.id] = character
                self._modified_characters.pop(character.id, None)
                
                return path
                
        except Exception as e:
            self.error_handler.handle_error(
                error=e,
                category=ErrorCategory.FILE,
                level=ErrorLevel.ERROR,
                context={'operation': 'save_character', 'path': str(path) if path else None}
            )
            return None

    async def _validate_character(self, character: CharacterData) -> bool:
        """Validate character data"""
        try:
            # Required fields
            if not character.name:
                return False
                
            # Validate each field
            for field_name, value in character.__dict__.items():
                if field_name.startswith('_'):
                    continue
                    
                result = await self.validation_service.validate_field(
                    field_name, value
                )
                if not result.is_valid:
                    return False
            
            return True
            
        except Exception as e:
            self.error_handler.handle_error(
                error=e,
                category=ErrorCategory.VALIDATION,
                level=ErrorLevel.ERROR,
                context={'operation': 'validate_character'}
            )
            return False

    def mark_modified(self, character_id: UUID):
        """Mark character as modified"""
        self._modified_characters[character_id] = datetime.now()

    def is_modified(self, character_id: UUID) -> bool:
        """Check if character has unsaved changes"""
        return character_id in self._modified_characters

    def get_cached_character(self, character_id: UUID) -> Optional[CharacterData]:
        """Get character from cache"""
        return self._character_cache.get(character_id)

    def clear_cache(self):
        """Clear character cache"""
        self._character_cache.clear()
        self._modified_characters.clear()

    async def create_character(self, name: str) -> CharacterData:
        """Create a new character"""
        try:
            character = CharacterData(
                name=name,
                id=uuid4(),
                created_at=datetime.now(),
                modified_at=datetime.now()
            )
            
            # Initialize CharacterGen metadata
            character._charactergen_metadata = {
                "version": "1.0",
                "created_with": "CharacterGen",
                "last_modified_with": "CharacterGen"
            }
            
            # Cache new character
            self._character_cache[character.id] = character
            self.mark_modified(character.id)
            
            return character
            
        except Exception as e:
            self.error_handler.handle_error(
                error=e,
                category=ErrorCategory.STATE,
                level=ErrorLevel.ERROR,
                context={'operation': 'create_character', 'name': name}
            )
            raise

    def _get_default_path(self, character: CharacterData) -> Path:
        """Get default save path for character"""
        base_dir = self.file_service.get_save_directory()
        safe_name = "".join(c for c in character.name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_name = safe_name.replace(' ', '_')
        return base_dir / f"{safe_name}.json"

    async def export_character(self, 
                             character: CharacterData,
                             path: Path,
                             include_metadata: bool = True) -> Optional[Path]:
        """Export character to file"""
        try:
            async with self._file_lock:
                # Get character data as dict
                data = character.to_dict()
                
                if not include_metadata:
                    # Remove CharacterGen metadata while preserving other extensions
                    extensions = data['data'].get('extensions', {})
                    if 'charactergen' in extensions:
                        del extensions['charactergen']
                    data['data']['extensions'] = extensions
                
                # Ensure directory exists
                self.file_service.ensure_directory(path.parent)
                
                # Save to file
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                return path
                
        except Exception as e:
            self.error_handler.handle_error(
                error=e,
                category=ErrorCategory.FILE,
                level=ErrorLevel.ERROR,
                context={'operation': 'export_character', 'path': str(path)}
            )
            return None