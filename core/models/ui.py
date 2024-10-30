from dataclasses import dataclass, field
from typing import Dict, Optional, List, Any
from enum import Enum, auto
from datetime import datetime

class TabType(Enum):
    """Types of available tabs"""
    EDITOR = auto()
    GENERATION = auto()
    SETTINGS = auto()
    PREVIEW = auto()

class DialogType(Enum):
    """Types of dialogs"""
    SAVE = auto()
    LOAD = auto()
    EXPORT = auto()
    SETTINGS = auto()
    CONFIRMATION = auto()
    ERROR = auto()

class StatusLevel(Enum):
    """Status message levels"""
    INFO = auto()
    SUCCESS = auto()
    WARNING = auto()
    ERROR = auto()

@dataclass
class FieldState:
    """State for a single editable field"""
    content: str = ""
    is_modified: bool = False
    is_valid: bool = True
    validation_message: str = ""
    is_generating: bool = False
    is_focused: bool = False
    is_expanded: bool = False
    scroll_position: int = 0
    last_modified: Optional[datetime] = None

@dataclass
class DialogInfo:
    """Information about an active dialog"""
    dialog_type: DialogType
    title: str
    message: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    callback: Optional[callable] = None

@dataclass
class StatusInfo:
    """Status bar information"""
    message: str
    level: StatusLevel
    timestamp: datetime = field(default_factory=datetime.now)
    duration: int = 5000  # milliseconds

@dataclass
class UIState:
    """Complete UI state"""
    current_tab: TabType = TabType.EDITOR
    field_states: Dict[str, FieldState] = field(default_factory=dict)
    expanded_fields: List[str] = field(default_factory=list)
    focused_field: Optional[str] = None
    dialog_stack: List[DialogInfo] = field(default_factory=list)
    status_message: Optional[StatusInfo] = None
    is_loading: bool = False