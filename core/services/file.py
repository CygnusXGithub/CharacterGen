import json
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging
import asyncio
import aiofiles

from ..errors.handler import ErrorHandler, FileOperationError, ErrorCategory, ErrorLevel
from ..models.character import CharacterData
from config.app_config import FileConfig

class FileService:
    """Service for handling all file operations"""

    def __init__(self, config: FileConfig, error_handler: ErrorHandler):
        self.config = config
        self.error_handler = error_handler
        self.logger = logging.getLogger(__name__)
        
        # Ensure directories exist
        self._ensure_directories()

    def _ensure_directories(self):
        """Create necessary directories if they don't exist"""
        try:
            self.config.save_dir.mkdir(parents=True, exist_ok=True)
            self.config.backup_dir.mkdir(parents=True, exist_ok=True)
            self.config.temp_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self.error_handler.handle_error(
                error=e,
                category=ErrorCategory.FILE,
                level=ErrorLevel.ERROR,
                context={'operation': 'create_directories'}
            )

    async def save_character(self, 
                           character: CharacterData, 
                           path: Optional[Path] = None,
                           create_backup: bool = True) -> Path:
        """Save character data to file"""
        try:
            # Determine save path
            if path is None:
                path = self._get_default_save_path(character)

            # Create backup if requested
            if create_backup and path.exists():
                await self._create_backup(path)

            # Save to temporary file first
            temp_path = self.config.temp_dir / f"temp_{datetime.now().timestamp()}.json"
            
            async with aiofiles.open(temp_path, 'w') as f:
                # Convert character data to dictionary
                data = self._character_to_dict(character)
                await f.write(json.dumps(data, indent=2))

            # Move temporary file to final location
            shutil.move(str(temp_path), str(path))
            
            self.logger.info(f"Character saved to {path}")
            return path

        except Exception as e:
            self.error_handler.handle_error(
                error=e,
                category=ErrorCategory.FILE,
                level=ErrorLevel.ERROR,
                context={'operation': 'save_character', 'path': str(path)}
            )
            raise FileOperationError(f"Failed to save character: {str(e)}")

    async def load_character(self, path: Path) -> CharacterData:
        """Load character data from file"""
        try:
            async with aiofiles.open(path, 'r') as f:
                content = await f.read()
                data = json.loads(content)
                return self._dict_to_character(data)

        except Exception as e:
            self.error_handler.handle_error(
                error=e,
                category=ErrorCategory.FILE,
                level=ErrorLevel.ERROR,
                context={'operation': 'load_character', 'path': str(path)}
            )
            raise FileOperationError(f"Failed to load character: {str(e)}")

    async def _create_backup(self, path: Path):
        """Create backup of existing file"""
        try:
            if not path.exists():
                return

            # Create backup filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.config.backup_dir / f"{path.stem}_{timestamp}{path.suffix}"
            
            # Copy file to backup location
            shutil.copy2(str(path), str(backup_path))
            
            # Clean up old backups
            await self._cleanup_old_backups(path.stem)

        except Exception as e:
            self.error_handler.handle_error(
                error=e,
                category=ErrorCategory.FILE,
                level=ErrorLevel.WARNING,
                context={'operation': 'create_backup', 'path': str(path)}
            )

    async def _cleanup_old_backups(self, character_name: str):
        """Remove old backups exceeding max_backups"""
        try:
            # Get all backups for this character
            backups = sorted(
                self.config.backup_dir.glob(f"{character_name}_*"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            
            # Remove excess backups
            for backup in backups[self.config.max_backups:]:
                backup.unlink()

        except Exception as e:
            self.error_handler.handle_error(
                error=e,
                category=ErrorCategory.FILE,
                level=ErrorLevel.WARNING,
                context={'operation': 'cleanup_backups', 'character': character_name}
            )

    def _get_default_save_path(self, character: CharacterData) -> Path:
        """Generate default save path for character"""
        # Create filename from character name
        safe_name = "".join(c for c in character.name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_name = safe_name.replace(' ', '_')
        
        return self.config.save_dir / f"{safe_name}.json"

    def _character_to_dict(self, character: CharacterData) -> Dict[str, Any]:
        """Convert character data to dictionary for saving"""
        # Use the character's built-in conversion
        return character.to_dict()

    def _dict_to_character(self, data: Dict[str, Any]) -> CharacterData:
        """Convert dictionary to character data when loading"""
        # Extract the actual character data from the template structure
        char_data = data.get('data', {})
        return CharacterData.from_dict(char_data)

    async def auto_save(self, character: CharacterData):
        """Perform auto-save operation"""
        try:
            if not self.config.auto_save_enabled:
                return

            auto_save_path = self.config.temp_dir / f"auto_save_{character.name}.json"
            await self.save_character(
                character=character,
                path=auto_save_path,
                create_backup=False
            )

        except Exception as e:
            self.error_handler.handle_error(
                error=e,
                category=ErrorCategory.FILE,
                level=ErrorLevel.WARNING,
                context={'operation': 'auto_save', 'character': character.name}
            )

    async def recover_auto_save(self, character_name: str) -> Optional[CharacterData]:
        """Attempt to recover character from auto-save"""
        try:
            auto_save_path = self.config.temp_dir / f"auto_save_{character_name}.json"
            if auto_save_path.exists():
                return await self.load_character(auto_save_path)
            return None

        except Exception as e:
            self.error_handler.handle_error(
                error=e,
                category=ErrorCategory.FILE,
                level=ErrorLevel.WARNING,
                context={'operation': 'recover_auto_save', 'character': character_name}
            )
            return None

    async def cleanup_temp_files(self):
        """Clean up temporary files"""
        try:
            # Remove files older than 1 day
            cutoff = datetime.now().timestamp() - (24 * 60 * 60)
            
            for temp_file in self.config.temp_dir.glob("*"):
                if temp_file.stat().st_mtime < cutoff:
                    temp_file.unlink()

        except Exception as e:
            self.error_handler.handle_error(
                error=e,
                category=ErrorCategory.FILE,
                level=ErrorLevel.WARNING,
                context={'operation': 'cleanup_temp_files'}
            )

    async def export_character(self, 
                             character: CharacterData, 
                             export_path: Path,
                             include_metadata: bool = True):
        """Export character to different format or location"""
        try:
            data = self._character_to_dict(character)
            
            if not include_metadata:
                # Remove metadata fields
                data.pop('metadata', None)
                data.pop('created_at', None)
                data.pop('modified_at', None)
                data.pop('id', None)

            async with aiofiles.open(export_path, 'w') as f:
                await f.write(json.dumps(data, indent=2))

        except Exception as e:
            self.error_handler.handle_error(
                error=e,
                category=ErrorCategory.FILE,
                level=ErrorLevel.ERROR,
                context={'operation': 'export_character', 'path': str(export_path)}
            )
            raise FileOperationError(f"Failed to export character: {str(e)}")

    async def import_character(self, import_path: Path) -> CharacterData:
        """Import character from external file"""
        try:
            async with aiofiles.open(import_path, 'r') as f:
                content = await f.read()
                data = json.loads(content)
                
                # Ensure required fields exist
                if 'name' not in data:
                    raise ValueError("Invalid character file: missing name field")
                
                # Add missing fields with defaults
                data.setdefault('description', '')
                data.setdefault('fields', {})
                data.setdefault('metadata', {})
                data.setdefault('created_at', datetime.now().isoformat())
                data.setdefault('modified_at', datetime.now().isoformat())
                
                return self._dict_to_character(data)

        except Exception as e:
            self.error_handler.handle_error(
                error=e,
                category=ErrorCategory.FILE,
                level=ErrorLevel.ERROR,
                context={'operation': 'import_character', 'path': str(import_path)}
            )
            raise FileOperationError(f"Failed to import character: {str(e)}")

    def get_recent_files(self, max_count: int = 10) -> List[Path]:
        """Get list of recently modified character files"""
        try:
            # Get all character files
            files = list(self.config.save_dir.glob("*.json"))
            
            # Sort by modification time
            files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            
            return files[:max_count]

        except Exception as e:
            self.error_handler.handle_error(
                error=e,
                category=ErrorCategory.FILE,
                level=ErrorLevel.WARNING,
                context={'operation': 'get_recent_files'}
            )
            return []

    def get_backup_files(self, character_name: str) -> List[Path]:
        """Get all backup files for a character"""
        try:
            backups = sorted(
                self.config.backup_dir.glob(f"{character_name}_*"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            return backups

        except Exception as e:
            self.error_handler.handle_error(
                error=e,
                category=ErrorCategory.FILE,
                level=ErrorLevel.WARNING,
                context={'operation': 'get_backup_files', 'character': character_name}
            )
            return []