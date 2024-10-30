import pytest
from PyQt6.QtCore import Qt
from ui.widgets.layout.status_display import StatusDisplay, StatusLevel
from PyQt6.QtWidgets import QPushButton

@pytest.fixture
def status_display(qtbot, ui_manager):
    """Create status display for testing"""
    display = StatusDisplay(ui_manager, max_messages=3)
    qtbot.addWidget(display)
    display.show()
    return display

class TestStatusDisplay:
    """Test status display functionality"""
    
    def test_show_message(self, status_display, qtbot):
        """Test showing messages"""
        # Show message and verify
        msg_id = status_display.show_message("Test message", StatusLevel.INFO)
        qtbot.wait(100)  # Wait for widget creation
        
        assert status_display.has_message(msg_id)
        assert len(status_display.get_active_messages()) == 1
        
        # Verify widget creation
        frame = status_display._message_widgets.get(msg_id)
        assert frame is not None
        assert frame.isVisible()
        assert "info" in frame.property("level")

    def test_message_levels(self, status_display, qtbot):
        """Test different message levels"""
        for level in StatusLevel:
            msg_id = status_display.show_message(
                f"Test {level.name}", 
                level=level
            )
            frame = status_display._message_widgets[msg_id]
            assert level.name.lower() in frame.property("level")

    def test_message_limit(self, status_display, qtbot):
        """Test maximum messages limit"""
        # Add max + 1 messages
        message_ids = []
        for i in range(4):  # max is 3
            msg_id = status_display.show_message(f"Message {i}", duration=0)  # Make them persistent
            message_ids.append(msg_id)
            qtbot.wait(50)  # Give time for widget creation
        
        # Verify oldest message was removed
        assert not status_display.has_message(message_ids[0])
        assert len(status_display.get_active_messages()) == status_display.max_messages

    @pytest.mark.parametrize("duration", [100, 200])
    def test_message_duration(self, status_display, qtbot, duration):
        """Test message duration"""
        with qtbot.waitSignal(status_display.message_hidden, timeout=duration + 100):
            msg_id = status_display.show_message(
                "Temporary message",
                duration=duration
            )
            assert status_display.has_message(msg_id)

    def test_persistent_message(self, status_display, qtbot):
        """Test persistent message"""
        msg_id = status_display.show_message(
            "Persistent message",
            duration=0  # persistent
        )
        
        # Verify close button exists
        frame = status_display._message_widgets[msg_id]
        close_button = frame.findChild(QPushButton, "close_button")
        assert close_button is not None
        
        # Test closing
        with qtbot.waitSignal(status_display.message_hidden):
            qtbot.mouseClick(close_button, Qt.MouseButton.LeftButton)
        
        assert not status_display.has_message(msg_id)

    def test_update_message(self, status_display, qtbot):
        """Test message updating"""
        # Show initial message
        msg_id = status_display.show_message("Initial text", StatusLevel.INFO)
        
        # Update message
        success = status_display.update_message(
            msg_id,
            text="Updated text",
            level=StatusLevel.WARNING
        )
        
        assert success
        message = status_display._active_messages[msg_id]
        assert message.text == "Updated text"
        assert message.level == StatusLevel.WARNING
        
        # Verify widget update
        frame = status_display._message_widgets[msg_id]
        assert "warning" in frame.property("level")
        
        # Test updating non-existent message
        assert not status_display.update_message("invalid_id", text="Test")

    def test_clear_messages(self, status_display, qtbot):
        """Test clearing all messages"""
        # Add exactly max_messages
        for i in range(status_display.max_messages):
            status_display.show_message(f"Message {i}", duration=0)
            qtbot.wait(50)  # Give time for widget creation
        
        # Verify message count
        active_messages = status_display.get_active_messages()
        assert len(active_messages) == status_display.max_messages
        
        # Clear messages
        status_display.clear_messages()
        qtbot.wait(50)  # Give time for cleanup
        
        assert len(status_display.get_active_messages()) == 0
        assert len(status_display._message_widgets) == 0