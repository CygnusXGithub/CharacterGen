from typing import Optional, Callable, List, Any
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QLineEdit, QComboBox,
    QFileDialog, QMessageBox, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal

class DragDropFrame(QFrame):
    """Base frame with drag & drop support"""
    file_dropped = pyqtSignal(str)  # Emits path of dropped file
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setAcceptDrops(True)
    
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()
    
    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        for file_path in files:
            self.file_dropped.emit(file_path)
        event.accept()

class LoadSaveWidget(QWidget):
    """Reusable load/save controls"""
    save_clicked = pyqtSignal(str)  # Emits save name
    load_clicked = pyqtSignal(str)  # Emits selected item name
    refresh_clicked = pyqtSignal()  # Emits when refresh requested
    
    def __init__(self, 
                 items: List[str] = None,
                 save_label: str = "Save Name:",
                 load_label: str = "Load:",
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.items = items or []
        self._init_ui(save_label, load_label)
    
    def _init_ui(self, save_label: str, load_label: str):
        layout = QHBoxLayout()
        
        # Save name input
        layout.addWidget(QLabel(save_label))
        self.save_name = QLineEdit()
        layout.addWidget(self.save_name)
        
        # Load selector
        layout.addWidget(QLabel(load_label))
        self.selector = QComboBox()
        self.selector.addItems(self.items)
        self.selector.currentTextChanged.connect(
            lambda text: self.load_clicked.emit(text)
        )
        layout.addWidget(self.selector)
        
        # Refresh button
        refresh_btn = QPushButton("🔄")
        refresh_btn.setFixedWidth(30)
        refresh_btn.clicked.connect(self.refresh_clicked.emit)
        layout.addWidget(refresh_btn)
        
        # Save button
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._handle_save)
        layout.addWidget(save_btn)
        
        self.setLayout(layout)
    
    def _handle_save(self):
        name = self.save_name.text().strip()
        if name:
            self.save_clicked.emit(name)
    
    def update_items(self, items: List[str]):
        """Update the list of available items"""
        current = self.selector.currentText()
        self.selector.clear()
        self.selector.addItems(items)
        
        if current in items:
            self.selector.setCurrentText(current)

class EditableField(QWidget):
    """Base widget for editable fields"""
    value_changed = pyqtSignal(str)  # Emits when value changes
    
    def __init__(self, 
                 label: str,
                 multiline: bool = False,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.multiline = multiline
        self._init_ui(label)
    
    def _init_ui(self, label: str):
        layout = QVBoxLayout()
        
        # Header
        header = QHBoxLayout()
        header.addWidget(QLabel(label))
        
        # Add buttons
        self.edit_btn = QPushButton("✏️")
        self.edit_btn.setFixedWidth(30)
        self.edit_btn.clicked.connect(self._toggle_edit)
        header.addWidget(self.edit_btn)
        
        header.addStretch()
        layout.addLayout(header)
        
        # Editor
        if self.multiline:
            from PyQt6.QtWidgets import QTextEdit
            self.editor = QTextEdit()
            self.editor.textChanged.connect(
                lambda: self.value_changed.emit(self.editor.toPlainText())
            )
        else:
            self.editor = QLineEdit()
            self.editor.textChanged.connect(
                lambda text: self.value_changed.emit(text)
            )
        
        layout.addWidget(self.editor)
        self.setLayout(layout)
        
        # Initial state
        self.editor.setReadOnly(True)
    
    def _toggle_edit(self):
        """Toggle edit mode"""
        self.editor.setReadOnly(not self.editor.isReadOnly())
        self.edit_btn.setText("💾" if not self.editor.isReadOnly() else "✏️")
    
    def get_value(self) -> str:
        """Get current value"""
        if self.multiline:
            return self.editor.toPlainText()
        return self.editor.text()
    
    def set_value(self, value: str):
        """Set current value"""
        if self.multiline:
            self.editor.setPlainText(value)
        else:
            self.editor.setText(value)

class StatusBar(QWidget):
    """Status bar with progress indication"""
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._init_ui()
        # Set minimum and maximum height to ensure consistent size
        self.setMinimumHeight(25)
        self.setMaximumHeight(25)
        # Set size policy to maintain height
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,  # Horizontal policy
            QSizePolicy.Policy.Fixed       # Vertical policy
        )
    
    def _init_ui(self):
        layout = QHBoxLayout()
        # Reduce margins to make it more compact
        layout.setContentsMargins(5, 0, 5, 0)
        layout.setSpacing(5)
        
        self.status_label = QLabel()
        self.status_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred
        )
        layout.addWidget(self.status_label)
        
        self.progress_label = QLabel()
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.progress_label)
        
        self.setLayout(layout)
    
    def set_status(self, message: str):
        """Set status message"""
        self.status_label.setText(message)
    
    def set_progress(self, current: int, total: int):
        """Set progress indicator"""
        self.progress_label.setText(f"{current}/{total}")
    
    def clear(self):
        """Clear status bar"""
        self.status_label.clear()
        self.progress_label.clear()
