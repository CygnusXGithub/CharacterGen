from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from ..models.generation import GenerationRequest, GenerationResult, GenerationStatus
from ..models.prompts import PromptSet
from .prompt import PromptManager
from .dependency import DependencyManager
from ..errors import ErrorHandler, ErrorCategory, ErrorLevel

@dataclass
class QueuedGeneration:
    """Detailed information about a queued generation"""
    request: GenerationRequest
    dependencies: Set[UUID]     # IDs of other requests this depends on
    prompt_set: PromptSet
    user_input: Optional[str] = None
    priority: int = 0
    queued_at: datetime = field(default_factory=datetime.now)

class GenerationQueueManager:
    """Manages generation requests with dependencies and priorities"""
    
    def __init__(self, 
                 prompt_manager: PromptManager,
                 dependency_manager: DependencyManager,
                 error_handler: ErrorHandler,
                 max_concurrent: int = 3):
        self.prompt_manager = prompt_manager
        self.dependency_manager = dependency_manager
        self.error_handler = error_handler
        self.max_concurrent = max_concurrent
        
        # Queue storage
        self._queued: Dict[UUID, QueuedGeneration] = {}
        self._active: Dict[UUID, QueuedGeneration] = {}
        self._completed: Dict[UUID, GenerationResult] = {}
        self._failed: Dict[UUID, GenerationResult] = {}
        
        # Track dependencies
        self._blocking: Dict[UUID, Set[UUID]] = {}  # Request -> Requests it blocks
        
    async def queue_generation(self,
                            field: str,
                            prompt_set: PromptSet,
                            context: Dict[str, Any],
                            user_input: Optional[str] = None,
                            priority: int = 0) -> UUID:
        """Queue a new generation request"""
        try:
            request_id = uuid4()
            request = GenerationRequest(
                field_name=field,
                input_context=context,  # Changed from context to input_context
                base_prompt_name=prompt_set.name,
                base_prompt_version=prompt_set.version,
                priority=priority,
                id=request_id
            )
            
            # Create generation entry
            generation = QueuedGeneration(
                request=request,
                dependencies=set(),
                prompt_set=prompt_set,
                user_input=user_input,
                priority=priority
            )
            
            # Add to queue
            self._queued[request_id] = generation
            
            # Setup dependencies based on prompt set
            self._setup_dependencies(generation)
            
            return request_id
            
        except Exception as e:
            self.error_handler.handle_error(
                error=e,
                category=ErrorCategory.GENERATION,
                level=ErrorLevel.ERROR,
                context={'operation': 'queue_generation', 'field': field}
            )
            raise
    
    def _setup_dependencies(self, generation: QueuedGeneration):
        """Setup dependencies for a generation request"""
        dependencies = self.dependency_manager.get_field_dependencies(
            generation.request.field_name,
            generation.prompt_set
        )
        
        # Look for active or queued generations for dependent fields
        for dep_field in dependencies:
            for req_id, req in {**self._queued, **self._active}.items():
                if req.request.field_name == dep_field:
                    # Add dependency
                    generation.dependencies.add(req_id)
                    # Track what this request blocks
                    if req_id not in self._blocking:
                        self._blocking[req_id] = set()
                    self._blocking[req_id].add(generation.request.id)

    async def get_next_generation(self) -> Optional[GenerationRequest]:
        """Get next generation that's ready to process"""
        if len(self._active) >= self.max_concurrent:
            return None
            
        # Find requests with no dependencies
        ready = [
            (req_id, gen) for req_id, gen in self._queued.items()
            if not gen.dependencies
        ]
        
        if not ready:
            return None
            
        # Sort first by dependencies (fields that come earlier in generation order)
        def get_field_order(gen: QueuedGeneration) -> int:
            try:
                return gen.prompt_set.generation_order.index(gen.request.field_name)
            except ValueError:
                return len(gen.prompt_set.generation_order)
        
        # Sort by:
        # 1. Generation order
        # 2. Priority
        # 3. Queue time
        ready.sort(key=lambda x: (
            get_field_order(x[1]),
            -x[1].priority,
            x[1].queued_at
        ))
        
        # Get highest priority request
        req_id, generation = ready[0]
        
        # Move to active
        self._queued.pop(req_id)
        self._active[req_id] = generation
    
        return generation.request

    
    async def complete_generation(self,
                                request_id: UUID,
                                result: str,
                                metrics: Optional[Dict[str, Any]] = None) -> GenerationResult:
        """Mark a generation as complete and update dependencies"""
        try:
            if request_id not in self._active:
                raise ValueError(f"No active generation for ID {request_id}")
                
            generation = self._active.pop(request_id)
            
            # Create result
            gen_result = GenerationResult(
                request_id=request_id,
                field_name=generation.request.field_name,
                content=result,
                status=GenerationStatus.COMPLETED,
                start_time=generation.queued_at,
                end_time=datetime.now(),
                metrics=metrics or {}
            )
            
            # Store result
            self._completed[request_id] = gen_result
            
            # Update dependencies
            if request_id in self._blocking:
                blocked_requests = self._blocking.pop(request_id)
                for blocked_id in blocked_requests:
                    if blocked_id in self._queued:
                        self._queued[blocked_id].dependencies.remove(request_id)
            
            return gen_result
            
        except Exception as e:
            self.error_handler.handle_error(
                error=e,
                category=ErrorCategory.GENERATION,
                level=ErrorLevel.ERROR,
                context={'operation': 'complete_generation', 'request_id': str(request_id)}
            )
            raise

    async def fail_generation(self,
                            request_id: UUID,
                            error_message: str,
                            should_retry: bool = True,
                            retry_count: int = 3) -> GenerationResult:
        """Handle failed generation"""
        try:
            # Check if generation is active or queued
            generation = None
            if request_id in self._active:
                generation = self._active.pop(request_id)
            elif request_id in self._queued:
                generation = self._queued.pop(request_id)
            
            if not generation:
                raise ValueError(f"No generation found for ID {request_id}")
            
            # Create failure result
            gen_result = GenerationResult(
                request_id=request_id,
                field_name=generation.request.field_name,
                content="",
                status=GenerationStatus.FAILED,
                start_time=generation.queued_at,
                end_time=datetime.now(),
                error_message=error_message
            )
            
            if should_retry and generation.request.retry_count < retry_count:
                # Requeue with increased retry count
                generation.request.retry_count += 1
                self._queued[request_id] = generation
            else:
                # Store as failed
                self._failed[request_id] = gen_result
                
                # Clean up dependencies
                if request_id in self._blocking:
                    # Fail all dependent requests
                    blocked_requests = self._blocking.pop(request_id)
                    for blocked_id in blocked_requests:
                        # Create failure results for dependent requests
                        dep_gen = None
                        if blocked_id in self._queued:
                            dep_gen = self._queued.pop(blocked_id)
                        elif blocked_id in self._active:
                            dep_gen = self._active.pop(blocked_id)
                            
                        if dep_gen:
                            dep_result = GenerationResult(
                                request_id=blocked_id,
                                field_name=dep_gen.request.field_name,
                                content="",
                                status=GenerationStatus.FAILED,
                                start_time=dep_gen.queued_at,
                                end_time=datetime.now(),
                                error_message=f"Dependent generation {request_id} failed"
                            )
                            self._failed[blocked_id] = dep_result
            
            return gen_result
            
        except Exception as e:
            self.error_handler.handle_error(
                error=e,
                category=ErrorCategory.GENERATION,
                level=ErrorLevel.ERROR,
                context={'operation': 'fail_generation', 'request_id': str(request_id)}
            )
            raise

    async def cancel_generation(self, request_id: UUID) -> bool:
        """Cancel a queued or active generation"""
        try:
            # Check queued
            if request_id in self._queued:
                generation = self._queued.pop(request_id)
                
                # Clean up dependencies
                if request_id in self._blocking:
                    blocked_requests = self._blocking.pop(request_id)
                    for blocked_id in blocked_requests:
                        await self.cancel_generation(blocked_id)
                
                return True
                
            # Check active
            if request_id in self._active:
                generation = self._active.pop(request_id)
                
                # Clean up dependencies
                if request_id in self._blocking:
                    blocked_requests = self._blocking.pop(request_id)
                    for blocked_id in blocked_requests:
                        await self.cancel_generation(blocked_id)
                
                return True
                
            return False
            
        except Exception as e:
            self.error_handler.handle_error(
                error=e,
                category=ErrorCategory.GENERATION,
                level=ErrorLevel.ERROR,
                context={'operation': 'cancel_generation', 'request_id': str(request_id)}
            )
            return False

    def get_queue_status(self) -> Dict[str, int]:
        """Get current queue statistics"""
        return {
            'queued': len(self._queued),
            'active': len(self._active),
            'completed': len(self._completed),
            'failed': len(self._failed)
        }

    def get_generation_status(self, request_id: UUID) -> Optional[GenerationStatus]:
        """Get status of a specific generation request"""
        if request_id in self._queued:
            return GenerationStatus.QUEUED
        elif request_id in self._active:
            return GenerationStatus.IN_PROGRESS
        elif request_id in self._completed:
            return GenerationStatus.COMPLETED
        elif request_id in self._failed:
            return GenerationStatus.FAILED
        return None

    def clear_completed(self, max_age: Optional[int] = None):
        """Clear completed generations older than max_age seconds"""
        if max_age is None:
            self._completed.clear()
            return
            
        now = datetime.now()
        to_remove = [
            req_id for req_id, result in self._completed.items()
            if (now - result.end_time).total_seconds() > max_age
        ]
        
        for req_id in to_remove:
            del self._completed[req_id]

    def clear_failed(self, max_age: Optional[int] = None):
        """Clear failed generations older than max_age seconds"""
        if max_age is None:
            self._failed.clear()
            return
            
        now = datetime.now()
        to_remove = [
            req_id for req_id, result in self._failed.items()
            if (now - result.end_time).total_seconds() > max_age
        ]
        
        for req_id in to_remove:
            del self._failed[req_id]