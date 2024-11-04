import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject
from main import ApplicationManager

@pytest.fixture
async def app_manager(qtbot, qapp):
    """Create and initialize application manager"""
    manager = ApplicationManager()
    success = await manager.initialize()
    assert success, "Failed to initialize application manager"
    
    if manager.main_window:
        qtbot.addWidget(manager.main_window)
    return manager

@pytest.mark.asyncio
async def test_application_initialization(app_manager):
    """Test basic application initialization"""
    manager = await app_manager
    assert manager.error_handler is not None
    assert len(manager.services) > 0
    assert len(manager.managers) > 0
    assert manager.main_window is not None

@pytest.mark.asyncio
async def test_component_initialization(app_manager):
    """Test component initialization"""
    manager = await app_manager
    # Verify core services
    assert 'validation' in manager.services
    assert 'file' in manager.services
    assert 'queue' in manager.services
    
    # Verify managers
    assert 'character' in manager.managers
    assert 'ui' in manager.managers
    assert 'config' in manager.managers

@pytest.mark.asyncio
async def test_main_window_structure(app_manager, qtbot):
    """Test main window structure"""
    manager = await app_manager
    window = manager.main_window
    
    assert window is not None
    assert window.windowTitle() == "CharacterGen"
    
    # Test core widgets exist
    assert hasattr(window, '_tab_container')
    assert hasattr(window, '_status_display')
    assert hasattr(window, '_image_widget')

@pytest.mark.asyncio
async def test_manager_connections(app_manager):
    """Test manager signal connections"""
    manager = await app_manager
    # Get managers
    char_manager = manager.managers['character']
    ui_manager = manager.managers['ui']
    
    # Test signal connections
    # PyQt signals have a 'connect' method
    assert hasattr(char_manager.state_changed, 'connect')
    assert hasattr(ui_manager.status_updated, 'connect')
    
    # Test connection between managers
    def test_slot(key, value):
        pass
    
    # Should be able to connect signals
    char_manager.state_changed.connect(test_slot)
    ui_manager.status_updated.connect(test_slot)
    
    # Verify connections
    assert char_manager.state_changed.receivers > 0
    assert ui_manager.status_updated.receivers > 0