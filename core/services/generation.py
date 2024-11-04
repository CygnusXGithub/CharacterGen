# core/services/generation.py
"""Service for handling character field generation."""
from dataclasses import dataclass, field
from typing import Optional, Dict, List
import asyncio
import logging
from datetime import datetime

from ..common.types import (
    BaseModel, JsonDict, Result,
    GenerationStatus
)
from ..models.prompts import PromptSet, ProcessedPrompt, PromptTemplate
from ..models.context import GenerationContext
from ..models.generation import GenerationRequest, GenerationResult
from ..models.batch import BatchOperation
from ..errors import ErrorHandler, ErrorCategory, ErrorLevel
from .prompt import PromptManager
from .queue import GenerationQueueManager
from .dependency import DependencyManager
from .context_preservation import ContextPreservationService

@dataclass
class GenerationConfig(BaseModel):
    """Configuration for generation operations."""
    max_retries: int = 3
    timeout: int = 30
    batch_size: int = 5
    preserve_context: bool = True
    max_concurrent: int = 3
    auto_retry: bool = True

@dataclass
class GenerationRequest(BaseModel):
    """Complete generation request with all necessary context."""
    field_name: str
    prompt_set: PromptSet
    input_context: JsonDict
    base_context: Optional[JsonDict] = None
    user_input: Optional[str] = None
    metadata: JsonDict = field(default_factory=dict)
    priority: int = 0

class GenerationService:
    """Service for handling all generation operations."""
    
    def __init__(self,
                 prompt_manager: PromptManager,
                 queue_manager: GenerationQueueManager,
                 dependency_manager: DependencyManager,
                 context_service: ContextPreservationService,
                 error_handler: ErrorHandler,
                 config: Optional[GenerationConfig] = None):
        self.prompt_manager = prompt_manager
        self.queue_manager = queue_manager
        self.dependency_manager = dependency_manager
        self.context_service = context_service
        self.error_handler = error_handler
        self.config = config or GenerationConfig()
        
        self.logger = logging.getLogger(__name__)
        self._processing_lock = asyncio.Lock()

    async def generate_field(self, request: GenerationRequest) -> Result[str]:
        """Queue a field for generation."""
        try:
            # Validate prompt template
            template = request.prompt_set.get_prompt_for_field(request.field_name)
            if not template:
                return Result(False, f"No prompt template found for {request.field_name}")

            # Get or create context
            context_result = await self._prepare_generation_context(request)
            if not context_result.success:
                return context_result

            # Queue generation request
            queue_result = await self.queue_manager.queue_generation(
                field=request.field_name,
                prompt_set=request.prompt_set,
                context=context_result.data.base_context,
                user_input=request.user_input,
                priority=request.priority
            )
            
            if not queue_result.success:
                return queue_result

            self.logger.info(f"Field queued for generation: {request.field_name}")
            return Result(True, "Generation queued successfully", queue_result.data)

        except Exception as e:
            self.error_handler.handle_error(
                e,
                ErrorCategory.GENERATION,
                ErrorLevel.ERROR,
                {'operation': 'generate_field', 'field': request.field_name}
            )
            return Result(False, f"Failed to queue generation: {str(e)}", error=e)

    async def create_batch_generation(self,
                                    fields: List[str],
                                    prompt_set: PromptSet,
                                    base_context: JsonDict,
                                    name: Optional[str] = None) -> Result[str]:
        """Create and queue a batch generation operation."""
        try:
            # Create batch
            batch_result = await self.queue_manager.create_batch(
                name=name or f"Batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                description=f"Batch generation for fields: {', '.join(fields)}"
            )
            
            if not batch_result.success:
                return batch_result

            batch_id = batch_result.data
            
            # Queue each field
            for field in fields:
                request = GenerationRequest(
                    field_name=field,
                    prompt_set=prompt_set,
                    input_context=base_context,
                    metadata={'batch_id': batch_id}
                )
                
                result = await self.generate_field(request)
                if result.success:
                    await self.queue_manager.add_to_batch(batch_id, result.data)
                else:
                    self.logger.warning(f"Failed to queue field {field} in batch: {result.message}")

            return Result(True, "Batch generation created successfully", batch_id)

        except Exception as e:
            self.error_handler.handle_error(
                e,
                ErrorCategory.GENERATION,
                ErrorLevel.ERROR,
                {'operation': 'create_batch'}
            )
            return Result(False, f"Failed to create batch generation: {str(e)}", error=e)

    async def process_next(self) -> Result:
        """Process next generation in queue."""
        try:
            async with self._processing_lock:
                # Get next generation
                next_result = await self.queue_manager.get_next_generation()
                if not next_result.success:
                    return next_result

                request = next_result.data
                
                # Get context
                context_result = await self.context_service.get_context(request.field_name)
                if not context_result.success:
                    return context_result

                # Process template
                template = request.prompt_set.get_prompt_for_field(request.field_name)
                if not template:
                    return Result(False, f"No template found for {request.field_name}")

                process_result = await self._process_generation(
                    template,
                    context_result.data,
                    request
                )

                if not process_result.success:
                    return process_result

                # Complete generation
                return await self.queue_manager.complete_generation(
                    str(request.id),
                    process_result.data,
                    {'processed_at': datetime.now().isoformat()}
                )

        except Exception as e:
            self.error_handler.handle_error(
                e,
                ErrorCategory.GENERATION,
                ErrorLevel.ERROR,
                {'operation': 'process_next'}
            )
            return Result(False, f"Failed to process generation: {str(e)}", error=e)

    async def _prepare_generation_context(self,
                                        request: GenerationRequest) -> Result[GenerationContext]:
        """Prepare context for generation."""
        try:
            # Get existing context or create new
            context_result = await self.context_service.get_context(request.field_name)
            
            base_context = request.base_context or {}
            if request.input_context:
                base_context.update(request.input_context)

            if context_result.success and not request.base_context:
                # Update existing context
                context = context_result.data
                return await self.context_service.update_context(
                    request.field_name,
                    base_context,
                    create_new=False
                )
            else:
                # Create new context
                new_context = GenerationContext(
                    field_name=request.field_name,
                    base_context=base_context,
                    metadata=request.metadata
                )
                return await self.context_service.store_context(new_context)

        except Exception as e:
            self.error_handler.handle_error(
                e,
                ErrorCategory.GENERATION,
                ErrorLevel.ERROR,
                {'operation': 'prepare_context', 'field': request.field_name}
            )
            return Result(False, f"Failed to prepare context: {str(e)}", error=e)

    async def _process_generation(self,
                                template: PromptTemplate,
                                context: GenerationContext,
                                request: GenerationRequest) -> Result[str]:
        """Process actual generation using template and context."""
        try:
            # Generate content based on template and context
            # This would typically interface with an LLM or other generation system
            # For now we'll just return a placeholder
            content = f"Generated content for {request.field_name}"
            return Result(True, "Content generated successfully", content)

        except Exception as e:
            self.error_handler.handle_error(
                e,
                ErrorCategory.GENERATION,
                ErrorLevel.ERROR,
                {'operation': 'process_generation', 'field': request.field_name}
            )
            return Result(False, f"Failed to process generation: {str(e)}", error=e)

    async def get_generation_status(self, request_id: str) -> Result[GenerationStatus]:
        """Get status of a specific generation."""
        return await self.queue_manager.get_generation_status(request_id)

    async def cancel_generation(self, request_id: str) -> Result:
        """Cancel a pending or in-progress generation."""
        try:
            # Cancel in queue
            cancel_result = await self.queue_manager.cancel_generation(request_id)
            if not cancel_result.success:
                return cancel_result

            # Clear context if needed
            context_result = await self.context_service.get_context(request_id)
            if context_result.success:
                context_result.data.metadata['cancelled_at'] = datetime.now().isoformat()
                await self.context_service.store_context(context_result.data)

            return Result(True, "Generation cancelled successfully")

        except Exception as e:
            self.error_handler.handle_error(
                e,
                ErrorCategory.GENERATION,
                ErrorLevel.ERROR,
                {'operation': 'cancel_generation', 'request_id': request_id}
            )
            return Result(False, f"Failed to cancel generation: {str(e)}", error=e)