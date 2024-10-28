from typing import Optional, Callable, List, Any
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QLineEdit, QComboBox,
    QFileDialog, QMessageBox, QSizePolicy, QTextEdit
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent

from ...core.enums import StatusLevel, UIMode
from ...core.managers import UIStateManager, SettingsManager

class DragDropFrame(QFrame):
    """Base frame with drag & drop support"""
    file_dropped = pyqtSignal(str)
    
    def __init__(self, 
                 ui_manager: UIStateManager,
                 parent: Optional[QWidget] = None):  # Parent parameter last
        super().__init__(parent)  # Correctly pass parent
        self.ui_manager = ui_manager
        self.setAcceptDrops(True)
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Sunken)
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter events"""
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()
    
    def dropEvent(self, event: QDropEvent):
        """Handle drop events"""
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        for file_path in files:
            self.file_dropped.emit(file_path)
        event.accept()

class EditableField(QWidget):
    """Base widget for editable fields"""
    value_changed = pyqtSignal(str)
    focus_changed = pyqtSignal(bool)
    
    def __init__(self, 
                 label: str,
                 ui_manager: UIStateManager,
                 settings_manager: Optional[SettingsManager] = None,
                 multiline: bool = False,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.label = label
        self.ui_manager = ui_manager
        self.settings_manager = settings_manager
        self.multiline = multiline
        self.is_updating = False
        self._init_ui()
        self._connect_signals()
    
    def _init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout()
        layout.setSpacing(5)
        
        # Header
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        
        # Label
        label = QLabel(self.label)
        font = label.font()
        font.setBold(True)
        label.setFont(font)
        header.addWidget(label)
        
        header.addStretch()
        layout.addLayout(header)
        
        # Editor
        if self.multiline:
            self.editor = QTextEdit()
            self.editor.textChanged.connect(self._handle_text_changed)
        else:
            self.editor = QLineEdit()
            self.editor.textChanged.connect(self._handle_text_changed)
        
        # Apply settings
        if self.settings_manager:
            font_size = self.settings_manager.get("ui.font_size", 10)
            font = self.editor.font()
            font.setPointSize(font_size)
            self.editor.setFont(font)
        
        layout.addWidget(self.editor)
        
        self.setLayout(layout)
    
    def _connect_signals(self):
        """Connect signals"""
        if self.settings_manager:
            self.settings_manager.settings_updated.connect(self._apply_settings)
    
    def _handle_text_changed(self):
        """Handle text changes"""
        if not self.is_updating:
            self.is_updating = True
            try:
                if isinstance(self.editor, QTextEdit):
                    self.value_changed.emit(self.editor.toPlainText())
                else:
                    self.value_changed.emit(self.editor.text())
            finally:
                self.is_updating = False
    
    def _apply_settings(self):
        """Apply updated settings"""
        if self.settings_manager:
            font_size = self.settings_manager.get("ui.font_size", 10)
            font = self.editor.font()
            font.setPointSize(font_size)
            self.editor.setFont(font)
    
    def get_value(self) -> str:
        """Get current value"""
        if isinstance(self.editor, QTextEdit):
            return self.editor.toPlainText()
        return self.editor.text()
    
    def set_value(self, value: str):
        """Set current value"""
        self.is_updating = True
        try:
            if isinstance(self.editor, QTextEdit):
                self.editor.setPlainText(value)
            else:
                self.editor.setText(value)
        finally:
            self.is_updating = False
    
    def focusInEvent(self, event):
        """Handle focus in"""
        super().focusInEvent(event)
        self.focus_changed.emit(True)
    
    def focusOutEvent(self, event):
        """Handle focus out"""
        super().focusOutEvent(event)
        self.focus_changed.emit(False)

class StatusBar(QWidget):
    """Status bar with progress indication"""
    def __init__(self, 
                 ui_manager: UIStateManager,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.ui_manager = ui_manager
        self._init_ui()
        self._connect_signals()
        
        # Set fixed height
        self.setMinimumHeight(25)
        self.setMaximumHeight(25)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed
        )
    
    def _init_ui(self):
        """Initialize UI"""
        layout = QHBoxLayout()
        layout.setContentsMargins(5, 0, 5, 0)
        layout.setSpacing(5)
        
        # Status message
        self.status_label = QLabel()
        self.status_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred
        )
        layout.addWidget(self.status_label)
        
        # Progress indicator
        self.progress_label = QLabel()
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.progress_label)
        
        self.setLayout(layout)
    
    def _connect_signals(self):
        """Connect signals"""
        self.ui_manager.status_message.connect(self._handle_status_message)
    
    def _handle_status_message(self, message: str, level: StatusLevel):
        """Handle status message updates"""
        # Set color based on level
        color = {
            StatusLevel.INFO: "black",
            StatusLevel.SUCCESS: "green",
            StatusLevel.WARNING: "orange",
            StatusLevel.ERROR: "red"
        }.get(level, "black")
        
        self.status_label.setStyleSheet(f"color: {color}")
        self.status_label.setText(message)
    
    def set_progress(self, current: int, total: int):
        """Set progress indicator"""
        self.progress_label.setText(f"{current}/{total}")
    
    def clear(self):
        """Clear status bar"""
        self.status_label.clear()
        self.progress_label.clear()

class LoadSaveWidget(QWidget):
    """Widget for load/save operations"""
    save_clicked = pyqtSignal(str)
    load_clicked = pyqtSignal(str)
    
    def __init__(self, 
                 save_label: str = "Name:",
                 load_label: str = "Load:",
                 parent: Optional[QWidget] = None):  # Parent parameter last
        super().__init__(parent)  # Correctly pass parent
        self.save_label = save_label
        self.load_label = load_label
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the user interface"""
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # Save section
        save_layout = QHBoxLayout()
        
        save_label = QLabel(self.save_label)
        save_layout.addWidget(save_label)
        
        self.save_name = QLineEdit()
        self.save_name.setPlaceholderText("Enter name...")
        self.save_name.setMinimumWidth(150)
        save_layout.addWidget(self.save_name)
        
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(
            lambda: self.save_clicked.emit(self.save_name.text().strip())
        )
        save_layout.addWidget(self.save_btn)
        
        layout.addLayout(save_layout)
        
        # Add separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)
        
        # Load section
        load_layout = QHBoxLayout()
        
        load_label = QLabel(self.load_label)
        load_layout.addWidget(load_label)
        
        self.load_combo = QComboBox()
        self.load_combo.setMinimumWidth(150)
        load_layout.addWidget(self.load_combo)
        
        self.load_btn = QPushButton("Load")
        self.load_btn.clicked.connect(
            lambda: self.load_clicked.emit(self.load_combo.currentText())
        )
        load_layout.addWidget(self.load_btn)
        
        layout.addLayout(load_layout)
        
        self.setLayout(layout)
    
    def update_items(self, items: List[str]):
        """Update list of loadable items"""
        current = self.load_combo.currentText()
        
        self.load_combo.clear()
        self.load_combo.addItems(items)
        
        # Restore previous selection if possible
        index = self.load_combo.findText(current)
        if index >= 0:
            self.load_combo.setCurrentIndex(index)
    
    def get_save_name(self) -> str:
        """Get current save name"""
        return self.save_name.text().strip()
    
    def get_selected_item(self) -> str:
        """Get selected load item"""
        return self.load_combo.currentText()
    
    def clear(self):
        """Clear all inputs"""
        self.save_name.clear()
        self.load_combo.clear()
    
    def set_save_enabled(self, enabled: bool):
        """Enable/disable save functionality"""
        self.save_name.setEnabled(enabled)
        self.save_btn.setEnabled(enabled)
    
    def set_load_enabled(self, enabled: bool):
        """Enable/disable load functionality"""
        self.load_combo.setEnabled(enabled)
        self.load_btn.setEnabled(enabled)