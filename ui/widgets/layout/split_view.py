from typing import Optional, Tuple
from PyQt6.QtWidgets import (
    QWidget, QSplitter, QVBoxLayout, QFrame,
    QLabel, QPushButton, QHBoxLayout, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal

from core.state import UIStateManager
from ..base import BaseWidget

class SplitHeader(QFrame):
    """Header component for split panels"""
    def __init__(self, title: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        
        self._label = QLabel(title)
        self._label.setObjectName("split_header_label")
        layout.addWidget(self._label)
        
        self.setObjectName("split_header")
        self._setup_styling()

    def _setup_styling(self):
        """Setup header styling"""
        self.setStyleSheet("""
            QFrame#split_header {
                background-color: #f8f9fa;
                border-bottom: 1px solid #e9ecef;
            }
            
            QLabel#split_header_label {
                font-weight: bold;
                color: #495057;
            }
        """)

class SplitPanel(QFrame):
    """Individual panel in split view"""
    def __init__(self, title: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        
        # Add header
        self._header = SplitHeader(title, self)
        self._layout.addWidget(self._header)
        
        # Content area
        self._content = QFrame(self)
        self._content.setObjectName("split_content")
        self._content_layout = QVBoxLayout(self._content)
        self._layout.addWidget(self._content)
        
        self.setObjectName("split_panel")
        self._setup_styling()

    def _setup_styling(self):
        """Setup panel styling"""
        self.setStyleSheet("""
            QFrame#split_panel {
                background-color: #ffffff;
                border: none;
            }
            
            QFrame#split_content {
                background-color: transparent;
            }
        """)

    def set_content(self, widget: QWidget):
        """Set panel content"""
        # Clear existing content
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Add new content
        self._content_layout.addWidget(widget)

class SplitView(BaseWidget):
    """Split view with two resizable panels"""
    
    splitter_moved = pyqtSignal(int, int)  # position, index

    def __init__(self, 
                 ui_manager: UIStateManager,
                 left_title: str = "Left Panel",
                 right_title: str = "Right Panel",
                 parent: Optional[QWidget] = None):
        self.left_title = left_title
        self.right_title = right_title
        super().__init__(ui_manager, parent)

    def _setup_ui(self):
        """Setup split view UI"""
        # Create splitter
        self._splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self._splitter.setChildrenCollapsible(False)
        self._layout.addWidget(self._splitter)
        
        # Create panels
        self._left_panel = SplitPanel(self.left_title, self._splitter)
        self._right_panel = SplitPanel(self.right_title, self._splitter)
        
        # Add panels to splitter
        self._splitter.addWidget(self._left_panel)
        self._splitter.addWidget(self._right_panel)
        
        # Set initial sizes
        self._splitter.setStretchFactor(0, 1)
        self._splitter.setStretchFactor(1, 1)
        
        # Connect signals
        self._splitter.splitterMoved.connect(self.splitter_moved.emit)

    def _setup_styling(self):
        """Setup split view styling"""
        self.setStyleSheet("""
            SplitView {
                background-color: #ffffff;
            }
            
            QSplitter::handle {
                background-color: #e9ecef;
                width: 2px;
            }
            
            QSplitter::handle:hover {
                background-color: #3498db;
            }
        """)

    def set_left_content(self, widget: QWidget):
        """Set content of left panel"""
        self._left_panel.set_content(widget)

    def set_right_content(self, widget: QWidget):
        """Set content of right panel"""
        self._right_panel.set_content(widget)

    def get_sizes(self) -> Tuple[int, int]:
        """Get current panel sizes"""
        return tuple(self._splitter.sizes())

    def set_sizes(self, left: int, right: int):
        """Set panel sizes"""
        self._splitter.setSizes([left, right])

    def set_stretch_factors(self, left: int, right: int):
        """Set panel stretch factors"""
        self._splitter.setStretchFactor(0, left)
        self._splitter.setStretchFactor(1, right)