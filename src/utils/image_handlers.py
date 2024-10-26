from typing import Optional, Tuple, Dict, Any
from pathlib import Path
import base64
import json
from io import BytesIO
from PIL import Image
from PIL.PngImagePlugin import PngInfo

from ..core.exceptions import FileError
from ..core.models import CharacterData

class ImageProcessor:
    """Handles image processing operations"""
    
    @staticmethod
    def resize_image(image: Image.Image, 
                max_size: Tuple[int, int] = (800, 800)) -> Image.Image:
        """Resize image while maintaining aspect ratio"""
        if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
            image.thumbnail(max_size, Image.Resampling.LANCZOS)
        return image
    
    @staticmethod
    def convert_to_png(image: Image.Image) -> Image.Image:
        """Convert image to PNG format"""
        if image.format != 'PNG':
            # Create new image with alpha channel
            png_image = Image.new('RGBA', image.size, (255, 255, 255, 0))
            if image.mode == 'RGBA':
                png_image.paste(image, mask=image.split()[3])
            else:
                png_image.paste(image)
            return png_image
        return image
    
    @staticmethod
    def optimize_png(image: Image.Image) -> Image.Image:
        """Optimize PNG image for size"""
        output = BytesIO()
        image.save(output, format='PNG', optimize=True)
        return Image.open(output)

class CharacterCardImage:
    """Handles character card image operations"""
    
    @staticmethod
    def create_card(data: CharacterData) -> bytes:
        """Create a character card PNG with embedded data"""
        # Use character's image or create default
        if data.image_data:
            image = ImageProcessor.convert_to_png(data.image_data)
            image = ImageProcessor.resize_image(image)
        else:
            # Create default blank image
            image = Image.new('RGBA', (400, 600), (255, 255, 255, 0))
        
        # Optimize the image
        image = ImageProcessor.optimize_png(image)
        
        # Create PNG metadata
        metadata = PngInfo()
        encoded_json = base64.b64encode(
            json.dumps(data.to_dict()).encode('utf-8')
        ).decode('utf-8')
        metadata.add_text("chara", encoded_json)
        
        # Save with metadata
        output = BytesIO()
        image.save(output, format='PNG', pnginfo=metadata)
        return output.getvalue()
    
    @staticmethod
    def extract_data(png_path: Path) -> Tuple[Dict[str, Any], Optional[Image.Image]]:
        """Extract character data and image from PNG file"""
        try:
            with Image.open(png_path) as im:
                im.load()  # Load image data
                
                if 'chara' not in im.info:
                    raise FileError(f"No character data found in {png_path}")
                
                # Decode character data
                encoded_json = im.info['chara']
                decoded_json = base64.b64decode(encoded_json).decode('utf-8')
                chara_data = json.loads(decoded_json)
                
                # Make a copy of the image
                image_copy = im.copy()
                
                return chara_data, image_copy
                
        except Exception as e:
            raise FileError(f"Failed to extract character data: {str(e)}")

class ImageValidator:
    """Validates image files"""
    
    @staticmethod
    def validate_image(file_path: Path) -> bool:
        """Validate image file"""
        try:
            with Image.open(file_path) as im:
                im.verify()
            return True
        except Exception:
            return False
    
    @staticmethod
    def validate_character_card(file_path: Path) -> bool:
        """Validate character card PNG"""
        try:
            with Image.open(file_path) as im:
                return 'chara' in im.info
        except Exception:
            return False

class ImageConverter:
    """Converts between image formats"""
    
    @staticmethod
    def to_base64(image: Image.Image, format: str = 'PNG') -> str:
        """Convert image to base64 string"""
        buffered = BytesIO()
        image.save(buffered, format=format)
        return base64.b64encode(buffered.getvalue()).decode()
    
    @staticmethod
    def from_base64(base64_string: str) -> Image.Image:
        """Create image from base64 string"""
        try:
            image_data = base64.b64decode(base64_string)
            return Image.open(BytesIO(image_data))
        except Exception as e:
            raise FileError(f"Error decoding base64 image: {str(e)}")

class ImageCache:
    """Caches processed images"""
    
    def __init__(self, cache_dir: Path, max_size: int = 50):
        self.cache_dir = cache_dir
        self.max_size = max_size
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def get(self, key: str) -> Optional[Image.Image]:
        """Get image from cache"""
        cache_path = self.cache_dir / f"{key}.png"
        if cache_path.exists():
            try:
                return Image.open(cache_path)
            except Exception:
                cache_path.unlink()
        return None
    
    def put(self, key: str, image: Image.Image) -> None:
        """Add image to cache"""
        # Clean cache if necessary
        self._cleanup_cache()
        
        # Save image to cache
        cache_path = self.cache_dir / f"{key}.png"
        try:
            image.save(cache_path, format='PNG')
        except Exception as e:
            raise FileError(f"Error caching image: {str(e)}")
    
    def _cleanup_cache(self) -> None:
        """Clean up old cache entries"""
        cache_files = sorted(
            self.cache_dir.glob('*.png'),
            key=lambda x: x.stat().st_mtime
        )
        
        while len(cache_files) >= self.max_size:
            try:
                cache_files.pop(0).unlink()
            except Exception:
                continue
