from typing import List, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QListWidget,
    QListWidgetItem, QFrame, QLabel
)
from PyQt6.QtCore import Qt, pyqtSignal

from core.state import UIStateManager
from ..base import BaseWidget

class PromptOrderWidget(BaseWidget):
    """Widget for managing prompt generation order"""
    
    order_changed = pyqtSignal(list)  # new_order
    
    def __init__(self, ui_manager: UIStateManager, parent: Optional[QWidget] = None):
        super().__init__(ui_manager, parent)
        
    def _setup_ui(self):
        """Setup order widget UI"""
        self._layout.setContentsMargins(16, 16, 16, 16)
        
        # Header
        header = QLabel("Generation Order")
        header.setObjectName("order_header")
        self._layout.addWidget(header)
        
        # Help text
        help_text = QLabel("Drag and drop to reorder. Fields can only depend on fields above them.")
        help_text.setObjectName("help_text")
        help_text.setWordWrap(True)
        self._layout.addWidget(help_text)
        
        # Order list
        self._list = QListWidget()
        self._list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self._list.model().rowsMoved.connect(self._order_updated)
        self._layout.addWidget(self._list)
        
        self._setup_styling()
        
    def _setup_styling(self):
        """Setup widget styling"""
        self.setStyleSheet("""
            QLabel#order_header {
                font-size: 16px;
                font-weight: bold;
                color: #2c3e50;
                margin-bottom: 8px;
            }
            
            QLabel#help_text {
                color: #666666;
                margin-bottom: 16px;
            }
            
            QListWidget {
                border: 1px solid #dcdcdc;
                border-radius: 4px;
                background-color: white;
            }
            
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #f0f0f0;
            }
            
            QListWidget::item:selected {
                background-color: #e8f4fc;
                color: #2c3e50;
            }
            
            QListWidget::item:hover {
                background-color: #f8f9fa;
            }
        """)
        
    def _order_updated(self):
        """Handle order changes"""
        new_order = [
            self._list.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self._list.count())
        ]
        self.order_changed.emit(new_order)
        
    def set_order(self, fields: List[str]):
        """Set current field order"""
        self._list.clear()
        
        for field in fields:
            item = QListWidgetItem(field.replace('_', ' ').title())
            item.setData(Qt.ItemDataRole.UserRole, field)
            self._list.addItem(item)
            
    def get_order(self) -> List[str]:
        """Get current field order"""
        return [
            self._list.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self._list.count())
        ]
        
    def move_field(self, field_name: str, direction: int):
        """Move field up or down"""
        items = self._list.findItems(
            field_name.replace('_', ' ').title(),
            Qt.MatchFlag.MatchExactly
        )
        if not items:
            return
            
        current_row = self._list.row(items[0])
        new_row = current_row + direction
        
        if 0 <= new_row < self._list.count():
            item = self._list.takeItem(current_row)
            self._list.insertItem(new_row, item)
            self._list.setCurrentItem(item)
            self._order_updated()