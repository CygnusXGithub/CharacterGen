# core/services/queue.py
"""Service for managing generation queue and dependencies."""
from dataclasses import dataclass, field
from typing import Dict, Optional, Set, List
import asyncio
import logging
from datetime import datetime

from ..common.types import (
    BaseModel, JsonDict, Result,
    GenerationStatus
)
from ..models.generation import (
    GenerationRequest, GenerationResult, GenerationQueue
)
from ..models.batch import BatchOperation, BatchStatus, BatchProgress
from ..models.prompts import PromptSet
from .prompt import PromptManager
from .dependency import DependencyManager
from ..errors import ErrorHandler, ErrorCategory, ErrorLevel

@dataclass
class QueuedGeneration(BaseModel):
    """Detailed information about a queued generation."""
    request: GenerationRequest
    dependencies: Set[str]      # IDs of other requests this depends on
    prompt_set: PromptSet
    user_input: Optional[str] = None
    priority: int = 0
    metadata: JsonDict = field(default_factory=dict)

class GenerationQueueManager:
    """Manages generation requests with dependencies and priorities."""
    
    def __init__(self,
                 prompt_manager: PromptManager,
                 dependency_manager: DependencyManager,
                 error_handler: ErrorHandler,
                 max_concurrent: int = 3):
        self.prompt_manager = prompt_manager
        self.dependency_manager = dependency_manager
        self.error_handler = error_handler
        self.max_concurrent = max_concurrent
        self.logger = logging.getLogger(__name__)
        
        # Queue storage
        self._queued: Dict[str, QueuedGeneration] = {}
        self._active: Dict[str, QueuedGeneration] = {}
        self._completed: Dict[str, GenerationResult] = {}
        self._failed: Dict[str, GenerationResult] = {}
        
        # Dependency tracking
        self._blocking: Dict[str, Set[str]] = {}  # Request -> Requests it blocks
        
        # Batch tracking
        self._batches: Dict[str, BatchOperation] = {}
        self._request_to_batch: Dict[str, str] = {}
        
        # Locks
        self._queue_lock = asyncio.Lock()
        self._batch_lock = asyncio.Lock()
    
    async def create_batch(self,
                          name: str,
                          description: str = "",
                          parent_batch_id: Optional[str] = None) -> Result[str]:
        """Create a new batch operation."""
        try:
            async with self._batch_lock:
                batch = BatchOperation(
                    name=name,
                    description=description,
                    parent_batch_id=parent_batch_id
                )
                self._batches[str(batch.id)] = batch
                return Result(True, "Batch created successfully", str(batch.id))
        except Exception as e:
            return Result(False, f"Failed to create batch: {str(e)}", error=e)
    
    async def add_to_batch(self,
                          batch_id: str,
                          request_id: str) -> Result:
        """Add a request to a batch."""
        try:
            async with self._batch_lock:
                if batch_id not in self._batches or request_id in self._request_to_batch:
                    return Result(False, "Invalid batch or request")
                    
                batch = self._batches[batch_id]
                batch.request_ids.add(request_id)
                self._request_to_batch[request_id] = batch_id
                return Result(True, "Request added to batch successfully")
        except Exception as e:
            return Result(False, f"Failed to add to batch: {str(e)}", error=e)

    async def queue_generation(self,
                             field: str,
                             prompt_set: PromptSet,
                             context: JsonDict,
                             user_input: Optional[str] = None,
                             priority: int = 0) -> Result[str]:
        """Queue a new generation request."""
        try:
            async with self._queue_lock:
                # Create generation request
                request = GenerationRequest(
                    field_name=field,
                    input_context=context,
                    base_prompt_name=str(prompt_set.name),
                    base_prompt_version=str(prompt_set.version),
                    priority=priority
                )
                
                # Create queue entry
                generation = QueuedGeneration(
                    request=request,
                    dependencies=set(),
                    prompt_set=prompt_set,
                    user_input=user_input,
                    priority=priority,
                    metadata={'queued_at': datetime.now().isoformat()}
                )
                
                # Setup dependencies
                await self._setup_dependencies(generation)
                
                # Add to queue
                self._queued[str(request.id)] = generation
                
                self.logger.info(f"Generation queued: {request.id}")
                return Result(True, "Generation queued successfully", str(request.id))
                
        except Exception as e:
            self.error_handler.handle_error(
                e,
                ErrorCategory.GENERATION,
                ErrorLevel.ERROR,
                {'operation': 'queue_generation', 'field': field}
            )
            return Result(False, f"Failed to queue generation: {str(e)}", error=e)
    
    async def _setup_dependencies(self, generation: QueuedGeneration) -> Result:
        """Setup dependencies for a generation request."""
        try:
            deps_result = self.dependency_manager.get_field_dependencies(
                generation.request.field_name,
                generation.prompt_set
            )
            
            if not deps_result.success:
                return deps_result
            
            # Look for active or queued generations for dependent fields
            all_generations = {**self._queued, **self._active}
            for dep_field in deps_result.data:
                for req_id, req in all_generations.items():
                    if req.request.field_name == dep_field:
                        # Add dependency
                        generation.dependencies.add(req_id)
                        # Track what this request blocks
                        if req_id not in self._blocking:
                            self._blocking[req_id] = set()
                        self._blocking[req_id].add(str(generation.request.id))
            
            return Result(True, "Dependencies setup successfully")
            
        except Exception as e:
            return Result(False, f"Failed to setup dependencies: {str(e)}", error=e)

    async def get_next_generation(self) -> Result[GenerationRequest]:
        """Get next generation that's ready to process."""
        try:
            async with self._queue_lock:
                if len(self._active) >= self.max_concurrent:
                    return Result(False, "Maximum concurrent generations reached")
                
                # Find requests with no dependencies
                ready = [
                    (req_id, gen) for req_id, gen in self._queued.items()
                    if not gen.dependencies
                ]
                
                if not ready:
                    return Result(False, "No ready generations found")
                
                # Sort by generation order and priority
                def get_field_order(gen: QueuedGeneration) -> int:
                    try:
                        return gen.prompt_set.generation_order.index(gen.request.field_name)
                    except ValueError:
                        return len(gen.prompt_set.generation_order)
                
                ready.sort(key=lambda x: (
                    get_field_order(x[1]),
                    -x[1].priority,
                    x[1].request.created_at
                ))
                
                # Get highest priority request
                req_id, generation = ready[0]
                
                # Move to active
                self._queued.pop(req_id)
                self._active[req_id] = generation
                
                self.logger.info(f"Generation started: {req_id}")
                return Result(True, "Generation ready to start", generation.request)
                
        except Exception as e:
            self.error_handler.handle_error(
                e,
                ErrorCategory.GENERATION,
                ErrorLevel.ERROR,
                {'operation': 'get_next_generation'}
            )
            return Result(False, f"Failed to get next generation: {str(e)}", error=e)

    async def complete_generation(self,
                                request_id: str,
                                result: str,
                                metrics: Optional[JsonDict] = None) -> Result[GenerationResult]:
        """Mark a generation as complete and update dependencies."""
        try:
            async with self._queue_lock:
                if request_id not in self._active:
                    return Result(False, f"No active generation for ID {request_id}")
                    
                generation = self._active.pop(request_id)
                
                # Create result
                gen_result = GenerationResult(
                    request_id=request_id,
                    field_name=generation.request.field_name,
                    content=result,
                    status=GenerationStatus.COMPLETED,
                    start_time=generation.request.created_at,
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
                
                # Update batch if request is part of one
                await self._update_batch_progress(request_id)
                
                self.logger.info(f"Generation completed: {request_id}")
                return Result(True, "Generation completed successfully", gen_result)
                
        except Exception as e:
            self.error_handler.handle_error(
                e,
                ErrorCategory.GENERATION,
                ErrorLevel.ERROR,
                {'operation': 'complete_generation', 'request_id': request_id}
            )
            return Result(False, f"Failed to complete generation: {str(e)}", error=e)

    async def _update_batch_progress(self, request_id: str) -> Result:
        """Update batch progress after request completion."""
        try:
            async with self._batch_lock:
                if request_id not in self._request_to_batch:
                    return Result(True, "Request not part of a batch")
                    
                batch_id = self._request_to_batch[request_id]
                batch = self._batches[batch_id]
                
                # Get status for all requests in batch
                request_statuses = {}
                for req_id in batch.request_ids:
                    status = await self.get_generation_status(req_id)
                    if status.success:
                        request_statuses[req_id] = status.data
                
                # Update batch progress
                batch.update_progress(request_statuses)
                
                # Check if batch is complete
                if batch.status in [BatchStatus.COMPLETED, BatchStatus.PARTIALLY_COMPLETED]:
                    batch.completed_at = datetime.now()
                
                return Result(True, "Batch progress updated successfully")
                
        except Exception as e:
            return Result(False, f"Failed to update batch progress: {str(e)}", error=e)

    async def get_generation_status(self, request_id: str) -> Result[GenerationStatus]:
        """Get status of a specific generation request."""
        try:
            if request_id in self._active:
                return Result(True, "Status retrieved", GenerationStatus.IN_PROGRESS)
            elif request_id in self._completed:
                return Result(True, "Status retrieved", GenerationStatus.COMPLETED)
            elif request_id in self._failed:
                return Result(True, "Status retrieved", GenerationStatus.FAILED)
            elif request_id in self._queued:
                return Result(True, "Status retrieved", GenerationStatus.QUEUED)
            
            return Result(False, f"No generation found with ID {request_id}")
            
        except Exception as e:
            return Result(False, f"Failed to get generation status: {str(e)}", error=e)

    async def get_batch_progress(self, batch_id: str) -> Result[BatchProgress]:
        """Get current batch progress."""
        try:
            if batch_id not in self._batches:
                return Result(False, "Batch not found")
                
            batch = self._batches[batch_id]
            return Result(True, "Batch progress retrieved", batch.progress)
            
        except Exception as e:
            return Result(False, f"Failed to get batch progress: {str(e)}", error=e)

    def get_queue_stats(self) -> Result[JsonDict]:
        """Get current queue statistics."""
        try:
            stats = {
                'queued': len(self._queued),
                'active': len(self._active),
                'completed': len(self._completed),
                'failed': len(self._failed),
                'batches': len(self._batches)
            }
            return Result(True, "Queue stats retrieved successfully", stats)
        except Exception as e:
            return Result(False, f"Failed to get queue stats: {str(e)}", error=e)