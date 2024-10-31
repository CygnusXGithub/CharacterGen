import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QLabel

from ui.widgets.validation import (
    ValidationDisplay, DismissibleValidationDisplay, 
    ValidationSeverity
)

@pytest.fixture
def validation_display(qtbot):
    widget = ValidationDisplay()
    qtbot.addWidget(widget)
    return widget

@pytest.fixture
def dismissible_display(qtbot):
    widget = DismissibleValidationDisplay()
    qtbot.addWidget(widget)
    return widget

class TestValidationDisplay:
    """Test validation display functionality"""

    def test_initial_state(self, validation_display):
        """Test initial widget state"""
        assert not validation_display.isVisible()
        assert validation_display._message_label.text() == ""

    def test_show_message(self, validation_display):
        """Test showing messages with different severities"""
        # Test info message
        validation_display.show_message("Info message", ValidationSeverity.INFO)
        assert validation_display.isVisible()
        assert "Info message" in validation_display._message_label.text()
        assert "#E6F3FF" in validation_display.styleSheet()  # Info background color
        
        # Test warning message
        validation_display.show_message("Warning message", ValidationSeverity.WARNING)
        assert "Warning message" in validation_display._message_label.text()
        assert "#FFF7E6" in validation_display.styleSheet()  # Warning background color
        
        # Test error message
        validation_display.show_message("Error message", ValidationSeverity.ERROR)
        assert "Error message" in validation_display._message_label.text()
        assert "#FFE9E9" in validation_display.styleSheet()  # Error background color

    def test_clear_message(self, validation_display):
        """Test clearing messages"""
        validation_display.show_message("Test message")
        validation_display.clear()
        
        assert not validation_display.isVisible()
        assert validation_display._message_label.text() == ""

    def test_click_signal(self, validation_display, qtbot):
        """Test click signal emission"""
        validation_display.show_message("Clickable message")
        
        with qtbot.waitSignal(validation_display.clicked):
            qtbot.mouseClick(validation_display, Qt.MouseButton.LeftButton)

class TestDismissibleValidationDisplay:
    """Test dismissible validation display functionality"""

    def test_dismiss_button(self, dismissible_display):
        """Test dismiss button presence"""
        assert len(dismissible_display.findChildren(QLabel)) == 2  # Message + dismiss button

    def test_dismissal(self, dismissible_display, qtbot):
        """Test dismissal functionality"""
        dismissible_display.show_message("Dismissible message")
        
        with qtbot.waitSignal(dismissible_display.dismissed):
            # Find and click dismiss button (last label)
            dismiss_button = dismissible_display.findChildren(QLabel)[-1]
            qtbot.mouseClick(dismiss_button, Qt.MouseButton.LeftButton)
        
        assert not dismissible_display.isVisible()

    def test_message_persistence(self, dismissible_display):
        """Test message stays visible until dismissed"""
        dismissible_display.show_message("Test message")
        assert dismissible_display.isVisible()
        
        # Show new message
        dismissible_display.show_message("New message")
        assert dismissible_display.isVisible()
        assert "New message" in dismissible_display._message_label.text()

    def test_styling(self, dismissible_display):
        """Test styling with different severities"""
        for severity in ValidationSeverity:
            dismissible_display.show_message(f"{severity.value} message", severity)
            
            if severity == ValidationSeverity.ERROR:
                assert "#FF4D4D" in dismissible_display.styleSheet()  # Error border color
            elif severity == ValidationSeverity.WARNING:
                assert "#FFB84D" in dismissible_display.styleSheet()  # Warning border color
            else:
                assert "#4DA6FF" in dismissible_display.styleSheet()  # Info border color