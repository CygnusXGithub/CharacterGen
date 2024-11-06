from typing import Optional, Dict
from PyQt6.QtWidgets import (
    QMainWindow, QMenuBar, QMenu,
    QWidget
)
from PyQt6.QtCore import Qt

from core.state import UIStateManager
from .actions import ActionManager, ActionCategory

class MainMenuBar(QMenuBar):
    """Main application menu bar"""
    
    def __init__(self,
                 window: QMainWindow,
                 action_manager: ActionManager,
                 ui_manager: UIStateManager):
        super().__init__(window)
        self.action_manager = action_manager
        self.ui_manager = ui_manager
        self._menus: Dict[str, QMenu] = {}
        self._setup_menus()
        
    def _setup_menus(self):
        """Setup all menus"""
        # File menu
        file_menu = self.addMenu("&File")
        self._add_actions_to_menu(file_menu, ActionCategory.FILE)
        file_menu.addSeparator()
        file_menu.addAction("E&xit", self.window().close)
        
        # Edit menu
        edit_menu = self.addMenu("&Edit")
        self._add_actions_to_menu(edit_menu, ActionCategory.EDIT)
        
        # View menu
        view_menu = self.addMenu("&View")
        self._add_actions_to_menu(view_menu, ActionCategory.VIEW)
        
        # Generation menu
        gen_menu = self.addMenu("&Generation")
        self._add_actions_to_menu(gen_menu, ActionCategory.GENERATION)
        
        # Character menu
        char_menu = self.addMenu("&Character")
        self._add_actions_to_menu(char_menu, ActionCategory.CHARACTER)
        
        # Tools menu
        tools_menu = self.addMenu("&Tools")
        self._add_actions_to_menu(tools_menu, ActionCategory.TOOLS)
        
        # Help menu
        help_menu = self.addMenu("&Help")
        self._add_actions_to_menu(help_menu, ActionCategory.HELP)
        
        # Store menus
        self._menus = {
            "file": file_menu,
            "edit": edit_menu,
            "view": view_menu,
            "generation": gen_menu,
            "character": char_menu,
            "tools": tools_menu,
            "help": help_menu
        }
        
    def _add_actions_to_menu(self, menu: QMenu, category: ActionCategory):
        """Add all actions in category to menu"""
        actions = self.action_manager.get_actions_by_category(category)
        for action in actions.values():
            menu.addAction(action)
            
    def get_menu(self, name: str) -> Optional[QMenu]:
        """Get menu by name"""
        return self._menus.get(name)