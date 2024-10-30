
# I. CharacterGen System Architecture

## Core Design Principles
1. **Single Source of Truth**
   - Each type of data has one authoritative source
   - All state changes flow through managers
   - No direct state modification in UI components

2. **Unidirectional Data Flow**
   ```
   User Action -> Manager Update -> State Change -> UI Update
   ```
   - UI components are "dumb" and reflect state
   - All state changes emit signals
   - Components subscribe to state changes

3. **Clear Separation of Concerns**
   ```
   Managers (State/Logic) -> Services (Operations) -> UI (Display/Input)
   ```
## Core System Components

### 1. State Management Layer
```python
# Core state managers
class StateManagerBase(QObject):
    """Base class for all state managers"""
    state_changed = pyqtSignal(str, object)  # (state_key, new_value)
    error_occurred = pyqtSignal(str, str)    # (error_type, message)
    
    def __init__(self):
        super().__init__()
        self._state: Dict[str, Any] = {}
        self._operation_lock = threading.Lock()
        
    def update_state(self, key: str, value: Any, emit: bool = True):
        """Thread-safe state update"""
        with self._operation_lock:
            self._state[key] = value
            if emit:
                self.state_changed.emit(key, value)

class AppStateManager(StateManagerBase):
    """Global application state"""
    def __init__(self):
        super().__init__()
        self.character_manager = CharacterStateManager()
        self.ui_manager = UIStateManager()
        self.generation_manager = GenerationManager()
        
        # Connect cross-manager signals
        self._connect_managers()
    
    def _connect_managers(self):
        """Connect inter-manager signals"""
        self.character_manager.state_changed.connect(
            self.ui_manager.handle_character_state_change)
        self.generation_manager.state_changed.connect(
            self.ui_manager.handle_generation_state_change)

@dataclass
class GenerationContext:
    """Enhanced generation context"""
    field: FieldName
    input_text: str
    base_prompt: str
    base_prompt_name: str
    additional_context: Dict[str, Any] = field(default_factory=dict)

class MetadataManager(StateManager['MetadataState']):
    """Manages generation metadata"""
    def store_generation_metadata(self, 
                                field: FieldName, 
                                context: GenerationContext,
                                result: str):
        """Store metadata for generated content"""
        metadata = GenerationMetadata(
            base_prompt_name=context.base_prompt_name,
            base_prompt_content=context.base_prompt,
            input_context=context.input_text,
            timestamp=datetime.now()
        )
        return metadata

    def load_field_context(self, 
                          field: FieldName, 
                          metadata: GenerationMetadata) -> GenerationContext:
        """Reconstruct generation context from metadata"""
```

### 2. Core Data Models
```python
@dataclass
class CharacterData:
    """Immutable character data container"""
    id: UUID = field(default_factory=uuid4)
    name: str
    description: str = ""
    fields: Dict[FieldName, str] = field(default_factory=dict)
    image_data: Optional[Image.Image] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    modified_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Ensure fields are properly initialized"""
        for field in FieldName:
            if field not in self.fields:
                self.fields[field] = ""

@dataclass(frozen=True)
class FieldState:
    """Immutable field state container"""
    content: str = ""
    is_modified: bool = False
    is_valid: bool = True
    validation_message: str = ""
    is_generating: bool = False
    is_focused: bool = False
    is_expanded: bool = False
    scroll_position: int = 0

@dataclass
class GenerationMetadata:
    """Metadata for generated content"""
    base_prompt_name: str
    base_prompt_content: str
    input_context: str
    timestamp: datetime
    generation_version: str = "1.0"

@dataclass
class CharacterData:
    """Immutable character data container"""
    id: UUID = field(default_factory=uuid4)
    name: str
    description: str = ""
    fields: Dict[FieldName, str] = field(default_factory=dict)
    field_metadata: Dict[FieldName, GenerationMetadata] = field(default_factory=dict)
    image_data: Optional[Image.Image] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    base_prompt_data: Optional[Dict[str, Any]] = None  # Stores complete base prompt used
    alternate_greetings: List[Tuple[str, GenerationMetadata]] = field(default_factory=list)
    extensions: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    modified_at: datetime = field(default_factory=datetime.now)
```

## 3. Service Layer
```python
class ServiceBase:
    """Base class for all services"""
    def __init__(self, app_state: AppStateManager):
        self.app_state = app_state
        self.logger = logging.getLogger(self.__class__.__name__)

class GenerationService(ServiceBase):
    """Handles AI generation requests"""
    def __init__(self, app_state: AppStateManager, api_config: ApiConfig):
        super().__init__(app_state)
        self.api_config = api_config
        self._request_queue: asyncio.Queue = asyncio.Queue()
        self._is_processing = False

    async def generate_field(self, 
                           field: FieldName, 
                           context: Dict[str, Any]) -> GenerationResult:
        """Async generation with proper error handling"""
        try:
            result = await self._make_request(field, context)
            return GenerationResult(
                field=field,
                content=result.content,
                success=True
            )
        except Exception as e:
            self.logger.error(f"Generation error: {str(e)}")
            return GenerationResult(
                field=field,
                error=str(e),
                success=False
            )

class FileService(ServiceBase):
    """Handles file operations"""
    def __init__(self, app_state: AppStateManager, config: FileConfig):
        super().__init__(app_state)
        self.config = config
        
    async def save_character(self, 
                           character: CharacterData, 
                           format: FileFormat) -> Path:
        """Save character with proper error handling"""
        try:
            return await self._save_file(character, format)
        except Exception as e:
            self.logger.error(f"Save error: {str(e)}")
            raise FileOperationError(str(e))
```

## 4. Application Configuration

```python
@dataclass
class AppConfig:
    """Application configuration"""
    api: ApiConfig
    files: FileConfig
    ui: UIConfig
    generation: GenerationConfig
    debug: DebugConfig

    @classmethod
    def load(cls, config_path: Path) -> 'AppConfig':
        """Load and validate configuration"""
        try:
            with open(config_path) as f:
                data = yaml.safe_load(f)
            return cls(**data)
        except Exception as e:
            raise ConfigError(f"Failed to load config: {str(e)}")

@dataclass
class ApiConfig:
    """API configuration"""
    endpoint: str
    api_key: Optional[str] = None
    timeout: int = 30
    retry_attempts: int = 3
    batch_size: int = 10

@dataclass
class FileConfig:
    """File handling configuration"""
    save_dir: Path
    backup_dir: Path
    temp_dir: Path
    max_backups: int = 5
    auto_backup: bool = True
```

## 5. Error Handling Strategy

```python
class ErrorHandler:
    """Centralized error handling"""
    def __init__(self, app_state: AppStateManager):
        self.app_state = app_state
        self.logger = logging.getLogger('ErrorHandler')
        
    def handle_error(self, 
                    error: Exception, 
                    context: Dict[str, Any],
                    level: ErrorLevel = ErrorLevel.ERROR):
        """Handle errors consistently"""
        error_info = self._create_error_info(error, context)
        
        # Log error
        self.logger.error(error_info.message, exc_info=error)
        
        # Update UI state
        self.app_state.ui_manager.show_error(error_info)
        
        # Handle recovery if possible
        if error_info.can_recover:
            self._attempt_recovery(error_info)

@dataclass
class ErrorInfo:
    """Error information container"""
    error_type: str
    message: str
    context: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    can_recover: bool = False
    recovery_action: Optional[Callable] = None
```

## 6. Core Interfaces

```python
class StateObserver(Protocol):
    """Interface for state observation"""
    def on_state_changed(self, key: str, value: Any): ...
    def on_error(self, error: ErrorInfo): ...

class StateProvider(Protocol):
    """Interface for state providers"""
    def get_state(self, key: str) -> Any: ...
    def set_state(self, key: str, value: Any): ...
    def register_observer(self, observer: StateObserver): ...
    def remove_observer(self, observer: StateObserver): ...

class OperationHandler(Protocol):
    """Interface for operation handling"""
    async def handle(self, operation: Operation) -> OperationResult: ...
    def can_handle(self, operation: Operation) -> bool: ...
```

# II. Manager Specifications

## 1. Core Manager Infrastructure

```python
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Dict, Set, Optional
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

T = TypeVar('T')

class ManagerBase(QObject, ABC):
    """Base class for all managers"""
    
    state_changed = pyqtSignal(str, object)
    operation_started = pyqtSignal(str, dict)
    operation_completed = pyqtSignal(str, dict)
    operation_failed = pyqtSignal(str, str, dict)
    
    def __init__(self):
        super().__init__()
        self._state: Dict[str, Any] = {}
        self._observers: Set[StateObserver] = set()
        self._operation_lock = threading.RLock()
        self._operation_stack: List[str] = []

    @contextmanager
    def operation(self, name: str, context: Optional[Dict] = None):
        """Context manager for operations"""
        try:
            self.start_operation(name, context or {})
            yield
            self.complete_operation(name, context or {})
        except Exception as e:
            self.fail_operation(name, str(e), context or {})
            raise

    def notify_state_change(self, key: str, value: Any):
        """Notify observers of state change"""
        with self._operation_lock:
            self.state_changed.emit(key, value)
            for observer in self._observers:
                observer.on_state_changed(key, value)

class StateManager(ManagerBase, Generic[T]):
    """Generic state manager with type safety"""
    
    def __init__(self):
        super().__init__()
        self._current_state: Optional[T] = None
        self._history: List[Tuple[datetime, T]] = []
        self._max_history = 100

    def get_state(self) -> Optional[T]:
        """Get current state"""
        return self._current_state

    def set_state(self, state: T, record_history: bool = True):
        """Set new state"""
        with self._operation_lock:
            old_state = self._current_state
            self._current_state = state
            if record_history:
                self._record_state(state)
            self.notify_state_change('state', state)
            return old_state

    def _record_state(self, state: T):
        """Record state in history"""
        self._history.append((datetime.now(), state))
        while len(self._history) > self._max_history:
            self._history.pop(0)
```

## 2. Character State Manager

```python
@dataclass
class CharacterState:
    """Complete character state"""
    data: CharacterData
    modified_fields: Set[FieldName]
    validation_states: Dict[FieldName, ValidationState]
    undo_stack: List[CharacterData]
    redo_stack: List[CharacterData]
    last_saved: Optional[datetime] = None

class CharacterStateManager(StateManager[CharacterState]):
    """Manages character state and operations"""
    
    # State signals
    character_loaded = pyqtSignal(CharacterData)
    character_saved = pyqtSignal(CharacterData, Path)
    field_updated = pyqtSignal(FieldName, str)
    field_validated = pyqtSignal(FieldName, ValidationResult)
    
    # Operation signals
    generation_started = pyqtSignal(FieldName)
    generation_completed = pyqtSignal(FieldName, str)
    
    def __init__(self, file_service: FileService):
        super().__init__()
        self.file_service = file_service
        self._initialize_state()

    def _initialize_state(self):
        """Initialize empty character state"""
        self.set_state(CharacterState(
            data=CharacterData(name="", fields={}),
            modified_fields=set(),
            validation_states={},
            undo_stack=[],
            redo_stack=[]
        ))

    async def update_field(self, 
                         field: FieldName, 
                         value: str, 
                         validate: bool = True):
        """Update field with validation"""
        with self.operation('update_field', {'field': field}):
            state = self.get_state()
            if not state:
                return

            # Store for undo
            self._push_undo_state()

            # Update field
            state.data.fields[field] = value
            state.modified_fields.add(field)
            
            # Validate if requested
            if validate:
                validation = await self._validate_field(field, value)
                state.validation_states[field] = validation
                self.field_validated.emit(field, validation)

            # Update state and notify
            self.set_state(state)
            self.field_updated.emit(field, value)

	    async def save_character(self, 
	                           path: Path, 
	                           format: FileFormat = FileFormat.JSON):
	        """Enhanced save with metadata"""
	        with self.operation('save_character', {'path': str(path)}):
	            state = self.get_state()
	            if not state:
	                return

            # Include base prompt data
            state.data.base_prompt_data = {
                'name': self.config_manager.get_current_prompt_set_name(),
                'content': self.config_manager.get_current_prompt_set_data(),
                'version': '1.0'
            }

            # Validate before saving
            if not await self._validate_character():
                raise ValidationError("Character validation failed")

            # Save character
            saved_path = await self.file_service.save_character(
                state.data, format, path
            )

            # Update state
            state.last_saved = datetime.now()
            state.modified_fields.clear()
            self.set_state(state)
            
            self.character_saved.emit(state.data, saved_path)
            return saved_path
```

## 3. UI State Manager

```python
@dataclass
class UIState:
    """Complete UI state"""
    current_tab: TabType
    field_states: Dict[FieldName, FieldState]
    expanded_fields: Set[FieldName]
    focused_field: Optional[FieldName]
    dialog_stack: List[DialogInfo]
    operation_status: Optional[OperationStatus] = None

class UIStateManager(StateManager[UIState]):
    """Manages UI state and interactions"""
    
    # UI state signals
    tab_changed = pyqtSignal(TabType)
    field_expanded = pyqtSignal(FieldName, bool)
    field_focused = pyqtSignal(FieldName, bool)
    dialog_requested = pyqtSignal(DialogInfo)
    status_updated = pyqtSignal(str, StatusLevel)
    
    def __init__(self):
        super().__init__()
        self._initialize_state()

    def _initialize_state(self):
        """Initialize empty UI state"""
        self.set_state(UIState(
            current_tab=TabType.EDITOR,
            field_states={field: FieldState() for field in FieldName},
            expanded_fields=set(),
            focused_field=None,
            dialog_stack=[]
        ))

    def set_field_state(self, field: FieldName, updates: Dict[str, Any]):
        """Update field state"""
        with self.operation('update_field_state', {'field': field}):
            state = self.get_state()
            if not state:
                return

            # Update field state
            field_state = state.field_states[field]
            for key, value in updates.items():
                setattr(field_state, key, value)

            # Handle special states
            if updates.get('is_expanded'):
                state.expanded_fields.add(field)
            elif 'is_expanded' in updates:
                state.expanded_fields.discard(field)

            if updates.get('is_focused'):
                if state.focused_field and state.focused_field != field:
                    self._clear_focus(state.focused_field)
                state.focused_field = field
            elif 'is_focused' in updates and not updates['is_focused']:
                if state.focused_field == field:
                    state.focused_field = None

            self.set_state(state)
```

## 4. Generation Manager

```python
@dataclass
class GenerationState:
    """Generation system state"""
    active_generations: Dict[FieldName, GenerationInfo]
    generation_queue: List[GenerationRequest]
    generation_history: Dict[FieldName, List[GenerationResult]]
    batch_operation: Optional[BatchOperation] = None

@dataclass
class GenerationRequest:
    """Enhanced generation request"""
    field: FieldName
    context: Dict[str, Any]
    timestamp: datetime
    base_prompt_name: Optional[str] = None
    base_prompt_content: Optional[str] = None
    dependencies: Set[FieldName] = field(default_factory=set)

class GenerationManager(StateManager[GenerationState]):
    """Manages generation operations"""
    
    # Keep original signals
    generation_queued = pyqtSignal(FieldName, dict)
    generation_started = pyqtSignal(FieldName, dict)
    generation_progress = pyqtSignal(FieldName, int, dict)
    generation_completed = pyqtSignal(FieldName, str, dict)
    batch_progress = pyqtSignal(int, int)
    
    async def generate_field(self, 
                           field: FieldName, 
                           context: Dict[str, Any] = None):
        """Queue field for generation"""
        with self.operation('generate_field', {'field': field}):
            state = self.get_state()
            if not state:
                return

            # Enhance context with prompt data
            enhanced_context = self._prepare_generation_context(field, context or {})
            
            request = GenerationRequest(
                field=field,
                context=enhanced_context,
                timestamp=datetime.now(),
                base_prompt_name=self.config_manager.current_prompt_set,
                base_prompt_content=self._get_field_prompt(field),
                dependencies=self._get_field_dependencies(field)
            )

            # Add to queue
            state.generation_queue.append(request)
            self.set_state(state)
            self.generation_queued.emit(field, request.context)

    def _prepare_generation_context(self, 
                                  field: FieldName, 
                                  context: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare complete generation context"""
        # Start with provided context
        enhanced_context = context.copy()
        
        # Add dependency values
        dependencies = self._get_field_dependencies(field)
        for dep in dependencies:
            if dep_value := self.character_manager.get_field_value(dep):
                enhanced_context[f'dependency_{dep.value}'] = dep_value
        
        # Add field-specific configuration
        enhanced_context.update({
            'field_type': field.value,
            'generation_order': self._get_generation_order(field),
            'previous_generations': self._get_field_history(field)
        })
        
        return enhanced_context

    async def _process_queue(self):
        """Process generation queue"""
        while True:
            state = self.get_state()
            if not state or not state.generation_queue:
                await asyncio.sleep(0.1)
                continue

            request = state.generation_queue.pop(0)
            try:
                # Start generation
                self.generation_started.emit(
                    request.field, request.context
                )

                # Generate content
                result = await self.generation_service.generate_field(
                    request.field, request.context
                )

                # Update state and notify
                if result.success:
                    self.generation_completed.emit(
                        request.field, result.content, request.context
                    )
                else:
                    raise GenerationError(result.error)

            except Exception as e:
                self.operation_failed.emit(
                    'generation',
                    str(e),
                    {'field': request.field}
                )
```

```python
class PromptGenerationSystem:
    """Specification of prompt and generation interaction"""
    
    class PromptProcessing:
        """How prompts are processed for generation"""
        steps = {
            'template_resolution': {
                'order': 1,
                'actions': [
                    'Load base prompt template',
                    'Verify template validity',
                    'Process conditional sections'
                ]
            },
            'context_injection': {
                'order': 2,
                'actions': [
                    'Insert field dependencies',
                    'Apply user input',
                    'Add generation metadata'
                ]
            },
            'validation': {
                'order': 3,
                'actions': [
                    'Verify all required fields',
                    'Validate dependency values',
                    'Check context completeness'
                ]
            }
        }
    
    class DependencyHandling:
        """How field dependencies affect generation"""
        rules = {
            'dependency_order': {
                'enforcement': 'strict',
                'validation': 'pre-generation',
                'missing_handling': 'fail_generation'
            },
            'circular_detection': {
                'check_type': 'pre-generation',
                'resolution': 'fail_with_error'
            },
            'value_requirements': {
                'empty_values': 'fail_generation',
                'invalid_values': 'fail_generation',
                'partial_values': 'warning_only'
            }
        }
    
    class GenerationFlow:
        """Complete generation process"""
        steps = {
            'preparation': {
                'order': 1,
                'actions': [
                    'Load base prompt',
                    'Gather dependencies',
                    'Validate requirements'
                ]
            },
            'context_building': {
                'order': 2,
                'actions': [
                    'Process template',
                    'Insert dependencies',
                    'Add metadata'
                ]
            },
            'execution': {
                'order': 3,
                'actions': [
                    'Queue generation',
                    'Monitor progress',
                    'Handle completion'
                ]
            },
            'post_processing': {
                'order': 4,
                'actions': [
                    'Store result',
                    'Update metadata',
                    'Trigger dependent updates'
                ]
            }
        }

class FieldDependencySystem:
    """Complete specification of field dependencies"""
    
    class DependencyTypes:
        """Types of field dependencies"""
        types = {
            'direct': {
                'description': 'Field directly references another field',
                'handling': 'strict_order',
                'validation': 'required'
            },
            'contextual': {
                'description': 'Field uses another for context',
                'handling': 'preferred_order',
                'validation': 'warning'
            },
            'conditional': {
                'description': 'Field optionally uses another',
                'handling': 'flexible',
                'validation': 'optional'
            }
        }
    
    class DependencyFlow:
        """How dependencies affect generation"""
        flows = {
            'validation': {
                'pre_generation': [
                    'Check dependency availability',
                    'Validate dependency values',
                    'Verify dependency order'
                ],
                'during_generation': [
                    'Monitor dependency states',
                    'Handle missing dependencies',
                    'Update dependent fields'
                ]
            },
            'regeneration': {
                'triggers': [
                    'Dependency value change',
                    'Dependency regeneration',
                    'Manual regeneration'
                ],
                'handling': [
                    'Check affected fields',
                    'Queue regenerations',
                    'Update UI state'
                ]
            }
        }
```
##  5. Configuration Manager

```python
@dataclass
class ConfigurationState:
    """Application configuration state"""
    settings: AppConfig
    base_prompts: Dict[str, PromptTemplate]
    recent_files: List[Path]
    last_used_paths: Dict[str, Path]
    auto_save_enabled: bool = True
    debug_mode: bool = False

class ConfigurationManager(StateManager[ConfigurationState]):
    """Manages application configuration and settings"""
    
    # Configuration signals
    settings_updated = pyqtSignal(str, Any)  # setting_key, new_value
    base_prompt_updated = pyqtSignal(str)    # prompt_name
    recent_files_updated = pyqtSignal()
    
    def __init__(self, config_path: Path):
        super().__init__()
        self.config_path = config_path
        self._load_configuration()
        
        # Start auto-save timer if enabled
        self._auto_save_timer = QTimer()
        self._auto_save_timer.timeout.connect(self._auto_save)
        self.update_auto_save_interval(300)  # 5 minutes default

    def update_setting(self, key: str, value: Any):
        """Update single setting"""
        with self.operation('update_setting', {'key': key}):
            state = self.get_state()
            if not state:
                return

            # Update nested setting using dot notation
            parts = key.split('.')
            current = state.settings
            for part in parts[:-1]:
                current = getattr(current, part)
            setattr(current, parts[-1], value)

            # Save immediately for critical settings
            if key in {'api.key', 'generation.max_tokens'}:
                self._save_configuration()

            self.set_state(state)
            self.settings_updated.emit(key, value)

    def update_base_prompt(self, name: str, template: PromptTemplate):
        """Update base prompt template"""
        with self.operation('update_base_prompt', {'name': name}):
            state = self.get_state()
            if not state:
                return

            state.base_prompts[name] = template
            self.set_state(state)
            self.base_prompt_updated.emit(name)

    def add_recent_file(self, path: Path):
        """Add file to recent files list"""
        with self.operation('add_recent_file'):
            state = self.get_state()
            if not state:
                return

            # Remove if exists and add to front
            if path in state.recent_files:
                state.recent_files.remove(path)
            state.recent_files.insert(0, path)

            # Keep only last 10
            state.recent_files = state.recent_files[:10]
            
            self.set_state(state)
            self.recent_files_updated.emit()

    def _load_configuration(self):
        """Load configuration from disk"""
        try:
            with self.operation('load_configuration'):
                config = AppConfig.load(self.config_path)
                prompts = self._load_base_prompts()
                
                self.set_state(ConfigurationState(
                    settings=config,
                    base_prompts=prompts,
                    recent_files=[],
                    last_used_paths={}
                ))
        except Exception as e:
            self.operation_failed.emit(
                'load_configuration', 
                str(e),
                {}
            )
            # Load defaults
            self._load_defaults()

    def _auto_save(self):
        """Auto-save configuration"""
        state = self.get_state()
        if state and state.auto_save_enabled:
            self._save_configuration()
```

You make an excellent point. Before proceeding with widget design, we should explicitly map out the user workflows and requirements from the existing codebase. Let's start with the UI Implementation Guide first, as this will inform our widget design decisions.

# III. UI Implementation Guide

## 1. Core User Workflows

### A. Character Creation and Editing
```plaintext
1. New Character Creation
   - Quick start with just name
   - Optional initial template selection
   - Immediate access to all editable fields
   - Image addition (drag-drop or file select)

2. Character Editing
   Primary Operations:
   - Direct field editing
   - Field expansion for detailed work
   - Image management
   - Greeting management
   - Message example management
   
3. Field Management Features
   - Expand/collapse fields
   - Field validation feedback
   - Auto-saving drafts
   - Undo/redo per field
   - Rich text editing
   - Context-aware validation
```

### B. Generation System
```plaintext
1. Field Generation Flow
   - Input context (optional)
   - Generate single field
   - Generate with dependencies
   - Regenerate options
   
2. Generation Features
   - Progress indication
   - Cancel generation
   - Modify generation context
   - Preview results
   - Accept/reject/regenerate
   - Batch generation
   
3. Generation Controls
   - Per-field regeneration
   - Cascade regeneration
   - Generation history
   - Context preservation
```

### C. Base Prompt Management
```plaintext
1. Prompt Set Management
   - Create/edit prompt sets
   - Import/export sets
   - Template validation
   - Quick switching between sets
   
2. Prompt Features
   - Syntax highlighting
   - Tag autocomplete
   - Live validation
   - Test generation
   - Template versioning
   
3. Prompt Organization
   - Categories/tags
   - Search/filter
   - Favorites
   - Usage statistics
```

## 2. UI States and Transitions

```python
@dataclass
class UIWorkflow:
    """Define possible UI states and transitions"""
    states: Dict[str, UIState]
    transitions: Dict[str, List[str]]
    validations: Dict[str, List[Callable]]

# Example workflow definition
CHARACTER_EDITING_WORKFLOW = UIWorkflow(
    states={
        'viewing': UIState(
            editable=False,
            expandable=True,
            can_generate=True
        ),
        'editing': UIState(
            editable=True,
            expandable=True,
            can_generate=True,
            auto_save=True
        ),
        'generating': UIState(
            editable=False,
            expandable=False,
            can_generate=False,
            show_progress=True
        ),
        'expanded': UIState(
            editable=True,
            expandable=True,
            can_generate=True,
            full_size=True
        )
    },
    transitions={
        'viewing': ['editing', 'expanded', 'generating'],
        'editing': ['viewing', 'expanded', 'generating'],
        'generating': ['viewing', 'editing'],
        'expanded': ['editing', 'viewing', 'generating']
    },
    validations={
        'editing_to_viewing': [validate_required_fields],
        'generating': [validate_generation_context]
    }
)
```

## 3. User Interaction Requirements

```python
class InteractionRequirements:
    """Core interaction requirements"""
    
    # Response Times
    MAX_UI_RESPONSE_TIME = 50  # ms
    MAX_GENERATION_START_TIME = 200  # ms
    MAX_SAVE_TIME = 100  # ms
    
    # Auto-save
    AUTO_SAVE_INTERVAL = 30  # seconds
    KEEP_DRAFTS = 5  # number of drafts to keep
    
    # Undo/Redo
    MAX_UNDO_STEPS = 50
    UNDO_GROUPING_DELAY = 1000  # ms
    
    # Field Behavior
    FIELD_EXPANSION_ANIMATION = 200  # ms
    AUTO_EXPAND_LENGTH = 1000  # characters
    MAX_FIELD_HEIGHT = 600  # pixels
    
    # Generation
    MAX_CONCURRENT_GENERATIONS = 3
    GENERATION_TIMEOUT = 30  # seconds
    SHOW_PROGRESS_DELAY = 500  # ms
```

## 4. Critical User Requirements
```plaintext
1. Field Management
   - Never lose content during editing
   - Clear feedback on validation/errors
   - Easy expansion for long content
   - Consistent undo/redo behavior
   - No UI freezing during operations

2. Generation
   - Clear generation progress
   - Easy regeneration options
   - Context preservation
   - Quick access to common operations
   - Batch operation support

3. Base Prompts
   - Easy template editing
   - Quick template switching
   - Clear validation feedback
   - Template testing
   - Version tracking

4. General UX
   - Responsive interface
   - Clear operation status
   - Easy error recovery
   - Session persistence
   - Intuitive workflows
```

You're right. Let me realign the Widget System Design to be more appropriate for our redesign document. This should bridge between our managers and UI implementation while staying at the right level of abstraction.

# IV. Widget System Design

## 1. Core Widget Hierarchy
```plaintext
BaseWidget (QWidget)
├── ContentEditWidget
│   ├── FieldEditWidget
│   └── PromptEditWidget
├── ImageWidget
└── StatusWidget

EditableField (ContentEditWidget)
├── StandardField
├── FirstMessageField
├── MessageExamplesField
└── ExpandableField
```

## 2. Widget Base Classes

```python
class BaseWidget(QWidget):
    """Foundation for all app widgets"""
    state_changed = pyqtSignal(str, object)

    def __init__(self, ui_manager: UIStateManager):
        self.ui_manager = ui_manager
        self._setup_base_styling()
        self._connect_manager_signals()

class ContentEditWidget(BaseWidget):
    """Base for content-editable widgets"""
    content_changed = pyqtSignal(str)
    validation_changed = pyqtSignal(bool, str)
    focus_changed = pyqtSignal(bool)

    def __init__(self, ui_manager: UIStateManager, field_name: Optional[str] = None):
        super().__init__(ui_manager)
        self.field_name = field_name
        self._setup_editor()
        self._setup_validation()
```

## 3. Field Widget Behaviors

```python
class EditableFieldBehaviors:
    """Core behaviors for editable fields"""
    
    # State Management
    - Managed by UIStateManager
    - Clean state transitions
    - Validation feedback
    - Focus tracking
    
    # Content Management
    - Undo/redo support
    - Auto-save
    - Content validation
    - Change tracking
    
    # UI Features
    - Expansion/collapse
    - Status indication
    - Error display
    - Progress feedback
```

## 4. Widget Factory System

```python
class WidgetFactory:
    """Central widget creation system"""
    
    @classmethod
    def create_field(cls, 
                    field_type: FieldType,
                    managers: ManagerGroup) -> BaseWidget:
        """Create appropriate field widget"""
        
    @classmethod
    def create_generation_controls(cls,
                                 field: FieldName,
                                 managers: ManagerGroup) -> BaseWidget:
        """Create generation controls"""
        
    @classmethod
    def create_status_widget(cls,
                           managers: ManagerGroup) -> StatusWidget:
        """Create status display widget"""
```

## 5. Widget-Manager Integration

```python
class ManagerAwareWidget(BaseWidget):
    """Base for widgets that work with multiple managers"""
    
    def __init__(self, managers: ManagerGroup):
        self.ui_manager = managers.ui
        self.character_manager = managers.character
        self.generation_manager = managers.generation
        self._setup_manager_connections()

class FieldStateIntegration:
    """How widgets interact with state management"""
    
    # State Flow
    Managers -> Widget:
        - State updates
        - Validation results
        - Operation status
        
    Widget -> Managers:
        - Content changes
        - User actions
        - State requests
        
    # Synchronization
    - Batched updates
    - State locking
    - Change verification
```

## 6. Core Widget Requirements

```python
class WidgetRequirements:
    """Essential requirements for all widgets"""
    
    # State Management
    - Single source of truth (managers)
    - Clean state transitions
    - Predictable behavior
    
    # Performance
    - Lazy loading
    - Efficient updates
    - Resource cleanup
    
    # User Experience
    - Consistent behavior
    - Clear feedback
    - Responsive interface
    
    # Integration
    - Manager awareness
    - Event propagation
    - State synchronization
```

You're right. Let me create the Data Flow and State Management section that ties together our architecture, managers, widgets, and UI implementation while addressing the practical needs we discovered from the previous codebase.

# V. Data Flow and State Management

## 1. State Hierarchy and Flow
```plaintext
Application State Flow:
┌─────────────────┐
│ ConfigManager   │◄──────┐
└────────┬────────┘       │
         │               ┌┴────────────┐
         ▼               │ FileService │
┌─────────────────┐      └┬────────────┘
│ CharacterState  │◄─────-┘
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────┐
│   UIState       │◄────┤GenManager   │
└────────┬────────┘     └─────────────┘
         │
         ▼
┌─────────────────┐
│ Widget States   │
└─────────────────┘
```

## 2. Data Flow Patterns

```python
class DataFlowPatterns:
    """Core data flow patterns"""
    
    class StateUpdate:
        """How state changes propagate"""
        # Example: Field content update
        flow = """
        1. Widget content change
        2. Widget notifies CharacterManager
        3. CharacterManager validates & updates
        4. CharacterManager notifies UIManager
        5. UIManager updates relevant widgets
        6. UIManager triggers validation display
        """
    
    class GenerationFlow:
        """Generation data flow"""
        # Example: Field generation
        flow = """
        1. User requests generation
        2. UIManager updates field state
        3. GenerationManager queues request
        4. GenerationManager processes queue
        5. CharacterManager updates content
        6. UIManager updates display
        """
    
    class ValidationFlow:
        """Validation handling"""
        # Example: Field validation
        flow = """
        1. Content change triggers validation
        2. Manager validates content
        3. Results propagate to UI
        4. UI updates validation display
        5. Save state updates
        """
        
	class MetadataFlowPattern:
	    """How metadata flows through the system"""
	    flows = {
	        'generation': {
	            'capture': [
	                'Store base prompt used',
	                'Store input context',
	                'Store generation timestamp',
	                'Associate with generated content'
	            ],
	            'loading': [
	                'Load base prompt if available',
	                'Restore generation context',
	                'Enable regeneration with same context'
	            ]
	        }
	    }
    ```

## 3. State Synchronization

```python
class StateSyncProtocol:
    """How different states stay synchronized"""
    
    # Character Data Sync
    character_sync = {
        'source': 'CharacterManager',
        'subscribers': [
            'UIManager',
            'GenerationManager',
            'Field Widgets'
        ],
        'sync_method': 'Signal-based notification',
        'conflict_resolution': 'Manager is source of truth'
    }
    
    # UI State Sync
    ui_sync = {
        'source': 'UIManager',
        'subscribers': [
            'Widgets',
            'Tab Controllers',
            'Dialog Controllers'
        ],
        'sync_method': 'Direct state updates',
        'conflict_resolution': 'Last update wins'
    }
    
    # Generation State Sync
    generation_sync = {
        'source': 'GenerationManager',
        'subscribers': [
            'UIManager',
            'CharacterManager',
            'Generation Widgets'
        ],
        'sync_method': 'Queue-based updates',
        'conflict_resolution': 'Sequential processing'
    }
```

## 4. State Change Handling

```python
class StateChangeProtocols:
    """How state changes are handled"""
    
    class UserInitiated:
        """Changes from user actions"""
        protocols = {
            'field_edit': {
                'validation': 'Immediate',
                'persistence': 'Debounced',
                'ui_update': 'Immediate'
            },
            'image_change': {
                'validation': 'On completion',
                'persistence': 'Immediate',
                'ui_update': 'Progressive'
            },
            'generation_request': {
                'validation': 'Pre-generation',
                'persistence': 'Post-generation',
                'ui_update': 'Progressive'
            }
        }
    
    class SystemInitiated:
        """Changes from system operations"""
        protocols = {
            'auto_save': {
                'trigger': 'Timer or state threshold',
                'validation': 'Pre-save',
                'user_notification': 'Status only'
            },
            'batch_operation': {
                'trigger': 'Queue threshold or manual',
                'validation': 'Per operation',
                'user_notification': 'Progress indication'
            }
        }
```

## 5. Error Handling and Recovery

```python
class ErrorHandlingProtocols:
    """Error handling across state boundaries"""
    
    class StateRecovery:
        """How to handle state corruption"""
        protocols = {
            'field_corruption': {
                'detection': 'Validation check',
                'recovery': 'Revert to last valid',
                'user_action': 'Notify and prompt'
            },
            'sync_failure': {
                'detection': 'State comparison',
                'recovery': 'Force resync from source',
                'user_action': 'Background recovery'
            }
        }
    
    class OperationFailure:
        """How to handle operation failures"""
        protocols = {
            'generation_failure': {
                'immediate_action': 'Revert to pre-generation',
                'retry_policy': 'User prompt',
                'state_cleanup': 'Automatic'
            },
            'save_failure': {
                'immediate_action': 'Maintain current state',
                'retry_policy': 'Automatic with timeout',
                'data_protection': 'Local backup'
            }
        }
```

## 6. State Persistence

```python
class StatePersistenceProtocols:
    """How state is maintained and restored"""
    
    class Runtime:
        """Active session state"""
        protocols = {
            'memory_management': 'Reference counting',
            'cache_strategy': 'LRU with size limits',
            'state_history': 'Circular buffer'
        }
    
    class Persistence:
        """Long-term state storage"""
        protocols = {
            'save_strategy': {
                'auto_save': 'Timed + change threshold',
                'manual_save': 'Immediate',
                'format': 'Versioned JSON/PNG'
            },
            'recovery_strategy': {
                'load_order': 'Config -> Character -> UI',
                'validation': 'Progressive',
                'fallback': 'Last known good'
            }
        }
```

# VI. Implementation Order and Dependencies

## 1. Implementation Phases

```plaintext
Phase 1: Core Infrastructure
├── State Management Foundation
│   ├── StateManagerBase
│   ├── Error handling system
│   └── State persistence layer
├── Manager Core Classes
│   ├── CharacterStateManager
│   ├── UIStateManager
│   └── ConfigurationManager
└── Basic Service Layer
    ├── FileService
    └── ValidationService

Phase 2: Base UI Components
├── Widget Base Classes
│   ├── BaseWidget
│   └── ContentEditWidget
├── Core Field Components
│   ├── StandardField
│   └── ValidationDisplay
└── Basic Layout System
    ├── TabContainer
    └── StatusDisplay

Phase 3: Character Management
├── Character Data Handling
│   ├── Load/Save operations
│   ├── Image management
│   └── Field validation
├── Basic Editor Interface
│   ├── Field editing
│   ├── Image handling
│   └── Status updates
└── State Synchronization
    ├── Field state tracking
    └── Change propagation

Phase 4: Generation System
├── Generation Infrastructure
│   ├── Queue management
│   ├── Batch operations
│   └── Progress tracking
├── Generation Interface
│   ├── Input handling
│   ├── Output display
│   └── Control widgets
└── State Integration
    ├── Generation state sync
    └── Result handling

Phase 5: Advanced Features
├── Base Prompt System
├── Template Management
├── Extended Validation
└── Advanced UI Features
```

## 2. Critical Dependencies

```python
class ImplementationDependencies:
    """Critical dependencies between components"""
    
    dependencies = {
        'CharacterStateManager': {
            'required_first': [
                'StateManagerBase',
                'FileService',
                'ValidationService'
            ],
            'must_complete_before': [
                'Field Widgets',
                'Editor Interface',
                'Generation System'
            ]
        },
        
        'UIStateManager': {
            'required_first': [
                'StateManagerBase',
                'ConfigurationManager'
            ],
            'must_complete_before': [
                'Widget Base Classes',
                'Tab System',
                'Status System'
            ]
        },
        
        'Widget System': {
            'required_first': [
                'UIStateManager',
                'CharacterStateManager',
                'BaseWidget'
            ],
            'must_complete_before': [
                'Editor Interface',
                'Generation Interface'
            ]
        }
    }
```
## 3. Implementation Order

```python
class ImplementationOrder:
    """Specific order of implementation"""
    
    STEP_1 = {
        'name': 'Core Infrastructure',
        'components': [
            'StateManagerBase',
            'ErrorHandling',
            'ValidationService',
            'FileService'
        ],
        'validation_criteria': [
            'All tests passing',
            'Error handling complete',
            'File operations working'
        ]
    }
    
    STEP_2 = {
        'name': 'Manager Layer',
        'components': [
            'CharacterStateManager',
            'UIStateManager',
            'ConfigurationManager'
        ],
        'validation_criteria': [
            'State management working',
            'Manager communication verified',
            'Configuration handling complete'
        ]
    }
    STEP_2_5 = {
	    'name': 'Metadata System',
	    'components': [
	        'MetadataManager',
	        'Generation tracking',
	        'Context preservation'
	    ],
	    'validation_criteria': [
	        'Metadata properly stored',
	        'Context properly preserved',
	        'Base prompts tracked'
	    ]
	}
    STEP_3 = {
        'name': 'Basic UI Foundation',
        'components': [
            'BaseWidget',
            'ContentEditWidget',
            'StandardField'
        ],
        'validation_criteria': [
            'Widget base functioning',
            'State integration verified',
            'Basic editing working'
        ]
    }
    
    STEP_4 = {
        'name': 'Core Functionality',
        'components': [
            'Character loading/saving',
            'Basic field editing',
            'Image handling'
        ],
        'validation_criteria': [
            'Character operations working',
            'Field editing functioning',
            'Image handling complete'
        ]
    }
    
    STEP_5 = {
        'name': 'Generation System',
        'components': [
            'Generation infrastructure',
            'Queue management',
            'Generation interface'
        ],
        'validation_criteria': [
            'Generation working',
            'Queue handling verified',
            'UI integration complete'
        ]
    }
```

## 4. Testing Strategy

```python
class TestingStrategy:
    """Testing approach for each phase"""
    
    strategies = {
        'Phase1': {
            'focus': 'Core functionality',
            'approach': 'Unit tests',
            'coverage_requirement': '95%',
            'critical_paths': [
                'State management',
                'File operations',
                'Error handling'
            ]
        },
        'Phase2': {
            'focus': 'Widget functionality',
            'approach': 'Integration tests',
            'coverage_requirement': '90%',
            'critical_paths': [
                'Widget-Manager communication',
                'State synchronization',
                'Event handling'
            ]
        },
        'Phase3': {
            'focus': 'Character operations',
            'approach': 'Functional tests',
            'coverage_requirement': '90%',
            'critical_paths': [
                'Load/Save operations',
                'Field editing',
                'State consistency'
            ]
        },
        'Phase4': {
            'focus': 'Generation system',
            'approach': 'System tests',
            'coverage_requirement': '85%',
            'critical_paths': [
                'Generation workflow',
                'Queue handling',
                'Error recovery'
            ]
        }
    }
```

## 5. Verification Points

```python
class VerificationPoints:
    """Critical checkpoints during implementation"""
    
    checkpoints = {
        'Core_Infrastructure': {
            'required_tests': [
                'State management complete',
                'Error handling working',
                'File operations verified'
            ],
            'success_criteria': [
                'All core tests passing',
                'Error recovery working',
                'State consistency maintained'
            ]
        },
        'Basic_UI': {
            'required_tests': [
                'Widget base functioning',
                'State integration working',
                'Event handling verified'
            ],
            'success_criteria': [
                'UI responsive',
                'State updates working',
                'User input handled correctly'
            ]
        },
        'Character_System': {
            'required_tests': [
                'Character operations working',
                'Field handling complete',
                'Image operations verified'
            ],
            'success_criteria': [
                'Load/Save working',
                'Field editing functioning',
                'Image handling complete'
            ]
        },
        'Generation_System': {
            'required_tests': [
                'Generation working',
                'Queue handling verified',
                'Results properly handled'
            ],
            'success_criteria': [
                'Generation functions working',
                'State properly updated',
                'UI feedback correct'
            ]
        }
        'Metadata_System': {
		    'required_tests': [
		        'Metadata storage complete',
		        'Context preservation working',
		        'Base prompt tracking verified'
		    ],
		    'success_criteria': [
		        'All metadata preserved in saved files',
		        'Generation context properly restored',
		        'Base prompts properly tracked'
		    ]
		}
    }
```
