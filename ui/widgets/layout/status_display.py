from typing import Optional, Dict, List
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QIcon, QColor

from core.state import UIStateManager
from ..base import BaseWidget

class StatusLevel(Enum):
    """Status message importance levels"""
    INFO = auto()
    SUCCESS = auto()
    WARNING = auto()
    ERROR = auto()

@dataclass
class StatusMessage:
    """Status message container"""
    text: str
    level: StatusLevel
    timestamp: datetime
    duration: int  # milliseconds, 0 for persistent
    id: str  # unique identifier for the message

class StatusDisplay(BaseWidget):
    """Widget for displaying status messages and notifications"""
    
    message_shown = pyqtSignal(str)  # Emitted when message is displayed (message_id)
    message_hidden = pyqtSignal(str)  # Emitted when message is hidden (message_id)
    
    def __init__(self, 
                 ui_manager: UIStateManager,
                 parent: Optional[QWidget] = None,
                 max_messages: int = 3):
        self.max_messages = max_messages
        self._active_messages: Dict[str, StatusMessage] = {}
        self._message_timers: Dict[str, QTimer] = {}
        self._message_widgets: Dict[str, QFrame] = {}
        super().__init__(ui_manager, parent)

    def _setup_ui(self):
        """Setup status display UI"""
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(4)
        self._layout.addStretch()  # Push messages to bottom
        
        self.setMinimumWidth(300)
        self._setup_styling()

    def _setup_styling(self):
        """Setup widget styling"""
        self.setStyleSheet("""
            StatusDisplay {
                background: transparent;
            }
            
            QFrame.status_message {
                border-radius: 4px;
                padding: 8px;
                margin: 2px 0px;
            }
            
            QFrame.info {
                background-color: #E3F2FD;
                border: 1px solid #2196F3;
            }
            
            QFrame.success {
                background-color: #E8F5E9;
                border: 1px solid #4CAF50;
            }
            
            QFrame.warning {
                background-color: #FFF3E0;
                border: 1px solid #FF9800;
            }
            
            QFrame.error {
                background-color: #FFEBEE;
                border: 1px solid #F44336;
            }
            
            QLabel.message_text {
                color: #333333;
                font-size: 12px;
            }
            
            QPushButton.close_button {
                background: transparent;
                border: none;
                color: #666666;
                font-weight: bold;
                padding: 2px 6px;
            }
            
            QPushButton.close_button:hover {
                color: #333333;
                background-color: rgba(0, 0, 0, 0.1);
                border-radius: 2px;
            }
        """)

    def show_message(self, 
                    text: str,
                    level: StatusLevel = StatusLevel.INFO,
                    duration: int = 5000,  # 5 seconds default
                    message_id: Optional[str] = None) -> str:
        """Show a new status message"""
        # Generate message ID if not provided
        if message_id is None:
            message_id = f"{level.name.lower()}_{datetime.now().timestamp()}"
        
        # Create message
        message = StatusMessage(
            text=text,
            level=level,
            timestamp=datetime.now(),
            duration=duration,
            id=message_id
        )
        
        # Remove old messages if at limit
        current_count = len(self._active_messages)
        if current_count >= self.max_messages:
            # Find oldest message
            oldest_id = min(
                self._active_messages.keys(),
                key=lambda k: self._active_messages[k].timestamp
            )
            # Remove it before adding new one
            self.hide_message(oldest_id)
        
        # Add new message
        self._active_messages[message_id] = message
        self._create_message_widget(message)
        
        # Setup timer if needed
        if duration > 0:
            timer = QTimer(self)
            timer.setSingleShot(True)
            timer.timeout.connect(lambda: self.hide_message(message_id))
            timer.start(duration)
            self._message_timers[message_id] = timer
        
        self.message_shown.emit(message_id)
        return message_id

    def hide_message(self, message_id: str):
        """Hide and remove a message"""
        if message_id not in self._active_messages:
            return
        
        # Stop timer if exists
        if message_id in self._message_timers:
            timer = self._message_timers[message_id]
            timer.stop()
            timer.deleteLater()
            del self._message_timers[message_id]
        
        # Remove widget
        if message_id in self._message_widgets:
            widget = self._message_widgets[message_id]
            self._layout.removeWidget(widget)
            widget.deleteLater()
            del self._message_widgets[message_id]
        
        # Remove message
        del self._active_messages[message_id]
        
        self.message_hidden.emit(message_id)

    def clear_messages(self):
        """Clear all messages"""
        message_ids = list(self._active_messages.keys())
        for message_id in message_ids:
            self.hide_message(message_id)

    def _create_message_widget(self, message: StatusMessage):
        """Create widget for message"""
        # Create frame
        frame = QFrame(self)
        frame.setObjectName(f"message_frame_{message.id}")
        frame.setProperty("class", "status_message")
        frame.setProperty("level", message.level.name.lower())
        
        # Layout
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)
        
        # Message text
        text_label = QLabel(message.text)
        text_label.setObjectName("message_text")
        text_label.setWordWrap(True)
        layout.addWidget(text_label)
        
        # Close button for persistent messages
        if message.duration == 0:
            close_button = QPushButton("×")
            close_button.setObjectName("close_button")
            close_button.setProperty("class", "close_button")
            close_button.clicked.connect(lambda: self.hide_message(message.id))
            close_button.setCursor(Qt.CursorShape.PointingHandCursor)
            layout.addWidget(close_button)
        
        # Add to layout before stretch
        insert_pos = self._layout.count() - 1 if self._layout.count() > 0 else 0
        self._layout.insertWidget(insert_pos, frame)
        self._message_widgets[message.id] = frame
        
        # Apply level-specific styling
        frame.setProperty("class", f"status_message {message.level.name.lower()}")
        frame.style().unpolish(frame)
        frame.style().polish(frame)

    def update_message(self,
                      message_id: str,
                      text: Optional[str] = None,
                      level: Optional[StatusLevel] = None,
                      duration: Optional[int] = None) -> bool:
        """Update an existing message"""
        if message_id not in self._active_messages:
            return False
        
        message = self._active_messages[message_id]
        
        # Update message properties
        if text is not None:
            message.text = text
        if level is not None:
            message.level = level
        if duration is not None:
            message.duration = duration
            
            # Update timer
            if message_id in self._message_timers:
                self._message_timers[message_id].stop()
                del self._message_timers[message_id]
            
            if duration > 0:
                timer = QTimer(self)
                timer.setSingleShot(True)
                timer.timeout.connect(lambda: self.hide_message(message_id))
                timer.start(duration)
                self._message_timers[message_id] = timer
        
        # Recreate widget
        if message_id in self._message_widgets:
            self._message_widgets[message_id].deleteLater()
            del self._message_widgets[message_id]
        
        self._create_message_widget(message)
        return True

    def get_active_messages(self) -> List[StatusMessage]:
        """Get list of active messages"""
        return list(self._active_messages.values())

    def has_message(self, message_id: str) -> bool:
        """Check if message exists"""
        return message_id in self._active_messages