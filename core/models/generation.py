from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum, auto
from uuid import UUID, uuid4

class GenerationStatus(Enum):
    """Status of a generation request"""
    QUEUED = auto()
    IN_PROGRESS = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()

@dataclass
class GenerationRequest:
    """A request for generation"""
    field_name: str
    input_context: Dict[str, Any]
    base_prompt_name: str
    base_prompt_version: str
    priority: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    dependencies: Dict[str, str] = field(default_factory=dict)
    generation_settings: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    max_retries: int = 3
    id: UUID = field(default_factory=uuid4)

@dataclass
class GenerationResult:
    """Result of a generation request"""
    request_id: UUID
    field_name: str
    content: str
    status: GenerationStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None
    duration_ms: Optional[int] = None
    retry_count: int = 0
    metrics: Dict[str, Any] = field(default_factory=dict)

@dataclass
class GenerationQueue:
    """Queue of generation requests"""
    pending: List[GenerationRequest] = field(default_factory=list)
    in_progress: Dict[UUID, GenerationRequest] = field(default_factory=dict)
    completed: Dict[UUID, GenerationResult] = field(default_factory=dict)
    failed: Dict[UUID, GenerationResult] = field(default_factory=dict)
    cancelled: Dict[UUID, GenerationResult] = field(default_factory=dict)