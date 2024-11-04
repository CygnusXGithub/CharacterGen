# core/models/metadata.py
"""Metadata models for tracking generation and field information."""
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from ..common.types import (
    BaseModel, JsonDict, Timestamp,
    Result
)

@dataclass
class GenerationMetadata(BaseModel):
    """Metadata for a single generation operation."""
    field_name: str
    prompt_used: str
    input_context: JsonDict
    result: str
    base_prompt_name: str
    base_prompt_version: str
    generation_settings: JsonDict = field(default_factory=dict)
    dependencies: Dict[str, str] = field(default_factory=dict)
    duration_ms: Optional[int] = None
    
    def to_dict(self) -> JsonDict:
        """Convert metadata to dictionary format."""
        data = super().to_dict()
        data.update({
            'field_name': self.field_name,
            'prompt_used': self.prompt_used,
            'input_context': self.input_context,
            'result': self.result,
            'base_prompt_name': self.base_prompt_name,
            'base_prompt_version': self.base_prompt_version,
            'generation_settings': self.generation_settings,
            'dependencies': self.dependencies,
            'duration_ms': self.duration_ms
        })
        return data

@dataclass
class FieldMetadata(BaseModel):
    """Metadata for a character field."""
    field_name: str
    last_generated: Optional[Timestamp] = None
    generation_history: List[GenerationMetadata] = field(default_factory=list)
    manual_edits: List[Timestamp] = field(default_factory=list)
    base_prompt_used: Optional[str] = None
    custom_context: JsonDict = field(default_factory=dict)
    
    def add_generation(self, metadata: GenerationMetadata) -> Result:
        """Add generation metadata to history."""
        try:
            self.generation_history.append(metadata)
            self.last_generated = Timestamp.now()
            self.modified_at = Timestamp.now()
            return Result(True, "Generation metadata added successfully")
        except Exception as e:
            return Result(False, f"Failed to add generation metadata: {str(e)}", error=e)
    
    def record_manual_edit(self) -> Result:
        """Record a manual edit."""
        try:
            self.manual_edits.append(Timestamp.now())
            self.modified_at = Timestamp.now()
            return Result(True, "Manual edit recorded successfully")
        except Exception as e:
            return Result(False, f"Failed to record manual edit: {str(e)}", error=e)
    
    def to_dict(self) -> JsonDict:
        """Convert metadata to dictionary format."""
        data = super().to_dict()
        data.update({
            'field_name': self.field_name,
            'last_generated': self.last_generated.isoformat() if self.last_generated else None,
            'generation_history': [g.to_dict() for g in self.generation_history],
            'manual_edits': [t.isoformat() for t in self.manual_edits],
            'base_prompt_used': self.base_prompt_used,
            'custom_context': self.custom_context
        })
        return data

@dataclass
class BasePromptMetadata(BaseModel):
    """Metadata for base prompts."""
    name: str
    version: str
    use_count: int = 0
    last_used: Optional[Timestamp] = None
    average_generation_time: Optional[float] = None
    custom_settings: JsonDict = field(default_factory=dict)
    
    def record_use(self, duration_ms: Optional[int] = None) -> Result:
        """Record prompt usage with timing."""
        try:
            self.use_count += 1
            self.last_used = Timestamp.now()
            
            if duration_ms is not None:
                if self.average_generation_time is None:
                    self.average_generation_time = float(duration_ms)
                else:
                    # Update running average
                    self.average_generation_time = (
                        (self.average_generation_time * (self.use_count - 1) + duration_ms)
                        / self.use_count
                    )
            
            return Result(True, "Prompt usage recorded successfully")
        except Exception as e:
            return Result(False, f"Failed to record prompt usage: {str(e)}", error=e)
    
    def to_dict(self) -> JsonDict:
        """Convert metadata to dictionary format."""
        data = super().to_dict()
        data.update({
            'name': self.name,
            'version': self.version,
            'use_count': self.use_count,
            'last_used': self.last_used.isoformat() if self.last_used else None,
            'average_generation_time': self.average_generation_time,
            'custom_settings': self.custom_settings
        })
        return data

@dataclass
class CharacterMetadata(BaseModel):
    """Complete character metadata."""
    character_id: str
    field_metadata: Dict[str, FieldMetadata] = field(default_factory=dict)
    base_prompts_used: List[BasePromptMetadata] = field(default_factory=list)
    generation_settings_history: List[JsonDict] = field(default_factory=list)
    custom_data: JsonDict = field(default_factory=dict)
    
    def get_field_metadata(self, field_name: str) -> FieldMetadata:
        """Get or create field metadata."""
        if field_name not in self.field_metadata:
            self.field_metadata[field_name] = FieldMetadata(field_name=field_name)
        return self.field_metadata[field_name]
    
    def update_prompt_stats(self, 
                          prompt_name: str,
                          version: str,
                          duration_ms: Optional[int] = None) -> Result:
        """Update prompt usage statistics."""
        try:
            prompt = next(
                (p for p in self.base_prompts_used 
                 if p.name == prompt_name and p.version == version),
                None
            )
            
            if not prompt:
                prompt = BasePromptMetadata(name=prompt_name, version=version)
                self.base_prompts_used.append(prompt)
            
            return prompt.record_use(duration_ms)
            
        except Exception as e:
            return Result(False, f"Failed to update prompt stats: {str(e)}", error=e)