from typing import Dict, List, Set, Optional
import json
from pathlib import Path
from datetime import datetime
import re

from ..core.models import PromptTemplate, PromptSet
from ..core.enums import FieldName
from ..core.exceptions import (
    PromptLoadError, PromptSaveError, 
    TagError, MismatchedTagError
)
from ..core.config import PathConfig

class PromptService:
    """Manages prompt templates and processing"""
    
    def __init__(self, path_config: PathConfig):
        self.path_config = path_config
        self._current_set: Optional[PromptSet] = None
        self._ensure_directories()
    
    def _ensure_directories(self) -> None:
        """Ensure required directories exist"""
        self.path_config.base_prompts_dir.mkdir(parents=True, exist_ok=True)
    
    def load_prompt_set(self, name: str) -> PromptSet:
        """Load a prompt set from file"""
        file_path = self.path_config.base_prompts_dir / f"{name}.json"
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            templates = {}
            for field_name, template_data in data['prompts'].items():
                try:
                    field = FieldName(field_name)
                    template = PromptTemplate(
                        text=template_data['text'],
                        field=field,
                        generation_order=data['orders'].get(field_name, 0)
                    )
                    templates[field] = template
                except ValueError:
                    continue  # Skip invalid field names
            
            prompt_set = PromptSet(
                name=name,
                templates=templates,
                description=data.get('description', ''),
                created_at=datetime.fromisoformat(data.get('created_at', datetime.now().isoformat())),
                modified_at=datetime.fromisoformat(data.get('modified_at', datetime.now().isoformat()))
            )
            
            self._current_set = prompt_set
            return prompt_set
            
        except Exception as e:
            raise PromptLoadError(f"Failed to load prompt set: {str(e)}")
    
    def save_prompt_set(self, prompt_set: PromptSet) -> None:
        """Save a prompt set to file"""
        file_path = self.path_config.base_prompts_dir / f"{prompt_set.name}.json"
        
        try:
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
            
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
                
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
        result = result.replace('{{input}}', input_text)
        
        # Replace field references
        for field, value in context.items():
            result = result.replace(f'{{{{{field.value}}}}}', value)
        
        return result.strip()
    
    def validate_dependencies(self, template: PromptTemplate, 
                            available_fields: Set[FieldName]) -> bool:
        """Validate template dependencies"""
        return template.required_fields.issubset(available_fields)
    
    def create_prompt_set(self, name: str, description: str = "") -> PromptSet:
        """Create a new prompt set"""
        return PromptSet(
            name=name,
            templates={},
            description=description,
            created_at=datetime.now(),
            modified_at=datetime.now()
        )
    
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
        ]
    
    @property
    def current_set(self) -> Optional[PromptSet]:
        """Get currently loaded prompt set"""
        return self._current_set
