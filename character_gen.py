from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Set, Any, Union
import requests
import re
import time
import yaml
import os
import json
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QTextEdit, QPushButton, QTabWidget,
    QScrollArea, QFrame, QGridLayout, QSplitter, QComboBox,
    QMessageBox,QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal
import sys

# --- Enums and Exceptions ---
class FieldName(Enum):
    NAME = "name"
    DESCRIPTION = "description"
    SCENARIO = "scenario"
    FIRST_MES = "first_mes"
    MES_EXAMPLE = "mes_example"
    PERSONALITY = "personality"

class ApiError(Exception):
    """Base exception for API-related errors"""
    pass

class ApiTimeoutError(ApiError):
    """Raised when API request times out"""
    pass

class ApiResponseError(ApiError):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        super().__init__(f"API error {status_code}: {message}")

# --- Data Classes ---
@dataclass
class Config:
    api_url: str
    api_key: str
    json_template_path: str
    output_json_path: str
    user_prompts_path: str
    update_references: bool

    @classmethod
    def from_yaml(cls, path: str) -> 'Config':
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
        return cls(
            api_url=data['API_URL'],
            api_key=data['API_KEY'],
            json_template_path=data['JSON_TEMPLATE_PATH'],
            output_json_path=data['OUTPUT_JSON_PATH'],
            user_prompts_path=data['USER_PROMPTS_PATH'],
            update_references=data['UPDATE_REFERENCES']
        )

@dataclass
class ApiResponse:
    content: str
    raw_response: Dict[str, Any]
    timestamp: float
    attempts: int

@dataclass
class FieldOrder:
    order: List[FieldName]

    def get_available_fields(self, current_field: FieldName) -> Set[FieldName]:
        if current_field not in self.order:
            return set()
        current_index = self.order.index(current_field)
        return set(self.order[:current_index])

# --- Core Classes ---
class BasePrompt:
    def __init__(self, text: str):
        self.text = text
        self._validate_tags()
    
    def _validate_tags(self) -> None:
        if_count = len(re.findall(r'{{if_input}}', self.text))
        end_if_count = len(re.findall(r'{{/if_input}}', self.text))
        if if_count != end_if_count:
            raise ValueError("Mismatched if_input tags")

    def get_required_fields(self) -> Set[FieldName]:
        field_tags = re.findall(r'{{(\w+)}}', self.text)
        fields = set()
        for tag in field_tags:
            try:
                if tag != 'input' and tag != 'if_input' and tag != '/if_input' and tag != 'char' and tag != 'user':
                    fields.add(FieldName(tag))
            except ValueError:
                pass
        return fields

    def process(self, user_input: str, generated_outputs: Dict[FieldName, str]) -> str:
        result = self.text

        # Handle conditional input section
        if user_input.strip():
            result = re.sub(
                r'{{if_input}}(.*?){{/if_input}}',
                r'\1',
                result,
                flags=re.DOTALL
            )
        else:
            result = re.sub(
                r'{{if_input}}.*?{{/if_input}}',
                '',
                result,
                flags=re.DOTALL
            )

        # Replace input tag with user input
        result = result.replace('{{input}}', user_input)

        # Replace field tags with generated outputs
        for field, value in generated_outputs.items():
            result = result.replace(f'{{{{{field.value}}}}}', value)

        return result.strip()

class PromptManager:
    def __init__(self):
        self.base_prompts: Dict[FieldName, BasePrompt] = {}
        self.inputs: Dict[FieldName, str] = {}
        self.outputs: Dict[FieldName, str] = {}
        self.field_order = FieldOrder([])
    
    def set_field_order(self, order: List[FieldName]) -> None:
        self.field_order = FieldOrder(order)
    
    def set_base_prompt(self, field: FieldName, prompt: str) -> None:
        base_prompt = BasePrompt(prompt)
        self.base_prompts[field] = base_prompt
    
    def set_input(self, field: FieldName, input_text: str) -> None:
        self.inputs[field] = input_text
    
    def set_output(self, field: FieldName, output_text: str) -> None:
        self.outputs[field] = output_text
    
    def validate_field_dependencies(self, field: FieldName) -> List[FieldName]:
        if field not in self.base_prompts:
            raise ValueError(f"No base prompt set for {field.value}")
            
        prompt = self.base_prompts[field]
        required_fields = prompt.get_required_fields()
        available_fields = self.field_order.get_available_fields(field)
        
        missing_fields = [f for f in required_fields 
                         if f not in available_fields]
        
        return missing_fields
    
    def get_processed_prompt(self, field: FieldName) -> str:
        missing_fields = self.validate_field_dependencies(field)
        if missing_fields:
            field_names = [f.value for f in missing_fields]
            raise ValueError(
                f"Cannot generate {field.value}. Missing required fields: {field_names}"
            )
            
        base_prompt = self.base_prompts[field]
        user_input = self.inputs.get(field, "")
        
        available_fields = self.field_order.get_available_fields(field)
        available_outputs = {
            f: self.outputs[f] 
            for f in available_fields 
            if f in self.outputs
        }
        
        return base_prompt.process(user_input, available_outputs)
    
    def get_dependent_fields(self, field: FieldName) -> List[FieldName]:
        """Get list of fields that might depend on the given field"""
        if not field in self.field_order.order:
            return []
            
        # Get all fields that come after this one in the order
        start_idx = self.field_order.order.index(field) + 1
        return self.field_order.order[start_idx:]
    
    def check_field_dependencies(self, field: FieldName, changed_field: FieldName) -> bool:
        """Check if a field needs regeneration based on a changed field"""
        try:
            prompt = self.base_prompts[field]
            required_fields = prompt.get_required_fields()
            return changed_field in required_fields
        except KeyError:
            return False

class ApiService:
    def __init__(self, config: Config):
        self.config = config
        self.max_retries = 3
        self.retry_delay = 1
        self.timeout = 60
        self._last_response: Optional[ApiResponse] = None
    
    def _prepare_payload(self, prompt: str) -> Dict[str, Any]:
        return {
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "mode": "instruct",
            "max_tokens": 2048,
        }
    
    def _prepare_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json"
        }
        
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
            
        return headers
    
    def _make_request(self, prompt: str, attempt: int = 1) -> ApiResponse:
        payload = self._prepare_payload(prompt)
        headers = self._prepare_headers()
        
        try:
            response = requests.post(
                self.config.api_url,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code == 429:
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay * attempt)
                    return self._make_request(prompt, attempt + 1)
                raise ApiError("Rate limit exceeded and max retries reached")
                
            response.raise_for_status()
            
            data = response.json()
            content = data['choices'][0]['message']['content']
            
            return ApiResponse(
                content=content,
                raw_response=data,
                timestamp=time.time(),
                attempts=attempt
            )
            
        except requests.Timeout:
            if attempt < self.max_retries:
                time.sleep(self.retry_delay * attempt)
                return self._make_request(prompt, attempt + 1)
            raise ApiTimeoutError("Request timed out after all retries")
            
        except requests.RequestException as e:
            if attempt < self.max_retries:
                time.sleep(self.retry_delay * attempt)
                return self._make_request(prompt, attempt + 1)
            raise ApiError(f"Request failed after {attempt} attempts: {str(e)}")
    
    def generate_text(self, prompt: str) -> str:
        try:
            response = self._make_request(prompt)
            self._last_response = response
            return response.content
        except ApiError as e:
            raise

class GenerationService:
    def __init__(self, prompt_manager: PromptManager, api_service: ApiService):
        self.prompt_manager = prompt_manager
        self.api_service = api_service
    
    def generate_field(self, field: FieldName) -> Optional[str]:
        try:
            prompt = self.prompt_manager.get_processed_prompt(field)
            generated_text = self.api_service.generate_text(prompt)
            self.prompt_manager.set_output(field, generated_text)
            return generated_text
        except (ValueError, ApiError) as e:
            raise

    def generate_field_with_dependents(self, 
                                     field: FieldName, 
                                     progress_callback: Optional[callable] = None,
                                     result_callback: Optional[callable] = None) -> Dict[FieldName, Union[str, Exception]]:
        """
        Generate a field and all dependent fields.
        progress_callback(field, status) called before generation
        result_callback(field, result) called after each generation
        """
        results = {}
        
        # First generate the requested field
        if progress_callback:
            progress_callback(field, "Generating...")
            
        try:
            output = self.generate_field(field)
            results[field] = output
            if result_callback:
                result_callback(field, output)
            
            # Get potential dependent fields
            dependent_fields = self.prompt_manager.get_dependent_fields(field)
            
            # Check and generate each potential dependent
            for dep_field in dependent_fields:
                if self.prompt_manager.check_field_dependencies(dep_field, field):
                    if progress_callback:
                        progress_callback(dep_field, "Generating...")
                    try:
                        output = self.generate_field(dep_field)
                        results[dep_field] = output
                        if result_callback:
                            result_callback(dep_field, output)
                    except Exception as e:
                        results[dep_field] = e
                        if result_callback:
                            result_callback(dep_field, e)
                        
        except Exception as e:
            results[field] = e
            if result_callback:
                result_callback(field, e)
            
        return results

class CharacterFile:
    """Handles saving and loading of character files"""
    def __init__(self):
        self.base_dir = "characters"
        self.template_path = "template.json"
        os.makedirs(self.base_dir, exist_ok=True)
    
    def save(self, name: str, outputs: Dict[FieldName, str]) -> None:
        """Save character outputs to a JSON file"""
        # Load template
        with open(self.template_path, 'r') as f:
            template = json.load(f)
        
        # Update template with outputs
        for field in FieldName:
            if field.value in template["data"]:
                template["data"][field.value] = outputs.get(field, "")
        
        # Save to file
        file_path = os.path.join(self.base_dir, f"{name}.json")
        with open(file_path, 'w') as f:
            json.dump(template, f, indent=2)
    
    def load(self, name: str) -> Dict[str, str]:
        """Load character from a JSON file"""
        file_path = os.path.join(self.base_dir, f"{name}.json")
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Extract relevant fields
        outputs = {}
        for field in FieldName:
            if field.value in data["data"]:
                outputs[field] = data["data"][field.value]
        
        return outputs
    
    def get_available_files(self) -> List[str]:
        """Get list of available character files (without .json extension)"""
        files = [f[:-5] for f in os.listdir(self.base_dir) 
                if f.endswith('.json')]
        return sorted(files)

# --- Gui ---
class FieldInputWidget(QWidget):
    """Widget for a single field's input/output"""
    regen_requested = pyqtSignal(FieldName)  # Signal for single regeneration
    regen_with_deps_requested = pyqtSignal(FieldName)  # Signal for regeneration with dependents
    
    def __init__(self, field: FieldName, parent=None):
        super().__init__(parent)
        self.field = field
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout()
        
        # Header layout
        header_layout = QHBoxLayout()
        
        # Label
        label = QLabel(self.field.value.capitalize())
        header_layout.addWidget(label)
        
        # Add checkbox for name field
        if self.field == FieldName.NAME:
            self.use_input_checkbox = QCheckBox("Generate Name")
            self.use_input_checkbox.setToolTip("When unchecked, the input will be used directly as the name without generation")
            self.use_input_checkbox.setChecked(True)
            header_layout.addWidget(self.use_input_checkbox)
        
        # Add stretch to push everything to the left
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Input area with buttons
        input_layout = QHBoxLayout()
        
        # Input text area
        self.input = QTextEdit()
        self.input.setPlaceholderText(f"Enter {self.field.value}...")
        self.input.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.input.setMinimumHeight(60)
        self.input.setMaximumHeight(100)
        input_layout.addWidget(self.input)
        
        # Buttons container
        button_layout = QVBoxLayout()
        
        # Regen button
        regen_button = QPushButton("🔄")
        regen_button.setToolTip("Regenerate this field")
        regen_button.clicked.connect(self._handle_regen)
        regen_button.setFixedWidth(30)
        button_layout.addWidget(regen_button)
        
        # Regen + deps button
        regen_deps_button = QPushButton("🔄+")
        regen_deps_button.setToolTip("Regenerate this field and its dependents")
        regen_deps_button.clicked.connect(self._handle_regen_deps)
        regen_deps_button.setFixedWidth(30)
        button_layout.addWidget(regen_deps_button)
        
        input_layout.addLayout(button_layout)
        layout.addLayout(input_layout)
        
        self.setLayout(layout)
    
    def _handle_regen(self):
        self.regen_requested.emit(self.field)
    
    def _handle_regen_deps(self):
        self.regen_with_deps_requested.emit(self.field)
    
    def get_input(self) -> str:
     return self.input.toPlainText()
    
    def set_input(self, text: str):
        self.input.setPlainText(text)

class BasePromptWidget(QWidget):
    """Widget for a single field's base prompt configuration"""
    def __init__(self, field: FieldName, parent=None):
        super().__init__(parent)
        self.field = field
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout()
        
        # Label
        label = QLabel(f"Base Prompt for {self.field.value.capitalize()}")
        layout.addWidget(label)
        
        # Base prompt text area
        self.prompt_edit = QTextEdit()
        self.prompt_edit.setPlaceholderText(
            "Enter base prompt...\n"
            "Use {{input}} for user input\n"
            "Use {{field_name}} for other fields\n"
            "Use {{if_input}}...{{/if_input}} for conditional content"
        )
        # Enable word wrap
        self.prompt_edit.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        layout.addWidget(self.prompt_edit)
        
        # Order input
        order_layout = QHBoxLayout()
        order_layout.addWidget(QLabel("Generation Order:"))
        self.order_input = QLineEdit()
        self.order_input.setPlaceholderText("Enter number (1-6)")
        order_layout.addWidget(self.order_input)
        layout.addLayout(order_layout)
        
        self.setLayout(layout)

    def get_prompt(self) -> str:
        return self.prompt_edit.toPlainText()
    
    def set_prompt(self, text: str):
        self.prompt_edit.setPlainText(text)
    
    def get_order(self) -> int:
        try:
            return int(self.order_input.text())
        except ValueError:
            return 0
        
class BasePromptFile:
    """Handles saving and loading of base prompt files"""
    def __init__(self):
        self.base_dir = "basePrompts"
        os.makedirs(self.base_dir, exist_ok=True)
    
    def save(self, name: str, prompts: Dict[str, str], orders: Dict[str, int]) -> None:
        """Save base prompts and their orders to a JSON file"""
        data = {
            "prompts": prompts,
            "orders": orders
        }
        
        file_path = os.path.join(self.base_dir, f"{name}.json")
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load(self, name: str) -> Dict[str, Any]:
        """Load base prompts and orders from a JSON file"""
        file_path = os.path.join(self.base_dir, f"{name}.json")
        with open(file_path, 'r') as f:
            return json.load(f)
    
    def get_available_files(self) -> List[str]:
        """Get list of available base prompt files (without .json extension)"""
        files = [f[:-5] for f in os.listdir(self.base_dir) 
                if f.endswith('.json')]
        return sorted(files)
    
class BasePromptsTab(QWidget):
    """Tab for configuring base prompts"""
    def __init__(self, prompt_manager: PromptManager, parent=None):
        super().__init__(parent)
        self.prompt_manager = prompt_manager
        self.prompt_widgets: Dict[FieldName, BasePromptWidget] = {}
        self.prompt_file = BasePromptFile()
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout()
        
        # File management section
        file_section = QHBoxLayout()
        
        # File name input
        self.file_name = QLineEdit()
        self.file_name.setPlaceholderText("Enter save name...")
        file_section.addWidget(QLabel("Save Name:"))
        file_section.addWidget(self.file_name)
        
        # File selection dropdown
        self.file_selector = QComboBox()
        self.file_selector.currentTextChanged.connect(self._handle_file_selection)
        file_section.addWidget(QLabel("Load:"))
        file_section.addWidget(self.file_selector)
        
        # Refresh button
        refresh_button = QPushButton("🔄")
        refresh_button.clicked.connect(self._refresh_file_list)
        refresh_button.setFixedWidth(30)
        file_section.addWidget(refresh_button)
        
        layout.addLayout(file_section)
        
        # Add a separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)
        
        # Create widgets for each field
        prompts_layout = QVBoxLayout()
        for field in FieldName:
            widget = BasePromptWidget(field)
            self.prompt_widgets[field] = widget
            prompts_layout.addWidget(widget)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        # Save button
        save_button = QPushButton("Save Base Prompts")
        save_button.clicked.connect(self._handle_save)
        button_layout.addWidget(save_button)
        
        # Clear button
        clear_button = QPushButton("Clear All")
        clear_button.clicked.connect(self._handle_clear)
        button_layout.addWidget(clear_button)
        
        prompts_layout.addLayout(button_layout)
        
        # Put prompts in a scroll area
        scroll = QScrollArea()
        container = QWidget()
        container.setLayout(prompts_layout)
        scroll.setWidget(container)
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)
        
        self.setLayout(layout)
        
        # Initialize file list
        self._refresh_file_list()
    
    def _refresh_file_list(self):
        """Refresh the list of available base prompt files"""
        current = self.file_selector.currentText()
        self.file_selector.clear()
        files = self.prompt_file.get_available_files()
        self.file_selector.addItems(files)
        
        # Try to restore the previous selection
        if current and current in files:
            self.file_selector.setCurrentText(current)
    
    def _handle_file_selection(self, file_name: str):
        """Handle selection of a base prompt file"""
        if not file_name:
            return
            
        try:
            data = self.prompt_file.load(file_name)
            
            # Update file name input
            self.file_name.setText(file_name)
            
            # Update all widgets and prompt manager
            order_list = []
            for field in FieldName:
                widget = self.prompt_widgets[field]
                
                # Update widget
                prompt_text = data["prompts"].get(field.value, "")
                widget.set_prompt(prompt_text)
                order = data["orders"].get(field.value, 0)
                widget.order_input.setText(str(order))
                
                # Update prompt manager
                if prompt_text:
                    self.prompt_manager.set_base_prompt(field, prompt_text)
                    if order > 0:
                        order_list.append((order, field))
            
            # Set generation order in prompt manager
            if order_list:
                # Sort by order number and extract just the fields
                ordered_fields = [field for _, field in sorted(order_list)]
                self.prompt_manager.set_field_order(ordered_fields)
                
        except Exception as e:
            QMessageBox.warning(
                self,
                "Load Error",
                f"Error loading base prompts: {str(e)}"
            )
            
    def _handle_save(self):
        """Handle saving of base prompts"""
        file_name = self.file_name.text().strip()
        
        if not file_name:
            QMessageBox.warning(
                self,
                "Save Error",
                "Please enter a save name"
            )
            return
        
        # Collect prompts and orders
        prompts = {}
        orders = {}
        
        for field in FieldName:
            widget = self.prompt_widgets[field]
            prompt = widget.get_prompt().strip()
            order = widget.get_order()
            
            if prompt:  # Only save non-empty prompts
                prompts[field.value] = prompt
                orders[field.value] = order
        
        try:
            self.prompt_file.save(file_name, prompts, orders)
            self._refresh_file_list()
            self.file_selector.setCurrentText(file_name)
            
            QMessageBox.information(
                self,
                "Success",
                "Base prompts saved successfully"
            )
            
        except Exception as e:
            QMessageBox.warning(
                self,
                "Save Error",
                f"Error saving base prompts: {str(e)}"
            )
    
    def _handle_clear(self):
        """Clear all input fields"""
        reply = QMessageBox.question(
            self,
            "Clear Confirmation",
            "Are you sure you want to clear all fields?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            for widget in self.prompt_widgets.values():
                widget.set_prompt("")
                widget.order_input.clear()

class GenerationTab(QWidget):
   def __init__(self, prompt_manager: PromptManager, generation_service: GenerationService, parent=None):
       super().__init__(parent)
       self.prompt_manager = prompt_manager
       self.generation_service = generation_service
       self.input_widgets: Dict[FieldName, FieldInputWidget] = {}
       self.output_texts: Dict[FieldName, QTextEdit] = {}
       self.character_file = CharacterFile()
       self._init_ui()
       self._connect_signals()

   def _connect_signals(self):
       """Connect regeneration signals from input widgets"""
       for field, widget in self.input_widgets.items():
           widget.regen_requested.connect(self._handle_single_regen)
           widget.regen_with_deps_requested.connect(self._handle_regen_with_deps)

   def _init_ui(self):
       layout = QVBoxLayout()

       # Character management section
       char_section = QHBoxLayout()
       
       # Character name input
       self.char_name = QLineEdit()
       self.char_name.setPlaceholderText("Enter character name...")
       char_section.addWidget(QLabel("Character Name:"))
       char_section.addWidget(self.char_name)
       
       # Character selection dropdown
       self.char_selector = QComboBox()
       self.char_selector.currentTextChanged.connect(self._handle_char_selection)
       char_section.addWidget(QLabel("Load:"))
       char_section.addWidget(self.char_selector)
       
       # Refresh button
       refresh_button = QPushButton("🔄")
       refresh_button.clicked.connect(self._refresh_char_list)
       refresh_button.setFixedWidth(30)
       char_section.addWidget(refresh_button)
       
       layout.addLayout(char_section)
       
       # Add a separator
       separator = QFrame()
       separator.setFrameShape(QFrame.Shape.HLine)
       separator.setFrameShadow(QFrame.Shadow.Sunken)
       layout.addWidget(separator)

       # Main content
       main_layout = QHBoxLayout()
       
       # Input section (left side)
       input_widget = QWidget()
       input_layout = QVBoxLayout()
       
       # Create input widgets for each field
       for field in FieldName:
           widget = FieldInputWidget(field)
           self.input_widgets[field] = widget
           input_layout.addWidget(widget)
       
       # Generate button
       generate_button = QPushButton("Generate All")
       generate_button.clicked.connect(self._handle_generate)
       input_layout.addWidget(generate_button)

       # Save character button
       save_button = QPushButton("Save Character")
       save_button.clicked.connect(self._handle_save_character)
       input_layout.addWidget(save_button)
       
       input_layout.addStretch()
       input_widget.setLayout(input_layout)
       
       # Output section (right side)
       output_widget = QWidget()
       output_layout = QVBoxLayout()
       
       # Create output text areas
       for field in FieldName:
           label = QLabel(f"{field.value.capitalize()} Output:")
           output_layout.addWidget(label)
           
           text_edit = QTextEdit()
           text_edit.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
           text_edit.textChanged.connect(lambda field=field: self._handle_output_edit(field))
           self.output_texts[field] = text_edit
           output_layout.addWidget(text_edit)
       
       output_widget.setLayout(output_layout)
       
       # Add splitter for resizable sections
       splitter = QSplitter(Qt.Orientation.Horizontal)
       splitter.addWidget(input_widget)
       splitter.addWidget(output_widget)
       
       main_layout.addWidget(splitter)
       layout.addLayout(main_layout)
       self.setLayout(layout)

       # Initialize character list
       self._refresh_char_list()
       
   def _handle_output_edit(self, field: FieldName):
       """When output is edited, update the PromptManager"""
       output_text = self.output_texts[field].toPlainText()
       self.prompt_manager.set_output(field, output_text)
       
   def _refresh_char_list(self):
       """Refresh the list of available character files"""
       current = self.char_selector.currentText()
       self.char_selector.clear()
       files = self.character_file.get_available_files()
       self.char_selector.addItems(files)
       
       if current and current in files:
           self.char_selector.setCurrentText(current)
   
   def _handle_char_selection(self, char_name: str):
       """Handle selection of a character file"""
       if not char_name:
           return
           
       try:
           outputs = self.character_file.load(char_name)
           
           # Update character name input
           self.char_name.setText(char_name)
           
           # Update output displays
           for field, output in outputs.items():
               self.output_texts[field].setPlainText(output)
               
       except Exception as e:
           QMessageBox.warning(
               self,
               "Load Error",
               f"Error loading character: {str(e)}"
           )
   
   def _handle_save_character(self):
       """Handle saving of character"""
       char_name = self.char_name.text().strip()
       
       if not char_name:
           QMessageBox.warning(
               self,
               "Save Error",
               "Please enter a character name"
           )
           return
       
       # Collect outputs
       outputs = {
           field: self.output_texts[field].toPlainText().strip()
           for field in FieldName
       }
       
       try:
           self.character_file.save(char_name, outputs)
           self._refresh_char_list()
           self.char_selector.setCurrentText(char_name)
           
           QMessageBox.information(
               self,
               "Success",
               "Character saved successfully"
           )
           
       except Exception as e:
           QMessageBox.warning(
               self,
               "Save Error",
               f"Error saving character: {str(e)}"
           )

   def _update_field_status(self, field: FieldName, status: str):
       """Update the status of a field in the UI"""
       self.output_texts[field].setPlainText(status)
       QApplication.processEvents()

   def _update_field_result(self, field: FieldName, result: Union[str, Exception]):
       """Update the result of a field in the UI"""
       if isinstance(result, Exception):
           self.output_texts[field].setPlainText(f"Error: {str(result)}")
           QMessageBox.warning(
               self,
               "Generation Warning",
               f"Error generating {field.value}: {str(result)}"
           )
       else:
           self.output_texts[field].setPlainText(result)
       QApplication.processEvents()
       
   def _update_prompt_manager_inputs(self):
        """Update all inputs in the prompt manager, handling the name field specially"""
        for field in FieldName:
            input_text = self.input_widgets[field].get_input()
            
            # For name field, if input is empty (checkbox unchecked), use the output
            if field == FieldName.NAME and not input_text:
                input_text = self.output_texts[field].toPlainText()
                
            self.prompt_manager.set_input(field, input_text)   

   def _handle_generate(self):
    """Handle the generation of all fields"""
    try:
        ordered_fields = self.prompt_manager.field_order.order
        if not ordered_fields:
            QMessageBox.warning(
                self,
                "Generation Error",
                "No generation order set. Please set the order in Base Prompts tab."
            )
            return

        # Update all inputs in the prompt manager
        for field in FieldName:
            input_text = self.input_widgets[field].get_input()
            self.prompt_manager.set_input(field, input_text)

        # Generate each field in order
        for field in ordered_fields:
            # Special handling for name field when checkbox is unchecked
            if field == FieldName.NAME and not self.input_widgets[field].use_input_checkbox.isChecked():
                # Directly copy input to output, no generation
                input_text = self.input_widgets[field].get_input()
                self.output_texts[field].setPlainText(input_text)
                self.prompt_manager.set_output(field, input_text)
                continue

            # Normal generation for other fields
            self.output_texts[field].setPlainText("Generating...")
            QApplication.processEvents()

            try:
                generated_text = self.generation_service.generate_field(field)
                if generated_text:
                    self.output_texts[field].setPlainText(generated_text)
                else:
                    self.output_texts[field].setPlainText("Generation failed!")

            except ValueError as e:
                self.output_texts[field].setPlainText(f"Error: {str(e)}")
                break

            except ApiError as e:
                self.output_texts[field].setPlainText(f"API Error: {str(e)}")
                QMessageBox.critical(
                    self,
                    "API Error",
                    f"Error generating {field.value}: {str(e)}"
                )
                break

    except Exception as e:
        QMessageBox.critical(
            self,
            "Generation Error",
            f"An unexpected error occurred: {str(e)}"
        )

   def _handle_single_regen(self, field: FieldName):
        """Handle regeneration of a single field"""
        try:
            input_text = self.input_widgets[field].get_input()
            self.prompt_manager.set_input(field, input_text)

            # Special handling for name field when checkbox is unchecked
            if field == FieldName.NAME and not self.input_widgets[field].use_input_checkbox.isChecked():
                # Directly copy input to output, no generation
                self.output_texts[field].setPlainText(input_text)
                self.prompt_manager.set_output(field, input_text)
                return

            self.output_texts[field].setPlainText("Generating...")
            QApplication.processEvents()
            
            generated_text = self.generation_service.generate_field(field)
            if generated_text:
                self.output_texts[field].setPlainText(generated_text)
            else:
                self.output_texts[field].setPlainText("Generation failed!")
                
        except Exception as e:
            self.output_texts[field].setPlainText(f"Error: {str(e)}")
            QMessageBox.critical(self,
                "Generation Error",
                f"Error regenerating {field.value}: {str(e)}"
            )

   def _handle_regen_with_deps(self, field: FieldName):
    """Handle regeneration of a field and its dependents"""
    try:
        # Update all inputs
        for input_field in FieldName:
            input_text = self.input_widgets[input_field].get_input()
            self.prompt_manager.set_input(input_field, input_text)

        # Special handling for name field when checkbox is unchecked
        if field == FieldName.NAME and not self.input_widgets[field].use_input_checkbox.isChecked():
            # Directly copy input to output, no generation
            input_text = self.input_widgets[field].get_input()
            self._update_field_status(field, "Copying...")
            self.output_texts[field].setPlainText(input_text)
            self.prompt_manager.set_output(field, input_text)
            
            # Now handle dependencies
            dependent_fields = self.prompt_manager.get_dependent_fields(field)
            for dep_field in dependent_fields:
                if self.prompt_manager.check_field_dependencies(dep_field, field):
                    try:
                        self._update_field_status(dep_field, "Generating...")
                        generated_text = self.generation_service.generate_field(dep_field)
                        self._update_field_result(dep_field, generated_text)
                    except Exception as e:
                        self._update_field_result(dep_field, e)
            return

        # Normal generation with dependencies
        results = self.generation_service.generate_field_with_dependents(
            field,
            progress_callback=self._update_field_status,
            result_callback=self._update_field_result
        )
    except Exception as e:
        self.output_texts[field].setPlainText(f"Error: {str(e)}")
        QMessageBox.critical(
            self,
            "Generation Error",
            f"Error in regeneration process: {str(e)}"
        )
           
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Character Generator")
        
        # Initialize services
        self.config = Config.from_yaml("config.yaml")
        self.api_service = ApiService(self.config)
        self.prompt_manager = PromptManager()
        self.generation_service = GenerationService(
            self.prompt_manager,
            self.api_service
        )
        
        self._init_ui()
    
    def _init_ui(self):
        self.setMinimumSize(800, 600)
        
        # Create tab widget
        tabs = QTabWidget()
        
        # Add tabs
        self.base_prompts_tab = BasePromptsTab(self.prompt_manager)
        tabs.addTab(self.base_prompts_tab, "Base Prompts")
        
        # Pass services to GenerationTab
        self.generation_tab = GenerationTab(
            self.prompt_manager,
            self.generation_service
        )
        tabs.addTab(self.generation_tab, "Generation")
        
        self.setCentralWidget(tabs)

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
