# core/models/generation.py
"""Generation request and result models."""
from dataclasses import dataclass, field
from typing import Optional, Dict, List

from ..common.types import (
    BaseModel, JsonDict, GenerationStatus,
    Result, Timestamp
)

@dataclass
class GenerationRequest(BaseModel):
    """A request for content generation."""
    field_name: str
    input_context: JsonDict
    base_prompt_name: str
    base_prompt_version: str
    priority: int = 0
    dependencies: Dict[str, str] = field(default_factory=dict)
    generation_settings: JsonDict = field(default_factory=dict)
    retry_count: int = 0
    max_retries: int = 3
    
    def to_dict(self) -> JsonDict:
        """Convert request to dictionary."""
        data = super().to_dict()
        data.update({
            'field_name': self.field_name,
            'input_context': self.input_context,
            'base_prompt_name': self.base_prompt_name,
            'base_prompt_version': self.base_prompt_version,
            'priority': self.priority,
            'dependencies': self.dependencies,
            'generation_settings': self.generation_settings,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries
        })
        return data

@dataclass
class GenerationResult(BaseModel):
    """Result of a generation request."""
    request_id: str
    field_name: str
    content: str
    status: GenerationStatus
    start_time: Timestamp
    end_time: Optional[Timestamp] = None
    error_message: Optional[str] = None
    duration_ms: Optional[int] = None
    retry_count: int = 0
    metrics: JsonDict = field(default_factory=dict)
    
    def to_dict(self) -> JsonDict:
        """Convert result to dictionary."""
        data = super().to_dict()
        data.update({
            'request_id': self.request_id,
            'field_name': self.field_name,
            'content': self.content,
            'status': self.status.name,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'error_message': self.error_message,
            'duration_ms': self.duration_ms,
            'retry_count': self.retry_count,
            'metrics': self.metrics
        })
        return data

    @classmethod
    def create_error(cls, request_id: str, field_name: str, error: Exception) -> 'GenerationResult':
        """Create an error result."""
        return cls(
            request_id=request_id,
            field_name=field_name,
            content="",
            status=GenerationStatus.FAILED,
            start_time=Timestamp.now(),
            end_time=Timestamp.now(),
            error_message=str(error)
        )

@dataclass
class GenerationQueue:
    """Queue of generation requests."""
    pending: List[GenerationRequest] = field(default_factory=list)
    in_progress: Dict[str, GenerationRequest] = field(default_factory=dict)
    completed: Dict[str, GenerationResult] = field(default_factory=dict)
    failed: Dict[str, GenerationResult] = field(default_factory=dict)
    cancelled: Dict[str, GenerationResult] = field(default_factory=dict)
    
    def add_request(self, request: GenerationRequest) -> Result:
        """Add a request to the queue."""
        try:
            self.pending.append(request)
            # Sort by priority
            self.pending.sort(key=lambda r: (-r.priority, r.created_at))
            return Result(True, "Request added successfully", request)
        except Exception as e:
            return Result(False, f"Failed to add request: {str(e)}", error=e)

    def get_next_request(self) -> Optional[GenerationRequest]:
        """Get next pending request."""
        return self.pending[0] if self.pending else None

    def get_queue_status(self) -> JsonDict:
        """Get current queue statistics."""
        return {
            'pending': len(self.pending),
            'in_progress': len(self.in_progress),
            'completed': len(self.completed),
            'failed': len(self.failed),
            'cancelled': len(self.cancelled)
        }