from typing import List, Optional
from PyQt6.QtWidgets import QMenu, QWidget
from PyQt6.QtCore import Qt, QPoint

from core.state import UIStateManager
from .actions import ActionManager, ActionCategory

class FieldContextMenu(QMenu):
    """Context menu for field editor"""
    
    def __init__(self,
                 action_manager: ActionManager,
                 ui_manager: UIStateManager,
                 field_name: str,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.action_manager = action_manager
        self.ui_manager = ui_manager
        self.field_name = field_name
        self._setup_menu()
        
    def _setup_menu(self):
        """Setup menu items"""
        # Generation actions
        if gen_action := self.action_manager.get_action("generate_field"):
            self.addAction(gen_action)
        if regen_action := self.action_manager.get_action("regenerate_with_deps"):
            self.addAction(regen_action)
            
        self.addSeparator()
        
        # Edit actions
        if cut_action := self.action_manager.get_action("cut"):
            self.addAction(cut_action)
        if copy_action := self.action_manager.get_action("copy"):
            self.addAction(copy_action)
        if paste_action := self.action_manager.get_action("paste"):
            self.addAction(paste_action)
            
        self.addSeparator()
        
        # Field actions
        if clear_action := self.action_manager.get_action("clear_field"):
            self.addAction(clear_action)
        if settings_action := self.action_manager.get_action("field_settings"):
            self.addAction(settings_action)

class GenerationContextMenu(QMenu):
    """Context menu for generation panel"""
    
    def __init__(self,
                 action_manager: ActionManager,
                 ui_manager: UIStateManager,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.action_manager = action_manager
        self.ui_manager = ui_manager
        self._setup_menu()
        
    def _setup_menu(self):
        """Setup menu items"""
        # Generation actions
        if gen_all := self.action_manager.get_action("generate_all"):
            self.addAction(gen_all)
        if gen_missing := self.action_manager.get_action("generate_missing"):
            self.addAction(gen_missing)
        if regen_all := self.action_manager.get_action("regenerate_all"):
            self.addAction(regen_all)
            
        self.addSeparator()
        
        # Queue actions
        if clear_queue := self.action_manager.get_action("clear_queue"):
            self.addAction(clear_queue)
        if cancel_all := self.action_manager.get_action("cancel_all"):
            self.addAction(cancel_all)

class PreviewContextMenu(QMenu):
    """Context menu for character preview"""
    
    def __init__(self,
                 action_manager: ActionManager,
                 ui_manager: UIStateManager,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.action_manager = action_manager
        self.ui_manager = ui_manager
        self._setup_menu()
        
    def _setup_menu(self):
        """Setup menu items"""
        # Preview actions
        if refresh := self.action_manager.get_action("refresh_preview"):
            self.addAction(refresh)
        if export := self.action_manager.get_action("export_character"):
            self.addAction(export)
            
        self.addSeparator()
        
        # View actions
        if zoom_in := self.action_manager.get_action("zoom_in"):
            self.addAction(zoom_in)
        if zoom_out := self.action_manager.get_action("zoom_out"):
            self.addAction(zoom_out)
        if reset_zoom := self.action_manager.get_action("reset_zoom"):
            self.addAction(reset_zoom)