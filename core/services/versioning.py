from typing import List, Dict, Any, Optional
from ..models.versioning import ChangeType, VersionChange
from ..models.character import CharacterData
from ..errors import ErrorHandler, ErrorCategory, ErrorLevel
from datetime import datetime
class VersioningService:
    """Service for handling character versioning"""
    
    def __init__(self, error_handler: ErrorHandler):
        self.error_handler = error_handler
    
    async def record_generation(self,
                              character: CharacterData,
                              field_name: str,
                              generation_context: Dict[str, Any]) -> Optional[VersionChange]:
        """Record a field generation"""
        try:
            return character.record_change(
                change_type=ChangeType.FIELD_GENERATION,
                fields=[field_name],
                description=f"Generated {field_name}",
                metadata={
                    'generation_context': generation_context,
                    'generation_type': 'initial' if not character.get_field_history(field_name) else 'regeneration'
                }
            )
        except Exception as e:
            self.error_handler.handle_error(
                error=e,
                category=ErrorCategory.STATE,
                level=ErrorLevel.ERROR,
                context={'operation': 'record_generation', 'field': field_name}
            )
            return None
    
    async def record_manual_edit(self,
                               character: CharacterData,
                               fields: List[str],
                               description: str = "Manual edit") -> Optional[VersionChange]:
        """Record manual edits"""
        try:
            return character.record_change(
                change_type=ChangeType.MANUAL_EDIT,
                fields=fields,
                description=description,
                metadata={
                    'edit_type': 'manual',
                    'timestamp': datetime.now().isoformat()
                }
            )
        except Exception as e:
            self.error_handler.handle_error(
                error=e,
                category=ErrorCategory.STATE,
                level=ErrorLevel.ERROR,
                context={'operation': 'record_manual_edit', 'fields': fields}
            )
            return None