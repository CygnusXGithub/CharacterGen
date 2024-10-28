from typing import Dict, Optional, List, Set, Tuple
import logging
from datetime import datetime

from ..core.models import (
    GenerationContext, GenerationResult, GenerationCallbacks,
    CharacterData, PromptTemplate
)
from ..core.enums import FieldName, GenerationMode
from ..core.exceptions import (
    GenerationError, DependencyError, ValidationError,
    ApiError, ApiTimeoutError
)
from .api_service import ApiService
from .prompt_service import PromptService

class GenerationService:
    """Handles character field generation logic"""
    
    def __init__(self, api_service: ApiService, prompt_service: PromptService):
        self.api_service = api_service
        self.prompt_service = prompt_service
        self._generation_history: Dict[FieldName, List[GenerationResult]] = {}
        self._generation_cache: Dict[str, GenerationResult] = {}
        self._is_generating = False
        self._pending_fields: List[Tuple[FieldName, str, GenerationMode]] = []
        
    @property
    def is_generating(self) -> bool:
        """Check if generation is in progress"""
        return self._is_generating

    def generate_field(self, context: GenerationContext,
                    callbacks: Optional[GenerationCallbacks] = None,
                    force_new: bool = True) -> GenerationResult:
        """Generate content for a single field"""
        if self._is_generating:
            raise GenerationError("Generation already in progress")
            
        try:
            self._is_generating = True
            
            # Validate context
            self._validate_context(context)
            
            # Get prompt template
            template = self._get_template(context.current_field)
            
            # Dependencies check removed - allow generation regardless
            
            # Handle direct input mode
            if context.generation_mode == GenerationMode.DIRECT:
                return self._handle_direct_input(context)
            
            if callbacks and callbacks.on_start:
                callbacks.on_start(context.current_field)
            
            prompt = self.prompt_service.process_prompt(
                template,
                context.current_input,
                context.character_data.fields
            )
            
            if callbacks and callbacks.on_progress:
                callbacks.on_progress(context.current_field, "Generating...")
            
            # Generate content
            try:
                content = self.api_service.generate_text(prompt)
            except ApiTimeoutError:
                if callbacks and callbacks.on_progress:
                    callbacks.on_progress(context.current_field, "Retrying generation...")
                content = self.api_service.generate_text(prompt)
            
            # Create result
            result = GenerationResult(
                field=context.current_field,
                content=content,
                timestamp=datetime.now(),
                attempts=self.api_service.last_response.attempts if self.api_service.last_response else 1
            )
            
            # Update history and cache
            self._add_to_history(result)
            if not force_new:
                cache_key = self._get_cache_key(context)
                self._generation_cache[cache_key] = result
            
            if callbacks and callbacks.on_result:
                callbacks.on_result(context.current_field, result)
            
            return result
            
        except Exception as e:
            error_result = GenerationResult(
                field=context.current_field,
                content="",
                timestamp=datetime.now(),
                error=e
            )
            self._add_to_history(error_result)
            
            if callbacks and callbacks.on_error:
                callbacks.on_error(context.current_field, e)
            
            raise
        finally:
            self._is_generating = False
    
    def generate_field_with_deps(self, 
                                context: GenerationContext,
                                callbacks: Optional[GenerationCallbacks] = None) -> Dict[FieldName, GenerationResult]:
        """Generate a field and its dependents"""
        results = {}
        
        try:
            # Get ordered fields
            ordered_fields = self._get_ordered_fields()
            if not ordered_fields:
                raise GenerationError("No fields with generation order defined")
            
            # Find starting point
            try:
                start_idx = ordered_fields.index(context.current_field)
            except ValueError:
                raise GenerationError(f"Field {context.current_field.value} not found in generation order")
            
            # Get fields that need regeneration
            fields_to_generate = self._get_fields_to_regenerate(
                ordered_fields[start_idx:],
                context.changed_fields
            )
            
            total_fields = len(fields_to_generate)
            
            # Generate fields
            for idx, field in enumerate(fields_to_generate):
                if callbacks and callbacks.on_progress:
                    callbacks.on_progress(
                        field,
                        f"Generating field {idx + 1}/{total_fields}..."
                    )
                
                try:
                    field_context = self._create_field_context(
                        context,
                        field,
                        context.field_inputs.get(field, "")
                    )
                    
                    result = self.generate_field(field_context)
                    results[field] = result
                    
                    # Update context with new content
                    if not result.error:
                        context.character_data.fields[field] = result.content
                        context.changed_fields.add(field)
                    
                except Exception as e:
                    results[field] = GenerationResult(
                        field=field,
                        content="",
                        timestamp=datetime.now(),
                        error=e
                    )
                    break
            
            return results
            
        except Exception as e:
            logging.error(f"Error in generate_field_with_deps: {str(e)}")
            raise
    
    def queue_generation(self, field: FieldName, input_text: str = "",
                        mode: GenerationMode = GenerationMode.GENERATE):
        """Queue a field for generation"""
        self._pending_fields.append((field, input_text, mode))
        if not self._is_generating:
            self._process_pending()
    
    def clear_generation_queue(self):
        """Clear pending generations"""
        self._pending_fields.clear()
    
    def get_field_history(self, field: FieldName) -> List[GenerationResult]:
        """Get generation history for a field"""
        return self._generation_history.get(field, []).copy()
    
    def clear_history(self, field: Optional[FieldName] = None):
        """Clear generation history"""
        if field:
            self._generation_history.pop(field, None)
        else:
            self._generation_history.clear()
    
    def clear_cache(self):
        """Clear generation cache"""
        self._generation_cache.clear()
    
    def _validate_context(self, context: GenerationContext):
        """Validate generation context"""
        if not context.character_data:
            raise ValidationError("No character data provided")
        
        if not context.current_field:
            raise ValidationError("No field specified")
    
    def _get_template(self, field: FieldName) -> PromptTemplate:
        """Get prompt template for field"""
        if not self.prompt_service.current_set:
            raise GenerationError("No prompt set loaded")
            
        template = self.prompt_service.current_set.templates.get(field)
        if not template:
            raise GenerationError(f"No template found for field {field.value}")
            
        return template
    
    def _validate_dependencies(self, template: PromptTemplate, 
                             context: GenerationContext) -> bool:
        """Validate template dependencies"""
        return self.prompt_service.validate_dependencies(
            template,
            set(context.character_data.fields.keys())
        )
    
    def _handle_direct_input(self, context: GenerationContext) -> GenerationResult:
        """Handle direct input mode"""
        return GenerationResult(
            field=context.current_field,
            content=context.current_input,
            timestamp=datetime.now(),
            attempts=0
        )
    
    def _get_cache_key(self, context: GenerationContext) -> str:
        """Generate cache key for context"""
        return f"{context.current_field.value}:{hash(context.current_input)}"
    
    def _add_to_history(self, result: GenerationResult):
        """Add result to generation history"""
        if result.field not in self._generation_history:
            self._generation_history[result.field] = []
        self._generation_history[result.field].append(result)
    
    def _process_pending(self):
        """Process pending generation requests"""
        if not self._pending_fields or self._is_generating:
            return
            
        field, input_text, mode = self._pending_fields.pop(0)
        context = GenerationContext(
            character_data=CharacterData("temp"),  # This should be provided by caller
            current_field=field,
            field_inputs={field: input_text},
            generation_mode=mode
        )
        
        try:
            self.generate_field(context)
        except Exception as e:
            logging.error(f"Error processing pending generation: {str(e)}")
    
    def _get_ordered_fields(self) -> List[FieldName]:
        """Get fields in generation order"""
        return self.prompt_service.get_generation_order()
    
    def _get_fields_to_regenerate(self, 
                                 fields: List[FieldName],
                                 changed_fields: Set[FieldName]) -> List[FieldName]:
        """Determine which fields need regeneration"""
        fields_to_generate = set()
        
        for field in fields:
            # Field needs regeneration if:
            # 1. It's in the changed_fields set
            # 2. Any of its dependencies have changed
            deps = self.prompt_service.get_dependent_fields(field)
            if (field in changed_fields or 
                any(dep in changed_fields for dep in deps)):
                fields_to_generate.add(field)
                # Add fields that depend on this field
                fields_to_generate.update(
                    self.prompt_service.get_dependent_fields(field)
                )
        
        # Return fields in correct order
        return [f for f in fields if f in fields_to_generate]
    
    def _create_field_context(self, 
                            base_context: GenerationContext,
                            field: FieldName,
                            input_text: str) -> GenerationContext:
        """Create context for field generation"""
        return GenerationContext(
            character_data=base_context.character_data,
            current_field=field,
            field_inputs={field: input_text},
            changed_fields=base_context.changed_fields.copy(),
            generation_mode=(base_context.generation_mode 
                           if field == base_context.current_field
                           else GenerationMode.GENERATE)
        )