import pytest
from typing import Tuple, Dict, Any
from PyQt6.QtWidgets import QApplication
import tempfile
from pathlib import Path
from PIL import Image, PngImagePlugin
import base64
import json
from core.errors import ErrorHandler
from core.state.ui import UIStateManager
from config.app_config import (
    AppConfig, FileConfig, ApiConfig, 
    UIConfig, GenerationConfig, DebugConfig
)
from ui.widgets.base import BaseWidget
from core.services import ValidationService, FileService
from ui.widgets.content_edit import EditableContentWidget

@pytest.fixture
def basic_content_widget(qtbot, ui_manager):
    """Create a basic content widget for testing base functionality"""
    widget = EditableContentWidget(ui_manager, "test_field")
    qtbot.addWidget(widget)
    return widget

@pytest.fixture
def base_widget(qtbot, ui_manager):
    """Create base widget for testing"""
    widget = BaseWidget(ui_manager)
    qtbot.addWidget(widget)
    return widget

@pytest.fixture
def content_widget(qtbot, ui_manager):
    """Create content widget for testing"""
    widget = EditableContentWidget(
        ui_manager,
        field_name="test_field",
        multiline=False,
        placeholder_text="Enter text..."
    )
    qtbot.addWidget(widget)
    return widget

@pytest.fixture
def multiline_widget(qtbot, ui_manager):
    """Create multiline content widget"""
    widget = EditableContentWidget(
        ui_manager,
        field_name="test_field",
        multiline=True,
        placeholder_text="Enter multiple lines..."
    )
    qtbot.addWidget(widget)
    return widget


@pytest.fixture(scope="session")
def qapp():
    """Create QApplication instance for the test session"""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app

@pytest.fixture
def ui_manager(error_handler):
    """Provide UI manager for tests"""
    return UIStateManager(error_handler)

@pytest.fixture
def error_handler():
    """Provide error handler for tests"""
    return ErrorHandler()

@pytest.fixture
def temp_dir():
    """Provide temporary directory"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)

@pytest.fixture
def file_config(temp_dir):
    """Provide test file configuration"""
    return FileConfig(
        save_dir=temp_dir / "saves",
        backup_dir=temp_dir / "backups",
        temp_dir=temp_dir / "temp",
        max_backups=3,
        auto_save_interval=30,
        auto_save_enabled=True
    )

@pytest.fixture
def app_config(file_config):
    """Provide test application configuration"""
    return AppConfig(
        api=ApiConfig(endpoint="http://test.local"),
        files=file_config,
        ui=UIConfig(),
        generation=GenerationConfig(),
        debug=DebugConfig(enabled=True)
    )

@pytest.fixture
def validation_service(error_handler):
    """Provide validation service"""
    return ValidationService(error_handler)

@pytest.fixture
def file_service(file_config, error_handler):
    """Provide file service"""
    return FileService(file_config, error_handler)

@pytest.fixture
def test_image_with_data(tmp_path) -> Tuple[Path, Dict[str, Any]]:
    """Create a test image file with embedded character data"""
    image_path = tmp_path / "test_char.png"
    
    # Sample character data
    char_data = {
        "name": "Test Character",
        "description": "A test character",
        "version": "1.0"
    }
    
    # Create test image
    img = Image.new('RGB', (100, 100), color='red')
    
    # Encode character data
    encoded_json = base64.b64encode(
        json.dumps(char_data).encode('utf-8')
    ).decode('utf-8')
    
    # Create metadata
    metadata = PngImagePlugin.PngInfo()
    metadata.add_text("chara", encoded_json)
    
    # Save image with metadata
    img.save(image_path, "PNG", pnginfo=metadata)
    
    return image_path, char_data