from typing import Optional, Dict, List, Any
import asyncio
import logging
from datetime import datetime
from uuid import UUID, uuid4

from ..models.generation import (
    GenerationRequest, GenerationResult, GenerationQueue, GenerationStatus
)
from ..errors import ErrorHandler, StateError, ErrorCategory, ErrorLevel

class GenerationTrackingService:
    """Service for tracking generation requests and results"""

    def __init__(self, error_handler: ErrorHandler):
        self.error_handler = error_handler
        self.logger = logging.getLogger(__name__)
        self._queue = GenerationQueue()
        self._lock = asyncio.Lock()
        self._max_concurrent = 3
        self._current_generations = 0

    def _reset_state(self):
        """Reset the service state (for testing)"""
        self._queue = GenerationQueue()
        self._current_generations = 0
        self._active_contexts = {}

    async def queue_generation(self, request: GenerationRequest) -> UUID:
        """Queue a new generation request"""
        try:
            async with self._lock:
                # Add to pending queue
                self._queue.pending.append(request)
                # Sort by priority
                self._queue.pending.sort(key=lambda r: (-r.priority, r.created_at))
                return request.id
        except Exception as e:
            self.error_handler.handle_error(
                error=e,
                category=ErrorCategory.GENERATION,
                level=ErrorLevel.ERROR,
                context={'operation': 'queue_generation'}
            )
            raise

    async def start_next_generation(self) -> Optional[GenerationRequest]:
        """Start the next pending generation if possible"""
        try:
            async with self._lock:
                if (self._current_generations >= self._max_concurrent or 
                    not self._queue.pending):
                    return None

                # Get next request
                request = self._queue.pending.pop(0)
                self._queue.in_progress[request.id] = request
                self._current_generations += 1
                return request

        except Exception as e:
            self.error_handler.handle_error(
                error=e,
                category=ErrorCategory.GENERATION,
                level=ErrorLevel.ERROR,
                context={'operation': 'start_generation'}
            )
            return None

    async def complete_generation(self, 
                                request_id: UUID, 
                                content: str,
                                metrics: Optional[Dict[str, Any]] = None) -> GenerationResult:
        """Mark a generation as complete"""
        try:
            async with self._lock:
                if request_id not in self._queue.in_progress:
                    raise StateError(f"No active generation for ID {request_id}")

                request = self._queue.in_progress.pop(request_id)
                self._current_generations -= 1

                # Create result
                end_time = datetime.now()
                result = GenerationResult(
                    request_id=request_id,
                    field_name=request.field_name,
                    content=content,
                    status=GenerationStatus.COMPLETED,
                    start_time=request.created_at,
                    end_time=end_time,
                    duration_ms=int((end_time - request.created_at).total_seconds() * 1000),
                    retry_count=request.retry_count,
                    metrics=metrics or {}
                )

                self._queue.completed[request_id] = result
                return result

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
                            should_retry: bool = True) -> GenerationResult:
        """Mark a generation as failed"""
        try:
            async with self._lock:
                if request_id not in self._queue.in_progress:
                    raise StateError(f"No active generation for ID {request_id}")

                request = self._queue.in_progress.pop(request_id)
                self._current_generations -= 1

                # Create failed result
                result = GenerationResult(
                    request_id=request_id,
                    field_name=request.field_name,
                    content="",
                    status=GenerationStatus.FAILED,
                    start_time=request.created_at,
                    end_time=datetime.now(),
                    error_message=error_message,
                    retry_count=request.retry_count
                )

                # Handle retry if needed
                if should_retry and request.retry_count < request.max_retries:
                    request.retry_count += 1
                    self._queue.pending.append(request)
                else:
                    self._queue.failed[request_id] = result

                return result

        except Exception as e:
            self.error_handler.handle_error(
                error=e,
                category=ErrorCategory.GENERATION,
                level=ErrorLevel.ERROR,
                context={'operation': 'fail_generation', 'request_id': str(request_id)}
            )
            raise
    
    def get_queue_status(self) -> Dict[str, int]:
        """Get current queue status"""
        return {
            'pending': len(self._queue.pending),
            'in_progress': self._current_generations,
            'completed': len(self._queue.completed),
            'failed': len(self._queue.failed),
            'cancelled': len(self._queue.cancelled)
        }

    def get_generation_status(self, request_id: UUID) -> Optional[GenerationStatus]:
        """Get status of a specific generation request"""
        if request_id in self._queue.in_progress:
            return GenerationStatus.IN_PROGRESS
        elif request_id in self._queue.completed:
            return GenerationStatus.COMPLETED
        elif request_id in self._queue.failed:
            return GenerationStatus.FAILED
        elif request_id in self._queue.cancelled:
            return GenerationStatus.CANCELLED
        
        for request in self._queue.pending:
            if request.id == request_id:
                return GenerationStatus.QUEUED
                
        return None

    async def cancel_generation(self, request_id: UUID) -> bool:
        """Cancel a pending or in-progress generation"""
        try:
            async with self._lock:
                # Check pending
                for i, request in enumerate(self._queue.pending):
                    if request.id == request_id:
                        self._queue.pending.pop(i)
                        
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
                        return True

                # Check in-progress
                if request_id in self._queue.in_progress:
                    request = self._queue.in_progress.pop(request_id)
                    self._current_generations -= 1
                    
                    result = GenerationResult(
                        request_id=request_id,
                        field_name=request.field_name,
                        content="",
                        status=GenerationStatus.CANCELLED,
                        start_time=request.created_at,
                        end_time=datetime.now()
                    )
                    
                    self._queue.cancelled[request_id] = result
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