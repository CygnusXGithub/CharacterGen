import pytest
from pathlib import Path
from PIL import Image, PngImagePlugin
from PyQt6.QtCore import Qt, QMimeData, QUrl
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
from ui.widgets.image import ImageWidget

@pytest.fixture
def image_widget(qtbot, ui_manager):
    """Create image widget for testing"""
    widget = ImageWidget(ui_manager)
    qtbot.addWidget(widget)
    widget.show()
    return widget

@pytest.fixture
def test_image(tmp_path) -> Path:
    """Create a test image file"""
    image_path = tmp_path / "test_image.png"
    # Create a simple test image
    img = Image.new('RGB', (100, 100), color='red')
    img.save(image_path)
    return image_path

class TestImageWidget:
    """Test image widget functionality"""

    def test_initialization(self, image_widget):
        """Test initial widget state"""
        assert image_widget._image_data is None
        assert not image_widget._clear_btn.isVisible()
        assert "Drop image here" in image_widget._image_label.text()

    def test_load_image(self, image_widget, test_image, qtbot):
        """Test loading image from file"""
        # Track signal emission
        with qtbot.waitSignal(image_widget.image_changed):
            image_widget.load_image(test_image)

        assert image_widget._image_data is not None
        assert image_widget._image_data.original_path == test_image
        assert image_widget._clear_btn.isVisible()
        assert not image_widget._image_label.text()  # Text should be cleared
        assert image_widget._image_label.pixmap() is not None

    def test_clear_image(self, image_widget, test_image, qtbot):
        """Test clearing image"""
        # Load image first
        image_widget.load_image(test_image)
        
        # Track clear signal
        with qtbot.waitSignal(image_widget.image_cleared):
            image_widget.clear_image()
        
        assert image_widget._image_data is None
        assert not image_widget._clear_btn.isVisible()
        assert "Drop image here" in image_widget._image_label.text()
        assert image_widget._image_label.pixmap().isNull()

    def test_invalid_image(self, image_widget, tmp_path, qtbot):
        """Test handling invalid image file"""
        # Create invalid image file
        invalid_file = tmp_path / "invalid.png"
        invalid_file.write_text("Not an image")

        # Track error signal
        with qtbot.waitSignal(image_widget.error_occurred):
            image_widget.load_image(invalid_file)

        assert image_widget._image_data is None
        assert not image_widget._clear_btn.isVisible()

    def test_resize_handling(self, image_widget, test_image, qtbot):
        """Test image resize handling"""
        # Load image
        image_widget.load_image(test_image)
        original_pixmap = image_widget._image_label.pixmap()

        # Resize widget
        new_size = image_widget.size() * 1.5
        image_widget.resize(new_size)
        qtbot.wait(100)  # Wait for resize processing

        # Verify image was rescaled
        new_pixmap = image_widget._image_label.pixmap()
        assert new_pixmap is not None
        assert new_pixmap.size() != original_pixmap.size()

    def test_image_resizing(self, image_widget, tmp_path, qtbot):
        """Test automatic image resizing for large images"""
        # Create oversized test image
        large_image_path = tmp_path / "large_image.png"
        large_img = Image.new('RGB', (2000, 2000), color='blue')
        large_img.save(large_image_path)

        # Load large image
        with qtbot.waitSignal(image_widget.image_changed):
            image_widget.load_image(large_image_path)

        assert image_widget._image_data is not None
        # Verify image was resized
        width, height = image_widget._image_data.image.size
        assert width <= image_widget._image_data.max_size[0]
        assert height <= image_widget._image_data.max_size[1]

    def test_load_image_with_data(self, image_widget, test_image_with_data, qtbot):
        """Test loading image with embedded character data"""
        image_path, expected_data = test_image_with_data
        
        # Track both signals
        with qtbot.waitSignals([
            image_widget.image_changed,
            image_widget.data_loaded
        ]):
            image_widget.load_image(image_path)
        
        assert image_widget._image_data is not None
        assert image_widget.has_embedded_data()
        assert image_widget.get_embedded_data() == expected_data

    def test_save_with_data(self, image_widget, test_image, tmp_path, qtbot):
        """Test saving image with embedded character data"""
        # Load regular image first
        image_widget.load_image(test_image)
        
        # Create test character data
        char_data = {
            "name": "Test Character",
            "description": "Test Description",
            "version": "1.0"
        }
        
        # Save with data
        save_path = tmp_path / "char_with_data.png"
        assert image_widget.save_with_data(save_path, char_data)
        
        # Load saved image and verify data
        with qtbot.waitSignal(image_widget.data_loaded) as blocker:
            image_widget.load_image(save_path)
        
        loaded_data = blocker.args[0]
        assert loaded_data == char_data

    def test_clear_image_with_data(self, image_widget, test_image_with_data, qtbot):
        """Test clearing image that has embedded data"""
        image_path, _ = test_image_with_data
        image_widget.load_image(image_path)
        
        with qtbot.waitSignal(image_widget.image_cleared):
            image_widget.clear_image()
        
        assert not image_widget.has_embedded_data()
        assert image_widget.get_embedded_data() is None

    def test_save_without_image(self, image_widget, tmp_path):
        """Test attempting to save data without an image loaded"""
        save_path = tmp_path / "no_image.png"
        assert not image_widget.save_with_data(save_path, {"test": "data"})

    def test_invalid_embedded_data(self, image_widget, tmp_path, qtbot):
        """Test handling invalid embedded data"""
        # Create image with invalid embedded data
        invalid_path = tmp_path / "invalid_data.png"
        img = Image.new('RGB', (100, 100), color='red')
        
        # Add invalid data
        metadata = PngImagePlugin.PngInfo()
        metadata.add_text("chara", "invalid-base64-data")
        img.save(invalid_path, "PNG", pnginfo=metadata)
        
        # Should emit error but not crash
        with qtbot.waitSignal(image_widget.error_occurred):
            image_widget.load_image(invalid_path)