from typing import Optional, Any, Dict
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, 
    QPushButton, QFrame, QLabel,
    QWidget
)
from PyQt6.QtCore import Qt, pyqtSignal
from core.state import UIStateManager

class BaseDialog(QDialog):
    """Base dialog with standard layout and styling"""

    confirmed = pyqtSignal(Dict[str, Any])  # Signal emitted with dialog data
    cancelled = pyqtSignal()

    def __init__(self, 
                 ui_manager: UIStateManager,
                 title: str,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.ui_manager = ui_manager
        
        # Setup dialog
        self.setWindowTitle(title)
        self.setModal(True)  # Make dialog modal
        self._setup_layout()
        self._setup_styling()
        
    def _setup_layout(self):
        """Setup standard dialog layout"""
        # Main layout
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        
        # Header
        self._header = QFrame()
        self._header.setObjectName("dialog_header")
        header_layout = QVBoxLayout(self._header)
        
        self._title_label = QLabel(self.windowTitle())
        self._title_label.setObjectName("dialog_title")
        header_layout.addWidget(self._title_label)
        
        self._layout.addWidget(self._header)
        
        # Content area
        self._content = QFrame()
        self._content.setObjectName("dialog_content")
        self._content_layout = QVBoxLayout(self._content)
        self._layout.addWidget(self._content)
        
        # Button bar
        self._button_bar = QFrame()
        self._button_bar.setObjectName("dialog_buttons")
        button_layout = QHBoxLayout(self._button_bar)
        
        # Standard buttons
        button_layout.addStretch()
        
        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setObjectName("cancel_button")
        self._cancel_btn.clicked.connect(self._handle_cancel)
        button_layout.addWidget(self._cancel_btn)
        
        self._ok_btn = QPushButton("OK")
        self._ok_btn.setObjectName("ok_button")
        self._ok_btn.clicked.connect(self._handle_confirm)
        button_layout.addWidget(self._ok_btn)
        
        self._layout.addWidget(self._button_bar)
        
    def _setup_styling(self):
        """Setup dialog styling"""
        self.setStyleSheet("""
            BaseDialog {
                background-color: #ffffff;
                min-width: 400px;
            }
            
            QFrame#dialog_header {
                background-color: #f8f9fa;
                border-bottom: 1px solid #e9ecef;
                padding: 16px;
            }
            
            QLabel#dialog_title {
                font-size: 16px;
                font-weight: bold;
                color: #2c3e50;
            }
            
            QFrame#dialog_content {
                padding: 16px;
            }
            
            QFrame#dialog_buttons {
                background-color: #f8f9fa;
                border-top: 1px solid #e9ecef;
                padding: 12px 16px;
            }
            
            QPushButton {
                min-width: 80px;
                padding: 6px 12px;
            }
            
            QPushButton#cancel_button {
                border: 1px solid #ced4da;
                border-radius: 4px;
                background-color: #ffffff;
            }
            
            QPushButton#cancel_button:hover {
                background-color: #f8f9fa;
            }
            
            QPushButton#ok_button {
                border: 1px solid #2980b9;
                border-radius: 4px;
                background-color: #3498db;
                color: white;
            }
            
            QPushButton#ok_button:hover {
                background-color: #2980b9;
            }
        """)
        
    def _handle_confirm(self):
        """Handle dialog confirmation"""
        self.confirmed.emit(self.get_data())
        self.accept()
        
    def _handle_cancel(self):
        """Handle dialog cancellation"""
        self.cancelled.emit()
        self.reject()
        
    def get_data(self) -> Dict[str, Any]:
        """Get dialog data - override in subclasses"""
        return {}
        
    def set_data(self, data: Dict[str, Any]):
        """Set dialog data - override in subclasses"""
        pass

class ConfirmDialog(BaseDialog):
    """Simple confirmation dialog"""
    
    def __init__(self, 
                 ui_manager: UIStateManager,
                 title: str,
                 message: str,
                 confirm_text: str = "OK",
                 cancel_text: str = "Cancel",
                 parent: Optional[QWidget] = None):
        super().__init__(ui_manager, title, parent)
        
        # Set button text
        self._ok_btn.setText(confirm_text)
        self._cancel_btn.setText(cancel_text)
        
        # Add message
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        message_label.setObjectName("confirm_message")
        self._content_layout.addWidget(message_label)
        
        # Update styling
        self.setStyleSheet(self.styleSheet() + """
            QLabel#confirm_message {
                color: #2c3e50;
                font-size: 14px;
                margin: 8px 0px;
            }
        """)