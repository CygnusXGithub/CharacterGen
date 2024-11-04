# core/models/image.py
"""Image handling and processing for characters."""
from dataclasses import dataclass, field
from typing import Optional, Tuple, Dict, Any
from pathlib import Path
from PIL import Image, PngImagePlugin
from io import BytesIO
import base64
import json

from ..common.types import (
    BaseModel, JsonDict, Result,
    PathLike
)

@dataclass
class ImageData(BaseModel):
    """Container for character image data and embedded info."""
    image: Optional[Image.Image] = None
    original_path: Optional[Path] = None
    dimensions: Tuple[int, int] = (256, 256)
    max_dimensions: Tuple[int, int] = (1024, 1024)
    embedded_data: Optional[JsonDict] = None
    
    def validate_image(self) -> Result:
        """Validate image data and dimensions."""
        if not self.image:
            return Result(False, "No image data present")
        
        width, height = self.image.size
        if width > self.max_dimensions[0] or height > self.max_dimensions[1]:
            return Result(
                False,
                f"Image dimensions ({width}x{height}) exceed maximum allowed "
                f"({self.max_dimensions[0]}x{self.max_dimensions[1]})"
            )
        
        return Result(True, "Image validation successful")
    
    def resize_if_needed(self) -> Result:
        """Resize image if it exceeds max dimensions."""
        try:
            if not self.image:
                return Result(False, "No image to resize")
                
            width, height = self.image.size
            if width > self.max_dimensions[0] or height > self.max_dimensions[1]:
                ratio = min(
                    self.max_dimensions[0]/width,
                    self.max_dimensions[1]/height
                )
                new_size = (int(width * ratio), int(height * ratio))
                self.image = self.image.resize(new_size, Image.Resampling.LANCZOS)
                return Result(True, f"Image resized to {new_size}")
                
            return Result(True, "No resize needed")
            
        except Exception as e:
            return Result(False, f"Failed to resize image: {str(e)}", error=e)
    
    def to_bytes(self) -> Result[bytes]:
        """Convert image to bytes for storage."""
        try:
            if not self.image:
                return Result(False, "No image data to convert")
                
            buffer = BytesIO()
            self.image.save(buffer, format='PNG')
            return Result(True, "Image converted to bytes", buffer.getvalue())
            
        except Exception as e:
            return Result(False, f"Failed to convert image: {str(e)}", error=e)
    
    @classmethod
    def from_bytes(cls, data: bytes) -> Result['ImageData']:
        """Create ImageData from bytes."""
        try:
            buffer = BytesIO(data)
            image = Image.open(buffer)
            return Result(True, "Image loaded from bytes", 
                        cls(image=image.copy()))
        except Exception as e:
            return Result(False, f"Failed to load image: {str(e)}", error=e)
    
    @classmethod
    def from_file(cls, path: PathLike) -> Result['ImageData']:
        """Create ImageData from file, extracting embedded data."""
        try:
            path = Path(path)
            with Image.open(path) as img:
                img.load()
                embedded_data = None
                
                # Extract embedded character data
                if 'chara' in img.info:
                    try:
                        encoded_json = img.info['chara']
                        decoded_json = base64.b64decode(encoded_json).decode('utf-8')
                        embedded_data = json.loads(decoded_json)
                    except Exception as e:
                        return Result(False, f"Failed to extract character data: {str(e)}", error=e)
                
                instance = cls(
                    image=img.copy(),
                    original_path=path,
                    embedded_data=embedded_data
                )
                
                # Validate the loaded image
                validation = instance.validate_image()
                if not validation.success:
                    return validation
                
                return Result(True, "Image loaded successfully", instance)
                
        except Exception as e:
            return Result(False, f"Failed to load image: {str(e)}", error=e)
    
    def save_with_data(self, path: PathLike, character_data: JsonDict) -> Result:
        """Save image with embedded character data."""
        try:
            if not self.image:
                return Result(False, "No image to save")
                
            path = Path(path)
            
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
            
            return Result(True, "Image saved successfully")
            
        except Exception as e:
            return Result(False, f"Failed to save image: {str(e)}", error=e)