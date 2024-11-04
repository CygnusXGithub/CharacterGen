# core/services/generation_tracking.py
"""Service for tracking generation requests and results."""
from dataclasses import dataclass, field
from typing import Optional, Dict, List
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
from ..errors import ErrorHandler, StateError, ErrorCategory, ErrorLevel

@dataclass
class GenerationMetrics(BaseModel):
    """Metrics for generation operations."""
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[int] = None
    token_count: Optional[int] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    retries: int = 0
    custom_metrics: JsonDict = field(default_factory=dict)

    @property
    def is_complete(self) -> bool:
        """Check if metrics are complete."""
        return self.end_time is not None and self.duration_ms is not None

    def complete(self, end_time: Optional[datetime] = None) -> None:
        """Complete metrics tracking."""
        self.end_time = end_time or datetime.now()
        self.duration_ms = int((self.end_time - self.start_time).total_seconds() * 1000)

@dataclass
class GenerationContext(BaseModel):
    """Context for generation operations."""
    request: GenerationRequest
    metrics: GenerationMetrics
    dependencies: Dict[str, str] = field(default_factory=dict)
    metadata: JsonDict = field(default_factory=dict)

class GenerationTrackingService:
    """Service for tracking generation requests and results."""

    def __init__(self, error_handler: ErrorHandler, max_concurrent: int = 3):
        self.error_handler = error_handler
        self.logger = logging.getLogger(__name__)
        self.max_concurrent = max_concurrent
        
        self._queue = GenerationQueue()
        self._contexts: Dict[str, GenerationContext] = {}
        self._lock = asyncio.Lock()
        self._current_generations = 0
        
    async def queue_generation(self, request: GenerationRequest) -> Result[str]:
        """Queue a new generation request."""
        try:
            async with self._lock:
                # Create tracking context
                context = GenerationContext(
                    request=request,
                    metrics=GenerationMetrics(start_time=datetime.now()),
                    dependencies=request.dependencies,
                    metadata={'queued_at': datetime.now().isoformat()}
                )
                
                # Store context
                self._contexts[str(request.id)] = context
                
                # Add to pending queue
                self._queue.pending.append(request)
                
                # Sort by priority
                self._queue.pending.sort(key=lambda r: (-r.priority, r.created_at))
                
                self.logger.info(f"Generation queued: {request.id}")
                return Result(True, "Generation queued successfully", str(request.id))
                
        except Exception as e:
            self.error_handler.handle_error(
                e,
                ErrorCategory.GENERATION,
                ErrorLevel.ERROR,
                {'operation': 'queue_generation'}
            )
            return Result(False, f"Failed to queue generation: {str(e)}", error=e)

    async def start_next_generation(self) -> Result[GenerationRequest]:
        """Start the next pending generation if possible."""
        try:
            async with self._lock:
                if (self._current_generations >= self.max_concurrent or 
                    not self._queue.pending):
                    return Result(False, "No generations can be started")

                # Get next request
                request = self._queue.pending.pop(0)
                self._queue.in_progress[str(request.id)] = request
                self._current_generations += 1
                
                # Update context
                if str(request.id) in self._contexts:
                    context = self._contexts[str(request.id)]
                    context.metadata['started_at'] = datetime.now().isoformat()
                
                self.logger.info(f"Generation started: {request.id}")
                return Result(True, "Generation started successfully", request)
                
        except Exception as e:
            self.error_handler.handle_error(
                e,
                ErrorCategory.GENERATION,
                ErrorLevel.ERROR,
                {'operation': 'start_generation'}
            )
            return Result(False, f"Failed to start generation: {str(e)}", error=e)

    async def complete_generation(self, 
                                request_id: str, 
                                content: str,
                                metrics: Optional[JsonDict] = None) -> Result[GenerationResult]:
        """Mark a generation as complete."""
        try:
            async with self._lock:
                if request_id not in self._queue.in_progress:
                    return Result(False, f"No active generation for ID {request_id}")

                request = self._queue.in_progress.pop(request_id)
                self._current_generations -= 1
                
                # Update context and metrics
                context = self._contexts.get(request_id)
                if context:
                    context.metrics.complete()
                    if metrics:
                        context.metrics.custom_metrics.update(metrics)
                    context.metadata['completed_at'] = datetime.now().isoformat()

                # Create result
                result = GenerationResult(
                    request_id=request_id,
                    field_name=request.field_name,
                    content=content,
                    status=GenerationStatus.COMPLETED,
                    start_time=request.created_at,
                    end_time=datetime.now(),
                    duration_ms=context.metrics.duration_ms if context else None,
                    retry_count=request.retry_count,
                    metrics=metrics or {}
                )

                self._queue.completed[request_id] = result
                self.logger.info(f"Generation completed: {request_id}")
                return Result(True, "Generation completed successfully", result)

        except Exception as e:
            self.error_handler.handle_error(
                e,
                ErrorCategory.GENERATION,
                ErrorLevel.ERROR,
                {'operation': 'complete_generation', 'request_id': request_id}
            )
            return Result(False, f"Failed to complete generation: {str(e)}", error=e)

    async def fail_generation(self, 
                            request_id: str, 
                            error_message: str,
                            should_retry: bool = True) -> Result[GenerationResult]:
        """Mark a generation as failed."""
        try:
            async with self._lock:
                if request_id not in self._queue.in_progress:
                    return Result(False, f"No active generation for ID {request_id}")

                request = self._queue.in_progress.pop(request_id)
                self._current_generations -= 1
                
                # Update context
                context = self._contexts.get(request_id)
                if context:
                    context.metrics.complete()
                    context.metadata['failed_at'] = datetime.now().isoformat()
                    context.metadata['error_message'] = error_message

                # Create failed result
                result = GenerationResult(
                    request_id=request_id,
                    field_name=request.field_name,
                    content="",
                    status=GenerationStatus.FAILED,
                    start_time=request.created_at,
                    end_time=datetime.now(),
                    error_message=error_message,
                    retry_count=request.retry_count,
                    metrics=context.metrics.custom_metrics if context else {}
                )

                # Handle retry if needed
                if should_retry and request.retry_count < request.max_retries:
                    request.retry_count += 1
                    self._queue.pending.append(request)
                    self.logger.info(f"Generation failed, retrying: {request_id}")
                else:
                    self._queue.failed[request_id] = result
                    self.logger.error(f"Generation failed: {request_id}")

                return Result(True, "Generation failure handled", result)

        except Exception as e:
            self.error_handler.handle_error(
                e,
                ErrorCategory.GENERATION,
                ErrorLevel.ERROR,
                {'operation': 'fail_generation', 'request_id': request_id}
            )
            return Result(False, f"Failed to handle generation failure: {str(e)}", error=e)
    
    def get_queue_status(self) -> Result[JsonDict]:
        """Get current queue statistics."""
        try:
            status = {
                'pending': len(self._queue.pending),
                'in_progress': self._current_generations,
                'completed': len(self._queue.completed),
                'failed': len(self._queue.failed),
                'cancelled': len(self._queue.cancelled)
            }
            return Result(True, "Queue status retrieved successfully", status)
        except Exception as e:
            return Result(False, f"Failed to get queue status: {str(e)}", error=e)

    def get_generation_status(self, request_id: str) -> Result[GenerationStatus]:
        """Get status of a specific generation request."""
        try:
            if request_id in self._queue.in_progress:
                return Result(True, "Status retrieved", GenerationStatus.IN_PROGRESS)
            elif request_id in self._queue.completed:
                return Result(True, "Status retrieved", GenerationStatus.COMPLETED)
            elif request_id in self._queue.failed:
                return Result(True, "Status retrieved", GenerationStatus.FAILED)
            elif request_id in self._queue.cancelled:
                return Result(True, "Status retrieved", GenerationStatus.CANCELLED)
            
            for request in self._queue.pending:
                if str(request.id) == request_id:
                    return Result(True, "Status retrieved", GenerationStatus.QUEUED)
                    
            return Result(False, f"No generation found with ID {request_id}")
            
        except Exception as e:
            return Result(False, f"Failed to get generation status: {str(e)}", error=e)

    async def cancel_generation(self, request_id: str) -> Result:
        """Cancel a pending or in-progress generation."""
        try:
            async with self._lock:
                # Check pending
                for i, request in enumerate(self._queue.pending):
                    if str(request.id) == request_id:
                        self._queue.pending.pop(i)
                        
                        context = self._contexts.get(request_id)
                        if context:
                            context.metadata['cancelled_at'] = datetime.now().isoformat()
                        
                        # Create cancelled result
                        result = GenerationResult(
                            request_id=request_id,
                            field_name=request.field_name,
                            content="",
                            status=GenerationStatus.CANCELLED,
                            start_time=request.created_at,
                            end_time=datetime.now()
                        )
                        
                        self._queue.cancelled[request_id] = result
                        self.logger.info(f"Generation cancelled: {request_id}")
                        return Result(True, "Generation cancelled successfully")

                # Check in-progress
                if request_id in self._queue.in_progress:
                    request = self._queue.in_progress.pop(request_id)
                    self._current_generations -= 1
                    
                    context = self._contexts.get(request_id)
                    if context:
                        context.metadata['cancelled_at'] = datetime.now().isoformat()
                    
                    result = GenerationResult(
                        request_id=request_id,
                        field_name=request.field_name,
                        content="",
                        status=GenerationStatus.CANCELLED,
                        start_time=request.created_at,
                        end_time=datetime.now()
                    )
                    
                    self._queue.cancelled[request_id] = result
                    self.logger.info(f"Generation cancelled: {request_id}")
                    return Result(True, "Generation cancelled successfully")

                return Result(False, f"No active generation found with ID {request_id}")

        except Exception as e:
            self.error_handler.handle_error(
                e,
                ErrorCategory.GENERATION,
                ErrorLevel.ERROR,
                {'operation': 'cancel_generation', 'request_id': request_id}
            )
            return Result(False, f"Failed to cancel generation: {str(e)}", error=e)

    def get_metrics(self, request_id: str) -> Result[GenerationMetrics]:
        """Get metrics for a generation."""
        try:
            context = self._contexts.get(request_id)
            if not context:
                return Result(False, f"No metrics found for ID {request_id}")
                
            return Result(True, "Metrics retrieved successfully", context.metrics)
            
        except Exception as e:
            return Result(False, f"Failed to get metrics: {str(e)}", error=e)

    def clear_completed(self, max_age: Optional[int] = None):
        """Clear completed generations older than max_age seconds."""
        if max_age is None:
            self._queue.completed.clear()
            return
            
        now = datetime.now()
        to_remove = [
            req_id for req_id, result in self._queue.completed.items()
            if (now - result.end_time).total_seconds() > max_age
        ]
        
        for req_id in to_remove:
            del self._queue.completed[req_id]
            if req_id in self._contexts:
                del self._contexts[req_id]

    def cleanup(self):
        """Clean up service state."""
        self._queue = GenerationQueue()
        self._contexts.clear()
        self._current_generations = 0