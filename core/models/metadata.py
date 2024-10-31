from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from uuid import UUID, uuid4

@dataclass
class GenerationMetadata:
    """Metadata for a single generation operation"""
    field_name: str
    prompt_used: str
    input_context: Dict[str, Any]
    result: str
    base_prompt_name: str
    base_prompt_version: str
    id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=datetime.now)
    generation_settings: Dict[str, Any] = field(default_factory=dict)
    dependencies: Dict[str, str] = field(default_factory=dict)  # field_name -> value
    duration_ms: Optional[int] = None

@dataclass
class FieldMetadata:
    """Metadata for a character field"""
    field_name: str
    last_generated: Optional[datetime] = None
    generation_history: List[GenerationMetadata] = field(default_factory=list)
    manual_edits: List[datetime] = field(default_factory=list)
    base_prompt_used: Optional[str] = None
    custom_context: Dict[str, Any] = field(default_factory=dict)

@dataclass
class BasePromptMetadata:
    """Metadata for base prompts"""
    name: str
    version: str
    created_at: datetime = field(default_factory=datetime.now)
    last_used: Optional[datetime] = None
    use_count: int = 0
    average_generation_time: Optional[float] = None
    custom_settings: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CharacterMetadata:
    """Complete character metadata"""
    character_id: UUID
    created_at: datetime = field(default_factory=datetime.now)
    modified_at: datetime = field(default_factory=datetime.now)
    field_metadata: Dict[str, FieldMetadata] = field(default_factory=dict)
    base_prompts_used: List[BasePromptMetadata] = field(default_factory=list)
    generation_settings_history: List[Dict[str, Any]] = field(default_factory=list)
    custom_data: Dict[str, Any] = field(default_factory=dict)