from typing import Dict, List, Set, Optional, Any
from pathlib import Path
import re
import json
import logging
from datetime import datetime

from ..core.models import PromptTemplate, PromptSet
from ..core.enums import FieldName, GenerationMode
from ..core.exceptions import (
    PromptLoadError, PromptSaveError, 
    TagError, MismatchedTagError, ValidationError
)
from ..core.config import PathConfig

class PromptService:
    """Manages prompt templates and processing"""
    
    def __init__(self, path_config: PathConfig):
        self.path_config = path_config
        self._current_set: Optional[PromptSet] = None
        self._cached_sets: Dict[str, PromptSet] = {}
        self._field_dependencies: Dict[FieldName, Set[FieldName]] = {}
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Ensure required directories exist"""
        self.path_config.base_prompts_dir.mkdir(parents=True, exist_ok=True)

    def _validate_template_text(self, text: str) -> List[str]:
        """Validate template text and return any warnings"""
        warnings = []
        
        # Check for balanced conditional tags
        open_tags = len(re.findall(r'{{if_input}}', text))
        close_tags = len(re.findall(r'{{/if_input}}', text))
        
        if open_tags != close_tags:
            raise MismatchedTagError(
                f"Mismatched conditional tags: {open_tags} opening, {close_tags} closing"
            )
        
        # Check for valid field references
        field_refs = re.findall(r'{{(\w+)}}', text)
        special_tags = {'input', 'if_input', '/if_input', 'char', 'user'}
        
        for ref in field_refs:
            if ref not in special_tags:
                try:
                    FieldName(ref)
                except ValueError:
                    warnings.append(f"Unknown field reference: {ref}")
        
        # Check for potential issues
        if '{{input}}' not in text:
            warnings.append("Template does not use {{input}} tag")
        
        if not any(tag in text for tag in ['{{char}}', '{{user}}']):
            warnings.append("Template does not use {{char}} or {{user}} tags")
        
        return warnings

    def _analyze_template_dependencies(self, template_text: str) -> Set[FieldName]:
        """Analyze template text for field dependencies"""
        deps = set()
        special_tags = {'input', 'if_input', '/if_input', 'char', 'user'}
        
        field_refs = re.findall(r'{{(\w+)}}', template_text)
        for ref in field_refs:
            if ref not in special_tags:
                try:
                    field = FieldName(ref)
                    deps.add(field)
                except ValueError:
                    continue
        
        return deps

    def _update_dependencies(self):
        """Update dependency cache for current prompt set"""
        if not self._current_set:
            return
            
        self._field_dependencies.clear()
        
        for field, template in self._current_set.templates.items():
            direct_deps = self._analyze_template_dependencies(template.text)
            
            # Include indirect dependencies
            all_deps = direct_deps.copy()
            for dep in direct_deps:
                if dep in self._field_dependencies:
                    all_deps.update(self._field_dependencies[dep])
            
            self._field_dependencies[field] = all_deps

    def load_prompt_set(self, name: str) -> PromptSet:
        """Load a prompt set from file"""
        # Check cache first
        if name in self._cached_sets:
            self._current_set = self._cached_sets[name]
            return self._current_set
        
        try:
            file_path = self.path_config.base_prompts_dir / f"{name}.json"
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            templates = {}
            warnings = []
            
            # Process templates
            for field_name, template_data in data['prompts'].items():
                try:
                    field = FieldName(field_name)
                    
                    # Validate template text
                    template_warnings = self._validate_template_text(template_data['text'])
                    if template_warnings:
                        warnings.extend([f"{field.value}: {w}" for w in template_warnings])
                    
                    # Create template
                    template = PromptTemplate(
                        text=template_data['text'],
                        field=field,
                        generation_order=data['orders'].get(field_name, -1),
                        required_fields=set()  # Will be updated during dependency analysis
                    )
                    
                    templates[field] = template
                    
                except ValueError:
                    logging.warning(f"Skipping invalid field name: {field_name}")
                    continue
                except MismatchedTagError as e:
                    raise PromptLoadError(f"Error in {field_name} template: {str(e)}")
            
            # Create prompt set
            prompt_set = PromptSet(
                name=name,
                templates=templates,
                description=data.get('description', ''),
                created_at=datetime.fromisoformat(data.get('created_at', datetime.now().isoformat())),
                modified_at=datetime.fromisoformat(data.get('modified_at', datetime.now().isoformat()))
            )
            
            # Update dependencies
            self._current_set = prompt_set
            self._cached_sets[name] = prompt_set
            self._update_dependencies()
            
            # Log any warnings
            if warnings:
                logging.warning(f"Warnings loading {name}:\n" + "\n".join(warnings))
            
            return prompt_set
            
        except Exception as e:
            raise PromptLoadError(f"Failed to load prompt set '{name}': {str(e)}")

    def save_prompt_set(self, prompt_set: PromptSet) -> None:
        """Save a prompt set to file"""
        try:
            file_path = self.path_config.base_prompts_dir / f"{prompt_set.name}.json"
            
            data = {
                'name': prompt_set.name,
                'description': prompt_set.description,
                'created_at': prompt_set.created_at.isoformat(),
                'modified_at': datetime.now().isoformat(),
                'prompts': {
                    template.field.value: {
                        'text': template.text,
                        'required_fields': [f.value for f in template.required_fields],
                        'conditional_tags': template.conditional_tags
                    }
                    for template in prompt_set.templates.values()
                },
                'orders': {
                    template.field.value: template.generation_order
                    for template in prompt_set.templates.values()
                }
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Update cache
            self._cached_sets[prompt_set.name] = prompt_set
            
        except Exception as e:
            raise PromptSaveError(f"Failed to save prompt set: {str(e)}")

    def list_prompt_sets(self) -> List[str]:
        """Get list of available prompt sets"""
        try:
            return sorted([
                f.stem for f in self.path_config.base_prompts_dir.glob('*.json')
            ])
        except Exception as e:
            raise PromptLoadError(f"Error scanning prompt sets: {str(e)}")

    def process_prompt(self, template: PromptTemplate, 
                    input_text: str, 
                    context: Dict[FieldName, str]) -> str:
        """Process a prompt template with given context"""
        try:
            result = template.text
            
            # Handle conditional sections
            if input_text.strip():
                result = re.sub(
                    r'{{if_input}}(.*?){{/if_input}}',
                    r'\1',
                    result,
                    flags=re.DOTALL
                )
            else:
                result = re.sub(
                    r'{{if_input}}.*?{{/if_input}}',
                    '',
                    result,
                    flags=re.DOTALL
                )
            
            # Replace input placeholder
            result = result.replace('{{input}}', input_text or '')
            
            # Replace field references with proper validation
            for field, value in context.items():
                if isinstance(field, FieldName):  # Ensure we have a FieldName
                    # Safely handle empty values
                    safe_value = str(value) if value is not None else ''
                    result = result.replace(f'{{{{{field.value}}}}}', safe_value)
                else:
                    logging.warning(f"Invalid field type in context: {type(field)}")
            
            return result.strip()
            
        except Exception as e:
            logging.error(f"Error processing prompt: {str(e)}", exc_info=True)
            raise ValidationError(f"Error processing prompt: {str(e)}")

    def validate_dependencies(self, template: PromptTemplate, 
                            available_fields: Set[FieldName]) -> bool:
        """Validate template dependencies"""
        if not template.required_fields:
            template.required_fields = self._analyze_template_dependencies(template.text)
        return template.required_fields.issubset(available_fields)

    def get_generation_order(self) -> List[FieldName]:
        """Get fields in generation order"""
        if not self._current_set:
            return []
        
        return [
        template.field
        for template in sorted(
            self._current_set.templates.values(),
            key=lambda x: x.generation_order
        )
        if template.generation_order >= 0
    ]

    def get_dependent_fields(self, field: FieldName) -> Set[FieldName]:
        """Get fields that depend on the given field"""
        dependents = set()
        
        if not self._current_set:
            return dependents
        
        # Use cached dependencies
        for other_field, deps in self._field_dependencies.items():
            if field in deps:
                dependents.add(other_field)
        
        return dependents

    def create_prompt_set(self, name: str, description: str = "") -> PromptSet:
        """Create a new prompt set"""
        return PromptSet(
            name=name,
            templates={},
            description=description,
            created_at=datetime.now(),
            modified_at=datetime.now()
        )

    @property
    def current_set(self) -> Optional[PromptSet]:
        """Get currently loaded prompt set"""
        return self._current_set