from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime

from ..common.types import (
    BaseModel, JsonDict, ChangeType,
    Result, Timestamp
)

@dataclass
class VersionChange(BaseModel):
    """Represents a single change to a model."""
    change_type: ChangeType = field()  # Make it non-default explicitly
    description: str = field()
    fields_changed: List[str] = field()
    parent_version: Optional[int] = None
    metadata: JsonDict = field(default_factory=dict)
    
    
    def to_dict(self) -> JsonDict:
        """Convert change to dictionary format."""
        data = super().to_dict()
        data.update({
            'change_type': self.change_type.name,
            'description': self.description,
            'fields_changed': self.fields_changed,
            'metadata': self.metadata,
            'parent_version': self.parent_version
        })
        return data
    
    @classmethod
    def from_dict(cls, data: JsonDict) -> 'VersionChange':
        """Create change from dictionary."""
        base_data = {
            'id': data['id'],
            'created_at': data['created_at'],
            'modified_at': data['modified_at']
        }
        return cls(
            **base_data,
            change_type=ChangeType[data['change_type']],
            description=data['description'],
            fields_changed=data['fields_changed'],
            metadata=data.get('metadata', {}),
            parent_version=data.get('parent_version')
        )

@dataclass
class VersionHistory(BaseModel):
    """Tracks version history for a model."""
    changes: List[VersionChange] = field(default_factory=list)
    current_version: int = 1
    field_versions: Dict[str, int] = field(default_factory=dict)
    
    def add_change(self, 
                  change_type: ChangeType,
                  fields: List[str],
                  description: str,
                  metadata: Optional[JsonDict] = None) -> Result[VersionChange]:
        """Record a new change."""
        try:
            change = VersionChange(
                change_type=change_type,
                description=description,
                fields_changed=fields,
                metadata=metadata or {},
                parent_version=self.current_version
            )
            
            self.changes.append(change)
            self.current_version += 1
            
            # Update field versions
            for field in fields:
                self.field_versions[field] = self.current_version
                
            return Result(True, "Change recorded successfully", change)
            
        except Exception as e:
            return Result(False, f"Failed to record change: {str(e)}", error=e)
    
    def get_field_history(self, field_name: str) -> List[VersionChange]:
        """Get history of changes for a specific field."""
        return [
            change for change in self.changes 
            if field_name in change.fields_changed
        ]
    
    def get_change(self, version: int) -> Optional[VersionChange]:
        """Get specific version change."""
        return next(
            (change for change in self.changes if change.version == version),
            None
        )
    
    def get_latest_field_version(self, field_name: str) -> Optional[int]:
        """Get latest version number for a field."""
        return self.field_versions.get(field_name)
    
    def to_dict(self) -> JsonDict:
        """Convert history to dictionary format."""
        data = super().to_dict()
        data.update({
            'current_version': self.current_version,
            'changes': [change.to_dict() for change in self.changes],
            'field_versions': self.field_versions
        })
        return data
    
    @classmethod
    def from_dict(cls, data: JsonDict) -> 'VersionHistory':
        """Create history from dictionary."""
        base_data = {
            'id': data['id'],
            'created_at': data['created_at'],
            'modified_at': data['modified_at']
        }
        
        history = cls(
            **base_data,
            current_version=data['current_version'],
            field_versions=data['field_versions']
        )
        
        history.changes = [
            VersionChange.from_dict(change_data)
            for change_data in data['changes']
        ]
        
        return history