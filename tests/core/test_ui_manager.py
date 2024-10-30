import pytest
from core.state.ui import UIStateManager
from core.models.ui import (
    TabType, DialogType, StatusLevel,
    DialogInfo, StatusInfo
)

@pytest.fixture
def ui_manager(error_handler):
    return UIStateManager(error_handler)

def test_tab_switching(ui_manager):
    """Test tab switching functionality"""
    # Track signal emissions
    tab_changes = []
    ui_manager.tab_changed.connect(lambda tab: tab_changes.append(tab))
    
    # Switch tab
    ui_manager.switch_tab(TabType.GENERATION)
    assert ui_manager._state.current_tab == TabType.GENERATION
    assert len(tab_changes) == 1
    assert tab_changes[0] == TabType.GENERATION
    
    # Switch to same tab (should not emit)
    ui_manager.switch_tab(TabType.GENERATION)
    assert len(tab_changes) == 1

def test_field_state_management(ui_manager):
    """Test field state management"""
    # Track expansions
    expansions = []
    ui_manager.field_expanded.connect(
        lambda field, state: expansions.append((field, state))
    )
    
    # Set field state
    ui_manager.set_field_state("test_field", {
        "content": "New content",
        "is_expanded": True,
        "is_valid": True
    })
    
    # Verify state
    field_state = ui_manager.get_field_state("test_field")
    assert field_state is not None
    assert field_state.content == "New content"
    assert field_state.is_expanded
    assert field_state.is_valid
    assert len(expansions) == 1
    assert expansions[0] == ("test_field", True)

def test_dialog_management(ui_manager):
    """Test dialog management"""
    # Track dialog signals
    shown_dialogs = []
    closed_dialogs = []
    ui_manager.dialog_requested.connect(lambda d: shown_dialogs.append(d))
    ui_manager.dialog_closed.connect(lambda d: closed_dialogs.append(d))
    
    # Show dialog
    dialog = DialogInfo(
        dialog_type=DialogType.CONFIRMATION,
        title="Test Dialog",
        message="Test message"
    )
    ui_manager.show_dialog(dialog)
    
    assert len(ui_manager._state.dialog_stack) == 1
    assert len(shown_dialogs) == 1
    
    # Close dialog
    ui_manager.close_dialog()
    assert len(ui_manager._state.dialog_stack) == 0
    assert len(closed_dialogs) == 1
    assert closed_dialogs[0] == DialogType.CONFIRMATION

def test_status_messages(ui_manager):
    """Test status message handling"""
    # Track status updates
    updates = []
    ui_manager.status_updated.connect(lambda s: updates.append(s))
    
    # Show status
    ui_manager.show_status(
        "Test message",
        StatusLevel.INFO,
        duration=1000
    )
    
    assert ui_manager._state.status_message is not None
    assert ui_manager._state.status_message.message == "Test message"
    assert ui_manager._state.status_message.level == StatusLevel.INFO
    assert len(updates) == 1

def test_loading_state(ui_manager):
    """Test loading state management"""
    # Track loading changes
    loading_states = []
    ui_manager.loading_changed.connect(lambda s: loading_states.append(s))
    
    # Set loading
    ui_manager.set_loading(True)
    assert ui_manager._state.is_loading
    assert len(loading_states) == 1
    assert loading_states[0]
    
    # Set same state (should not emit)
    ui_manager.set_loading(True)
    assert len(loading_states) == 1
    
    # Clear loading
    ui_manager.set_loading(False)
    assert not ui_manager._state.is_loading
    assert len(loading_states) == 2
    assert not loading_states[1]

def test_character_state_handling(ui_manager):
    """Test handling of character state changes"""
    ui_manager.handle_character_state_change('field_updated', {
        'field': 'test_field',
        'value': 'new_value'
    })
    
    field_state = ui_manager.get_field_state('test_field')
    assert field_state is not None
    assert field_state.content == 'new_value'
    assert field_state.is_modified