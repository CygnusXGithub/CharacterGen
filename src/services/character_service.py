from typing import Dict, List, Optional, Union
from pathlib import Path
import json
import base64
from datetime import datetime
from PIL import Image
from PIL.PngImagePlugin import PngInfo
from PIL.ImageQt import ImageQt
from io import BytesIO

from ..core.models import CharacterData
from ..core.enums import CardFormat, SaveMode
from ..core.exceptions import CharacterLoadError, CharacterSaveError
from ..core.config import PathConfig

class CharacterService:
    """Manages character data operations"""
    
    def __init__(self, path_config: PathConfig):
        self.path_config = path_config
        self._ensure_directories()
        self._image_cache: Dict[str, Image.Image] = {}
    
    def _ensure_directories(self) -> None:
        """Ensure required directories exist"""
        self.path_config.characters_dir.mkdir(parents=True, exist_ok=True)
    
    def load(self, identifier: Union[str, Path]) -> CharacterData:
        """Load character data from file"""
        # Handle path conversion
        if isinstance(identifier, str):
            file_path = Path(identifier)
        else:
            file_path = identifier
            
        try:
            # Handle absolute paths vs names
            if file_path.is_absolute():
                if not file_path.exists():
                    raise CharacterLoadError(f"File not found: {file_path}")
            else:
                # Try exact path first
                if not file_path.exists():
                    # Try with extensions
                    json_path = self.path_config.characters_dir / f"{file_path.stem}.json"
                    png_path = self.path_config.characters_dir / f"{file_path.stem}.png"
                    
                    if json_path.exists():
                        file_path = json_path
                    elif png_path.exists():
                        file_path = png_path
                    else:
                        raise CharacterLoadError(f"Character not found: {identifier}")
            
            # Load based on format
            if file_path.suffix.lower() == '.json':
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                character = CharacterData.from_dict(data)
            else:  # PNG
                data, image = self._extract_png_data(file_path)
                character = CharacterData.from_dict(data)
                character.image_data = image
                self._cache_image(character.name, image)
            
            return character
                
        except Exception as e:
            raise CharacterLoadError(f"Failed to load character: {str(e)}")
    
    def _extract_png_data(self, png_path: Path) -> tuple[dict, Optional[Image.Image]]:
        """Extract character data and image from PNG file"""
        try:
            with Image.open(png_path) as im:
                im.load()  # Load image data
                
                if 'chara' not in im.info:
                    raise CharacterLoadError(f"No character data found in {png_path}")
                
                # Decode character data
                encoded_json = im.info['chara']
                decoded_json = base64.b64decode(encoded_json).decode('utf-8')
                chara_data = json.loads(decoded_json)
                
                # Make a copy of the image
                image_copy = im.copy()
                
                return chara_data, image_copy
                
        except Exception as e:
            raise CharacterLoadError(f"Failed to extract character data: {str(e)}")
    
    def save(self, data: CharacterData, 
            format: CardFormat = CardFormat.JSON,
            mode: SaveMode = SaveMode.OVERWRITE) -> Path:
        """Save character data to file"""
        try:
            # Update modification time
            data.modified_at = datetime.now()
            
            # Determine file path
            base_name = data.name
            if mode == SaveMode.VERSIONED:
                base_name = f"{data.name}_v{data.version}"
            
            file_path = self.path_config.characters_dir / base_name
            
            # Save based on format
            if format == CardFormat.JSON:
                file_path = file_path.with_suffix('.json')
                char_data = data.to_dict()
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(char_data, f, indent=2, ensure_ascii=False)
            else:
                file_path = file_path.with_suffix('.png')
                png_data = self._create_png_card(data)
                with open(file_path, 'wb') as f:
                    f.write(png_data)
            
            return file_path
            
        except Exception as e:
            raise CharacterSaveError(f"Failed to save character: {str(e)}")
    
    def _create_png_card(self, data: CharacterData) -> bytes:
        """Create a character card PNG with embedded data"""
        try:
            # Get or create image
            if data.image_data:
                image = data.image_data
            else:
                # Create default image
                image = Image.new('RGBA', (400, 600), (255, 255, 255, 0))
            
            # Ensure image is in PNG format
            if image.format != 'PNG':
                # Create new image with alpha channel
                png_image = Image.new('RGBA', image.size, (255, 255, 255, 0))
                if image.mode == 'RGBA':
                    png_image.paste(image, mask=image.split()[3])
                else:
                    png_image.paste(image)
                image = png_image
            
            # Create PNG metadata
            metadata = PngInfo()
            encoded_json = base64.b64encode(
                json.dumps(data.to_dict()).encode('utf-8')
            ).decode('utf-8')
            metadata.add_text("chara", encoded_json)
            
            # Save to bytes
            output = BytesIO()
            image.save(output, format='PNG', pnginfo=metadata, optimize=True)
            return output.getvalue()
            
        except Exception as e:
            raise CharacterSaveError(f"Failed to create PNG card: {str(e)}")
    
    def export_character(self, data: CharacterData,
                        format: CardFormat,
                        output_dir: Path) -> Path:
        """Export character to specified directory"""
        try:
            # Ensure output directory exists
            if not output_dir.exists():
                output_dir.mkdir(parents=True)
            
            # Create export path
            file_name = f"{data.name}_v{data.version}"
            file_path = output_dir / file_name
            
            if format == CardFormat.JSON:
                file_path = file_path.with_suffix('.json')
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data.to_dict(), f, indent=2, ensure_ascii=False)
            else:
                file_path = file_path.with_suffix('.png')
                png_data = self._create_png_card(data)
                with open(file_path, 'wb') as f:
                    f.write(png_data)
            
            return file_path
            
        except Exception as e:
            raise CharacterSaveError(f"Failed to export character: {str(e)}")
    
    def _cache_image(self, key: str, image: Image.Image):
        """Cache image for reuse"""
        self._image_cache[key] = image
        
        # Limit cache size
        if len(self._image_cache) > 10:
            self._image_cache.pop(next(iter(self._image_cache)))
    
    def get_cached_image(self, key: str) -> Optional[Image.Image]:
        """Get image from cache"""
        return self._image_cache.get(key)
    
    def create_character(self, name: str) -> CharacterData:
        """Create a new character instance"""
        return CharacterData(
            name=name,
            created_at=datetime.now(),
            modified_at=datetime.now()
        )
    
    def validate_character(self, data: CharacterData) -> List[str]:
        """Validate character data and return any warnings"""
        warnings = []
        
        # Check required fields
        if not data.name:
            warnings.append("Character name is missing")
            
        # Check field content
        for field_name, content in data.fields.items():
            if not content:
                warnings.append(f"Field '{field_name}' is empty")
        
        # Validate image
        if data.image_data:
            if data.image_data.size[0] > 800 or data.image_data.height > 800:
                warnings.append("Image dimensions exceed recommended size (800x800)")
        
        return warnings