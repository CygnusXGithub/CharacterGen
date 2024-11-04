# core/services/versioning.py
"""Service for managing version control and change tracking."""
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

from ..common.types import (
    BaseModel, JsonDict, Result,
    ChangeType
)
from ..models.character import CharacterData
from ..models.versioning import VersionChange
from ..errors import ErrorHandler, ErrorCategory, ErrorLevel

@dataclass
class VersionOperation(BaseModel):
    """Context for version operations."""
    change_type: ChangeType
    description: str
    fields: List[str]
    metadata: Optional[JsonDict] = None

class VersioningService:
    """Service for handling character versioning."""
    
    def __init__(self, error_handler: ErrorHandler):
        self.error_handler = error_handler
    
    async def record_generation(self,
                              character: CharacterData,
                              field_name: str,
                              generation_context: JsonDict) -> Result[VersionChange]:
        """Record a field generation."""
        try:
            operation = VersionOperation(
                change_type=ChangeType.FIELD_GENERATION,
                fields=[field_name],
                description=f"Generated {field_name}",
                metadata={
                    'generation_context': generation_context,
                    'generation_type': 'initial' if not character.get_field_history(field_name) else 'regeneration'
                }
            )
            
            return await self._record_change(character, operation)
            
        except Exception as e:
            self.error_handler.handle_error(
                e,
                ErrorCategory.STATE,
                ErrorLevel.ERROR,
                {'operation': 'record_generation', 'field': field_name}
            )
            return Result(False, f"Failed to record generation: {str(e)}", error=e)
    
    async def record_manual_edit(self,
                               character: CharacterData,
                               fields: List[str],
                               description: str = "Manual edit") -> Result[VersionChange]:
        """Record manual edits."""
        try:
            operation = VersionOperation(
                change_type=ChangeType.MANUAL_EDIT,
                fields=fields,
                description=description,
                metadata={
                    'edit_type': 'manual',
                    'timestamp': datetime.now().isoformat()
                }
            )
            
            return await self._record_change(character, operation)
            
        except Exception as e:
            self.error_handler.handle_error(
                e,
                ErrorCategory.STATE,
                ErrorLevel.ERROR,
                {'operation': 'record_manual_edit', 'fields': fields}
            )
            return Result(False, f"Failed to record edit: {str(e)}", error=e)

    async def _record_change(self,
                           character: CharacterData,
                           operation: VersionOperation) -> Result[VersionChange]:
        """Record a change to the character."""
        try:
            change = character._charactergen_metadata.version_history.add_change(
                change_type=operation.change_type,
                fields=operation.fields,
                description=operation.description,
                metadata=operation.metadata
            )
            
            if not change.success:
                return change
            
            character.modified_at = datetime.now()
            return Result(True, "Change recorded successfully", change.data)
            
        except Exception as e:
            self.error_handler.handle_error(
                e,
                ErrorCategory.STATE,
                ErrorLevel.ERROR,
                {'operation': 'record_change', 'change_type': operation.change_type.name}
            )
            return Result(False, f"Failed to record change: {str(e)}", error=e)