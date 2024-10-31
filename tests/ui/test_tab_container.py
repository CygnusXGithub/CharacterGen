# charactergen/tests/ui/test_tab_container.py

import pytest
from PyQt6.QtWidgets import QLabel, QWidget, QPushButton
from PyQt6.QtCore import Qt

from ui.widgets.layout.tab_container import TabContainer, TabState

@pytest.fixture
def tab_container(qtbot, ui_manager):
    """Create tab container for testing"""
    container = TabContainer(ui_manager)
    qtbot.addWidget(container)
    container.show()
    return container

class TestTabContainer:
    """Test tab container functionality"""
    
    def test_initialization(self, tab_container):
        """Test initial state"""
        assert tab_container._current_tab is None
        assert len(tab_container._tabs) == 0
        assert len(tab_container._tab_states) == 0

    def test_add_tab(self, tab_container, qtbot):
        """Test adding tabs"""
        # Add first tab
        content1 = QLabel("Content 1")
        success = tab_container.add_tab("tab1", "Tab 1", content1)
        assert success
        assert "tab1" in tab_container._tabs
        assert tab_container.get_current_tab() == "tab1"  # First tab becomes active
        
        # Add second tab
        content2 = QLabel("Content 2")
        success = tab_container.add_tab("tab2", "Tab 2", content2)
        assert success
        assert "tab2" in tab_container._tabs
        assert tab_container.get_current_tab() == "tab1"  # First tab remains active
        
        # Try adding duplicate
        success = tab_container.add_tab("tab1", "Tab 1", QLabel("Duplicate"))
        assert not success

    def test_tab_switching(self, tab_container, qtbot):
        """Test tab switching"""
        # Add tabs
        tab_container.add_tab("tab1", "Tab 1", QLabel("Content 1"))
        tab_container.add_tab("tab2", "Tab 2", QLabel("Content 2"))
        
        # Track signal emission
        with qtbot.waitSignal(tab_container.tab_changed) as blocker:
            tab_container.set_current_tab("tab2")
        
        assert tab_container.get_current_tab() == "tab2"
        assert blocker.args == ["tab2"]
        
        # Test invalid tab
        assert not tab_container.set_current_tab("invalid")

    def test_tab_states(self, tab_container, qtbot):
        """Test tab state handling"""
        tab_container.add_tab("tab1", "Tab 1", QLabel("Content"))
        
        # Verify initial state
        assert tab_container.get_tab_state("tab1") == TabState.ENABLED
        
        # Test disabling
        with qtbot.waitSignal(tab_container.tab_state_changed) as blocker:
            success = tab_container.set_tab_state("tab1", TabState.DISABLED)
            assert success
        
        # Verify state change
        assert tab_container.get_tab_state("tab1") == TabState.DISABLED
        assert blocker.args == ["tab1", TabState.DISABLED]
        
        # Verify button state
        button = tab_container._buttons["tab1"]  # Use stored reference
        assert not button.isEnabled()
        
        # Test enabling
        success = tab_container.set_tab_state("tab1", TabState.ENABLED)
        assert success
        assert tab_container.get_tab_state("tab1") == TabState.ENABLED
        assert button.isEnabled()

    def test_remove_tab(self, tab_container):
        """Test tab removal"""
        # Add tabs
        tab_container.add_tab("tab1", "Tab 1", QLabel("Content 1"))
        tab_container.add_tab("tab2", "Tab 2", QLabel("Content 2"))
        tab_container.set_current_tab("tab2")
        
        # Remove current tab
        success = tab_container.remove_tab("tab2")
        assert success
        assert "tab2" not in tab_container._tabs
        assert tab_container.get_current_tab() == "tab1"  # Switches to remaining tab
        
        # Remove last tab
        success = tab_container.remove_tab("tab1")
        assert success
        assert len(tab_container._tabs) == 0
        assert tab_container.get_current_tab() is None

    def test_loading_state(self, tab_container, qtbot):
        """Test loading state"""
        tab_container.add_tab("tab1", "Tab 1", QLabel("Content"))
        
        # Verify initial state
        assert tab_container.get_tab_state("tab1") == TabState.ENABLED
        
        # Set loading state
        with qtbot.waitSignal(tab_container.tab_state_changed) as blocker:
            success = tab_container.set_tab_state("tab1", TabState.LOADING)
            assert success
        
        # Verify state change
        assert tab_container.get_tab_state("tab1") == TabState.LOADING
        assert blocker.args == ["tab1", TabState.LOADING]
        
        # Verify button state
        button = tab_container._buttons["tab1"]  # Use stored reference
        assert not button.isEnabled()
        assert "Loading" in button.toolTip()

    def test_button_management(self, tab_container):
        """Test button handling"""
        # Add tab and verify button exists
        tab_container.add_tab("tab1", "Tab 1", QLabel("Content"))
        assert "tab1" in tab_container._buttons
        assert isinstance(tab_container._buttons["tab1"], QPushButton)
        
        # Remove tab and verify button is removed
        tab_container.remove_tab("tab1")
        assert "tab1" not in tab_container._buttons