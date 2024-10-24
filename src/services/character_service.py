from typing import Dict, List, Optional, Tuple
from pathlib import Path
import json
import shutil
from datetime import datetime
from PIL import Image
from PIL.PngImagePlugin import PngInfo
import base64
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
        
    def _ensure_directories(self) -> None:
        """Ensure required directories exist"""
        self.path_config.characters_dir.mkdir(parents=True, exist_ok=True)
    
    def _create_png_card(self, data: CharacterData, image: Optional[Image.Image] = None) -> bytes:
        """Create a character card PNG with embedded data"""
        if image is None:
            # Create a default image if none provided
            image = Image.new('RGBA', (400, 600), (255, 255, 255, 0))
        
        # Convert image to PNG format
        output = BytesIO()
        
        # Create PNG metadata
        metadata = PngInfo()
        encoded_json = base64.b64encode(
            json.dumps(data.to_dict()).encode('utf-8')
        ).decode('utf-8')
        metadata.add_text("chara", encoded_json)
        
        # Save with metadata
        image.save(output, format='PNG', pnginfo=metadata)
        return output.getvalue()
    
    def _extract_png_data(self, png_path: Path) -> Tuple[dict, Optional[Image.Image]]:
        """Extract character data and image from PNG file"""
        try:
            with Image.open(png_path) as im:
                im.load()
                if 'chara' not in im.info:
                    raise CharacterLoadError(f"Character data not found in {png_path}")
                
                # Decode character data
                encoded_json = im.info['chara']
                decoded_json = base64.b64decode(encoded_json).decode('utf-8')
                chara_data = json.loads(decoded_json)
                
                # Make a copy of the image
                image_copy = im.copy()
                
                return chara_data, image_copy
                
        except Exception as e:
            raise CharacterLoadError(f"Failed to extract character data: {str(e)}")
    
    def load(self, identifier: str) -> CharacterData:
        """Load character data from file"""
        # Handle full paths vs just names
        if Path(identifier).is_absolute():
            file_path = Path(identifier)
            # Copy to characters directory if not already there
            if file_path.parent != self.path_config.characters_dir:
                shutil.copy2(file_path, self.path_config.characters_dir)
        else:
            # Try exact path first
            file_path = self.path_config.characters_dir / identifier
            if not file_path.exists():
                # Try with extensions
                json_path = file_path.with_suffix('.json')
                png_path = file_path.with_suffix('.png')
                
                if json_path.exists():
                    file_path = json_path
                elif png_path.exists():
                    file_path = png_path
                else:
                    raise CharacterLoadError(f"Character file not found: {identifier}")
        
        try:
            if file_path.suffix.lower() == '.json':
                with open(file_path, 'r') as f:
                    data = json.load(f)
                return CharacterData.from_dict(data)
            else:
                data, image = self._extract_png_data(file_path)
                char_data = CharacterData.from_dict(data)
                char_data.image_data = image
                return char_data
                
        except Exception as e:
            raise CharacterLoadError(f"Failed to load character: {str(e)}")
    
    def save(self, data: CharacterData, 
            format: CardFormat = CardFormat.JSON,
            mode: SaveMode = SaveMode.OVERWRITE) -> Path:
        """Save character data to file"""
        # Update modification time
        data.modified_at = datetime.now()
        
        # Determine file path
        base_name = data.name
        if mode == SaveMode.VERSIONED:
            base_name = f"{data.name}_v{data.version}"
            
        file_path = self.path_config.characters_dir / base_name
        
        try:
            if format == CardFormat.JSON:
                file_path = file_path.with_suffix('.json')
                with open(file_path, 'w') as f:
                    json.dump(data.to_dict(), f, indent=2)
            else:
                file_path = file_path.with_suffix('.png')
                png_data = self._create_png_card(data, data.image_data)
                with open(file_path, 'wb') as f:
                    f.write(png_data)
            
            return file_path
            
        except Exception as e:
            raise CharacterSaveError(f"Failed to save character: {str(e)}")
    
    def list_characters(self) -> List[str]:
        """Get list of available character files"""
        files = set()
        valid_extensions = {'.json', '.png'}
        
        try:
            for file_path in self.path_config.characters_dir.iterdir():
                if file_path.suffix.lower() in valid_extensions:
                    # For PNGs, verify they contain character data
                    if file_path.suffix.lower() == '.png':
                        try:
                            with Image.open(file_path) as im:
                                if 'chara' in im.info:
                                    files.add(file_path.stem)
                        except Exception:
                            continue
                    else:
                        files.add(file_path.stem)
                        
            return sorted(list(files))
            
        except Exception as e:
            raise CharacterLoadError(f"Error scanning character directory: {str(e)}")
    
    def create_character(self, name: str) -> CharacterData:
        """Create a new character instance"""
        return CharacterData(
            name=name,
            created_at=datetime.now(),
            modified_at=datetime.now()
        )
    
    def delete_character(self, identifier: str) -> None:
        """Delete a character file"""
        try:
            base_path = self.path_config.characters_dir / identifier
            # Try both extensions
            for ext in ['.json', '.png']:
                file_path = base_path.with_suffix(ext)
                if file_path.exists():
                    file_path.unlink()
                    
        except Exception as e:
            raise CharacterSaveError(f"Failed to delete character: {str(e)}")
    
    def export_character(self, data: CharacterData, 
                        format: CardFormat,
                        output_dir: Path) -> Path:
        """Export character to specified directory"""
        try:
            if not output_dir.exists():
                output_dir.mkdir(parents=True)
            
            file_name = f"{data.name}_v{data.version}"
            file_path = output_dir / file_name
            
            if format == CardFormat.JSON:
                file_path = file_path.with_suffix('.json')
                with open(file_path, 'w') as f:
                    json.dump(data.to_dict(), f, indent=2)
            else:
                file_path = file_path.with_suffix('.png')
                png_data = self._create_png_card(data, data.image_data)
                with open(file_path, 'wb') as f:
                    f.write(png_data)
            
            return file_path
            
        except Exception as e:
            raise CharacterSaveError(f"Failed to export character: {str(e)}")
