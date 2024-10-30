# charactergen/tests/ui/test_content_edit.py

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtTest import QTest

from ui.widgets.content_edit import EditableContentWidget
from ui.widgets.validation import ValidationSeverity
from ui.widgets.content_edit import ValidationDisplay

@pytest.fixture
def content_widget(qtbot, ui_manager):
    """Create single-line content widget"""
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

class TestEditableContentWidget:
    """Test editable content widget functionality"""
    
    def test_initialization(self, content_widget):
        """Test widget initialization"""
        assert content_widget.field_name == "test_field"
        assert not content_widget.multiline
        assert content_widget._editor.placeholderText() == "Enter text..."
        assert content_widget._label.text() == "Test Field"

    def test_content_handling(self, content_widget, qtbot):
        """Test content manipulation"""
        # Test setting content
        content_widget.set_content("Test content")
        assert content_widget.get_content() == "Test content"
        
        # Test content change signal
        with qtbot.waitSignal(content_widget.content_changed):
            content_widget._editor.setPlainText("New content")
        
        assert content_widget.get_content() == "New content"
        assert content_widget._is_modified

    def test_multiline_handling(self, multiline_widget, qtbot):
        """Test multiline content handling"""
        # Test multiline content
        content = "Line 1\nLine 2\nLine 3"
        multiline_widget.set_content(content)
        assert multiline_widget.get_content() == content
        
        # Verify it accepts line breaks
        assert multiline_widget._editor.toPlainText().count('\n') == 2

    def test_validation_display(self, content_widget, qtbot):
        """Test validation display integration"""
        # Make sure the widget is shown and processing events
        content_widget.show()
        qtbot.waitExposed(content_widget)
        
        # Print initial states for debugging
        print(f"\nInitial visibility: {content_widget._validation_display.isVisible()}")
        print(f"Initial geometry: {content_widget._validation_display.geometry()}")
        print(f"Parent visibility: {content_widget.isVisible()}")
        
        # Test error state
        content_widget.set_validation_state(False, "Error message")
        qtbot.wait(100)  # Give more time for display
        
        # Print states after setting validation
        print(f"\nAfter validation visibility: {content_widget._validation_display.isVisible()}")
        print(f"Validation display geometry: {content_widget._validation_display.geometry()}")
        print(f"Validation message: {content_widget._validation_display._message_label.text()}")
        
        assert not content_widget.is_valid()
        assert content_widget._validation_display.isVisible()
        assert content_widget._validation_display._message_label.text().strip() == "Error message"

    def test_focus_handling(self, content_widget, qtbot):
        """Test focus behavior"""
        # First, ensure widget is visible and active
        content_widget.show()
        qtbot.waitExposed(content_widget)
        
        # Ensure editor is focusable
        assert content_widget._editor.focusPolicy() == Qt.FocusPolicy.StrongFocus
        
        # Test focus in
        with qtbot.waitSignal(content_widget.focus_changed, timeout=1000) as blocker:
            content_widget._editor.setFocus()
            qtbot.wait(100)  # Give time for focus to process
        
        assert blocker.args == [True]
        field_state = content_widget.ui_manager.get_field_state("test_field")
        assert field_state.is_focused
        
        # Test focus out
        with qtbot.waitSignal(content_widget.focus_changed, timeout=1000) as blocker:
            content_widget._editor.clearFocus()
            qtbot.wait(100)  # Give time for focus to process
        
        assert blocker.args == [False]
        assert not field_state.is_focused

    def test_read_only(self, content_widget):
        """Test read-only functionality"""
        content_widget.set_read_only(True)
        assert content_widget._editor.isReadOnly()
        
        content_widget.set_read_only(False)
        assert not content_widget._editor.isReadOnly()

    def test_clearing(self, content_widget):
        """Test content clearing"""
        content_widget.set_content("Test content")
        content_widget.set_validation_state(False, "Error")
        
        content_widget.clear_content()
        assert content_widget.get_content() == ""
        assert not content_widget._is_modified
        assert content_widget.is_valid()
        assert not content_widget._validation_display.isVisible()

    def test_styling(self, content_widget):
        """Test styling functionality"""
        # Test font setting
        font = QFont("Arial", 12)
        content_widget.set_font(font)
        assert content_widget._editor.font().family() == "Arial"
        assert content_widget._editor.font().pointSize() == 12
        
        # Verify style classes are applied
        assert "field_label" in content_widget._label.objectName()
        assert "content_editor" in content_widget._editor.objectName()

    def test_ui_integration(self, content_widget, qtbot):
        """Test UI manager integration"""
        content_widget.set_content("Test content")
        content_widget._handle_text_changed()
        
        field_state = content_widget.ui_manager.get_field_state("test_field")
        assert field_state is not None
        assert field_state.content == "Test content"
        assert field_state.is_modified