from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from uuid import UUID, uuid4

@dataclass
class GenerationContext:
    """Complete context for a generation operation"""
    field_name: str
    base_context: Dict[str, Any]  # Core context values
    dependencies: Dict[str, str] = field(default_factory=dict)  # field -> value mapping
    user_modifications: Dict[str, Any] = field(default_factory=dict)  # User-specified changes
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional metadata
    parent_context_id: Optional[UUID] = None  # For tracking context lineage
    created_at: datetime = field(default_factory=datetime.now)
    id: UUID = field(default_factory=uuid4)

@dataclass
class ContextHistory:
    """History of contexts for a field"""
    field_name: str
    contexts: List[GenerationContext] = field(default_factory=list)
    current_context_id: Optional[UUID] = None