from dataclasses import dataclass, field, replace
from typing import Dict, List, Optional, Any
from datetime import datetime
from uuid import UUID, uuid4
import copy

@dataclass
class CharacterGenMetadata:
    """Our application-specific metadata"""
    generation_history: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    last_validated: Optional[datetime] = None
    validation_state: Dict[str, Any] = field(default_factory=dict)
    custom_settings: Dict[str, Any] = field(default_factory=dict)

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
    _charactergen_metadata: Optional[CharacterGenMetadata] = field(default=None, repr=False)
    
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
        return {
            "data": {
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
                    # Preserve any existing extensions when reading files
                    **(self._extensions or {}),
                    # Add our own metadata
                    "charactergen": self._charactergen_metadata.__dict__ if self._charactergen_metadata else {}
                }
            },
            "spec": "chara_card_v2",
            "spec_version": "2.0"
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CharacterData':
        """Create from template format"""
        # Handle both full template and partial data
        if "data" in data:
            char_data = data["data"]
        else:
            char_data = data
            
        # Extract non-extension fields that match our dataclass
        fields = {k: v for k, v in char_data.items() 
                if k != 'extensions' and hasattr(cls, k)}
        
        # Create instance
        instance = cls(**fields)
        
        # Handle extensions if they exist
        if 'extensions' in char_data and char_data['extensions'] is not None:
            extensions = char_data['extensions']
            # Store non-charactergen extensions
            instance._extensions = {k: v for k, v in extensions.items() 
                                if k != 'charactergen'}
            
            # Handle charactergen metadata
            if 'charactergen' in extensions:
                instance._charactergen_metadata = CharacterGenMetadata(
                    **extensions['charactergen']
                )
        
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