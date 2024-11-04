from typing import Dict, Optional, List, Any, Set
from datetime import datetime
import logging
from uuid import UUID
import asyncio

from .base import StateManagerBase, OperationContext
from ..common.types import Result, JsonDict
from ..models.metadata import (
    CharacterMetadata, FieldMetadata,
    GenerationMetadata, BasePromptMetadata
)
from ..errors import (
    ErrorHandler, StateError, ErrorCategory, 
    ErrorLevel
)

class MetadataManager(StateManagerBase[CharacterMetadata]):
    """Manages metadata for characters and generations"""
    
    def __init__(self, error_handler: ErrorHandler):
        super().__init__(error_handler)
        self._active_character_id: Optional[UUID] = None
        self._metadata_cache: Dict[UUID, CharacterMetadata] = {}
        self._field_locks: Dict[str, asyncio.Lock] = {}
        self._metadata_lock = asyncio.Lock()

    async def initialize_character_metadata(self, character_id: UUID) -> Result[CharacterMetadata]:
        """Initialize metadata for a new character"""
        try:
            async with self._metadata_lock:
                metadata = CharacterMetadata(character_id=str(character_id))
                self._metadata_cache[character_id] = metadata
                
                await self.update_state(
                    f"character_{character_id}", 
                    metadata,
                    metadata={'operation': 'initialize', 'character_id': str(character_id)}
                )
                
                return Result(True, "Metadata initialized successfully", metadata)
                
        except Exception as e:
            self.error_handler.handle_error(
                e,
                ErrorCategory.STATE,
                ErrorLevel.ERROR,
                {'operation': 'initialize_metadata', 'character_id': str(character_id)}
            )
            return Result(False, f"Failed to initialize metadata: {str(e)}", error=e)

    async def set_active_character(self, character_id: UUID) -> Result:
        """Set the active character for metadata operations"""
        try:
            async with self._metadata_lock:
                self._active_character_id = character_id
                
                if character_id not in self._metadata_cache:
                    result = await self.initialize_character_metadata(character_id)
                    if not result.success:
                        return result
                
                return Result(True, "Active character set successfully")
                
        except Exception as e:
            self.error_handler.handle_error(
                e,
                ErrorCategory.STATE,
                ErrorLevel.ERROR,
                {'operation': 'set_active_character', 'character_id': str(character_id)}
            )
            return Result(False, f"Failed to set active character: {str(e)}", error=e)

    async def record_generation(self, 
                              field_name: str,
                              generation_data: Dict[str, Any]) -> Result[GenerationMetadata]:
        """Record a generation operation"""
        try:
            if not self._active_character_id:
                return Result(False, "No active character")

            # Get or create field lock
            if field_name not in self._field_locks:
                self._field_locks[field_name] = asyncio.Lock()
            
            async with self._field_locks[field_name]:
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
                    duration_ms=generation_data.get('duration_ms')
                )
                
                # Update field metadata
                field_meta = metadata.field_metadata[field_name]
                field_meta.last_generated = datetime.now()
                field_meta.generation_history.append(gen_metadata)
                field_meta.base_prompt_used = gen_metadata.base_prompt_name
                
                # Update base prompt stats
                await self._update_base_prompt_stats(
                    gen_metadata.base_prompt_name,
                    gen_metadata.base_prompt_version,
                    generation_data.get('duration_ms')
                )
                
                # Update state
                await self.update_state(
                    f"generation_{field_name}",
                    gen_metadata,
                    metadata={
                        'field': field_name,
                        'character_id': str(self._active_character_id)
                    }
                )
                
                return Result(True, "Generation recorded successfully", gen_metadata)
            
        except Exception as e:
            self.error_handler.handle_error(
                e,
                ErrorCategory.STATE,
                ErrorLevel.ERROR,
                {
                    'operation': 'record_generation', 
                    'field': field_name,
                    'character_id': str(self._active_character_id) if self._active_character_id else None
                }
            )
            return Result(False, f"Failed to record generation: {str(e)}", error=e)

    async def record_manual_edit(self, field_name: str) -> Result:
        """Record a manual field edit"""
        try:
            if not self._active_character_id:
                return Result(False, "No active character")

            async with self._field_locks.get(field_name, asyncio.Lock()):
                metadata = self._metadata_cache[self._active_character_id]
                
                if field_name not in metadata.field_metadata:
                    metadata.field_metadata[field_name] = FieldMetadata(field_name=field_name)
                
                field_meta = metadata.field_metadata[field_name]
                field_meta.manual_edits.append(datetime.now())
                metadata.modified_at = datetime.now()
                
                await self.update_state(
                    f"field_{field_name}",
                    field_meta,
                    metadata={
                        'edit_type': 'manual',
                        'character_id': str(self._active_character_id)
                    }
                )
                
                return Result(True, "Manual edit recorded successfully")
            
        except Exception as e:
            self.error_handler.handle_error(
                e,
                ErrorCategory.STATE,
                ErrorLevel.WARNING,
                {'operation': 'record_edit', 'field': field_name}
            )
            return Result(False, f"Failed to record manual edit: {str(e)}", error=e)

    async def get_field_history(self, field_name: str) -> Result[List[GenerationMetadata]]:
        """Get generation history for a field"""
        try:
            if not self._active_character_id:
                return Result(True, "No active character", [])

            async with self._field_locks.get(field_name, asyncio.Lock()):
                metadata = self._metadata_cache[self._active_character_id]
                field_meta = metadata.field_metadata.get(field_name)
                
                history = field_meta.generation_history if field_meta else []
                return Result(True, "Field history retrieved successfully", history)
            
        except Exception as e:
            self.error_handler.handle_error(
                e,
                ErrorCategory.STATE,
                ErrorLevel.WARNING,
                {'operation': 'get_history', 'field': field_name}
            )
            return Result(False, f"Failed to get field history: {str(e)}", error=e)

    async def get_last_generation_context(self, field_name: str) -> Result[Optional[Dict[str, Any]]]:
        """Get context from last generation"""
        try:
            history_result = await self.get_field_history(field_name)
            if not history_result.success or not history_result.data:
                return Result(True, "No generation history found", None)
            
            last_generation = history_result.data[-1]
            return Result(True, "Context retrieved successfully", last_generation.input_context)
            
        except Exception as e:
            self.error_handler.handle_error(
                e,
                ErrorCategory.STATE,
                ErrorLevel.WARNING,
                {'operation': 'get_context', 'field': field_name}
            )
            return Result(False, f"Failed to get generation context: {str(e)}", error=e)

    async def _update_base_prompt_stats(self, 
                                      prompt_name: str,
                                      version: str,
                                      duration_ms: Optional[int]) -> Result:
        """Update base prompt usage statistics"""
        try:
            if not self._active_character_id:
                return Result(False, "No active character")

            async with self._metadata_lock:
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
                prompt_meta.use_count += 1
                prompt_meta.last_used = datetime.now()
                
                if duration_ms is not None:
                    if prompt_meta.average_generation_time is None:
                        prompt_meta.average_generation_time = float(duration_ms)
                    else:
                        # Update running average
                        prompt_meta.average_generation_time = (
                            (prompt_meta.average_generation_time * (prompt_meta.use_count - 1) + duration_ms)
                            / prompt_meta.use_count
                        )
                
                await self.update_state(
                    f"prompt_stats_{prompt_name}_{version}",
                    prompt_meta,
                    metadata={'character_id': str(self._active_character_id)}
                )
                
                return Result(True, "Prompt stats updated successfully")
                
        except Exception as e:
            self.error_handler.handle_error(
                e,
                ErrorCategory.STATE,
                ErrorLevel.WARNING,
                {
                    'operation': 'update_prompt_stats',
                    'prompt': prompt_name,
                    'version': version
                }
            )
            return Result(False, f"Failed to update prompt stats: {str(e)}", error=e)

    async def get_metadata_for_save(self) -> Result[Dict[str, Any]]:
        """Get metadata in format for saving"""
        try:
            if not self._active_character_id:
                return Result(False, "No active character", {})
            
            async with self._metadata_lock:
                metadata = self._metadata_cache[self._active_character_id]
                
                save_data = {
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
                
                return Result(True, "Metadata prepared for save", save_data)
                
        except Exception as e:
            self.error_handler.handle_error(
                e,
                ErrorCategory.STATE,
                ErrorLevel.ERROR,
                {'operation': 'get_save_metadata'}
            )
            return Result(False, f"Failed to prepare metadata for save: {str(e)}", error=e)