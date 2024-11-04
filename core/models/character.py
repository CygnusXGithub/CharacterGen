# core/models/character.py
"""Character data model and related types."""
from dataclasses import dataclass, field
from typing import Any, List, Dict, Optional, Set
import copy

from ..common.types import (
    BaseModel, JsonDict, ChangeType,
    Result, Timestamp
)
from .versioning import VersionHistory, VersionChange

@dataclass
class CharacterMetadata(BaseModel):
    """Metadata specific to character generation."""
    version_history: VersionHistory = field(default_factory=VersionHistory)
    generation_history: Dict[str, List[JsonDict]] = field(default_factory=dict)
    last_validated: Optional[Timestamp] = None
    validation_state: JsonDict = field(default_factory=dict)
    custom_settings: JsonDict = field(default_factory=dict)
    created_with: str = "CharacterGen"
    
    def update(self, data: JsonDict) -> Result:
        """Update metadata fields."""
        try:
            for key, value in data.items():
                if hasattr(self, key):
                    setattr(self, key, value)
                else:
                    self.custom_settings[key] = value
            return Result(True, "Metadata updated successfully")
        except Exception as e:
            return Result(False, f"Failed to update metadata: {str(e)}", error=e)

    def to_dict(self) -> JsonDict:
        """Convert metadata to dictionary."""
        data = super().to_dict()
        data.update({
            "generation_history": self.generation_history,
            "last_validated": self.last_validated.isoformat() if self.last_validated else None,
            "validation_state": self.validation_state,
            "custom_settings": self.custom_settings,
            "created_with": self.created_with,
            "version_history": self.version_history.to_dict()
        })
        return data

    @classmethod
    def from_dict(cls, data: JsonDict) -> 'CharacterMetadata':
        """Create metadata from dictionary."""
        if data is None:
            return cls()

        base_data = {
            'id': data.get('id', None),
            'created_at': data.get('created_at', None),
            'modified_at': data.get('modified_at', None)
        }

        version_history = VersionHistory.from_dict(data['version_history']) if 'version_history' in data else VersionHistory()

        return cls(
            **base_data,
            version_history=version_history,
            generation_history=data.get('generation_history', {}),
            last_validated=Timestamp.fromisoformat(data['last_validated']) if data.get('last_validated') else None,
            validation_state=data.get('validation_state', {}),
            custom_settings=data.get('custom_settings', {}),
            created_with=data.get('created_with', "CharacterGen")
        )

@dataclass
class CharacterData(BaseModel):
    """Character data container."""
    # Required fields
    name: str = ""
    description: str = ""
    personality: str = ""
    first_mes: str = ""
    avatar: str = "none"
    mes_example: str = ""
    scenario: str = ""
    creator_notes: str = ""
    system_prompt: str = ""
    post_history_instructions: str = ""
    
    # Optional fields
    alternate_greetings: List[str] = field(default_factory=list)
    tags: Set[str] = field(default_factory=set)
    creator: str = "Anonymous"
    character_version: str = "1.0.0"
    
    # Private fields for extension handling
    _extensions: Dict[str, Any] = field(default_factory=dict, repr=False)
    _charactergen_metadata: CharacterMetadata = field(
        default_factory=CharacterMetadata,
        repr=False
    )
    
    def copy(self) -> 'CharacterData':
        """Create a deep copy of the character data."""
        new_char = copy.deepcopy(self)
        new_char.modified_at = Timestamp.now()
        return new_char
    
    def validate(self) -> Result:
        """Validate character data."""
        try:
            if not self.name:
                return Result(False, "Character name is required")
            if not self.first_mes:
                return Result(False, "First message is required")
                
            # Add more validation as needed
            return Result(True, "Character data is valid")
        except Exception as e:
            return Result(False, f"Validation error: {str(e)}", error=e)
    
    def to_dict(self) -> JsonDict:
        """Convert to template format."""
        base_data = super().to_dict()
        char_data = {
            "name": self.name,
            "description": self.description,
            "personality": self.personality,
            "first_mes": self.first_mes,
            "avatar": self.avatar,
            "mes_example": self.mes_example,
            "scenario": self.scenario,
            "creator_notes": self.creator_notes,
            "system_prompt": self.system_prompt,
            "post_history_instructions": self.post_history_instructions,
            "alternate_greetings": list(self.alternate_greetings),
            "tags": list(self.tags),
            "creator": self.creator,
            "character_version": self.character_version,
            "extensions": {
                **self._extensions,
                "charactergen": self._charactergen_metadata.to_dict()
            }
        }

        return {
            "spec": "chara_card_v2",
            "spec_version": "2.0",
            "data": char_data,
            "base": base_data
        }
    
    @classmethod
    def from_dict(cls, data: JsonDict) -> 'CharacterData':
        """Create from template format."""
        # Extract the actual character data
        char_data = data.get('data', data)
        base_data = data.get('base', {})
        
        # Create instance with base data
        instance = cls(
            id=base_data.get('id'),
            created_at=base_data.get('created_at'),
            modified_at=base_data.get('modified_at'),
            
            # Character fields
            name=char_data.get('name', ''),
            description=char_data.get('description', ''),
            personality=char_data.get('personality', ''),
            first_mes=char_data.get('first_mes', ''),
            avatar=char_data.get('avatar', 'none'),
            mes_example=char_data.get('mes_example', ''),
            scenario=char_data.get('scenario', ''),
            creator_notes=char_data.get('creator_notes', ''),
            system_prompt=char_data.get('system_prompt', ''),
            post_history_instructions=char_data.get('post_history_instructions', ''),
            alternate_greetings=set(char_data.get('alternate_greetings', [])),
            tags=set(char_data.get('tags', [])),
            creator=char_data.get('creator', 'Anonymous'),
            character_version=char_data.get('character_version', '1.0.0')
        )
        
        # Handle extensions
        extensions = char_data.get('extensions', {})
        instance._extensions = {
            k: v for k, v in extensions.items() 
            if k != 'charactergen'
        }
        
        # Handle CharacterGen metadata
        charactergen_data = extensions.get('charactergen', {})
        if charactergen_data:
            instance._charactergen_metadata = CharacterMetadata.from_dict(charactergen_data)
        
        return instance
    
    @classmethod
    def create_empty(cls) -> 'CharacterData':
        """Create a new empty character with default values."""
        return cls(_charactergen_metadata=CharacterMetadata())

    def record_change(self,
                     change_type: ChangeType,
                     fields: List[str],
                     description: str,
                     metadata: Optional[JsonDict] = None) -> Result[VersionChange]:
        """Record a change to the character."""
        result = self._charactergen_metadata.version_history.add_change(
            change_type=change_type,
            fields=fields,
            description=description,
            metadata=metadata
        )
        
        if result.success:
            self.modified_at = Timestamp.now()
            
        return result
    
    def get_field_history(self, field_name: str) -> List[VersionChange]:
        """Get version history for a field."""
        return self._charactergen_metadata.version_history.get_field_history(field_name)
    
    def get_current_version(self) -> int:
        """Get current version number."""
        return self._charactergen_metadata.version_history.current_version