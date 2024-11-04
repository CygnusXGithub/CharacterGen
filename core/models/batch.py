# core/models/batch.py
"""Batch operation models for generation."""
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional
from enum import Enum, auto

from ..common.types import (
    BaseModel, JsonDict, Timestamp,
    GenerationStatus, Result
)

class BatchStatus(Enum):
    """Status of a generation batch."""
    PENDING = auto()
    IN_PROGRESS = auto()
    COMPLETED = auto()
    FAILED = auto()
    PARTIALLY_COMPLETED = auto()
    CANCELLED = auto()

@dataclass
class BatchProgress(BaseModel):
    """Progress information for a batch."""
    total: int = 0
    completed: int = 0
    failed: int = 0
    in_progress: int = 0
    pending: int = 0
    
    @property
    def progress_percentage(self) -> float:
        """Calculate progress percentage."""
        return (self.completed + self.failed) / self.total * 100 if self.total > 0 else 0.0
    
    def to_dict(self) -> JsonDict:
        """Convert progress to dictionary."""
        data = super().to_dict()
        data.update({
            'total': self.total,
            'completed': self.completed,
            'failed': self.failed,
            'in_progress': self.in_progress,
            'pending': self.pending,
            'progress_percentage': self.progress_percentage
        })
        return data

@dataclass
class BatchOperation(BaseModel):
    """Batch generation operation."""
    name: str
    description: str = ""
    request_ids: Set[str] = field(default_factory=set)
    started_at: Optional[Timestamp] = None
    completed_at: Optional[Timestamp] = None
    status: BatchStatus = BatchStatus.PENDING
    progress: BatchProgress = field(default_factory=BatchProgress)
    metadata: JsonDict = field(default_factory=dict)
    parent_batch_id: Optional[str] = None
    
    def update_progress(self, request_statuses: Dict[str, GenerationStatus]) -> Result:
        """Update progress based on request statuses."""
        try:
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
                
            return Result(True, "Progress updated successfully")
            
        except Exception as e:
            return Result(False, f"Failed to update progress: {str(e)}", error=e)
    
    def to_dict(self) -> JsonDict:
        """Convert batch operation to dictionary."""
        data = super().to_dict()
        data.update({
            'name': self.name,
            'description': self.description,
            'request_ids': list(self.request_ids),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'status': self.status.name,
            'progress': self.progress.to_dict(),
            'metadata': self.metadata,
            'parent_batch_id': self.parent_batch_id
        })
        return data
    
    @classmethod
    def from_dict(cls, data: JsonDict) -> 'BatchOperation':
        """Create batch operation from dictionary."""
        base_data = {
            'id': data['id'],
            'created_at': data['created_at'],
            'modified_at': data['modified_at']
        }
        
        return cls(
            **base_data,
            name=data['name'],
            description=data.get('description', ''),
            request_ids=set(data.get('request_ids', [])),
            started_at=Timestamp.fromisoformat(data['started_at']) if data.get('started_at') else None,
            completed_at=Timestamp.fromisoformat(data['completed_at']) if data.get('completed_at') else None,
            status=BatchStatus[data['status']],
            progress=BatchProgress.from_dict(data['progress']),
            metadata=data.get('metadata', {}),
            parent_batch_id=data.get('parent_batch_id')
        )