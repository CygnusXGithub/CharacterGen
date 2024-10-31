from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional
from enum import Enum
from uuid import UUID, uuid4

class TagType(Enum):
    """Types of tags in prompts"""
    FIELD = "field"         # {{name}}, {{description}}, etc.
    CONDITIONAL = "cond"    # {{if_input}}, {{if_name}}, etc.
    INPUT = "input"         # {{input}}
    SYSTEM = "system"       # {{char}}, {{user}}, etc.

@dataclass
class PromptTemplate:
    """Single prompt template"""
    content: str
    field_name: str
    description: str = ""
    required_fields: Set[str] = field(default_factory=set)  # Fields this prompt depends on
    optional_fields: Set[str] = field(default_factory=set)  # Fields that can be used if available
    system_tags: Set[str] = field(default_factory=set)      # System tags used
    version: str = "1.0"
    id: UUID = field(default_factory=uuid4)

@dataclass
class PromptSet:
    """Collection of prompts for character generation"""
    name: str
    description: str
    prompts: Dict[str, PromptTemplate]  # field_name -> template
    generation_order: List[str]         # Field generation order
    version: str = "1.0"
    id: UUID = field(default_factory=uuid4)
    
    def get_prompt_for_field(self, field_name: str) -> Optional[PromptTemplate]:
        """Get prompt template for a specific field"""
        return self.prompts.get(field_name)
    
    def validate_generation_order(self) -> bool:
        """Validate that generation order is valid with dependencies"""
        # Check all fields in prompts are in generation order
        if set(self.prompts.keys()) != set(self.generation_order):
            return False
            
        # Check dependencies
        for idx, field in enumerate(self.generation_order):
            prompt = self.prompts[field]
            # Check that required fields come before this field
            available_fields = set(self.generation_order[:idx])
            if not prompt.required_fields.issubset(available_fields):
                return False
        
        return True

@dataclass
class ProcessedPrompt:
    """Result of processing a prompt template"""
    original_template: PromptTemplate
    processed_content: str
    used_fields: Set[str]           # Fields actually used in processing
    missing_required: Set[str]      # Required fields that were missing
    missing_optional: Set[str]      # Optional fields that were missing
    used_conditionals: Set[str]     # Conditional blocks that were used