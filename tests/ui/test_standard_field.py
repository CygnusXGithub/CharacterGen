import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QPushButton, QLabel

from ui.widgets.fields.standard import StandardField

@pytest.fixture
def standard_field(qtbot, ui_manager):
    """Create standard field for testing"""
    widget = StandardField(
        ui_manager,
        field_name="test_field",
        label="Test Field",
        placeholder="Enter test content",
        help_text="This is help text",
        required=True
    )
    qtbot.addWidget(widget)
    return widget

class TestStandardField:
    """Test standard field functionality"""
    
    def test_initialization(self, standard_field):
        """Test field initialization"""
        assert standard_field.field_name == "test_field"
        assert standard_field._label.text() == "Test Field *"  # Required field should have asterisk
        assert standard_field._editor.placeholderText() == "Enter test content"
        assert standard_field.required
        
        # Check buttons exist
        buttons = standard_field.findChildren(QPushButton)
        assert len(buttons) == 3  # Help, Generate, Clear
        
        # Check help text
        help_labels = [w for w in standard_field.findChildren(QLabel) 
                    if w.objectName() == "help_text"]
        assert len(help_labels) == 1
        assert help_labels[0].text() == "This is help text"

    def test_required_field_label(self, qtbot, ui_manager):
        """Test required field label handling"""
        # Test required field
        required_field = StandardField(
            ui_manager,
            field_name="required_field",
            label="Required Field",
            required=True
        )
        qtbot.addWidget(required_field)
        assert required_field._label.text() == "Required Field *"
        
        # Test optional field
        optional_field = StandardField(
            ui_manager,
            field_name="optional_field",
            label="Optional Field",
            required=False
        )
        qtbot.addWidget(optional_field)
        assert optional_field._label.text() == "Optional Field"
        
        # Test changing required state
        optional_field.set_required(True)
        assert optional_field._label.text() == "Optional Field *"
        
        optional_field.set_required(False)
        assert optional_field._label.text() == "Optional Field"

    def test_content_handling(self, standard_field, qtbot):
        """Test content manipulation"""
        # Set content
        standard_field.set_content("Test content")
        assert standard_field.get_content() == "Test content"
        
        # Clear content
        clear_button = [b for b in standard_field.findChildren(QPushButton)
                       if b.objectName() == "clear_button"][0]
        
        with qtbot.waitSignal(standard_field.clear_requested):
            qtbot.mouseClick(clear_button, Qt.MouseButton.LeftButton)
        
        assert standard_field.get_content() == ""
        assert standard_field.is_empty()

    def test_required_validation(self, standard_field, qtbot):
        """Test required field validation"""
        # Ensure widget is shown
        standard_field.show()
        qtbot.waitExposed(standard_field)
        
        # Empty required field
        assert not standard_field.validate()
        assert not standard_field.is_valid()
        qtbot.wait(100)  # Wait for display update
        assert standard_field._validation_display.isVisible()
        assert "required" in standard_field._validation_display._message_label.text().lower()
        
        # Fill required field
        standard_field.set_content("Content")
        assert standard_field.validate()
        assert standard_field.is_valid()
        assert not standard_field._validation_display.isVisible()

    def test_help_button_visibility(self, qtbot, ui_manager):
        """Test help button visibility based on help text"""
        # Field with help text
        field_with_help = StandardField(
            ui_manager=ui_manager,
            field_name="test",
            help_text="Help text"
        )
        qtbot.addWidget(field_with_help)
        help_buttons = [b for b in field_with_help.findChildren(QPushButton)
                    if b.objectName() == "help_button"]
        assert len(help_buttons) == 1
        
        # Field without help text
        field_without_help = StandardField(
            ui_manager=ui_manager,
            field_name="test"
        )
        qtbot.addWidget(field_without_help)
        help_buttons = [b for b in field_without_help.findChildren(QPushButton)
                    if b.objectName() == "help_button"]
        assert len(help_buttons) == 0

    def test_generation_state(self, standard_field):
        """Test generation state handling"""
        # Set generating state
        standard_field.set_generating(True)
        assert standard_field._editor.isReadOnly()
        
        # Check buttons disabled
        for button in standard_field.findChildren(QPushButton):
            assert not button.isEnabled()
        
        # Clear generating state
        standard_field.set_generating(False)
        assert not standard_field._editor.isReadOnly()
        
        # Check buttons enabled
        for button in standard_field.findChildren(QPushButton):
            assert button.isEnabled()

    def test_help_system(self, standard_field, qtbot):
        """Test help functionality"""
        # Find help button
        help_button = [b for b in standard_field.findChildren(QPushButton)
                      if b.objectName() == "help_button"][0]
        
        # Test help signal
        with qtbot.waitSignal(standard_field.help_requested):
            qtbot.mouseClick(help_button, Qt.MouseButton.LeftButton)
        
        # Test help text update
        new_help = "Updated help text"
        standard_field.set_help_text(new_help)
        help_label = [w for w in standard_field.findChildren(QLabel)
                     if w.objectName() == "help_text"][0]
        assert help_label.text() == new_help

    def test_generate_signal(self, standard_field, qtbot):
        """Test generation signal"""
        generate_button = [b for b in standard_field.findChildren(QPushButton)
                         if b.objectName() == "generate_button"][0]
        
        with qtbot.waitSignal(standard_field.generate_requested):
            qtbot.mouseClick(generate_button, Qt.MouseButton.LeftButton)

    def test_style_application(self, standard_field):
        """Test style application"""
        assert "StandardField" in standard_field.styleSheet()
        assert "field_label" in standard_field.styleSheet()
        assert "field_editor" in standard_field.styleSheet()
        assert "generate_button" in standard_field.styleSheet()