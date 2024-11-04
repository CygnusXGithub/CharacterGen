# core/models/context.py
"""Generation context and history models."""
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from ..common.types import (
    BaseModel, JsonDict, Result,
    Timestamp
)

@dataclass
class GenerationContext(BaseModel):
    """Complete context for a generation operation."""
    field_name: str
    base_context: JsonDict
    dependencies: Dict[str, str] = field(default_factory=dict)
    user_modifications: JsonDict = field(default_factory=dict)
    metadata: JsonDict = field(default_factory=dict)
    parent_context_id: Optional[str] = None
    
    def update_context(self, updates: JsonDict) -> Result:
        """Update context with new values."""
        try:
            self.base_context.update(updates)
            self.user_modifications.update(updates)
            self.modified_at = Timestamp.now()
            return Result(True, "Context updated successfully")
        except Exception as e:
            return Result(False, f"Failed to update context: {str(e)}", error=e)
    
    def merge_dependencies(self, new_deps: Dict[str, str]) -> Result:
        """Merge new dependencies into context."""
        try:
            self.dependencies.update(new_deps)
            return Result(True, "Dependencies merged successfully")
        except Exception as e:
            return Result(False, f"Failed to merge dependencies: {str(e)}", error=e)
    
    def to_dict(self) -> JsonDict:
        """Convert context to dictionary format."""
        data = super().to_dict()
        data.update({
            'field_name': self.field_name,
            'base_context': self.base_context,
            'dependencies': self.dependencies,
            'user_modifications': self.user_modifications,
            'metadata': self.metadata,
            'parent_context_id': self.parent_context_id
        })
        return data
    
    @classmethod
    def from_dict(cls, data: JsonDict) -> 'GenerationContext':
        """Create context from dictionary."""
        base_data = {
            'id': data['id'],
            'created_at': data['created_at'],
            'modified_at': data['modified_at']
        }
        
        return cls(
            **base_data,
            field_name=data['field_name'],
            base_context=data['base_context'],
            dependencies=data.get('dependencies', {}),
            user_modifications=data.get('user_modifications', {}),
            metadata=data.get('metadata', {}),
            parent_context_id=data.get('parent_context_id')
        )

@dataclass
class ContextHistory(BaseModel):
    """History of contexts for a field."""
    field_name: str
    contexts: List[GenerationContext] = field(default_factory=list)
    current_context_id: Optional[str] = None
    
    def add_context(self, context: GenerationContext) -> Result:
        """Add a new context to history."""
        try:
            self.contexts.append(context)
            self.current_context_id = str(context.id)
            self.modified_at = Timestamp.now()
            return Result(True, "Context added successfully", context)
        except Exception as e:
            return Result(False, f"Failed to add context: {str(e)}", error=e)
    
    def get_context(self, context_id: str) -> Optional[GenerationContext]:
        """Get context by ID."""
        return next(
            (ctx for ctx in self.contexts if str(ctx.id) == context_id),
            None
        )
    
    def get_current_context(self) -> Optional[GenerationContext]:
        """Get current active context."""
        if not self.current_context_id:
            return None
        return self.get_context(self.current_context_id)
    
    def to_dict(self) -> JsonDict:
        """Convert history to dictionary format."""
        data = super().to_dict()
        data.update({
            'field_name': self.field_name,
            'contexts': [ctx.to_dict() for ctx in self.contexts],
            'current_context_id': self.current_context_id
        })
        return data
    
    @classmethod
    def from_dict(cls, data: JsonDict) -> 'ContextHistory':
        """Create history from dictionary."""
        base_data = {
            'id': data['id'],
            'created_at': data['created_at'],
            'modified_at': data['modified_at']
        }
        
        history = cls(
            **base_data,
            field_name=data['field_name'],
            current_context_id=data.get('current_context_id')
        )
        
        history.contexts = [
            GenerationContext.from_dict(ctx_data)
            for ctx_data in data.get('contexts', [])
        ]
        
        return history