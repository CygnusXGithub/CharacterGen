from enum import Enum
from PyQt6.QtWidgets import (
    QWidget, QLabel, QHBoxLayout, 
    QVBoxLayout, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPalette

class ValidationSeverity(Enum):
    """Validation message severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"

class ValidationDisplay(QFrame):
    """Widget for displaying validation messages"""
    
    clicked = pyqtSignal()  # Signal when clicked (for dismissible messages)

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Plain)
        
        # Setup layout
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(8, 8, 8, 8)
        self._layout.setSpacing(4)
        
        # Message label
        self._message_label = QLabel()
        self._message_label.setWordWrap(True)
        self._message_label.setTextFormat(Qt.TextFormat.RichText)
        self._layout.addWidget(self._message_label)
        
        # Default severity
        self._severity = ValidationSeverity.INFO
        
        # Ensure proper sizing
        self.setMinimumHeight(20)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)

        # Initial state
        self.hide()
        self._setup_styling()

    def _setup_styling(self):
        """Setup widget styling"""
        self.setStyleSheet("""
            ValidationDisplay {
                border-radius: 4px;
            }
            QLabel {
                color: #333333;
            }
        """)

    def show_message(self, message: str, severity: ValidationSeverity = ValidationSeverity.INFO):
        """Show validation message with specified severity"""
        self._severity = severity
        
        # Set message
        self._message_label.setText(message)
        self._message_label.adjustSize()  # Ensure label size is updated
        
        # Apply severity-specific styling
        self._apply_severity_styling(severity)
        
        # Ensure widget is visible and update layout
        self.show()
        self.adjustSize()  # Ensure frame size is updated
        
        # Force update
        self.update()
        
        print(f"ValidationDisplay.show_message: isVisible={self.isVisible()}, geometry={self.geometry()}")

    def clear(self):
        """Clear validation message"""
        self._message_label.clear()
        self.hide()

    def mousePressEvent(self, event):
        """Handle mouse press events"""
        self.clicked.emit()
        super().mousePressEvent(event)

    def _apply_severity_styling(self, severity: ValidationSeverity):
        """Apply styling based on severity"""
        base_style = """
            ValidationDisplay {
                border-radius: 4px;
                padding: 4px;
                margin: 4px 0px;
            }
        """
        
        if severity == ValidationSeverity.ERROR:
            style = base_style + """
                ValidationDisplay {
                    background-color: #FFE9E9;
                    border: 1px solid #FF4D4D;
                }
                QLabel {
                    color: #CC0000;
                }
            """
        elif severity == ValidationSeverity.WARNING:
            style = base_style + """
                ValidationDisplay {
                    background-color: #FFF7E6;
                    border: 1px solid #FFB84D;
                }
                QLabel {
                    color: #995C00;
                }
            """
        else:  # INFO
            style = base_style + """
                ValidationDisplay {
                    background-color: #E6F3FF;
                    border: 1px solid #4DA6FF;
                }
                QLabel {
                    color: #004D99;
                }
            """
        
        self.setStyleSheet(style)
class DismissibleValidationDisplay(ValidationDisplay):
    """Validation display that can be dismissed"""
    
    dismissed = pyqtSignal()  # Signal when message is dismissed

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self._setup_dismiss_button()

    def _setup_dismiss_button(self):
        """Setup dismiss button"""
        # Convert to horizontal layout
        new_layout = QHBoxLayout()
        new_layout.setContentsMargins(8, 8, 8, 8)
        new_layout.setSpacing(4)
        
        # Move message label to horizontal layout
        self._layout.removeWidget(self._message_label)
        new_layout.addWidget(self._message_label)
        
        # Add dismiss button
        dismiss_label = QLabel("×")  # Using × character as close button
        dismiss_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        dismiss_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                padding: 0 4px;
            }
            QLabel:hover {
                color: #666666;
            }
        """)
        new_layout.addWidget(dismiss_label)
        
        # Replace layout
        QWidget().setLayout(self._layout)  # Delete old layout
        self._layout = new_layout
        self.setLayout(self._layout)
        
        # Connect dismiss action
        dismiss_label.mousePressEvent = lambda e: self._dismiss()

    def _dismiss(self):
        """Handle dismissal"""
        self.clear()
        self.dismissed.emit()