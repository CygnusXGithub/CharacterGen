import pytest
from pathlib import Path

import yaml
from core.state.config import ConfigurationManager
from config.app_config import AppConfig, UIConfig
from core.errors.handler import ErrorHandler

@pytest.fixture
def config_path(tmp_path):
    return tmp_path / "config.yaml"

@pytest.fixture
def config_manager(config_path, error_handler):
    return ConfigurationManager(config_path, error_handler)

def test_initialization(config_manager):
    """Test configuration manager initialization"""
    assert config_manager.config is not None
    assert isinstance(config_manager.config, AppConfig)

def test_get_setting(config_manager):
    """Test getting configuration settings"""
    # Test existing setting
    assert config_manager.get_setting('ui.theme') == 'default'
    
    # Test nested setting
    assert isinstance(config_manager.get_setting('ui'), UIConfig)
    
    # Test missing setting
    assert config_manager.get_setting('nonexistent', 'default') == 'default'

@pytest.mark.asyncio
async def test_update_setting(config_manager):
    """Test updating configuration settings"""
    # Update simple setting
    success = await config_manager.update_setting('ui.theme', 'dark')
    assert success
    assert config_manager.get_setting('ui.theme') == 'dark'
    
    # Update nested setting
    success = await config_manager.update_setting('generation.max_retries', 5)
    assert success
    assert config_manager.get_setting('generation.max_retries') == 5
    
    # Test invalid setting
    success = await config_manager.update_setting('invalid.path', 'value')
    assert not success

def test_runtime_config(config_manager):
    """Test runtime configuration"""
    # Set runtime value
    config_manager.set_runtime_config('test_key', 'test_value')
    assert config_manager.get_runtime_config('test_key') == 'test_value'
    
    # Test default value
    assert config_manager.get_runtime_config('missing', 'default') == 'default'

@pytest.mark.asyncio
async def test_save_load_config(config_manager, config_path, error_handler: ErrorHandler):
    """Test saving and loading configuration"""
    # Update some settings
    await config_manager.update_setting('ui.theme', 'dark')
    await config_manager.update_setting('generation.max_retries', 5)
    
    # Save configuration
    success = await config_manager.save_configuration()
    assert success
    assert config_path.exists()
    
    # Verify file content
    with open(config_path) as f:
        saved_config = yaml.safe_load(f)
        assert saved_config['ui']['theme'] == 'dark'
        assert saved_config['generation']['max_retries'] == 5

    # Create new manager to test loading
    new_manager = ConfigurationManager(config_path, error_handler)
    assert new_manager.get_setting('ui.theme') == 'dark'
    assert new_manager.get_setting('generation.max_retries') == 5

def test_reset_to_defaults(config_manager):
    """Test resetting configuration"""
    # Change some settings first
    config_manager.config.ui.theme = 'dark'
    config_manager.config.generation.max_retries = 5
    
    # Reset configuration
    success = config_manager.reset_to_defaults()
    assert success
    
    # Verify reset
    assert config_manager.get_setting('ui.theme') == 'default'
    assert config_manager.get_setting('generation.max_retries') == 3

@pytest.mark.asyncio
async def test_error_handling(config_manager):
    """Test error handling in configuration operations"""
    # Test invalid setting update
    success = await config_manager.update_setting('invalid.setting', 'value')
    assert not success
    
    # Test invalid save path
    config_manager.config_path = Path("/invalid/path/config.yaml")
    success = await config_manager.save_configuration()
    assert not success

@pytest.mark.asyncio
async def test_config_change_signals(config_manager):
    """Test configuration change signals"""
    changes = []
    config_manager.state_changed.connect(
        lambda key, value: changes.append((key, value))
    )
    
    # Update setting
    await config_manager.update_setting('ui.theme', 'dark')
    assert len(changes) > 0
    assert any(change[0] == 'config_updated' for change in changes)