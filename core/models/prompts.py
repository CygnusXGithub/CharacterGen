# core/models/prompts.py
"""Prompt template and processing system."""
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Set, Optional
import re

from ..common.types import (
    BaseModel, JsonDict, Result,
    ResourceType
)

class PromptTagType(Enum):
    """Types of tags in prompts."""
    FIELD = "field"         # {{name}}, {{description}}, etc.
    CONDITIONAL = "cond"    # {{if_input}}, {{if_name}}, etc.
    INPUT = "input"         # {{input}}
    SYSTEM = "system"       # {{char}}, {{user}}, etc.

@dataclass
class PromptTemplate(BaseModel):
    """Single prompt template with validation and processing."""
    content: str
    field_name: str
    description: str = ""
    required_fields: Set[str] = field(default_factory=set)
    optional_fields: Set[str] = field(default_factory=set)
    system_tags: Set[str] = field(default_factory=set)
    version: str = "1.0"
    
    # Regex patterns for validation
    _field_pattern = re.compile(r'{{(\w+)}}')
    _conditional_pattern = re.compile(r'{{if_(\w+)}}(.*?){{/if_\1}}', re.DOTALL)
    _system_pattern = re.compile(r'{{(char|user)}}')
    
    def validate(self) -> Result:
        """Validate template structure and tags."""
        try:
            # Check for unclosed conditionals
            opens = len(re.findall(r'{{if_\w+}}', self.content))
            closes = len(re.findall(r'{{/if_\w+}}', self.content))
            if opens != closes:
                return Result(False, "Unclosed conditional blocks found")
            
            # Validate all field references exist
            fields = set(self._field_pattern.findall(self.content))
            unknown_fields = fields - (self.required_fields | self.optional_fields)
            if unknown_fields:
                return Result(False, f"Unknown fields referenced: {unknown_fields}")
            
            # Validate system tags
            system_tags = set(self._system_pattern.findall(self.content))
            unknown_tags = system_tags - self.system_tags
            if unknown_tags:
                return Result(False, f"Unknown system tags: {unknown_tags}")
            
            return Result(True, "Template validation successful")
            
        except Exception as e:
            return Result(False, f"Template validation failed: {str(e)}", error=e)
    
    def get_dependencies(self) -> Set[str]:
        """Get all fields this template depends on."""
        fields = set()
        
        # Add explicit fields
        fields.update(self.required_fields)
        fields.update(self.optional_fields)
        
        # Add fields from conditionals
        for match in self._conditional_pattern.finditer(self.content):
            condition = match.group(1)
            if condition != 'input':  # Skip input conditionals
                fields.add(condition)
        
        return fields
    
    def to_dict(self) -> JsonDict:
        """Convert template to dictionary format."""
        data = super().to_dict()
        data.update({
            'content': self.content,
            'field_name': self.field_name,
            'description': self.description,
            'required_fields': list(self.required_fields),
            'optional_fields': list(self.optional_fields),
            'system_tags': list(self.system_tags),
            'version': self.version
        })
        return data

@dataclass
class ProcessedPrompt(BaseModel):
    """Result of processing a prompt template."""
    original_template: PromptTemplate
    processed_content: str
    used_fields: Set[str] = field(default_factory=set)
    missing_required: Set[str] = field(default_factory=set)
    missing_optional: Set[str] = field(default_factory=set)
    used_conditionals: Set[str] = field(default_factory=set)
    
    def is_valid(self) -> bool:
        """Check if processing resulted in a valid prompt."""
        return len(self.missing_required) == 0
    
    def get_validation_message(self) -> str:
        """Get validation status message."""
        if self.is_valid():
            return "Prompt processed successfully"
        return f"Missing required fields: {', '.join(self.missing_required)}"

@dataclass
class PromptSet(BaseModel):
    """Collection of prompts for character generation."""
    name: str
    description: str
    prompts: Dict[str, PromptTemplate]
    generation_order: List[str]
    version: str = "1.0"
    
    def validate(self) -> Result:
        """Validate prompt set configuration."""
        try:
            # Check all prompts exist
            if set(self.prompts.keys()) != set(self.generation_order):
                return Result(False, "Generation order doesn't match available prompts")
            
            # Validate each prompt
            for field_name, prompt in self.prompts.items():
                result = prompt.validate()
                if not result.success:
                    return Result(False, f"Invalid prompt for {field_name}: {result.message}")
            
            # Validate dependencies
            for idx, field in enumerate(self.generation_order):
                prompt = self.prompts[field]
                available_fields = set(self.generation_order[:idx])
                missing_deps = prompt.required_fields - available_fields
                if missing_deps:
                    return Result(False, 
                                f"Field {field} requires unavailable fields: {missing_deps}")
            
            return Result(True, "Prompt set validation successful")
            
        except Exception as e:
            return Result(False, f"Prompt set validation failed: {str(e)}", error=e)
    
    def get_prompt_for_field(self, field_name: str) -> Optional[PromptTemplate]:
        """Get prompt template for a specific field."""
        return self.prompts.get(field_name)
    
    def get_field_dependencies(self, field_name: str) -> Set[str]:
        """Get all dependencies for a field."""
        prompt = self.get_prompt_for_field(field_name)
        return prompt.get_dependencies() if prompt else set()
    
    def to_dict(self) -> JsonDict:
        """Convert prompt set to dictionary format."""
        data = super().to_dict()
        data.update({
            'name': self.name,
            'description': self.description,
            'prompts': {name: prompt.to_dict() 
                       for name, prompt in self.prompts.items()},
            'generation_order': self.generation_order,
            'version': self.version
        })
        return data