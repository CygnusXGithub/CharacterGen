from typing import Dict, Optional, Callable, List, Any
from dataclasses import dataclass
from datetime import datetime

from ..core.models import GenerationContext, GenerationResult, CharacterData
from ..core.enums import FieldName, GenerationMode
from ..core.exceptions import GenerationError, DependencyError
from .api_service import ApiService
from .prompt_service import PromptService

@dataclass
class GenerationCallbacks:
    """Callbacks for generation progress and results"""
    on_start: Optional[Callable[[FieldName], None]] = None
    on_progress: Optional[Callable[[FieldName, str], None]] = None
    on_result: Optional[Callable[[FieldName, GenerationResult], None]] = None
    on_error: Optional[Callable[[FieldName, Exception], None]] = None

class GenerationService:
    """Handles character field generation logic"""
    
    def __init__(self, api_service: ApiService, prompt_service: PromptService):
        self.api_service = api_service
        self.prompt_service = prompt_service
        self.generation_history: Dict[FieldName, List[GenerationResult]] = {}
    
    def generate_field(self, context: GenerationContext) -> GenerationResult:
        """Generate content for a single field"""
        try:
            # Get the prompt template
            template = self.prompt_service.current_set.templates.get(context.current_field)
            if not template:
                raise GenerationError(f"No template found for field {context.current_field.value}")
            
            # Validate dependencies
            available_fields = set(context.available_fields.keys())
            if not self.prompt_service.validate_dependencies(template, available_fields):
                missing = template.required_fields - available_fields
                raise DependencyError(
                    context.current_field.value,
                    [f.value for f in missing]
                )
            
            # Handle direct input mode
            if context.generation_mode == GenerationMode.DIRECT:
                return GenerationResult(
                    field=context.current_field,
                    content=context.user_input,
                    attempts=0
                )
            
            # Process the prompt template
            prompt = self.prompt_service.process_prompt(
                template,
                context.user_input,
                context.available_fields
            )
            
            # Generate content
            content = self.api_service.generate_text(prompt)
            
            # Create and store result
            result = GenerationResult(
                field=context.current_field,
                content=content,
                attempts=self.api_service.last_response.attempts if self.api_service.last_response else 1
            )
            
            self._add_to_history(result)
            return result
            
        except Exception as e:
            error_result = GenerationResult(
                field=context.current_field,
                content="",
                error=e
            )
            self._add_to_history(error_result)
            raise
    
    def generate_field_with_deps(self, context: GenerationContext, 
                               callbacks: Optional[GenerationCallbacks] = None) -> Dict[FieldName, GenerationResult]:
        results = {}
        
        # Get the ordered list of fields (only those with orders)
        ordered_fields = self._get_ordered_fields()
        if not ordered_fields:
            raise GenerationError("No fields with generation order defined")
        
        # Find starting index
        try:
            start_idx = ordered_fields.index(context.current_field)
        except ValueError:
            raise GenerationError(f"Field {context.current_field.value} not found in generation order")
        
        # Generate each field in order starting from the requested field
        for field in ordered_fields[start_idx:]:
            if callbacks and callbacks.on_start:
                callbacks.on_start(field)
            
            try:
                # Create new context for this field
                field_context = GenerationContext(
                    character_data=context.character_data,
                    current_field=field,
                    user_input=context.user_input if field == context.current_field else "",
                    generation_mode=context.generation_mode if field == context.current_field 
                                  else GenerationMode.GENERATE
                )
                
                if callbacks and callbacks.on_progress:
                    callbacks.on_progress(field, "Generating...")
                
                result = self.generate_field(field_context)
                results[field] = result
                
                # Update character data with new result
                context.character_data.fields[field] = result.content
                
                if callbacks and callbacks.on_result:
                    callbacks.on_result(field, result)
                
            except Exception as e:
                if callbacks and callbacks.on_error:
                    callbacks.on_error(field, e)
                results[field] = GenerationResult(
                    field=field,
                    content="",
                    error=e
                )
                # Stop generation if there's an error
                break
        
        return results
    
    def generate_alternate_greeting(self, 
                                  character: CharacterData,
                                  callbacks: Optional[GenerationCallbacks] = None) -> str:
        """Generate an alternate greeting"""
        if FieldName.FIRST_MES not in self.prompt_service.current_set.templates:
            raise GenerationError("No template found for first message")
        
        context = GenerationContext(
            character_data=character,
            current_field=FieldName.FIRST_MES,
            user_input="Generate an alternate greeting",
            generation_mode=GenerationMode.GENERATE
        )
        
        if callbacks and callbacks.on_start:
            callbacks.on_start(FieldName.FIRST_MES)
        
        try:
            result = self.generate_field(context)
            if callbacks and callbacks.on_result:
                callbacks.on_result(FieldName.FIRST_MES, result)
            return result.content
        except Exception as e:
            if callbacks and callbacks.on_error:
                callbacks.on_error(FieldName.FIRST_MES, e)
            raise
    
    def append_message_example(self, 
                             character: CharacterData,
                             context_input: str = "",
                             callbacks: Optional[GenerationCallbacks] = None) -> str:
        """Generate and append a new message example"""
        if FieldName.MES_EXAMPLE not in self.prompt_service.current_set.templates:
            raise GenerationError("No template found for message examples")
        
        context = GenerationContext(
            character_data=character,
            current_field=FieldName.MES_EXAMPLE,
            user_input=context_input,
            generation_mode=GenerationMode.GENERATE
        )
        
        if callbacks and callbacks.on_start:
            callbacks.on_start(FieldName.MES_EXAMPLE)
        
        try:
            result = self.generate_field(context)
            if callbacks and callbacks.on_result:
                callbacks.on_result(FieldName.MES_EXAMPLE, result)
            return result.content
        except Exception as e:
            if callbacks and callbacks.on_error:
                callbacks.on_error(FieldName.MES_EXAMPLE, e)
            raise
    
    def _get_ordered_fields(self) -> List[FieldName]:
        """Get fields with order, sorted by order number"""
        ordered_fields = [
            (field, template.generation_order)
            for field, template in self.prompt_service.current_set.templates.items()
            if hasattr(template, 'generation_order') and template.generation_order >= 0
        ]
        return [field for field, _ in sorted(ordered_fields, key=lambda x: x[1])]
    
    def _add_to_history(self, result: GenerationResult) -> None:
        """Add generation result to history"""
        if result.field not in self.generation_history:
            self.generation_history[result.field] = []
        self.generation_history[result.field].append(result)
    
    def get_field_history(self, field: FieldName) -> List[GenerationResult]:
        """Get generation history for a field"""
        return self.generation_history.get(field, [])
    
    def clear_history(self, field: Optional[FieldName] = None) -> None:
        """Clear generation history for a field or all fields"""
        if field:
            self.generation_history.pop(field, None)
        else:
            self.generation_history.clear()
