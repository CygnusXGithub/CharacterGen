from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from PyQt6.QtWidgets import QWidget, QStackedWidget
from PyQt6.QtCore import Qt, pyqtSignal

from core.state import UIStateManager
from core.models.ui import TabType
from .editor_tab import EditorTab
from .generation_tab import GenerationTab
from .prompts_tab import PromptsTab
from ..base import BaseWidget

@dataclass
class TabData:
    """Data for a managed tab"""
    widget: BaseWidget
    type: TabType
    title: str
    enabled: bool = True
    visible: bool = True
    last_active: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

class TabManager(BaseWidget):
    """Manages application tabs and their states"""
    
    tab_changed = pyqtSignal(TabType)  # New active tab
    tab_state_changed = pyqtSignal(TabType, bool)  # Tab type, enabled
    
    def __init__(self, ui_manager: UIStateManager, parent: Optional[QWidget] = None):
        self._tabs: Dict[TabType, TabData] = {}
        self._active_tab: Optional[TabType] = None
        super().__init__(ui_manager, parent)
        
    def _setup_ui(self):
        """Setup tab manager UI"""
        self._layout.setContentsMargins(0, 0, 0, 0)
        
        # Tab container
        self._container = QStackedWidget()
        self._layout.addWidget(self._container)
        
        # Create standard tabs
        self._editor_tab = EditorTab(self.ui_manager)
        self._generation_tab = GenerationTab(self.ui_manager)
        self._prompts_tab = PromptsTab(self.ui_manager)
        
        # Register tabs
        self.register_tab(TabType.EDITOR, self._editor_tab, "Editor")
        self.register_tab(TabType.GENERATION, self._generation_tab, "Generation")
        self.register_tab(TabType.PROMPTS, self._prompts_tab, "Prompts")
        
        # Set initial tab
        self.activate_tab(TabType.EDITOR)
        
    def register_tab(self, 
                    tab_type: TabType,
                    widget: BaseWidget,
                    title: str,
                    enabled: bool = True,
                    visible: bool = True) -> bool:
        """Register a new tab"""
        if tab_type in self._tabs:
            return False
            
        # Create tab data
        tab_data = TabData(
            widget=widget,
            type=tab_type,
            title=title,
            enabled=enabled,
            visible=visible
        )
        
        # Add widget to container
        self._container.addWidget(widget)
        
        # Store tab data
        self._tabs[tab_type] = tab_data
        
        return True
        
    def activate_tab(self, tab_type: TabType) -> bool:
        """Activate specified tab"""
        if tab_type not in self._tabs or not self._tabs[tab_type].enabled:
            return False
            
        # Update previous tab
        if self._active_tab:
            prev_tab = self._tabs[self._active_tab]
            prev_tab.last_active = datetime.now()
            
        # Update new tab
        tab_data = self._tabs[tab_type]
        tab_data.last_active = datetime.now()
        self._active_tab = tab_type
        
        # Switch visible widget
        self._container.setCurrentWidget(tab_data.widget)
        
        # Emit signal
        self.tab_changed.emit(tab_type)
        
        return True
        
    def set_tab_enabled(self, tab_type: TabType, enabled: bool):
        """Set tab enabled state"""
        if tab_type in self._tabs:
            self._tabs[tab_type].enabled = enabled
            self.tab_state_changed.emit(tab_type, enabled)
            
    def set_tab_visible(self, tab_type: TabType, visible: bool):
        """Set tab visibility"""
        if tab_type in self._tabs:
            self._tabs[tab_type].visible = visible
            
    def get_active_tab(self) -> Optional[TabType]:
        """Get currently active tab"""
        return self._active_tab
        
    def get_tab_widget(self, tab_type: TabType) -> Optional[BaseWidget]:
        """Get widget for tab"""
        return self._tabs[tab_type].widget if tab_type in self._tabs else None
        
    def get_tab_title(self, tab_type: TabType) -> Optional[str]:
        """Get tab title"""
        return self._tabs[tab_type].title if tab_type in self._tabs else None
        
    def get_tab_metadata(self, tab_type: TabType) -> Dict[str, Any]:
        """Get tab metadata"""
        return self._tabs[tab_type].metadata if tab_type in self._tabs else {}
        
    def set_tab_metadata(self, tab_type: TabType, metadata: Dict[str, Any]):
        """Set tab metadata"""
        if tab_type in self._tabs:
            self._tabs[tab_type].metadata = metadata.copy()
            
    def get_visible_tabs(self) -> List[TabType]:
        """Get list of visible tabs"""
        return [
            tab_type for tab_type, data in self._tabs.items()
            if data.visible
        ]
        
    def get_enabled_tabs(self) -> List[TabType]:
        """Get list of enabled tabs"""
        return [
            tab_type for tab_type, data in self._tabs.items()
            if data.enabled
        ]
        
    async def save_state(self) -> Dict[str, Any]:
        """Save tab manager state"""
        return {
            'active_tab': self._active_tab.name if self._active_tab else None,
            'tabs': {
                tab_type.name: {
                    'enabled': data.enabled,
                    'visible': data.visible,
                    'last_active': data.last_active.isoformat() if data.last_active else None,
                    'metadata': data.metadata
                }
                for tab_type, data in self._tabs.items()
            }
        }
        
    async def restore_state(self, state: Dict[str, Any]):
        """Restore tab manager state"""
        # Restore tab states
        tab_states = state.get('tabs', {})
        for tab_name, tab_data in tab_states.items():
            try:
                tab_type = TabType[tab_name]
                if tab_type in self._tabs:
                    self._tabs[tab_type].enabled = tab_data.get('enabled', True)
                    self._tabs[tab_type].visible = tab_data.get('visible', True)
                    if tab_data.get('last_active'):
                        self._tabs[tab_type].last_active = datetime.fromisoformat(
                            tab_data['last_active']
                        )
                    self._tabs[tab_type].metadata = tab_data.get('metadata', {})
            except (KeyError, ValueError):
                continue
                
        # Restore active tab
        active_tab_name = state.get('active_tab')
        if active_tab_name:
            try:
                self.activate_tab(TabType[active_tab_name])
            except (KeyError, ValueError):
                pass