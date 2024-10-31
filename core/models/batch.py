from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional
from datetime import datetime
from uuid import UUID, uuid4
from enum import Enum, auto
from .generation import GenerationStatus

class BatchStatus(Enum):
    """Status of a generation batch"""
    PENDING = auto()
    IN_PROGRESS = auto()
    COMPLETED = auto()
    FAILED = auto()
    PARTIALLY_COMPLETED = auto()  # Some succeeded, some failed
    CANCELLED = auto()

@dataclass
class BatchProgress:
    """Progress information for a batch"""
    total: int = 0
    completed: int = 0
    failed: int = 0
    in_progress: int = 0
    pending: int = 0
    
    @property
    def progress_percentage(self) -> float:
        """Calculate progress percentage"""
        if self.total == 0:
            return 0.0
        return (self.completed + self.failed) / self.total * 100

@dataclass
class BatchOperation:
    """Batch generation operation"""
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    description: str = ""
    request_ids: Set[UUID] = field(default_factory=set)
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: BatchStatus = BatchStatus.PENDING
    progress: BatchProgress = field(default_factory=BatchProgress)
    metadata: Dict[str, any] = field(default_factory=dict)
    parent_batch_id: Optional[UUID] = None  # For sub-batches
    
    def update_progress(self, request_statuses: Dict[UUID, GenerationStatus]):
        """Update progress based on request statuses"""
        self.progress.total = len(self.request_ids)
        self.progress.completed = sum(1 for status in request_statuses.values() 
                                    if status == GenerationStatus.COMPLETED)
        self.progress.failed = sum(1 for status in request_statuses.values() 
                                 if status == GenerationStatus.FAILED)
        self.progress.in_progress = sum(1 for status in request_statuses.values() 
                                      if status == GenerationStatus.IN_PROGRESS)
        self.progress.pending = sum(1 for status in request_statuses.values() 
                                  if status == GenerationStatus.QUEUED)
        
        # Update batch status
        if self.progress.total == 0:
            self.status = BatchStatus.PENDING
        elif self.progress.failed == self.progress.total:
            self.status = BatchStatus.FAILED
        elif self.progress.completed == self.progress.total:
            self.status = BatchStatus.COMPLETED
        elif self.progress.completed + self.progress.failed == self.progress.total:
            self.status = BatchStatus.PARTIALLY_COMPLETED
        elif self.progress.in_progress > 0 or self.progress.pending > 0:
            self.status = BatchStatus.IN_PROGRESS