from typing import Dict, Optional, List
from enum import Enum, auto
from PyQt6.QtWidgets import (
    QWidget, QTabWidget, QVBoxLayout,
    QStackedWidget, QPushButton, QHBoxLayout
)
from PyQt6.QtCore import Qt, pyqtSignal

from core.state import UIStateManager
from ..base import BaseWidget
from core.errors import ErrorLevel, ErrorCategory

class TabState(Enum):
    """Tab states"""
    ENABLED = auto()
    DISABLED = auto()
    HIDDEN = auto()
    LOADING = auto()

class TabContainer(BaseWidget):
    """Container for managing tabbed content"""
    
    tab_changed = pyqtSignal(str)  # Emitted when active tab changes
    tab_state_changed = pyqtSignal(str, TabState)  # Emitted when tab state changes
    
    def __init__(self, ui_manager: UIStateManager, parent: Optional[QWidget] = None):
        super().__init__(ui_manager, parent)
        self._tabs: Dict[str, QWidget] = {}
        self._tab_states: Dict[str, TabState] = {}
        self._buttons: Dict[str, QPushButton] = {}
        self._current_tab: Optional[str] = None
        self._setup_ui()
        
        # Create layout first
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)
        
        # Tab bar
        self._tab_bar_widget = QWidget()
        self._tab_bar = QHBoxLayout(self._tab_bar_widget)
        self._tab_bar.setSpacing(2)
        self._tab_bar.setContentsMargins(4, 4, 4, 0)
        self._main_layout.addWidget(self._tab_bar_widget)
        
        # Content area
        self._content = QStackedWidget(self)
        self._main_layout.addWidget(self._content)
        
        self._setup_styling()
        
    def _setup_ui(self):
        """Setup UI layout"""
        # Main layout
        self._main_layout = QVBoxLayout()
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)
        self.setLayout(self._main_layout)
        
        # Tab bar
        self._tab_bar_widget = QWidget()
        self._tab_bar = QHBoxLayout()
        self._tab_bar.setSpacing(2)
        self._tab_bar.setContentsMargins(4, 4, 4, 0)
        self._tab_bar_widget.setLayout(self._tab_bar)
        self._main_layout.addWidget(self._tab_bar_widget)
        
        # Content area
        self._content = QStackedWidget()
        self._main_layout.addWidget(self._content)
        
        self._setup_styling()

    def _setup_styling(self):
        """Setup container styling"""
        self.setStyleSheet("""
            TabContainer {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
            }
            
            QPushButton {
                padding: 8px 16px;
                border: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                color: #666666;
                background-color: transparent;
            }
            
            QPushButton:hover {
                background-color: #f5f5f5;
            }
            
            QPushButton[active="true"] {
                color: #2980b9;
                border-bottom: 2px solid #2980b9;
                font-weight: bold;
                background-color: #f8f9fa;
            }
            
            QPushButton:disabled {
                color: #cccccc;
                background-color: #f5f5f5;
            }
        """)

    def add_tab(self, 
                tab_id: str, 
                title: str, 
                widget: QWidget,
                state: TabState = TabState.ENABLED) -> bool:
        """Add a new tab"""
        try:
            if tab_id in self._tabs:
                return False

            # Create tab button with proper object naming
            button_name = f"tab_button_{tab_id}"
            tab_button = QPushButton(title, self)  # Set parent explicitly
            tab_button.setObjectName(button_name)  # Set object name
            tab_button.clicked.connect(lambda: self.set_current_tab(tab_id))
            
            # Store button reference
            self._buttons[tab_id] = tab_button  # Add this line
            
            # Insert before the stretch
            self._tab_bar.insertWidget(self._tab_bar.count() - 1, tab_button)
            
            # Store widget
            self._tabs[tab_id] = widget
            self._tab_states[tab_id] = state
            self._content.addWidget(widget)
            
            # Set initial state
            self._update_tab_state(tab_id, state)
            
            # If first tab, make it active
            if len(self._tabs) == 1:
                self.set_current_tab(tab_id)
            
            return True
            
        except Exception as e:
            self.error_handler.handle_error(
                error=e,
                category=ErrorCategory.UI,
                level=ErrorLevel.ERROR,
                context={'operation': 'add_tab', 'tab_id': tab_id}
            )
            return False

    def remove_tab(self, tab_id: str) -> bool:
        """Remove a tab"""
        if tab_id not in self._tabs:
            return False
        
        # Remove button
        if tab_id in self._buttons:
            self._buttons[tab_id].deleteLater()
            del self._buttons[tab_id]
        
        # Remove widget
        widget = self._tabs.pop(tab_id)
        self._content.removeWidget(widget)
        self._tab_states.pop(tab_id)
        
        # Update current tab if needed
        if self._current_tab == tab_id:
            self._current_tab = None
            if self._tabs:
                self.set_current_tab(next(iter(self._tabs)))
        
        return True

    def set_current_tab(self, tab_id: str) -> bool:
        """Set the current active tab"""
        if tab_id not in self._tabs or self._tab_states[tab_id] == TabState.DISABLED:
            return False
        
        # Update previous tab
        if self._current_tab:
            prev_button = self.findChild(QPushButton, f"tab_button_{self._current_tab}")
            if prev_button:
                prev_button.setProperty("active", False)
                prev_button.setStyleSheet(prev_button.styleSheet())
        
        # Update new tab
        self._current_tab = tab_id
        curr_button = self.findChild(QPushButton, f"tab_button_{tab_id}")
        if curr_button:
            curr_button.setProperty("active", True)
            curr_button.setStyleSheet(curr_button.styleSheet())
        
        # Show widget
        widget = self._tabs[tab_id]
        self._content.setCurrentWidget(widget)
        
        # Emit signal
        self.tab_changed.emit(tab_id)
        return True

    def set_tab_state(self, tab_id: str, state: TabState) -> bool:
        """Set tab state"""
        if tab_id not in self._tabs:
            return False
        
        # Update internal state first
        self._tab_states[tab_id] = state
        
        # Update visual state
        self._update_tab_state(tab_id, state)
        
        # Emit signal
        self.tab_state_changed.emit(tab_id, state)
        
        return True

    def _update_tab_state(self, tab_id: str, state: TabState):
        """Update tab button state"""
        button = self._buttons.get(tab_id)  # Use stored reference
        if not button:
            return
        
        if state == TabState.DISABLED:
            button.setEnabled(False)
            button.setToolTip("This tab is currently disabled")
        elif state == TabState.HIDDEN:
            button.hide()
        elif state == TabState.LOADING:
            button.setEnabled(False)
            button.setToolTip("Loading...")
        else:  # ENABLED
            button.setEnabled(True)
            button.show()
            button.setToolTip("")

    def get_current_tab(self) -> Optional[str]:
        """Get current tab ID"""
        return self._current_tab

    def get_tab_state(self, tab_id: str) -> Optional[TabState]:
        """Get tab state"""
        return self._tab_states.get(tab_id)

    def get_tab_widget(self, tab_id: str) -> Optional[QWidget]:
        """Get tab widget"""
        return self._tabs.get(tab_id)