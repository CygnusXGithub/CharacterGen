from dataclasses import dataclass, field, replace
from typing import Dict, List, Optional, Any
from datetime import datetime
from uuid import UUID, uuid4
import copy

@dataclass
class CharacterGenMetadata:
    """Metadata specific to our application"""
    generation_history: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    last_validated: Optional[datetime] = None
    validation_state: Dict[str, Any] = field(default_factory=dict)
    custom_settings: Dict[str, Any] = field(default_factory=dict)
    version: str = "1.0"
    created_with: str = "CharacterGen"
    last_modified_with: str = "CharacterGen"
    last_modified: Optional[str] = None

    def update(self, data: Dict[str, Any]):
        """Update metadata fields"""
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                self.custom_settings[key] = value

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary"""
        return {
            "generation_history": self.generation_history,
            "last_validated": self.last_validated.isoformat() if self.last_validated else None,
            "validation_state": self.validation_state,
            "custom_settings": self.custom_settings,
            "version": self.version,
            "created_with": self.created_with,
            "last_modified_with": self.last_modified_with,
            "last_modified": self.last_modified or datetime.now().isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CharacterGenMetadata':
        """Create metadata from dictionary"""
        if data is None:
            return cls()
            
        return cls(
            generation_history=data.get('generation_history', {}),
            last_validated=datetime.fromisoformat(data['last_validated']) if data.get('last_validated') else None,
            validation_state=data.get('validation_state', {}),
            custom_settings=data.get('custom_settings', {}),
            version=data.get('version', "1.0"),
            created_with=data.get('created_with', "CharacterGen"),
            last_modified_with=data.get('last_modified_with', "CharacterGen"),
            last_modified=data.get('last_modified')
        )

@dataclass
class CharacterData:
    """Core character data structure"""
    # Template-required fields
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
    alternate_greetings: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    creator: str = "Anonymous"
    character_version: str = ""
    
    # Internal tracking fields
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.now)
    modified_at: datetime = field(default_factory=datetime.now)
    
    # Private fields for extension handling
    _extensions: Dict[str, Any] = field(default_factory=dict, repr=False)
    _charactergen_metadata: CharacterGenMetadata = field(
        default_factory=CharacterGenMetadata,
        repr=False
    )
    
    def copy(self) -> 'CharacterData':
        """Create a deep copy of the character data"""
        # Create a new instance with copied basic fields
        new_char = replace(self)
        
        # Deep copy mutable fields
        new_char.alternate_greetings = copy.deepcopy(self.alternate_greetings)
        new_char.tags = copy.deepcopy(self.tags)
        new_char._extensions = copy.deepcopy(self._extensions)
        
        # Copy metadata if it exists
        if self._charactergen_metadata:
            new_char._charactergen_metadata = copy.deepcopy(self._charactergen_metadata)
        
        return new_char
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to template format"""
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
            "alternate_greetings": self.alternate_greetings,
            "tags": self.tags,
            "creator": self.creator,
            "character_version": self.character_version,
            "extensions": {
                **self._extensions,
                "charactergen": self._charactergen_metadata.to_dict()
            }
        }

        return {
            "data": char_data,
            "spec": "chara_card_v2",
            "spec_version": "2.0"
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CharacterData':
        """Create from template format"""
        # Handle both full template and data-only format
        char_data = data.get('data', data)
        
        # Extract base fields
        base_fields = {
            field: char_data.get(field, "") 
            for field in [
                "name", "description", "personality", "first_mes",
                "avatar", "mes_example", "scenario", "creator_notes",
                "system_prompt", "post_history_instructions",
                "creator", "character_version"
            ]
        }
        
        # Handle list fields
        base_fields["alternate_greetings"] = char_data.get("alternate_greetings", [])
        base_fields["tags"] = char_data.get("tags", [])
        
        # Create instance
        instance = cls(**base_fields)
        
        # Handle extensions
        extensions = char_data.get("extensions", {}) or {}  # Handle None case
        instance._extensions = {
            k: v for k, v in extensions.items() 
            if k != "charactergen"
        }
        
        # Handle CharacterGen metadata
        charactergen_data = extensions.get("charactergen", {})
        if charactergen_data is not None:
            instance._charactergen_metadata = CharacterGenMetadata.from_dict(charactergen_data)
        
        return instance
    
    @classmethod
    def create_empty(cls) -> 'CharacterData':
        """Create a new empty character with default values"""
        return cls(
            _charactergen_metadata=CharacterGenMetadata()
        )

@dataclass
class FieldValidationState:
    """Validation state for a single field"""
    is_valid: bool = True
    message: str = ""
    last_validated: Optional[datetime] = None