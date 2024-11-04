# core/services/prompt.py
"""Service for managing prompt templates and processing."""
import re
from typing import Dict, Set, Optional, Match, Tuple
from dataclasses import dataclass, field

from ..common.types import (
    BaseModel, JsonDict, Result,
    ValidationLevel
)
from ..models.prompts import (
    PromptTemplate, ProcessedPrompt,
    PromptSet, PromptTagType
)
from ..errors import ErrorHandler, ErrorCategory, ErrorLevel

@dataclass
class PromptContext(BaseModel):
    """Context for prompt processing."""
    available_data: JsonDict
    user_input: Optional[str] = None
    system_values: Optional[Dict[str, str]] = None
    metadata: JsonDict = field(default_factory=dict)

@dataclass
class TagValidationResult(BaseModel):
    """Result of tag validation."""
    is_valid: bool
    missing_required: Set[str] = field(default_factory=set)
    missing_optional: Set[str] = field(default_factory=set)
    invalid_tags: Set[str] = field(default_factory=set)

class PromptManager:
    """Manages prompt templates and processing."""
    
    def __init__(self, error_handler: ErrorHandler):
        self.error_handler = error_handler
        self._prompt_sets: Dict[str, PromptSet] = {}
        
        # Compile regex patterns for performance
        self._patterns = {
            'field': re.compile(r'{{(\w+)}}'),
            'conditional': re.compile(r'{{if_(\w+)}}(.*?){{/if_\1}}', re.DOTALL),
            'input': re.compile(r'{{input}}'),
            'system': re.compile(r'{{(char|user)}}')
        }
    
    def add_prompt_set(self, prompt_set: PromptSet) -> Result:
        """Add or update a prompt set."""
        try:
            # Validate the prompt set
            validation = self._validate_prompt_set(prompt_set)
            if not validation.success:
                return validation
                
            self._prompt_sets[str(prompt_set.id)] = prompt_set
            return Result(True, "Prompt set added successfully", prompt_set)
            
        except Exception as e:
            self.error_handler.handle_error(
                e,
                ErrorCategory.CONFIG,
                ErrorLevel.ERROR,
                {'operation': 'add_prompt_set', 'prompt_set': prompt_set.name}
            )
            return Result(False, f"Failed to add prompt set: {str(e)}", error=e)
    
    def process_prompt(self,
                      template: PromptTemplate,
                      context: PromptContext) -> Result[ProcessedPrompt]:
        """Process a prompt template with available data."""
        try:
            # Validate template first
            validation = self._validate_template_tags(template)
            if not validation.success:
                return Result(
                    False,
                    f"Template validation failed: {validation.message}",
                    validation
                )

            content = template.content
            used_fields = set()
            missing_required = set()
            missing_optional = set()
            used_conditionals = set()
            
            # Process system tags first
            if context.system_values:
                content = self._process_system_tags(content, context.system_values)
            
            # Process conditional blocks
            content, conditionals_used = self._process_conditional_blocks(
                content, context
            )
            used_conditionals.update(conditionals_used)
            
            # Process field tags
            content, field_results = self._process_field_tags(
                content, context, template
            )
            
            used_fields.update(field_results.used_fields)
            missing_required.update(field_results.missing_required)
            missing_optional.update(field_results.missing_optional)
            
            processed = ProcessedPrompt(
                original_template=template,
                processed_content=content,
                used_fields=used_fields,
                missing_required=missing_required,
                missing_optional=missing_optional,
                used_conditionals=used_conditionals
            )
            
            # Validate final result
            if missing_required:
                return Result(
                    False,
                    f"Missing required fields: {', '.join(missing_required)}",
                    processed
                )
            
            return Result(True, "Prompt processed successfully", processed)
            
        except Exception as e:
            self.error_handler.handle_error(
                e,
                ErrorCategory.GENERATION,
                ErrorLevel.ERROR,
                {
                    'operation': 'process_prompt',
                    'template': template.field_name
                }
            )
            return Result(False, f"Failed to process prompt: {str(e)}", error=e)

    def _process_system_tags(self, content: str, system_values: Dict[str, str]) -> str:
        """Process system tags in content."""
        for tag, value in system_values.items():
            content = content.replace(f"{{{{char}}}}", system_values.get("char", "[char]"))
            content = content.replace(f"{{{{user}}}}", system_values.get("user", "[user]"))
        return content
    
    def _process_conditional_blocks(self, 
                                  content: str,
                                  context: PromptContext) -> Tuple[str, Set[str]]:
        """Process conditional blocks in content."""
        used_conditionals = set()
        
        def conditional_replacer(match: Match) -> str:
            condition = match.group(1)
            block_content = match.group(2)
            
            # Handle input condition
            if condition == 'input' and context.user_input:
                used_conditionals.add(condition)
                return block_content.replace('{{input}}', context.user_input)
            
            # Handle field conditions
            elif condition in context.available_data:
                used_conditionals.add(condition)
                return block_content
                
            return ''
        
        processed_content = self._patterns['conditional'].sub(
            conditional_replacer, content
        )
        return processed_content, used_conditionals
    
    def _process_field_tags(self,
                          content: str,
                          context: PromptContext,
                          template: PromptTemplate) -> Tuple[str, TagValidationResult]:
        """Process field tags in content."""
        used_fields = set()
        missing_required = set()
        missing_optional = set()
        
        def field_replacer(match: Match) -> str:
            field = match.group(1)
            if field in context.available_data:
                used_fields.add(field)
                return str(context.available_data[field])
            else:
                if field in template.required_fields:
                    missing_required.add(field)
                elif field in template.optional_fields:
                    missing_optional.add(field)
                return f"[{field}]"
        
        processed_content = self._patterns['field'].sub(field_replacer, content)
        
        return processed_content, TagValidationResult(
            is_valid=len(missing_required) == 0,
            missing_required=missing_required,
            missing_optional=missing_optional
        )

    def _validate_template_tags(self, template: PromptTemplate) -> Result:
        """Validate template tag structure."""
        try:
            # Check for unclosed conditionals
            conditionals = list(self._patterns['conditional'].finditer(template.content))
            for match in conditionals:
                condition = match.group(1)
                if condition not in ['input'] and condition not in template.required_fields:
                    return Result(False, f"Unknown conditional field: {condition}")
            
            # Check field references
            fields = set(self._patterns['field'].findall(template.content))
            unknown_fields = fields - (template.required_fields | template.optional_fields)
            if unknown_fields:
                return Result(False, f"Unknown fields referenced: {unknown_fields}")
            
            # Check system tags
            system_tags = set(self._patterns['system'].findall(template.content))
            if system_tags - {'char', 'user'}:
                return Result(False, f"Invalid system tags: {system_tags - {'char', 'user'}}")
            
            return Result(True, "Template validation successful")
            
        except Exception as e:
            return Result(False, f"Template validation failed: {str(e)}", error=e)

    def _validate_prompt_set(self, prompt_set: PromptSet) -> Result:
        """Validate prompt set configuration."""
        try:
            # Validate each template
            for field_name, template in prompt_set.prompts.items():
                template_validation = self._validate_template_tags(template)
                if not template_validation.success:
                    return Result(
                        False,
                        f"Invalid template for {field_name}: {template_validation.message}"
                    )
            
            # Validate generation order
            if not prompt_set.validate_generation_order():
                return Result(False, "Invalid generation order")
            
            return Result(True, "Prompt set validation successful")
            
        except Exception as e:
            return Result(False, f"Prompt set validation failed: {str(e)}", error=e)

    def analyze_dependencies(self, 
                           template: PromptTemplate) -> Result[Tuple[Set[str], Set[str]]]:
        """Analyze template for required and optional field dependencies."""
        try:
            required = set(template.required_fields)
            optional = set()
            
            # Find all field references
            fields = set(self._patterns['field'].findall(template.content))
            
            # Find conditional fields
            conditionals = self._patterns['conditional'].finditer(template.content)
            for match in conditionals:
                condition = match.group(1)
                if condition != 'input':
                    fields.add(condition)
            
            # Fields referenced but not required are optional
            optional = fields - required
                    
            return Result(
                True,
                "Dependencies analyzed successfully",
                (required, optional)
            )
                
        except Exception as e:
            return Result(False, f"Failed to analyze dependencies: {str(e)}", error=e)

    def get_prompt_set(self, prompt_set_id: str) -> Optional[PromptSet]:
        """Get prompt set by ID."""
        return self._prompt_sets.get(prompt_set_id)