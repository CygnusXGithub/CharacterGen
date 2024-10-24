from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any, Union, Callable
from datetime import datetime
from PIL import Image
from .exceptions import MismatchedTagError
from .enums import FieldName, CardFormat, GenerationMode, PromptTagType

@dataclass
class CharacterData:
    """Container for character data and metadata"""
    name: str
    fields: Dict[FieldName, str] = field(default_factory=dict)
    image_data: Optional[Image.Image] = None
    alternate_greetings: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    creator: str = "Anonymous"
    version: str = "main"
    created_at: datetime = field(default_factory=datetime.now)
    modified_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for saving"""
        return {
            "data": {
                "name": self.name,
                **{field.value: value for field, value in self.fields.items()},
                "alternate_greetings": self.alternate_greetings,
                "tags": self.tags,
                "creator": self.creator,
                "character_version": self.version,
                "created_at": self.created_at.isoformat(),
                "modified_at": self.modified_at.isoformat()
            },
            "spec": "chara_card_v2",
            "spec_version": "2.0"
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CharacterData':
        """Create instance from dictionary data"""
        card_data = data.get("data", {})
        return cls(
            name=card_data.get("name", ""),
            fields={
                field: card_data.get(field.value, "")
                for field in FieldName
                if field.value in card_data
            },
            alternate_greetings=card_data.get("alternate_greetings", []),
            tags=card_data.get("tags", []),
            creator=card_data.get("creator", "Anonymous"),
            version=card_data.get("character_version", "main"),
            created_at=datetime.fromisoformat(card_data.get("created_at", datetime.now().isoformat())),
            modified_at=datetime.fromisoformat(card_data.get("modified_at", datetime.now().isoformat()))
        )

@dataclass
class PromptTemplate:
    """Template for generating character fields"""
    text: str
    field: FieldName
    generation_order: int
    required_fields: Set[FieldName] = field(default_factory=set)
    conditional_tags: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        self._validate_tags()
        self._extract_required_fields()
    
    def _validate_tags(self) -> None:
        """Validate template tags"""
        # Count opening and closing conditional tags
        open_tags = self.text.count("{{if_input}}")
        close_tags = self.text.count("{{/if_input}}")
        
        if open_tags != close_tags:
            raise MismatchedTagError(
                f"Mismatched conditional tags: {open_tags} opening tags, {close_tags} closing tags"
            )
    
    def _extract_required_fields(self) -> None:
        """Extract required fields from template text"""
        import re
        field_tags = re.findall(r'{{(\w+)}}', self.text)
        
        for tag in field_tags:
            try:
                if tag not in ['input', 'if_input', '/if_input', 'char', 'user']:
                    self.required_fields.add(FieldName(tag))
            except ValueError:
                pass

@dataclass
class PromptSet:
    """Collection of prompt templates"""
    name: str
    templates: Dict[FieldName, PromptTemplate]
    description: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    modified_at: datetime = field(default_factory=datetime.now)
    
    def validate(self) -> bool:
        """Validate prompt set for circular dependencies"""
        # Sort templates by generation order
        ordered_templates = sorted(
            self.templates.values(),
            key=lambda x: x.generation_order
        )
        
        # Check each template only requires fields that come before it
        for template in ordered_templates:
            available_fields = {
                t.field for t in ordered_templates
                if t.generation_order < template.generation_order
            }
            
            if not template.required_fields.issubset(available_fields):
                return False
        
        return True

@dataclass
class GenerationResult:
    """Result of field generation"""
    field: FieldName
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    attempts: int = 1
    error: Optional[Exception] = None
    
    @property
    def success(self) -> bool:
        return self.error is None

@dataclass
class GenerationCallbacks:
    """Callbacks for generation progress and results"""
    on_start: Optional[Callable[[FieldName], None]] = None
    on_progress: Optional[Callable[[FieldName, str], None]] = None
    on_result: Optional[Callable[[FieldName, GenerationResult], None]] = None
    on_error: Optional[Callable[[FieldName, Exception], None]] = None

@dataclass
class GenerationContext:
    """Context for field generation"""
    character_data: CharacterData
    current_field: FieldName
    user_input: str
    generation_mode: GenerationMode = GenerationMode.GENERATE
    max_retries: int = 3
    
    @property
    def available_fields(self) -> Dict[FieldName, str]:
        """Get fields available for use in generation"""
        return {
            field: value
            for field, value in self.character_data.fields.items()
            if field != self.current_field
        }
