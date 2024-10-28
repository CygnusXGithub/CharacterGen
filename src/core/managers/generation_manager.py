from typing import Dict, Optional, List, Tuple, Set
import logging
from PyQt6.QtCore import QObject, pyqtSignal

from ..models import (
    GenerationContext, GenerationResult, GenerationCallbacks,
    CharacterData
)
from ..enums import FieldName, GenerationMode
from ..exceptions import GenerationError, DependencyError
from ...services.generation_service import GenerationService

class GenerationManager(QObject):
    """Centralized manager for generation operations"""
    
    # Generation status signals
    generation_started = pyqtSignal(FieldName)  # When generation begins
    generation_progress = pyqtSignal(FieldName, str)  # Progress updates
    generation_completed = pyqtSignal(FieldName, GenerationResult)  # Successful generation
    generation_error = pyqtSignal(FieldName, Exception)  # Generation errors
    
    # Batch operation signals
    batch_started = pyqtSignal(int)  # Total fields to generate
    batch_progress = pyqtSignal(int, int)  # (current, total)
    batch_completed = pyqtSignal()  # All fields generated
    
    def __init__(self, generation_service: GenerationService, character_manager):
        super().__init__()
        self.generation_service = generation_service
        self.character_manager = character_manager
        self.current_context: Optional[GenerationContext] = None
        self._is_generating = False
        self._generation_queue: List[Tuple[FieldName, str, GenerationMode]] = []
        
    @property
    def is_generating(self) -> bool:
        """Check if generation is in progress"""
        return self._is_generating
    
    def generate_field(self, field: FieldName, input_text: str = "", 
                      mode: GenerationMode = GenerationMode.GENERATE):
        """Generate content for a single field"""
        # Queue the generation if already generating
        if self._is_generating:
            self._generation_queue.append((field, input_text, mode))
            return
        
        try:
            self._is_generating = True
            self.generation_started.emit(field)
            
            # Create generation context
            context = self._create_context(field, input_text, mode)
            
            # Create callbacks for progress tracking
            callbacks = self._create_callbacks()
            
            # Generate content
            result = self.generation_service.generate_field(context)
            
            # Update character with result
            if not result.error:
                self.character_manager.update_field(field.value, result.content)
            
            # Emit completion signal
            self.generation_completed.emit(field, result)
            
        except Exception as e:
            logging.error(f"Generation error for {field.value}: {str(e)}")
            self.generation_error.emit(field, e)
        finally:
            self._is_generating = False
            self._process_queue()
    
    def generate_with_dependencies(self, field: FieldName, input_text: str = "",
                                 mode: GenerationMode = GenerationMode.GENERATE):
        """Generate a field and its dependents"""
        if self._is_generating:
            self._generation_queue.append((field, input_text, mode))
            return
        
        try:
            self._is_generating = True
            
            # Create initial context
            context = self._create_context(field, input_text, mode)
            
            # Get all fields that need regeneration
            fields_to_generate = self._get_dependent_fields(field)
            self.batch_started.emit(len(fields_to_generate))
            
            # Generate each field
            for idx, current_field in enumerate(fields_to_generate):
                self.generation_started.emit(current_field)
                self.batch_progress.emit(idx + 1, len(fields_to_generate))
                
                try:
                    # Update context for current field
                    context.current_field = current_field
                    result = self.generation_service.generate_field(context)
                    
                    if not result.error:
                        self.character_manager.update_field(current_field.value, result.content)
                        context.changed_fields.add(current_field)
                    
                    self.generation_completed.emit(current_field, result)
                    
                except Exception as e:
                    self.generation_error.emit(current_field, e)
                    break
            
            self.batch_completed.emit()
            
        finally:
            self._is_generating = False
            self._process_queue()
    
    def generate_all(self):
        """Generate all fields in order"""
        ordered_fields = self.generation_service._get_ordered_fields()
        if not ordered_fields:
            return
        
        self.generate_with_dependencies(ordered_fields[0])
    
    def _create_context(self, field: FieldName, input_text: str,
                       mode: GenerationMode) -> GenerationContext:
        """Create generation context"""
        return GenerationContext(
            character_data=self.character_manager.current_character,
            current_field=field,
            field_inputs={field: input_text},
            changed_fields=set(),
            generation_mode=mode
        )
    
    def _create_callbacks(self) -> GenerationCallbacks:
        """Create generation callbacks"""
        return GenerationCallbacks(
            on_start=lambda field: self.generation_started.emit(field),
            on_progress=lambda field, status: self.generation_progress.emit(field, status),
            on_result=lambda field, result: self.generation_completed.emit(field, result),
            on_error=lambda field, error: self.generation_error.emit(field, error)
        )
    
    def _get_dependent_fields(self, starting_field: FieldName) -> List[FieldName]:
        """Get list of fields that need regeneration"""
        ordered_fields = self.generation_service._get_ordered_fields()
        try:
            start_idx = ordered_fields.index(starting_field)
            return ordered_fields[start_idx:]
        except ValueError:
            return []
    
    def _process_queue(self):
        """Process next item in generation queue"""
        if self._generation_queue and not self._is_generating:
            field, input_text, mode = self._generation_queue.pop(0)
            self.generate_field(field, input_text, mode)

    def cancel_generation(self):
        """Cancel current generation and clear queue"""
        self._generation_queue.clear()
        self._is_generating = False