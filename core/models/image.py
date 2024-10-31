from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any
from pathlib import Path
from PIL import Image, PngImagePlugin
from io import BytesIO
import base64
import json

@dataclass
class ImageData:
    """Container for character image data and embedded character info"""
    image: Optional[Image.Image] = None
    original_path: Optional[Path] = None
    dimensions: Tuple[int, int] = (256, 256)  # Default dimensions
    max_size: Tuple[int, int] = (1024, 1024)  # Maximum allowed dimensions
    embedded_data: Optional[Dict[str, Any]] = None
    
    
    def resize_if_needed(self) -> bool:
        """Resize image if it exceeds max dimensions"""
        if not self.image:
            return False
            
        width, height = self.image.size
        if width > self.max_size[0] or height > self.max_size[1]:
            ratio = min(self.max_size[0]/width, self.max_size[1]/height)
            new_size = (int(width * ratio), int(height * ratio))
            self.image = self.image.resize(new_size, Image.Resampling.LANCZOS)
            return True
        return False
    
    def to_bytes(self) -> Optional[bytes]:
        """Convert image to bytes for storage"""
        if not self.image:
            return None
        buffer = BytesIO()
        self.image.save(buffer, format='PNG')
        return buffer.getvalue()
        
    @classmethod
    def from_bytes(cls, data: bytes) -> 'ImageData':
        """Create ImageData from bytes"""
        buffer = BytesIO(data)
        image = Image.open(buffer)
        return cls(image=image)
    
    @classmethod
    def from_file(cls, path: Path) -> 'ImageData':
        """Create ImageData from file, extracting any embedded character data"""
        with Image.open(path) as img:
            img.load()  # Load image data
            embedded_data = None
            
            # Check for embedded character data
            if 'chara' in img.info:
                try:
                    encoded_json = img.info['chara']
                    decoded_json = base64.b64decode(encoded_json).decode('utf-8')
                    embedded_data = json.loads(decoded_json)
                except Exception as e:
                    raise ValueError(f"Failed to extract character data: {str(e)}")
            
            # Create copy of image for our use
            image_copy = img.copy()
            
            return cls(
                image=image_copy,
                original_path=path,
                embedded_data=embedded_data
            )
    
    def save_with_data(self, path: Path, character_data: Dict[str, Any]) -> None:
        """Save image with embedded character data"""
        if not self.image:
            raise ValueError("No image to save")
            
        # Encode character data
        encoded_json = base64.b64encode(
            json.dumps(character_data).encode('utf-8')
        ).decode('utf-8')
        
        # Create PNG metadata
        metadata = PngImagePlugin.PngInfo()
        
        # Preserve existing metadata except 'chara'
        if self.image.info:
            for key, value in self.image.info.items():
                if key != "chara" and isinstance(value, str):
                    metadata.add_text(key, value)
        
        # Add character data
        metadata.add_text("chara", encoded_json)
        
        # Save image with metadata
        self.image.save(path, "PNG", pnginfo=metadata)
        self.original_path = path
        self.embedded_data = character_data
    
    def extract_character_data(self) -> Optional[Dict[str, Any]]:
        """Get embedded character data"""
        return self.embedded_data