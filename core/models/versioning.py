from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum, auto

class ChangeType(Enum):
    """Types of changes that can happen to a character"""
    FIELD_GENERATION = auto()    # Field was generated
    MANUAL_EDIT = auto()         # Manual edit by user
    FIELD_REGENERATION = auto()  # Field was regenerated
    BATCH_CHANGE = auto()        # Multiple fields changed together
    IMAGE_CHANGE = auto()        # Character image changed
    METADATA_UPDATE = auto()     # Metadata was updated

@dataclass
class VersionChange:
    """Represents a single change to the character"""
    version: int                  # Incremental version number
    change_type: ChangeType       # Type of change
    timestamp: datetime = field(default_factory=datetime.now)
    fields_changed: List[str] = field(default_factory=list)  # Fields affected
    change_description: str = ""  # Human readable description
    change_metadata: Dict[str, Any] = field(default_factory=dict)  # Additional context
    parent_version: Optional[int] = None  # Previous version number

@dataclass
class VersionHistory:
    """Tracks version history for a character"""
    current_version: int = 1
    changes: List[VersionChange] = field(default_factory=list)
    field_versions: Dict[str, int] = field(default_factory=dict)  # Latest version per field
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert version history to dictionary format"""
        return {
            "current_version": self.current_version,
            "changes": [
                {
                    "version": change.version,
                    "change_type": change.change_type.name,
                    "timestamp": change.timestamp.isoformat(),
                    "fields_changed": change.fields_changed,
                    "change_description": change.change_description,
                    "change_metadata": change.change_metadata,
                    "parent_version": change.parent_version
                }
                for change in self.changes
            ],
            "field_versions": self.field_versions
        }

    def from_dict(self, data: Dict[str, Any]):
        """Load version history from dictionary format"""
        if not data:
            return
            
        self.current_version = data.get('current_version', 1)
        self.field_versions = data.get('field_versions', {})
        
        # Load changes
        self.changes = []
        for change_data in data.get('changes', []):
            change = VersionChange(
                version=change_data['version'],
                change_type=ChangeType[change_data['change_type']],
                timestamp=datetime.fromisoformat(change_data['timestamp']),
                fields_changed=change_data['fields_changed'],
                change_description=change_data['change_description'],
                change_metadata=change_data.get('change_metadata', {}),
                parent_version=change_data.get('parent_version')
            )
            self.changes.append(change)
            
    def add_change(self, 
                    change_type: ChangeType,
                    fields: List[str],
                    description: str,
                    metadata: Dict[str, Any] = None) -> VersionChange:
        """Record a new change"""
        change = VersionChange(
            version=self.current_version + 1,
            change_type=change_type,
            fields_changed=fields,
            change_description=description,
            change_metadata=metadata or {},
            parent_version=self.current_version
        )
        
        self.changes.append(change)
        self.current_version = change.version
        
        # Update field versions
        for field in fields:
            self.field_versions[field] = change.version
            
        return change
    
    def get_field_history(self, field_name: str) -> List[VersionChange]:
        """Get history of changes for a specific field"""
        return [
            change for change in self.changes 
            if field_name in change.fields_changed
        ]
    
    def get_change(self, version: int) -> Optional[VersionChange]:
        """Get specific version change"""
        for change in self.changes:
            if change.version == version:
                return change
        return None
    
    def get_latest_field_version(self, field_name: str) -> Optional[int]:
        """Get latest version number for a field"""
        return self.field_versions.get(field_name)