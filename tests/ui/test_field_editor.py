import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QPushButton, QLabel, QApplication

from ui.widgets.fields.editor import FieldEditor

@pytest.fixture
def field_editor(qtbot, ui_manager):
    """Create field editor for testing"""
    editor = FieldEditor(
        ui_manager=ui_manager,
        field_name="test_field",
        label="Test Field",
        help_text="This is a test field",
        multiline=True,
        required=True
    )
    qtbot.addWidget(editor)
    editor.show()
    qtbot.waitExposed(editor)  # Wait for widget to be shown
    return editor

class TestFieldEditor:
    def test_initialization(self, field_editor):
        """Test initial editor state"""
        assert field_editor.field_name == "test_field"
        assert not field_editor._has_unsaved_changes
        
        # Check UI elements
        assert field_editor._field is not None
        assert field_editor._save_btn is not None
        assert not field_editor._save_btn.isVisible()
    
    def test_content_handling(self, field_editor, qtbot):
        """Test content changes"""
        # Ensure widget is visible
        field_editor.show()
        qtbot.waitExposed(field_editor)
        
        # Initial state check
        assert not field_editor._has_unsaved_changes
        assert not field_editor._save_btn.isVisible()
        
        # Set content and verify change handling
        with qtbot.waitSignal(field_editor._field.content_changed):
            field_editor._field.set_content("Test content")
        
        # Wait for event processing
        qtbot.wait(100)
        
        # Process any pending events
        QApplication.processEvents()
        
        # Verify changed state
        assert field_editor._has_unsaved_changes
        assert field_editor._save_btn.isVisible()
        assert field_editor.get_content() == "Test content"
    
    def test_validation(self, field_editor, qtbot):
        """Test validation state"""
        # Initial state
        field_editor.set_validation_state(True, "")
        qtbot.wait(100)
        assert field_editor.is_valid()
        
        # Set invalid state
        field_editor.set_validation_state(False, "Error message")
        qtbot.wait(100)
        assert not field_editor.is_valid()
        
        # Set valid state
        field_editor.set_validation_state(True, "")
        qtbot.wait(100)
        assert field_editor.is_valid()
    
    def test_generate_request(self, field_editor, qtbot):
        """Test generation request"""
        # Verify button exists
        generate_button = field_editor._generate_btn
        assert generate_button is not None
        
        # Test signal emission
        with qtbot.waitSignal(field_editor.generate_requested) as blocker:
            qtbot.mouseClick(generate_button, Qt.MouseButton.LeftButton)
        
        assert blocker.args == ["test_field"]
    
    def test_status_updates(self, field_editor, qtbot):
        """Test status bar updates"""
        # Initial state
        assert "No changes" in field_editor._status_label.text()
        assert not field_editor._save_btn.isVisible()
        
        # Make changes by simulating content change
        field_editor._field.set_content("New content")
        qtbot.wait(100)  # Wait for signal handling
        
        # Verify changed state
        assert "Unsaved changes" in field_editor._status_label.text()
        assert field_editor._save_btn.isVisible()
        
        # Save changes
        field_editor._handle_save()
        qtbot.wait(100)  # Wait for state update
        
        # Verify saved state
        assert "No changes" in field_editor._status_label.text()
        assert not field_editor._save_btn.isVisible()
    
    def test_read_only(self, field_editor):
        """Test read-only state"""
        field_editor.set_read_only(True)
        assert field_editor._field._editor.isReadOnly()
        
        field_editor.set_read_only(False)
        assert not field_editor._field._editor.isReadOnly()
    
    def test_clear(self, field_editor):
        """Test clearing content"""
        # Add content and verify changes
        field_editor.set_content("Test content")
        field_editor._field.handle_content_change()
        assert field_editor._has_unsaved_changes
        
        # Clear content
        field_editor.clear()
        assert field_editor.get_content() == ""
        assert not field_editor._has_unsaved_changes
        assert not field_editor._save_btn.isVisible()