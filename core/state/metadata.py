from typing import Dict, Optional, List, Any
from datetime import datetime
import logging
from uuid import UUID

from .base import StateManagerBase
from ..models.metadata import (
    CharacterMetadata, FieldMetadata,
    GenerationMetadata, BasePromptMetadata
)
from ..errors import ErrorHandler, StateError, ErrorCategory, ErrorLevel

class MetadataManager(StateManagerBase):
    """Manages metadata for characters and generations"""
    
    def __init__(self, error_handler: ErrorHandler):
        super().__init__()
        self.error_handler = error_handler
        self.logger = logging.getLogger(__name__)
        self._active_character_id: Optional[UUID] = None
        self._metadata_cache: Dict[UUID, CharacterMetadata] = {}

    def initialize_character_metadata(self, character_id: UUID) -> CharacterMetadata:
        """Initialize metadata for a new character"""
        try:
            metadata = CharacterMetadata(character_id=character_id)
            self._metadata_cache[character_id] = metadata
            return metadata
        except Exception as e:
            self.error_handler.handle_error(
                error=e,
                category=ErrorCategory.STATE,
                level=ErrorLevel.ERROR,
                context={'operation': 'initialize_metadata'}
            )
            raise

    def set_active_character(self, character_id: UUID):
        """Set the active character for metadata operations"""
        self._active_character_id = character_id
        if character_id not in self._metadata_cache:
            self.initialize_character_metadata(character_id)

    async def record_generation(self, 
                              field_name: str,
                              generation_data: Dict[str, Any]) -> GenerationMetadata:
        """Record a generation operation"""
        try:
            if not self._active_character_id:
                raise StateError("No active character")

            metadata = self._metadata_cache[self._active_character_id]
            
            # Create field metadata if it doesn't exist
            if field_name not in metadata.field_metadata:
                metadata.field_metadata[field_name] = FieldMetadata(field_name=field_name)
            
            # Create generation metadata
            gen_metadata = GenerationMetadata(
                field_name=field_name,
                prompt_used=generation_data['prompt'],
                input_context=generation_data['context'],
                result=generation_data['result'],
                base_prompt_name=generation_data['base_prompt_name'],
                base_prompt_version=generation_data['base_prompt_version'],
                generation_settings=generation_data.get('settings', {}),
                dependencies=generation_data.get('dependencies', {}),
                duration_ms=generation_data.get('duration_ms')  # Make sure we get duration
            )
            
            # Update field metadata
            field_meta = metadata.field_metadata[field_name]
            field_meta.last_generated = datetime.now()
            field_meta.generation_history.append(gen_metadata)
            field_meta.base_prompt_used = gen_metadata.base_prompt_name
            
            # Update base prompt stats with duration
            self._update_base_prompt_stats(
                gen_metadata.base_prompt_name,
                gen_metadata.base_prompt_version,
                generation_data.get('duration_ms')  # Pass duration to stats update
            )
            
            self.state_changed.emit('generation_recorded', {
                'field': field_name,
                'metadata': gen_metadata
            })
            
            return gen_metadata
            
        except Exception as e:
            self.error_handler.handle_error(
                error=e,
                category=ErrorCategory.STATE,
                level=ErrorLevel.ERROR,
                context={'operation': 'record_generation', 'field': field_name}
            )
            raise

    def record_manual_edit(self, field_name: str):
        """Record a manual field edit"""
        try:
            if not self._active_character_id:
                raise StateError("No active character")

            metadata = self._metadata_cache[self._active_character_id]
            
            if field_name not in metadata.field_metadata:
                metadata.field_metadata[field_name] = FieldMetadata(field_name=field_name)
            
            metadata.field_metadata[field_name].manual_edits.append(datetime.now())
            metadata.modified_at = datetime.now()
            
        except Exception as e:
            self.error_handler.handle_error(
                error=e,
                category=ErrorCategory.STATE,
                level=ErrorLevel.WARNING,
                context={'operation': 'record_edit', 'field': field_name}
            )

    def get_field_history(self, field_name: str) -> List[GenerationMetadata]:
        """Get generation history for a field"""
        try:
            if not self._active_character_id:
                return []

            metadata = self._metadata_cache[self._active_character_id]
            field_meta = metadata.field_metadata.get(field_name)
            
            return field_meta.generation_history if field_meta else []
            
        except Exception as e:
            self.error_handler.handle_error(
                error=e,
                category=ErrorCategory.STATE,
                level=ErrorLevel.WARNING,
                context={'operation': 'get_history', 'field': field_name}
            )
            return []

    def get_last_generation_context(self, field_name: str) -> Optional[Dict[str, Any]]:
        """Get context from last generation"""
        try:
            history = self.get_field_history(field_name)
            return history[-1].input_context if history else None
        except Exception as e:
            self.error_handler.handle_error(
                error=e,
                category=ErrorCategory.STATE,
                level=ErrorLevel.WARNING,
                context={'operation': 'get_context', 'field': field_name}
            )
            return None

    def _update_base_prompt_stats(self, 
                                prompt_name: str,
                                version: str,
                                duration_ms: Optional[int]):
        """Update base prompt usage statistics"""
        if not self._active_character_id:
            return

        metadata = self._metadata_cache[self._active_character_id]
        
        # Find or create base prompt metadata
        prompt_meta = next(
            (p for p in metadata.base_prompts_used 
             if p.name == prompt_name and p.version == version),
            None
        )
        
        if not prompt_meta:
            prompt_meta = BasePromptMetadata(
                name=prompt_name,
                version=version
            )
            metadata.base_prompts_used.append(prompt_meta)
        
        # Update stats
        prompt_meta.last_used = datetime.now()
        prompt_meta.use_count += 1
        
        # Only update average if we have a duration
        if duration_ms is not None:
            if prompt_meta.average_generation_time is None:
                prompt_meta.average_generation_time = float(duration_ms)
            else:
                # Update running average
                prompt_meta.average_generation_time = (
                    (prompt_meta.average_generation_time * (prompt_meta.use_count - 1) + duration_ms)
                    / prompt_meta.use_count
                )

    def get_metadata_for_save(self) -> Dict[str, Any]:
        """Get metadata in format for saving"""
        if not self._active_character_id:
            return {}
            
        metadata = self._metadata_cache[self._active_character_id]
        return {
            "charactergen": {
                "character_id": str(metadata.character_id),
                "created_at": metadata.created_at.isoformat(),
                "modified_at": metadata.modified_at.isoformat(),
                "field_metadata": {
                    name: {
                        "last_generated": meta.last_generated.isoformat() if meta.last_generated else None,
                        "generation_count": len(meta.generation_history),
                        "manual_edit_count": len(meta.manual_edits),
                        "base_prompt_used": meta.base_prompt_used,
                        "custom_context": meta.custom_context
                    }
                    for name, meta in metadata.field_metadata.items()
                },
                "base_prompts": [
                    {
                        "name": prompt.name,
                        "version": prompt.version,
                        "use_count": prompt.use_count,
                        "last_used": prompt.last_used.isoformat() if prompt.last_used else None,
                        "average_generation_time": prompt.average_generation_time
                    }
                    for prompt in metadata.base_prompts_used
                ],
                "custom_data": metadata.custom_data
            }
        }