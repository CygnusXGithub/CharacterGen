import re
from typing import Dict, Any, Set, Optional, Tuple, Match
from ..models.prompts import PromptTemplate, ProcessedPrompt, TagType, PromptSet
from ..errors import ErrorHandler, ErrorCategory, ErrorLevel

class PromptManager:
    """Manages prompt templates and processing"""
    
    def __init__(self, error_handler: ErrorHandler):
        self.error_handler = error_handler
        self._prompt_sets: Dict[str, PromptSet] = {}
        
        # Regex patterns for tag parsing
        self._field_pattern = re.compile(r'{{(\w+)}}')
        self._conditional_pattern = re.compile(r'{{if_(\w+)}}(.*?){{/if_\1}}', re.DOTALL)
        self._input_pattern = re.compile(r'{{input}}')
        self._system_pattern = re.compile(r'{{(char|user)}}')
    
    def add_prompt_set(self, prompt_set: PromptSet) -> bool:
        """Add or update a prompt set"""
        try:
            if not prompt_set.validate_generation_order():
                raise ValueError("Invalid generation order in prompt set")
                
            self._prompt_sets[prompt_set.id] = prompt_set
            return True
            
        except Exception as e:
            self.error_handler.handle_error(
                error=e,
                category=ErrorCategory.CONFIG,
                level=ErrorLevel.ERROR,
                context={'operation': 'add_prompt_set', 'prompt_set': prompt_set.name}
            )
            return False
    
    def process_prompt(self,
                      template: PromptTemplate,
                      available_data: Dict[str, Any],
                      user_input: Optional[str] = None,
                      system_values: Optional[Dict[str, str]] = None) -> ProcessedPrompt:
        """Process a prompt template with available data"""
        try:
            # Validate conditional tags first
            self._validate_conditional_tags(template.content)

            content = template.content
            used_fields = set()
            missing_required = set()
            missing_optional = set()
            used_conditionals = set()
            
            # Process system tags first
            if system_values:
                for tag, value in system_values.items():
                    content = content.replace(f"{{{{char}}}}", system_values.get("char", "[char]"))
                    content = content.replace(f"{{{{user}}}}", system_values.get("user", "[user]"))
            
            # Process conditional blocks
            def conditional_replacer(match: Match) -> str:
                condition = match.group(1)
                block_content = match.group(2)
                
                # Check if condition is met
                if condition == 'input' and user_input:
                    used_conditionals.add(condition)
                    return block_content.replace('{{input}}', user_input)
                elif condition in available_data:
                    used_conditionals.add(condition)
                    return block_content
                return ''
            
            content = self._conditional_pattern.sub(conditional_replacer, content)
            
            # Replace field tags
            def field_replacer(match: Match) -> str:
                field = match.group(1)
                if field in available_data:
                    used_fields.add(field)
                    return str(available_data[field])
                else:
                    if field in template.required_fields:
                        missing_required.add(field)
                    elif field in template.content:  # If field is referenced but not in required_fields
                        missing_optional.add(field)
                    return f"[{field}]"  # Placeholder for missing fields
            
            content = self._field_pattern.sub(field_replacer, content)
            
            return ProcessedPrompt(
                original_template=template,
                processed_content=content,
                used_fields=used_fields,
                missing_required=missing_required,
                missing_optional=missing_optional,
                used_conditionals=used_conditionals
            )
            
        except Exception as e:
            self.error_handler.handle_error(
                error=e,
                category=ErrorCategory.GENERATION,
                level=ErrorLevel.ERROR,
                context={
                    'operation': 'process_prompt',
                    'template': template.field_name
                }
            )
            raise ValueError(f"Failed to process prompt: {str(e)}")

    def analyze_dependencies(self, template: PromptTemplate) -> Tuple[Set[str], Set[str]]:
        """Analyze template for required and optional field dependencies"""
        required = set(template.required_fields)  # Use template's required fields
        optional = set()
        
        # Find all field references
        fields = set(self._field_pattern.findall(template.content))
        
        # Find conditional fields
        conditionals = self._conditional_pattern.finditer(template.content)
        for match in conditionals:
            condition = match.group(1)
            if condition != 'input':  # input is special case
                fields.add(condition)
        
        # Fields referenced but not required are optional
        optional = fields - required
                
        return required, optional
    
    def _validate_conditional_tags(self, content: str) -> None:
        """Validate that all conditional tags are properly formed and matched"""
        # Find all opening and closing tags
        opening_tags = re.findall(r'{{if_(\w+)}}', content)
        closing_tags = re.findall(r'{{/if_(\w+)}}', content)
        
        # Track tags for proper nesting
        open_stack = []
        
        # Scan through content looking for tags in order
        for match in re.finditer(r'{{(?:/)?if_(\w+)}}', content):
            tag = match.group(1)
            is_closing = match.group(0).startswith('{{/')
            
            if is_closing:
                if not open_stack:
                    raise ValueError("Unexpected closing tag")
                if open_stack[-1] != tag:
                    raise ValueError("Mismatched conditional tags")
                open_stack.pop()
            else:
                open_stack.append(tag)
        
        if open_stack:
            raise ValueError("Unclosed conditional block")