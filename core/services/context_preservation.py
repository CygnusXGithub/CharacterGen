# core/services/context_preservation.py
"""Service for managing and preserving generation contexts."""
from dataclasses import dataclass, field
from typing import Dict, Optional, List
import json
from pathlib import Path
import asyncio
import logging
from datetime import datetime
import aiofiles

from ..common.types import (
    BaseModel, JsonDict, Result,
    PathLike
)
from ..models.context import GenerationContext, ContextHistory
from ..errors import ErrorHandler, ErrorCategory, ErrorLevel

@dataclass
class StorageConfig(BaseModel):
    """Configuration for context storage."""
    storage_path: Path
    max_history: int = 100
    cleanup_interval: int = 3600  # 1 hour in seconds
    compression_enabled: bool = True

@dataclass
class ContextMetadata(BaseModel):
    """Metadata for context tracking."""
    field_name: str
    version: str = "1.0"
    source: str = "generation"
    tags: List[str] = field(default_factory=list)
    parent_ids: List[str] = field(default_factory=list)

class ContextPreservationService:
    """Service for managing and preserving generation contexts."""
    
    def __init__(self, 
                 error_handler: ErrorHandler,
                 storage_path: PathLike,
                 config: Optional[StorageConfig] = None):
        self.error_handler = error_handler
        self.logger = logging.getLogger(__name__)
        self.config = config or StorageConfig(storage_path=Path(storage_path))
        
        # Runtime storage
        self._context_histories: Dict[str, ContextHistory] = {}
        self._active_contexts: Dict[str, GenerationContext] = {}
        
        # Locks
        self._file_lock = asyncio.Lock()
        self._context_lock = asyncio.Lock()
        
        # Setup storage
        self._setup_storage()
        
        # Start cleanup task
        if self.config.cleanup_interval > 0:
            asyncio.create_task(self._periodic_cleanup())

    def _setup_storage(self) -> Result:
        """Setup storage directory."""
        try:
            self.config.storage_path.mkdir(parents=True, exist_ok=True)
            return Result(True, "Storage setup completed")
        except Exception as e:
            self.error_handler.handle_error(
                e,
                ErrorCategory.FILE,
                ErrorLevel.ERROR,
                {'operation': 'setup_storage'}
            )
            return Result(False, f"Failed to setup storage: {str(e)}", error=e)

    async def store_context(self, 
                          context: GenerationContext,
                          metadata: Optional[ContextMetadata] = None) -> Result[str]:
        """Store a new generation context."""
        try:
            async with self._context_lock:
                # Get or create history for field
                if context.field_name not in self._context_histories:
                    self._context_histories[context.field_name] = ContextHistory(
                        field_name=context.field_name
                    )
                
                history = self._context_histories[context.field_name]
                
                # Add metadata if provided
                if metadata:
                    context.metadata.update({
                        'parent_ids': metadata.parent_ids,
                        'version': metadata.version,
                        'source': metadata.source,
                        'tags': metadata.tags
                    })
                
                # Update history
                history.contexts.append(context)
                history.current_context_id = str(context.id)
                
                # Store in active contexts
                self._active_contexts[str(context.id)] = context
                
                # Persist to disk
                persist_result = await self._persist_context(context)
                if not persist_result.success:
                    return persist_result
                
                return Result(True, "Context stored successfully", str(context.id))

        except Exception as e:
            self.error_handler.handle_error(
                e,
                ErrorCategory.STATE,
                ErrorLevel.ERROR,
                {'operation': 'store_context'}
            )
            return Result(False, f"Failed to store context: {str(e)}", error=e)

    async def get_context(self, 
                         field_name: str,
                         context_id: Optional[str] = None) -> Result[GenerationContext]:
        """Get context by ID or current context for field."""
        try:
            async with self._context_lock:
                if context_id:
                    # Try memory first
                    if context_id in self._active_contexts:
                        return Result(True, "Context retrieved from memory", 
                                    self._active_contexts[context_id])
                        
                    # Try loading from disk
                    return await self._load_context(context_id)
                
                # Get current context for field
                history = self._context_histories.get(field_name)
                if not history or not history.current_context_id:
                    return Result(False, f"No current context for field {field_name}")
                    
                return await self.get_context(field_name, history.current_context_id)

        except Exception as e:
            self.error_handler.handle_error(
                e,
                ErrorCategory.STATE,
                ErrorLevel.ERROR,
                {'operation': 'get_context', 'field': field_name}
            )
            return Result(False, f"Failed to get context: {str(e)}", error=e)

    async def update_context(self,
                           field_name: str,
                           updates: JsonDict,
                           create_new: bool = True) -> Result[str]:
        """Update existing context or create new one."""
        try:
            async with self._context_lock:
                current_result = await self.get_context(field_name)
                current = current_result.data if current_result.success else None
                
                if current and not create_new:
                    # Update existing context
                    current.base_context.update(updates)
                    current.user_modifications.update(updates)
                    current.modified_at = datetime.now()
                    
                    # Persist updates
                    persist_result = await self._persist_context(current)
                    if not persist_result.success:
                        return persist_result
                    
                    return Result(True, "Context updated successfully", str(current.id))
                else:
                    # Create new context
                    new_context = GenerationContext(
                        field_name=field_name,
                        base_context=updates,
                        parent_context_id=str(current.id) if current else None
                    )
                    return await self.store_context(new_context)

        except Exception as e:
            self.error_handler.handle_error(
                e,
                ErrorCategory.STATE,
                ErrorLevel.ERROR,
                {'operation': 'update_context', 'field': field_name}
            )
            return Result(False, f"Failed to update context: {str(e)}", error=e)

    async def get_context_history(self, field_name: str) -> Result[List[GenerationContext]]:
        """Get complete context history for a field."""
        try:
            async with self._context_lock:
                history = self._context_histories.get(field_name)
                if not history:
                    return Result(True, "No history found", [])
                    
                # Ensure all contexts are loaded
                contexts = []
                for context in history.contexts:
                    context_result = await self.get_context(field_name, str(context.id))
                    if context_result.success:
                        contexts.append(context_result.data)
                
                return Result(True, "Context history retrieved", contexts)

        except Exception as e:
            self.error_handler.handle_error(
                e,
                ErrorCategory.STATE,
                ErrorLevel.ERROR,
                {'operation': 'get_history', 'field': field_name}
            )
            return Result(False, f"Failed to get context history: {str(e)}", error=e)

    async def _persist_context(self, context: GenerationContext) -> Result:
        """Save context to disk."""
        try:
            context_path = self.config.storage_path / f"{context.id}.json"
            
            # Convert to dictionary
            data = {
                'id': str(context.id),
                'field_name': context.field_name,
                'base_context': context.base_context,
                'dependencies': context.dependencies,
                'user_modifications': context.user_modifications,
                'metadata': context.metadata,
                'parent_context_id': context.parent_context_id,
                'created_at': context.created_at.isoformat(),
                'modified_at': context.modified_at.isoformat()
            }
            
            async with self._file_lock:
                async with aiofiles.open(context_path, 'w') as f:
                    await f.write(json.dumps(data, indent=2))
                    
            return Result(True, "Context persisted successfully")

        except Exception as e:
            self.error_handler.handle_error(
                e,
                ErrorCategory.STATE,
                ErrorLevel.ERROR,
                {'operation': 'persist_context', 'context_id': str(context.id)}
            )
            return Result(False, f"Failed to persist context: {str(e)}", error=e)

    async def _load_context(self, context_id: str) -> Result[GenerationContext]:
        """Load context from disk."""
        try:
            context_path = self.config.storage_path / f"{context_id}.json"
            if not context_path.exists():
                return Result(False, f"Context file not found: {context_id}")
                
            async with self._file_lock:
                async with aiofiles.open(context_path) as f:
                    content = await f.read()
                    data = json.loads(content)
            
            # Create context from data
            context = GenerationContext(
                id=data['id'],
                field_name=data['field_name'],
                base_context=data['base_context'],
                dependencies=data.get('dependencies', {}),
                user_modifications=data.get('user_modifications', {}),
                metadata=data.get('metadata', {}),
                created_at=datetime.fromisoformat(data['created_at']),
                modified_at=datetime.fromisoformat(data['modified_at'])
            )
            
            if data.get('parent_context_id'):
                context.parent_context_id = data['parent_context_id']
            
            # Cache the loaded context
            self._active_contexts[str(context.id)] = context
            
            # Update history if needed
            if context.field_name not in self._context_histories:
                self._context_histories[context.field_name] = ContextHistory(
                    field_name=context.field_name
                )
            history = self._context_histories[context.field_name]
            if context not in history.contexts:
                history.contexts.append(context)
            
            return Result(True, "Context loaded successfully", context)

        except Exception as e:
            self.error_handler.handle_error(
                e,
                ErrorCategory.STATE,
                ErrorLevel.ERROR,
                {'operation': 'load_context', 'context_id': context_id}
            )
            return Result(False, f"Failed to load context: {str(e)}", error=e)

    async def _periodic_cleanup(self):
        """Periodically clean up old contexts."""
        while True:
            try:
                await asyncio.sleep(self.config.cleanup_interval)
                await self._cleanup_old_contexts()
            except Exception as e:
                self.logger.error(f"Cleanup task failed: {str(e)}")

    async def _cleanup_old_contexts(self):
        """Clean up old contexts exceeding max_history."""
        try:
            async with self._context_lock:
                for field_name, history in self._context_histories.items():
                    while len(history.contexts) > self.config.max_history:
                        oldest = history.contexts.pop(0)
                        if str(oldest.id) in self._active_contexts:
                            del self._active_contexts[str(oldest.id)]
                        
                        # Remove from disk
                        context_path = self.config.storage_path / f"{oldest.id}.json"
                        if context_path.exists():
                            context_path.unlink()
                            
            return Result(True, "Cleanup completed successfully")
            
        except Exception as e:
            self.error_handler.handle_error(
                e,
                ErrorCategory.STATE,
                ErrorLevel.ERROR,
                {'operation': 'cleanup_contexts'}
            )
            return Result(False, f"Failed to cleanup contexts: {str(e)}", error=e)