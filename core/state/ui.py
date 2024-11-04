from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Set
from datetime import datetime
import asyncio
import logging
from PyQt6.QtCore import pyqtSignal
from uuid import UUID

from .base import StateManagerBase, OperationContext
from ..common.types import Result, JsonDict
from ..models.ui import (
    UIState, FieldState, DialogInfo, StatusInfo,
    TabType, DialogType, StatusLevel
)
from ..errors import ErrorHandler, StateError, ErrorCategory, ErrorLevel

@dataclass
class FieldUpdateContext:
    """Context for field updates"""
    field_name: str
    updates: Dict[str, Any]
    source: str
    metadata: JsonDict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

class UIStateManager(StateManagerBase[UIState]):
    """Manages UI state and interactions"""
    
    # Additional signals
    tab_changed = pyqtSignal(TabType)
    field_expanded = pyqtSignal(str, bool)
    field_focused = pyqtSignal(str, bool)
    dialog_requested = pyqtSignal(DialogInfo)
    dialog_closed = pyqtSignal(DialogType)
    status_updated = pyqtSignal(StatusInfo)
    loading_changed = pyqtSignal(bool)

    def __init__(self, error_handler: ErrorHandler):
        super().__init__(error_handler)
        self._ui_state = UIState()
        self._active_dialogs: List[DialogInfo] = []
        self._status_messages: List[StatusInfo] = []
        self._field_locks: Dict[str, asyncio.Lock] = {}
        self._dialog_lock = asyncio.Lock()
        self._status_lock = asyncio.Lock()
        self._tab_lock = asyncio.Lock()

    async def switch_tab(self, tab: TabType) -> Result:
        """Switch current tab with proper handling"""
        try:
            async with self._tab_lock:
                async with self.operation('switch_tab', {'tab': tab.name}):
                    if tab != self._ui_state.current_tab:
                        old_tab = self._ui_state.current_tab
                        self._ui_state.current_tab = tab
                        
                        # Update state and emit signal
                        await self.update_state(
                            'current_tab',
                            tab,
                            metadata={'previous_tab': old_tab.name if old_tab else None}
                        )
                        
                        self.tab_changed.emit(tab)
                        
                    return Result(True, "Tab switched successfully")
                    
        except Exception as e:
            self.error_handler.handle_error(
                e, ErrorCategory.UI, ErrorLevel.ERROR,
                {'operation': 'switch_tab', 'tab': tab.name}
            )
            return Result(False, f"Failed to switch tab: {str(e)}", error=e)

    async def set_field_state(self, 
                            field_name: str, 
                            updates: Dict[str, Any],
                            source: str = "user") -> Result:
        """Update field state with proper locking"""
        # Get or create field lock
        if field_name not in self._field_locks:
            self._field_locks[field_name] = asyncio.Lock()
            
        try:
            async with self._field_locks[field_name]:
                async with self.operation('update_field_state', {
                    'field': field_name,
                    'source': source
                }):
                    # Get or create field state
                    if field_name not in self._ui_state.field_states:
                        self._ui_state.field_states[field_name] = FieldState()

                    field_state = self._ui_state.field_states[field_name]
                    update_context = FieldUpdateContext(
                        field_name=field_name,
                        updates=updates,
                        source=source
                    )
                    
                    # Store old values for state change
                    old_values = {
                        key: getattr(field_state, key)
                        for key in updates
                        if hasattr(field_state, key)
                    }
                    
                    # Update fields
                    for key, value in updates.items():
                        if hasattr(field_state, key):
                            setattr(field_state, key, value)
                    
                    # Handle special states
                    if 'is_expanded' in updates:
                        await self._handle_expansion_change(
                            field_name,
                            updates['is_expanded']
                        )

                    if 'is_focused' in updates:
                        await self._handle_focus_change(
                            field_name,
                            updates['is_focused']
                        )

                    # Update last modified if content changed
                    if 'content' in updates:
                        field_state.last_modified = datetime.now()
                        field_state.is_modified = True
                    
                    # Update state
                    await self.update_state(
                        f'field_state_{field_name}',
                        field_state,
                        metadata={
                            'old_values': old_values,
                            'source': source
                        }
                    )
                    
                    return Result(True, "Field state updated successfully")
                    
        except Exception as e:
            self.error_handler.handle_error(
                e, ErrorCategory.UI, ErrorLevel.ERROR,
                {
                    'operation': 'set_field_state',
                    'field': field_name,
                    'updates': updates
                }
            )
            return Result(False, f"Failed to update field state: {str(e)}", error=e)

    async def show_dialog(self, dialog_info: DialogInfo) -> Result:
        """Show a dialog with proper management"""
        try:
            async with self._dialog_lock:
                async with self.operation('show_dialog', {
                    'type': dialog_info.dialog_type.name
                }):
                    # Add to dialog stack
                    self._active_dialogs.append(dialog_info)
                    
                    # Update state
                    await self.update_state(
                        'dialog_stack',
                        self._active_dialogs,
                        metadata={'added': dialog_info.dialog_type.name}
                    )
                    
                    # Emit signal
                    self.dialog_requested.emit(dialog_info)
                    
                    return Result(True, "Dialog shown successfully")
                    
        except Exception as e:
            self.error_handler.handle_error(
                e, ErrorCategory.UI, ErrorLevel.ERROR,
                {'operation': 'show_dialog', 'dialog_type': dialog_info.dialog_type.name}
            )
            return Result(False, f"Failed to show dialog: {str(e)}", error=e)

    async def close_dialog(self, dialog_type: Optional[DialogType] = None) -> Result:
        """Close dialog(s) with proper cleanup"""
        try:
            async with self._dialog_lock:
                async with self.operation('close_dialog', {
                    'type': dialog_type.name if dialog_type else None
                }):
                    if not self._active_dialogs:
                        return Result(True, "No dialogs to close")

                    if dialog_type:
                        # Remove specific dialog type
                        before_count = len(self._active_dialogs)
                        self._active_dialogs = [
                            d for d in self._active_dialogs 
                            if d.dialog_type != dialog_type
                        ]
                        removed = before_count - len(self._active_dialogs)
                    else:
                        # Remove top dialog
                        dialog = self._active_dialogs.pop()
                        dialog_type = dialog.dialog_type
                        removed = 1
                    
                    # Update state if any dialogs were removed
                    if removed > 0:
                        await self.update_state(
                            'dialog_stack',
                            self._active_dialogs,
                            metadata={
                                'removed': dialog_type.name,
                                'count': removed
                            }
                        )
                        
                        self.dialog_closed.emit(dialog_type)
                    
                    return Result(True, "Dialog(s) closed successfully")
                    
        except Exception as e:
            self.error_handler.handle_error(
                e, ErrorCategory.UI, ErrorLevel.ERROR,
                {'operation': 'close_dialog', 'dialog_type': dialog_type.name if dialog_type else None}
            )
            return Result(False, f"Failed to close dialog: {str(e)}", error=e)

    async def show_status(self, 
                         message: str,
                         level: StatusLevel,
                         duration: int = 5000) -> Result[str]:
        """Show status message with proper management"""
        try:
            async with self._status_lock:
                async with self.operation('show_status'):
                    # Create status info
                    status = StatusInfo(
                        message=message,
                        level=level,
                        duration=duration
                    )
                    
                    # Add to status list
                    self._status_messages.append(status)
                    
                    # Update state
                    await self.update_state(
                        'status_message',
                        status,
                        metadata={'duration': duration}
                    )
                    
                    # Emit signal
                    self.status_updated.emit(status)
                    
                    # Setup auto-clear if needed
                    if duration > 0:
                        asyncio.create_task(self._auto_clear_status(status, duration))
                    
                    return Result(True, "Status shown successfully", str(id(status)))
                    
        except Exception as e:
            self.error_handler.handle_error(
                e, ErrorCategory.UI, ErrorLevel.ERROR,
                {'operation': 'show_status', 'message': message}
            )
            return Result(False, f"Failed to show status: {str(e)}", error=e)

    async def set_loading(self, is_loading: bool) -> Result:
        """Set loading state"""
        try:
            async with self.operation('set_loading', {'loading': is_loading}):
                if self._ui_state.is_loading != is_loading:
                    self._ui_state.is_loading = is_loading
                    
                    # Update state
                    await self.update_state(
                        'is_loading',
                        is_loading,
                        metadata={'timestamp': datetime.now().isoformat()}
                    )
                    
                    # Emit signal
                    self.loading_changed.emit(is_loading)
                    
                return Result(True, "Loading state updated successfully")
                
        except Exception as e:
            self.error_handler.handle_error(
                e, ErrorCategory.UI, ErrorLevel.ERROR,
                {'operation': 'set_loading'}
            )
            return Result(False, f"Failed to set loading state: {str(e)}", error=e)

    async def _handle_expansion_change(self, field_name: str, is_expanded: bool) -> None:
        """Handle field expansion state change"""
        if is_expanded:
            if field_name not in self._ui_state.expanded_fields:
                self._ui_state.expanded_fields.append(field_name)
        else:
            if field_name in self._ui_state.expanded_fields:
                self._ui_state.expanded_fields.remove(field_name)
                
        self.field_expanded.emit(field_name, is_expanded)

    async def _handle_focus_change(self, field_name: str, is_focused: bool) -> None:
        """Handle field focus state change"""
        if is_focused:
            if self._ui_state.focused_field and self._ui_state.focused_field != field_name:
                # Clear focus from previous field
                await self.set_field_state(
                    self._ui_state.focused_field,
                    {'is_focused': False},
                    source='system'
                )
            self._ui_state.focused_field = field_name
        elif self._ui_state.focused_field == field_name:
            self._ui_state.focused_field = None
            
        self.field_focused.emit(field_name, is_focused)

    async def _auto_clear_status(self, status: StatusInfo, duration: int) -> None:
        """Auto-clear status message after duration"""
        await asyncio.sleep(duration / 1000)  # Convert to seconds
        
        async with self._status_lock:
            if status in self._status_messages:
                self._status_messages.remove(status)
                
                await self.update_state(
                    'status_cleared',
                    status,
                    metadata={'auto_cleared': True}
                )

    def get_field_state(self, field_name: str) -> Optional[FieldState]:
        """Get field state if exists"""
        return self._ui_state.field_states.get(field_name)

    def get_active_dialogs(self) -> List[DialogInfo]:
        """Get list of active dialogs"""
        return self._active_dialogs.copy()

    def get_status_messages(self) -> List[StatusInfo]:
        """Get list of active status messages"""
        return self._status_messages.copy()