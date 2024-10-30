# charactergen/tests/ui/test_base_widgets.py

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest

from ui.widgets.base import BaseWidget, ContentEditWidget, ExpandableWidget
from core.state.ui import UIStateManager
from core.errors import ErrorHandler

class TestBaseWidgetFunctionality:
    """Test basic widget functionality"""
    
    def test_state_changes(self, base_widget, qtbot):
        """Test state change handling"""
        with qtbot.waitSignal(base_widget.state_changed) as blocker:
            base_widget.update_state("test", "value")
        
        assert blocker.args == ["test", "value"]

    def test_error_handling(self, base_widget, qtbot):
        """Test error handling"""
        with qtbot.waitSignal(base_widget.error_occurred) as blocker:
            base_widget.handle_error("test_error", "Error message")
        
        assert blocker.args == ["test_error", "Error message"]

class TestContentEditWidget:
    """Test content edit widget functionality"""
    
    def test_content_handling(self, content_widget, qtbot):
        """Test content handling"""
        # Test content changes
        with qtbot.waitSignal(content_widget.content_changed):
            content_widget.set_content("Test content")
            content_widget.handle_content_change()
        
        assert content_widget.get_content() == "Test content"
        assert content_widget._is_modified
        
        # Test clearing content
        content_widget.clear_content()
        assert content_widget.get_content() == ""
        assert not content_widget._is_modified

    def test_validation(self, content_widget, qtbot):
        """Test validation handling"""
        # Test validation state
        with qtbot.waitSignal(content_widget.validation_changed) as blocker:
            content_widget.set_validation_state(False, "Error message")
        
        assert not content_widget.is_valid()
        assert blocker.args == [False, "Error message"]
        
        # Test validation display
        assert "border: 1px solid #ff0000" in content_widget._content_frame.styleSheet()
        
        # Test clearing validation
        content_widget.set_validation_state(True)
        assert content_widget.is_valid()
        assert content_widget._content_frame.styleSheet() == ""

    def test_focus_handling(self, content_widget, qtbot):
        """Test focus handling"""
        # Test focus changes
        with qtbot.waitSignal(content_widget.focus_changed) as blocker:
            content_widget.handle_focus_in()
        
        assert blocker.args == [True]
        
        # Verify UI manager state
        field_state = content_widget.ui_manager.get_field_state("test_field")
        assert field_state is not None
        assert field_state.is_focused
        
        with qtbot.waitSignal(content_widget.focus_changed) as blocker:
            content_widget.handle_focus_out()
        
        assert blocker.args == [False]
        assert not field_state.is_focused

    def test_state_integration(self, content_widget, qtbot):
        """Test integration with UI state manager"""
        content_widget.set_content("Test content")
        content_widget.handle_content_change()
        
        # Verify state is updated
        field_state = content_widget.ui_manager.get_field_state("test_field")
        assert field_state is not None
        assert field_state.content == "Test content"
        assert field_state.is_modified