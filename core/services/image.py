# core/services/image.py
"""Service for handling character image operations."""
from typing import Optional, Dict
from pathlib import Path
import asyncio

from ..common.types import (
   BaseModel, JsonDict, Result,
   PathLike
)
from ..models.image import ImageData
from ..models.character import CharacterData
from ..errors import ErrorHandler, ErrorCategory, ErrorLevel

@dataclass
class ImageConfig(BaseModel):
   """Configuration for image handling."""
   max_width: int = 1024
   max_height: int = 1024
   allowed_formats: set[str] = field(default_factory=lambda: {'png', 'jpg', 'jpeg', 'gif'})
   max_file_size: int = 5 * 1024 * 1024  # 5MB
   enable_compression: bool = True

class ImageService:
   """Service for handling character image operations."""
   
   def __init__(self, 
                error_handler: ErrorHandler,
                config: Optional[ImageConfig] = None):
       self.error_handler = error_handler
       self.config = config or ImageConfig()
       self._image_lock = asyncio.Lock()
       self._cache: Dict[str, ImageData] = {}

   async def load_image(self, path: PathLike) -> Result[ImageData]:
       """Load and validate image from file."""
       try:
           path = Path(path)
           if not path.exists():
               return Result(False, f"Image file not found: {path}")
               
           if not self._validate_file_extension(path):
               return Result(False, "Unsupported image format")
               
           async with self._image_lock:
               # Load image using ImageData's from_file
               load_result = ImageData.from_file(path)
               if not load_result.success:
                   return load_result
               
               image_data = load_result.data
               
               # Validate image
               validation = await self._validate_image(image_data)
               if not validation.success:
                   return validation
               
               # Resize if needed
               if self.config.enable_compression:
                   resize_result = image_data.resize_if_needed()
                   if resize_result.success and resize_result.data:  # If resized
                       self.logger.info(f"Image resized: {path}")
               
               # Cache image
               cache_key = str(path)
               self._cache[cache_key] = image_data
               
               return Result(True, "Image loaded successfully", image_data)
               
       except Exception as e:
           self.error_handler.handle_error(
               e,
               ErrorCategory.FILE,
               ErrorLevel.ERROR,
               {'operation': 'load_image', 'path': str(path)}
           )
           return Result(False, f"Failed to load image: {str(e)}", error=e)

   async def save_with_character_data(self,
                                    image: ImageData,
                                    character: CharacterData,
                                    path: Optional[PathLike] = None) -> Result[Path]:
       """Save image with embedded character data."""
       try:
           if not image.image:
               return Result(False, "No image data to save")
               
           if path is None:
               path = self._get_default_path(character)
           path = Path(path)
           
           # Validate image
           validation = await self._validate_image(image)
           if not validation.success:
               return validation
           
           async with self._image_lock:
               # Convert character to embeddable format
               char_data = character.to_dict()
               
               # Save image with embedded data
               save_result = image.save_with_data(path, char_data)
               if not save_result.success:
                   return save_result
               
               # Update cache
               self._cache[str(path)] = image
               
               return Result(True, "Image saved successfully", path)
               
       except Exception as e:
           self.error_handler.handle_error(
               e,
               ErrorCategory.FILE,
               ErrorLevel.ERROR,
               {'operation': 'save_image', 'path': str(path) if path else None}
           )
           return Result(False, f"Failed to save image: {str(e)}", error=e)

   async def extract_character_data(self, image: ImageData) -> Result[JsonDict]:
       """Extract embedded character data from image."""
       try:
           if not image.image:
               return Result(False, "No image data available")
               
           data = image.extract_character_data()
           if not data:
               return Result(False, "No character data found in image")
               
           return Result(True, "Character data extracted successfully", data)
           
       except Exception as e:
           self.error_handler.handle_error(
               e,
               ErrorCategory.FILE,
               ErrorLevel.ERROR,
               {'operation': 'extract_data'}
           )
           return Result(False, f"Failed to extract character data: {str(e)}", error=e)

   async def _validate_image(self, image: ImageData) -> Result:
       """Validate image data."""
       try:
           if not image.image:
               return Result(False, "No image data to validate")
           
           # Check dimensions
           width, height = image.image.size
           if width > self.config.max_width or height > self.config.max_height:
               return Result(False, 
                   f"Image dimensions ({width}x{height}) exceed maximum allowed "
                   f"({self.config.max_width}x{self.config.max_height})")
           
           # Check file size (approximate)
           image_bytes = image.to_bytes()
           if image_bytes.success and len(image_bytes.data) > self.config.max_file_size:
               return Result(False, "Image file size exceeds maximum allowed")
           
           return Result(True, "Image validation successful")
           
       except Exception as e:
           self.error_handler.handle_error(
               e,
               ErrorCategory.VALIDATION,
               ErrorLevel.ERROR,
               {'operation': 'validate_image'}
           )
           return Result(False, f"Image validation failed: {str(e)}", error=e)

   def _validate_file_extension(self, path: Path) -> bool:
       """Check if file has allowed extension."""
       return path.suffix.lower().lstrip('.') in self.config.allowed_formats

   def _get_default_path(self, character: CharacterData) -> Path:
       """Generate default path for character image."""
       safe_name = "".join(c for c in character.name if c.isalnum() or c in (' ', '-', '_')).strip()
       safe_name = safe_name.replace(' ', '_')
       return Path(f"images/{safe_name}.png")

   def get_cached_image(self, cache_key: str) -> Optional[ImageData]:
       """Get image from cache if available."""
       return self._cache.get(cache_key)

   def clear_cache(self):
       """Clear image cache."""
       self._cache.clear()