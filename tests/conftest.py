import pytest
from PyQt6.QtWidgets import QApplication
import tempfile
from pathlib import Path
from core.errors import ErrorHandler
from core.state.ui import UIStateManager
from config.app_config import (
    AppConfig, FileConfig, ApiConfig, 
    UIConfig, GenerationConfig, DebugConfig
)
from core.services import ValidationService, FileService

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