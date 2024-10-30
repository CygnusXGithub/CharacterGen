from typing import Dict, Optional, List, Any
import json
from pathlib import Path
import asyncio
import logging
from uuid import UUID, uuid4
import aiofiles
from datetime import datetime
from ..models.context import GenerationContext, ContextHistory
from ..errors import ErrorHandler, StateError, ErrorCategory, ErrorLevel

class ContextPreservationService:
    """Service for managing and preserving generation contexts"""
    
    def __init__(self, 
                 error_handler: ErrorHandler,
                 storage_path: Path):
        self.error_handler = error_handler
        self.storage_path = storage_path
        self.logger = logging.getLogger(__name__)
        
        # Runtime storage
        self._context_histories: Dict[str, ContextHistory] = {}
        self._active_contexts: Dict[UUID, GenerationContext] = {}
        self._file_lock = asyncio.Lock()
        
        # Ensure storage directory exists
        self.storage_path.mkdir(parents=True, exist_ok=True)

    async def store_context(self, context: GenerationContext) -> UUID:
        """Store a new generation context"""
        try:
            # Get or create history for field
            if context.field_name not in self._context_histories:
                self._context_histories[context.field_name] = ContextHistory(
                    field_name=context.field_name
                )
            
            history = self._context_histories[context.field_name]
            history.contexts.append(context)
            history.current_context_id = context.id
            
            # Store in active contexts
            self._active_contexts[context.id] = context
            
            # Persist to disk
            await self._persist_context(context)
            
            return context.id

        except Exception as e:
            self.error_handler.handle_error(
                error=e,
                category=ErrorCategory.STATE,
                level=ErrorLevel.ERROR,
                context={'operation': 'store_context'}
            )
            raise

    async def get_context(self, 
                         field_name: str,
                         context_id: Optional[UUID] = None) -> Optional[GenerationContext]:
        """Get context by ID or current context for field"""
        try:
            if context_id:
                # Try memory first
                if context_id in self._active_contexts:
                    return self._active_contexts[context_id]
                    
                # Try loading from disk
                return await self._load_context(context_id)
            
            # Get current context for field
            history = self._context_histories.get(field_name)
            if not history or not history.current_context_id:
                return None
                
            return await self.get_context(field_name, history.current_context_id)

        except Exception as e:
            self.error_handler.handle_error(
                error=e,
                category=ErrorCategory.STATE,
                level=ErrorLevel.ERROR,
                context={'operation': 'get_context', 'field': field_name}
            )
            return None

    async def update_context(self,
                           field_name: str,
                           updates: Dict[str, Any],
                           create_new: bool = True) -> Optional[UUID]:
        """Update existing context or create new one"""
        try:
            current = await self.get_context(field_name)
            
            if current and not create_new:
                # Update existing context
                current.base_context.update(updates)
                current.user_modifications.update(updates)
                await self._persist_context(current)
                return current.id
            else:
                # Create new context
                new_context = GenerationContext(
                    field_name=field_name,
                    base_context=updates,
                    parent_context_id=current.id if current else None
                )
                return await self.store_context(new_context)

        except Exception as e:
            self.error_handler.handle_error(
                error=e,
                category=ErrorCategory.STATE,
                level=ErrorLevel.ERROR,
                context={'operation': 'update_context', 'field': field_name}
            )
            return None

    async def get_context_history(self, field_name: str) -> List[GenerationContext]:
        """Get complete context history for a field"""
        try:
            history = self._context_histories.get(field_name)
            if not history:
                return []
                
            # Ensure all contexts are loaded
            contexts = []
            for context in history.contexts:
                loaded = await self.get_context(field_name, context.id)
                if loaded:
                    contexts.append(loaded)
            
            return contexts

        except Exception as e:
            self.error_handler.handle_error(
                error=e,
                category=ErrorCategory.STATE,
                level=ErrorLevel.ERROR,
                context={'operation': 'get_history', 'field': field_name}
            )
            return []

    async def _persist_context(self, context: GenerationContext):
        """Save context to disk"""
        try:
            context_path = self.storage_path / f"{context.id}.json"
            
            # Convert to dictionary
            data = {
                'id': str(context.id),
                'field_name': context.field_name,
                'base_context': context.base_context,
                'dependencies': context.dependencies,
                'user_modifications': context.user_modifications,
                'metadata': context.metadata,
                'parent_context_id': str(context.parent_context_id) if context.parent_context_id else None,
                'created_at': context.created_at.isoformat()  # This is correct
            }
            
            async with self._file_lock:
                async with aiofiles.open(context_path, 'w') as f:
                    await f.write(json.dumps(data, indent=2))

        except Exception as e:
            self.error_handler.handle_error(
                error=e,
                category=ErrorCategory.STATE,
                level=ErrorLevel.ERROR,
                context={'operation': 'persist_context', 'context_id': str(context.id)}
            )
            raise

    async def _load_context(self, context_id: UUID) -> Optional[GenerationContext]:
        """Load context from disk"""
        try:
            context_path = self.storage_path / f"{context_id}.json"
            if not context_path.exists():
                return None
                
            async with self._file_lock:
                async with aiofiles.open(context_path) as f:
                    content = await f.read()
                    data = json.loads(content)
            
            # Fix datetime parsing
            try:
                created_at = datetime.fromisoformat(data['created_at'])
            except ValueError:
                # If there's an issue with the datetime string, use current time
                created_at = datetime.now()
                self.logger.warning(f"Could not parse datetime {data['created_at']}, using current time")
                
            # Convert loaded data back to GenerationContext
            context = GenerationContext(
                id=UUID(data['id']),
                field_name=data['field_name'],
                base_context=data['base_context'],
                dependencies=data.get('dependencies', {}),
                user_modifications=data.get('user_modifications', {}),
                metadata=data.get('metadata', {}),
                created_at=created_at
            )
            
            if data.get('parent_context_id'):
                context.parent_context_id = UUID(data['parent_context_id'])
            
            # Cache the loaded context
            self._active_contexts[context.id] = context
            
            # Update history if needed
            if context.field_name not in self._context_histories:
                self._context_histories[context.field_name] = ContextHistory(
                    field_name=context.field_name
                )
            history = self._context_histories[context.field_name]
            if context not in history.contexts:
                history.contexts.append(context)
            
            return context

        except Exception as e:
            self.error_handler.handle_error(
                error=e,
                category=ErrorCategory.STATE,
                level=ErrorLevel.ERROR,
                context={'operation': 'load_context', 'context_id': str(context_id)}
            )
            return None