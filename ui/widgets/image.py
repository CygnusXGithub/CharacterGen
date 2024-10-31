from typing import Optional
from pathlib import Path
from PIL import Image, ImageQt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, 
    QFileDialog, QFrame, QHBoxLayout
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QDragEnterEvent, QDropEvent

from .base import BaseWidget
from core.state import UIStateManager
from core.models.image import ImageData

class ImageWidget(BaseWidget):
    """Widget for handling character images"""
    
    image_changed = pyqtSignal(ImageData)    # Emitted when image changes
    image_cleared = pyqtSignal()             # Emitted when image is cleared
    data_loaded = pyqtSignal(dict)           # Emitted when character data is found in image
    
    def __init__(self, 
                 ui_manager: UIStateManager,
                 parent: Optional[QWidget] = None):
        super().__init__(ui_manager, parent)
        self._image_data: Optional[ImageData] = None
        self.setAcceptDrops(True)  # Enable drag and drop
        
    def _setup_ui(self):
        """Setup image widget UI"""
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(4)
        
        # Image display frame
        self._image_frame = QFrame(self)
        self._image_frame.setObjectName("image_frame")
        self._image_frame.setMinimumSize(256, 256)
        self._image_frame.setMaximumSize(512, 512)
        
        # Image label
        self._image_label = QLabel(self._image_frame)
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_label.setObjectName("image_label")
        self._image_label.setText("Drop image here\nor click to select")
        
        # Frame layout
        frame_layout = QVBoxLayout(self._image_frame)
        frame_layout.addWidget(self._image_label)
        self._layout.addWidget(self._image_frame)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self._select_btn = QPushButton("Select Image")
        self._select_btn.clicked.connect(self._select_image)
        button_layout.addWidget(self._select_btn)
        
        self._clear_btn = QPushButton("Clear")
        self._clear_btn.clicked.connect(self.clear_image)
        self._clear_btn.setVisible(False)
        button_layout.addWidget(self._clear_btn)
        
        self._layout.addLayout(button_layout)
        
        self._setup_styling()
        
    def _setup_styling(self):
        """Setup widget styling"""
        self.setStyleSheet("""
            QFrame#image_frame {
                border: 2px dashed #cccccc;
                border-radius: 4px;
                background-color: #f8f9fa;
            }
            
            QFrame#image_frame:hover {
                border-color: #3498db;
                background-color: #e8f4fc;
            }
            
            QLabel#image_label {
                color: #666666;
                font-size: 14px;
            }
            
            QPushButton {
                padding: 6px 12px;
                border: 1px solid #cccccc;
                border-radius: 4px;
                background-color: #ffffff;
            }
            
            QPushButton:hover {
                border-color: #3498db;
                background-color: #e8f4fc;
            }
        """)

    def _select_image(self):
        """Open file dialog to select image"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Character Image",
            "",
            "Images (*.png *.jpg *.jpeg *.gif *.bmp)"
        )
        if file_path:
            self.load_image(Path(file_path))
            
    def load_image(self, path: Path):
        """Load image from path and extract any embedded data"""
        try:
            # Use ImageData's from_file classmethod
            self._image_data = ImageData.from_file(path)
            self._image_data.resize_if_needed()
            self._update_display()
            
            # Emit image changed signal
            self.image_changed.emit(self._image_data)
            
            # If there's embedded data, emit it
            if self._image_data.embedded_data:
                self.data_loaded.emit(self._image_data.embedded_data)
                
        except Exception as e:
            self.error_occurred.emit("image_load_error", str(e))

    def save_with_data(self, path: Path, character_data: dict) -> bool:
        """Save current image with embedded character data"""
        try:
            if not self._image_data or not self._image_data.image:
                return False
                
            self._image_data.save_with_data(path, character_data)
            return True
            
        except Exception as e:
            self.error_occurred.emit("image_save_error", str(e))
            return False

    def has_embedded_data(self) -> bool:
        """Check if current image has embedded character data"""
        return bool(self._image_data and self._image_data.embedded_data)
    
    def get_embedded_data(self) -> Optional[dict]:
        """Get embedded character data if available"""
        return self._image_data.embedded_data if self._image_data else None
          
    def _update_display(self):
        """Update image display"""
        if self._image_data and self._image_data.image:
            # Convert PIL image to QPixmap
            qt_image = ImageQt.ImageQt(self._image_data.image)
            pixmap = QPixmap.fromImage(qt_image)
            
            # Scale pixmap to fit frame while maintaining aspect ratio
            scaled = pixmap.scaled(
                self._image_frame.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            
            self._image_label.setPixmap(scaled)
            self._clear_btn.setVisible(True)
            self._image_label.setText("")
        else:
            self._image_label.clear()  # Change this line from setPixmap(QPixmap())
            self._clear_btn.setVisible(False)
            self._image_label.setText("Drop image here\nor click to select")
            
    def clear_image(self):
        """Clear current image"""
        self._image_data = None
        self._image_label.clear()
        self._image_label.setPixmap(QPixmap())  # Use empty QPixmap instead of None
        self._clear_btn.setVisible(False)
        self._image_label.setText("Drop image here\nor click to select")
        self.image_cleared.emit()
        
    def get_image_data(self) -> Optional[ImageData]:
        """Get current image data"""
        return self._image_data
        
    # Drag and drop handlers
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter event"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            
    def dropEvent(self, event: QDropEvent):
        """Handle drop event"""
        urls = event.mimeData().urls()
        if urls:
            path = Path(urls[0].toLocalFile())
            if path.suffix.lower() in ['.png', '.jpg', '.jpeg', '.gif', '.bmp']:
                self.load_image(path)
                
    def resizeEvent(self, event):
        """Handle resize event"""
        super().resizeEvent(event)
        if self._image_data:
            self._update_display()