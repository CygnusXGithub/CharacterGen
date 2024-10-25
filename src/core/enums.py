from enum import Enum, auto

class FieldName(Enum):
    """Enumeration of character card fields"""
    NAME = "name"
    DESCRIPTION = "description"
    SCENARIO = "scenario"
    FIRST_MES = "first_mes"
    MES_EXAMPLE = "mes_example"
    PERSONALITY = "personality"

class CardFormat(Enum):
    """Supported character card formats"""
    JSON = "json"
    PNG = "png"
    
class GenerationMode(Enum):
    """Different generation modes for fields"""
    DIRECT = auto()  # Use input directly without generation
    GENERATE = auto()  # Generate new content
    HYBRID = auto()  # Combine input with generation
    
class PromptTagType(Enum):
    """Types of tags that can be used in prompts"""
    FIELD = "field"  # References another field
    INPUT = "input"  # User input
    CONDITIONAL = "conditional"  # Conditional content
    CHAR = "char"  # Character name placeholder
    USER = "user"  # User name placeholder
    
class SaveMode(Enum):
    """Different modes for saving character data"""
    OVERWRITE = auto()  # Replace existing file
    NEW = auto()  # Create new file
    VERSIONED = auto()  # Create new version
    
class UIMode(Enum):
    """Different UI modes for field editing"""
    COMPACT = auto()  # Normal view
    EXPANDED = auto()  # Expanded/focused view
    READONLY = auto()  # Non-editable view