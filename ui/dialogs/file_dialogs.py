from typing import Optional, List, Dict, Any
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem,
    QLineEdit, QLabel, QPushButton,
    QFileDialog, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from datetime import datetime

from .base import BaseDialog
from core.state import UIStateManager

class RecentFilesList(QFrame):
    """List of recently accessed files"""
    
    file_selected = pyqtSignal(Path)
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup list UI"""
        layout = QVBoxLayout(self)
        
        # Header
        header = QLabel("Recent Files")
        header.setObjectName("recent_header")
        layout.addWidget(header)
        
        # File list
        self._list = QListWidget()
        self._list.itemDoubleClicked.connect(
            lambda item: self.file_selected.emit(Path(item.data(Qt.ItemDataRole.UserRole)))
        )
        layout.addWidget(self._list)
        
    def set_files(self, files: List[Path]):
        """Update list of recent files"""
        self._list.clear()
        for file_path in files:
            item = QListWidgetItem(file_path.name)
            item.setData(Qt.ItemDataRole.UserRole, str(file_path))
            # Add modification time
            mod_time = datetime.fromtimestamp(file_path.stat().st_mtime)
            item.setToolTip(f"Modified: {mod_time.strftime('%Y-%m-%d %H:%M')}")
            self._list.addItem(item)

class SaveDialog(BaseDialog):
    """Dialog for saving character files"""
    
    def __init__(self, 
                 ui_manager: UIStateManager,
                 default_name: str = "",
                 recent_files: Optional[List[Path]] = None,
                 parent: Optional[QWidget] = None):
        super().__init__(ui_manager, "Save Character", parent)
        self._recent_files = recent_files or []
        self._setup_save_ui(default_name)
        
    def _setup_save_ui(self, default_name: str):
        """Setup save dialog specific UI"""
        # Name input
        name_layout = QHBoxLayout()
        
        name_label = QLabel("File Name:")
        name_layout.addWidget(name_label)
        
        self._name_input = QLineEdit()
        self._name_input.setText(default_name)
        self._name_input.textChanged.connect(self._update_ok_button)
        name_layout.addWidget(self._name_input)
        
        self._content_layout.addLayout(name_layout)
        
        # Recent files
        if self._recent_files:
            self._recent_list = RecentFilesList()
            self._recent_list.set_files(self._recent_files)
            self._recent_list.file_selected.connect(self._handle_recent_selected)
            self._content_layout.addWidget(self._recent_list)
            
        # Browse button
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse)
        self._content_layout.addWidget(browse_btn)
        
        # Initial state
        self._update_ok_button()
        
    def _update_ok_button(self):
        """Update OK button enabled state"""
        self._ok_btn.setEnabled(bool(self._name_input.text().strip()))
        
    def _handle_recent_selected(self, path: Path):
        """Handle selection from recent files"""
        self._name_input.setText(path.name)
        
    def _browse(self):
        """Open file browser"""
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Character",
            str(Path.home()),
            "Character Files (*.json);;All Files (*.*)"
        )
        if path:
            self._name_input.setText(Path(path).name)
            
    def get_data(self) -> Dict[str, Any]:
        """Get dialog data"""
        return {
            'file_name': self._name_input.text().strip()
        }

class LoadDialog(BaseDialog):
    """Dialog for loading character files"""
    
    def __init__(self,
                 ui_manager: UIStateManager, 
                 recent_files: Optional[List[Path]] = None,
                 parent: Optional[QWidget] = None):
        super().__init__(ui_manager, "Load Character", parent)
        self._recent_files = recent_files or []
        self._setup_load_ui()
        
    def _setup_load_ui(self):
        """Setup load dialog specific UI"""
        # Recent files
        if self._recent_files:
            self._recent_list = RecentFilesList()
            self._recent_list.set_files(self._recent_files)
            self._recent_list.file_selected.connect(self._handle_recent_selected)
            self._content_layout.addWidget(self._recent_list)
        
        # Browse button
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse)
        self._content_layout.addWidget(browse_btn)
        
        # Initially disable OK until file selected
        self._ok_btn.setEnabled(False)
        
    def _handle_recent_selected(self, path: Path):
        """Handle selection from recent files"""
        self._selected_path = path
        self._ok_btn.setEnabled(True)
        
    def _browse(self):
        """Open file browser"""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Character",
            str(Path.home()),
            "Character Files (*.json);;All Files (*.*)"
        )
        if path:
            self._selected_path = Path(path)
            self._ok_btn.setEnabled(True)
            
    def get_data(self) -> Dict[str, Any]:
        """Get dialog data"""
        return {
            'file_path': self._selected_path
        } if hasattr(self, '_selected_path') else {}