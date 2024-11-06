from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtCore import Qt

class ActionCategory(Enum):
    """Categories for application actions"""
    FILE = auto()
    EDIT = auto()
    VIEW = auto()
    GENERATION = auto()
    CHARACTER = auto()
    TOOLS = auto()
    HELP = auto()

@dataclass
class ActionDefinition:
    """Definition of a menu/toolbar action"""
    id: str
    text: str
    category: ActionCategory
    callback: Optional[Callable] = None
    shortcut: Optional[str] = None
    icon_name: Optional[str] = None
    tooltip: Optional[str] = None
    checkable: bool = False
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

class ActionManager:
    """Manages application actions and their states"""
    
    def __init__(self):
        self._actions: Dict[str, QAction] = {}
        self._definitions: Dict[str, ActionDefinition] = {}
        self._setup_default_actions()
        
    def _setup_default_actions(self):
        """Setup default application actions"""
        # File actions
        self.register_action(ActionDefinition(
            id="new_character",
            text="&New Character",
            category=ActionCategory.FILE,
            shortcut="Ctrl+N",
            tooltip="Create a new character",
            icon_name="new"
        ))
        
        self.register_action(ActionDefinition(
            id="open_character",
            text="&Open...",
            category=ActionCategory.FILE,
            shortcut="Ctrl+O",
            tooltip="Open an existing character",
            icon_name="open"
        ))
        
        self.register_action(ActionDefinition(
            id="save_character",
            text="&Save",
            category=ActionCategory.FILE,
            shortcut="Ctrl+S",
            tooltip="Save current character",
            icon_name="save"
        ))
        
        self.register_action(ActionDefinition(
            id="save_as",
            text="Save &As...",
            category=ActionCategory.FILE,
            shortcut="Ctrl+Shift+S",
            tooltip="Save character with a new name",
            icon_name="save-as"
        ))
        
        self.register_action(ActionDefinition(
            id="export_character",
            text="&Export...",
            category=ActionCategory.FILE,
            shortcut="Ctrl+E",
            tooltip="Export character in different format",
            icon_name="export"
        ))
        
        # Edit actions
        self.register_action(ActionDefinition(
            id="undo",
            text="&Undo",
            category=ActionCategory.EDIT,
            shortcut="Ctrl+Z",
            tooltip="Undo last action",
            icon_name="undo",
            enabled=False
        ))
        
        self.register_action(ActionDefinition(
            id="redo",
            text="&Redo",
            category=ActionCategory.EDIT,
            shortcut="Ctrl+Y",
            tooltip="Redo last undone action",
            icon_name="redo",
            enabled=False
        ))
        
        # Generation actions
        self.register_action(ActionDefinition(
            id="generate_field",
            text="Generate &Field",
            category=ActionCategory.GENERATION,
            shortcut="Ctrl+G",
            tooltip="Generate current field",
            icon_name="generate"
        ))
        
        self.register_action(ActionDefinition(
            id="generate_all",
            text="Generate &All",
            category=ActionCategory.GENERATION,
            shortcut="Ctrl+Shift+G",
            tooltip="Generate all fields",
            icon_name="generate-all"
        ))
        
        # View actions
        self.register_action(ActionDefinition(
            id="toggle_preview",
            text="Toggle &Preview",
            category=ActionCategory.VIEW,
            shortcut="Ctrl+P",
            tooltip="Toggle character preview",
            icon_name="preview",
            checkable=True
        ))
        
        # Tools actions
        self.register_action(ActionDefinition(
            id="settings",
            text="&Settings",
            category=ActionCategory.TOOLS,
            shortcut="Ctrl+,",
            tooltip="Open settings dialog",
            icon_name="settings"
        ))
        
        # Help actions
        self.register_action(ActionDefinition(
            id="help",
            text="&Help",
            category=ActionCategory.HELP,
            shortcut="F1",
            tooltip="Show help",
            icon_name="help"
        ))
        
        self.register_action(ActionDefinition(
            id="about",
            text="&About",
            category=ActionCategory.HELP,
            tooltip="About CharacterGen",
            icon_name="about"
        ))
        
    def register_action(self, definition: ActionDefinition) -> QAction:
        """Register a new action"""
        action = QAction(definition.text)
        
        # Set properties
        if definition.shortcut:
            action.setShortcut(QKeySequence(definition.shortcut))
        if definition.tooltip:
            action.setToolTip(definition.tooltip)
        if definition.icon_name:
            # TODO: Set icon from theme
            pass
        
        action.setCheckable(definition.checkable)
        action.setEnabled(definition.enabled)
        
        # Store action and definition
        self._actions[definition.id] = action
        self._definitions[definition.id] = definition
        
        return action
    
    def get_action(self, action_id: str) -> Optional[QAction]:
        """Get action by ID"""
        return self._actions.get(action_id)
        
    def set_callback(self, action_id: str, callback: Callable):
        """Set callback for action"""
        if action_id in self._actions:
            self._actions[action_id].triggered.connect(callback)
            self._definitions[action_id].callback = callback
            
    def set_enabled(self, action_id: str, enabled: bool):
        """Set enabled state of action"""
        if action_id in self._actions:
            self._actions[action_id].setEnabled(enabled)
            
    def get_actions_by_category(self, category: ActionCategory) -> Dict[str, QAction]:
        """Get all actions in a category"""
        return {
            action_id: action 
            for action_id, action in self._actions.items()
            if self._definitions[action_id].category == category
        }