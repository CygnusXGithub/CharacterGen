from enum import Enum, auto

class FieldName(Enum):
    """Enumeration of character card fields"""
    NAME = "name"
    DESCRIPTION = "description"
    SCENARIO = "scenario"
    FIRST_MES = "first_mes"
    MES_EXAMPLE = "mes_example"
    PERSONALITY = "personality"

class CardField(Enum):
    """All character card fields including metadata"""
    # Generated fields (map to FieldName)
    NAME = "name"
    DESCRIPTION = "description"
    SCENARIO = "scenario"
    FIRST_MES = "first_mes"
    MES_EXAMPLE = "mes_example"
    PERSONALITY = "personality"
    
    # Metadata fields
    SYSTEM_PROMPT = "system_prompt"
    CREATOR_NOTES = "creator_notes"
    POST_HISTORY_INSTRUCTIONS = "post_history_instructions"

class CardFormat(Enum):
    """Supported character card formats"""
    JSON = "json"
    PNG = "png"

class GenerationMode(Enum):
    """Different generation modes for fields"""
    DIRECT = auto()   # Use input directly without generation
    GENERATE = auto() # Generate new content
    HYBRID = auto()   # Combine input with generation

class UIMode(Enum):
    """Different UI modes for field editing"""
    COMPACT = auto()  # Normal view
    EXPANDED = auto() # Expanded/focused view
    READONLY = auto() # Non-editable view

class TabType(Enum):
    """Types of tabs in the application"""
    EDITOR = "editor"
    GENERATION = "generation"
    BASE_PROMPTS = "base_prompts"

class PromptTagType(Enum):
    """Types of tags that can be used in prompts"""
    FIELD = "field"       # References another field
    INPUT = "input"       # User input
    CONDITIONAL = "conditional" # Conditional content
    CHAR = "char"         # Character name placeholder
    USER = "user"         # User name placeholder

class SaveMode(Enum):
    """Different modes for saving character data"""
    OVERWRITE = auto()  # Replace existing file
    NEW = auto()        # Create new file
    VERSIONED = auto()  # Create new version

class DialogType(Enum):
    """Types of application dialogs"""
    PREFERENCES = "preferences"
    ABOUT = "about"
    FIELD_EDITOR = "field_editor"
    SAVE_PROMPT = "save_prompt"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

class ThemeType(Enum):
    """Application theme types"""
    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"

class StatusLevel(Enum):
    """Status message importance levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"

class OperationType(Enum):
    """Types of operations that can be performed"""
    LOAD = "load"
    SAVE = "save"
    GENERATE = "generate"
    EXPORT = "export"
    IMPORT = "import"
    VALIDATE = "validate"

class ValidationLevel(Enum):
    """Validation result levels"""
    PASS = "pass"           # No issues
    WARNING = "warning"     # Potential issues
    ERROR = "error"        # Critical issues

class ImageFormat(Enum):
    """Supported image formats"""
    PNG = "png"
    JPEG = "jpeg"
    WEBP = "webp"
    DEFAULT = PNG

class CharacterDataVersion(Enum):
    """Character data format versions"""
    V1 = "chara_card_v1"
    V2 = "chara_card_v2"
    LATEST = V2

class EventType(Enum):
    """Types of application events"""
    CHARACTER_LOADED = "character_loaded"
    CHARACTER_SAVED = "character_saved"
    GENERATION_STARTED = "generation_started"
    GENERATION_COMPLETED = "generation_completed"
    SETTINGS_UPDATED = "settings_updated"
    ERROR_OCCURRED = "error_occurred"