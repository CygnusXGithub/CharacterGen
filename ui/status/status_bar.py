from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
from PyQt6.QtWidgets import (
    QStatusBar, QLabel, QProgressBar,
    QWidget, QHBoxLayout, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer

from core.state import UIStateManager
from core.models.ui import StatusLevel
from ..widgets.base import BaseWidget

@dataclass
class StatusInfo:
    """Status message information"""
    text: str
    level: StatusLevel
    timestamp: datetime
    duration: int  # milliseconds, 0 for persistent
    metadata: Dict[str, Any]

class StatusIndicator(QFrame):
    """Status indicator widget"""
    
    clicked = pyqtSignal()
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup indicator UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(4)
        
        # Status icon/color
        self._indicator = QLabel("●")
        self._indicator.setObjectName("status_indicator")
        layout.addWidget(self._indicator)
        
        # Status text
        self._label = QLabel()
        self._label.setObjectName("status_text")
        layout.addWidget(self._label)
        
        self.setObjectName("status_indicator_frame")
        self._setup_styling()
        
    def _setup_styling(self):
        """Setup indicator styling"""
        self.setStyleSheet("""
            QFrame#status_indicator_frame {
                border: none;
                border-radius: 2px;
                padding: 2px;
            }
            
            QFrame#status_indicator_frame:hover {
                background-color: rgba(0, 0, 0, 0.1);
            }
            
            QLabel#status_indicator {
                font-size: 10px;
            }
            
            QLabel#status_text {
                color: #666666;
            }
        """)
        
    def mousePressEvent(self, event):
        """Handle mouse press"""
        self.clicked.emit()
        super().mousePressEvent(event)
        
    def set_status(self, info: StatusInfo):
        """Update status display"""
        self._label.setText(info.text)
        
        # Set color based on level
        color = {
            StatusLevel.INFO: "#3498db",    # Blue
            StatusLevel.SUCCESS: "#2ecc71",  # Green
            StatusLevel.WARNING: "#f1c40f",  # Yellow
            StatusLevel.ERROR: "#e74c3c"     # Red
        }.get(info.level, "#666666")
        
        self._indicator.setStyleSheet(f"""
            QLabel#status_indicator {{
                color: {color};
            }}
        """)

class ProgressWidget(QFrame):
    """Progress indicator widget"""
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup progress UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(4)
        
        # Progress bar
        self._progress = QProgressBar()
        self._progress.setObjectName("status_progress")
        self._progress.setMinimumWidth(100)
        self._progress.setMaximumWidth(150)
        self._progress.setMaximumHeight(16)
        layout.addWidget(self._progress)
        
        # Status text
        self._label = QLabel()
        self._label.setObjectName("progress_text")
        layout.addWidget(self._label)
        
        self.setObjectName("progress_frame")
        self._setup_styling()
        
    def _setup_styling(self):
        """Setup progress styling"""
        self.setStyleSheet("""
            QFrame#progress_frame {
                border: none;
                background: transparent;
            }
            
            QProgressBar#status_progress {
                border: 1px solid #dcdcdc;
                border-radius: 2px;
                background-color: #f5f5f5;
                text-align: center;
            }
            
            QProgressBar#status_progress::chunk {
                background-color: #3498db;
                border-radius: 1px;
            }
            
            QLabel#progress_text {
                color: #666666;
                font-size: 11px;
            }
        """)
        
    def set_progress(self, value: int, max_value: int, text: str = ""):
        """Update progress display"""
        self._progress.setMaximum(max_value)
        self._progress.setValue(value)
        self._label.setText(text)
        
    def set_indeterminate(self, text: str = ""):
        """Set indeterminate progress"""
        self._progress.setMaximum(0)
        self._label.setText(text)

class MainStatusBar(QStatusBar):
    """Main application status bar"""
    
    def __init__(self, ui_manager: UIStateManager, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.ui_manager = ui_manager
        self._active_messages: Dict[str, StatusInfo] = {}
        self._timers: Dict[str, QTimer] = {}
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup status bar UI"""
        # Primary status indicator
        self._status = StatusIndicator()
        self.addWidget(self._status)
        
        # Progress indicator (hidden by default)
        self._progress = ProgressWidget()
        self._progress.hide()
        self.addWidget(self._progress)
        
        # Permanent widgets on right
        self._character_status = QLabel()
        self._character_status.setObjectName("character_status")
        self.addPermanentWidget(self._character_status)
        
        self._generation_status = QLabel()
        self._generation_status.setObjectName("generation_status")
        self.addPermanentWidget(self._generation_status)
        
        self._setup_styling()
        
    def _setup_styling(self):
        """Setup status bar styling"""
        self.setStyleSheet("""
            QStatusBar {
                border-top: 1px solid #dcdcdc;
            }
            
            QLabel#character_status, QLabel#generation_status {
                color: #666666;
                padding: 0 8px;
                border-left: 1px solid #dcdcdc;
            }
        """)
        
    def show_message(self, 
                    text: str,
                    level: StatusLevel = StatusLevel.INFO,
                    duration: int = 5000,
                    metadata: Optional[Dict[str, Any]] = None) -> str:
        """Show status message"""
        # Create status info
        info = StatusInfo(
            text=text,
            level=level,
            timestamp=datetime.now(),
            duration=duration,
            metadata=metadata or {}
        )
        
        # Generate unique ID
        message_id = f"{level.name.lower()}_{datetime.now().timestamp()}"
        
        # Store message
        self._active_messages[message_id] = info
        
        # Update display
        self._status.set_status(info)
        
        # Setup timer if needed
        if duration > 0:
            timer = QTimer(self)
            timer.setSingleShot(True)
            timer.timeout.connect(lambda: self.clear_message(message_id))
            timer.start(duration)
            self._timers[message_id] = timer
            
        return message_id
        
    def clear_message(self, message_id: str):
        """Clear specific message"""
        if message_id in self._active_messages:
            # Stop timer
            if message_id in self._timers:
                self._timers[message_id].stop()
                del self._timers[message_id]
            
            # Remove message
            del self._active_messages[message_id]
            
            # Update display with next message or clear
            if self._active_messages:
                latest = max(
                    self._active_messages.items(),
                    key=lambda x: x[1].timestamp
                )
                self._status.set_status(latest[1])
            else:
                self._status.set_status(StatusInfo(
                    text="Ready",
                    level=StatusLevel.INFO,
                    timestamp=datetime.now(),
                    duration=0,
                    metadata={}
                ))
                
    def show_progress(self, 
                     value: int,
                     max_value: int,
                     text: str = ""):
        """Show progress indicator"""
        self._progress.show()
        self._progress.set_progress(value, max_value, text)
        
    def show_indeterminate_progress(self, text: str = ""):
        """Show indeterminate progress"""
        self._progress.show()
        self._progress.set_indeterminate(text)
        
    def hide_progress(self):
        """Hide progress indicator"""
        self._progress.hide()
        
    def set_character_status(self, text: str):
        """Set character status text"""
        self._character_status.setText(text)
        
    def set_generation_status(self, text: str):
        """Set generation status text"""
        self._generation_status.setText(text)