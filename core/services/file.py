# core/services/file.py
"""Service for handling all file operations."""
from dataclasses import dataclass, field
import json
import shutil
from pathlib import Path
from typing import Optional, List
from datetime import datetime
import logging
import asyncio
import aiofiles

from ..common.types import (
    BaseModel, JsonDict, Result,
    PathLike, Timestamp
)
from ..errors import (
    ErrorHandler, FileOperationError,
    ErrorCategory, ErrorLevel
)
from config.app_config import FileConfig
from ..models.character import CharacterData

@dataclass
class FileOperationContext(BaseModel):
    """Context for file operations."""
    operation: str
    path: PathLike
    create_backup: bool = True
    allow_overwrite: bool = False
    metadata: JsonDict = field(default_factory=dict)

class FileService:
    """Service for handling all file operations."""

    def __init__(self, config: FileConfig, error_handler: ErrorHandler):
        self.config = config
        self.error_handler = error_handler
        self.logger = logging.getLogger(__name__)
        self._file_lock = asyncio.Lock()
        
        # Initial directory setup
        self._setup_directories()
    
    def _setup_directories(self) -> Result:
        """Setup required directories."""
        try:
            dirs = [
                self.config.save_dir,
                self.config.backup_dir,
                self.config.temp_dir
            ]
            
            for directory in dirs:
                result = self.ensure_directory(directory)
                if not result.success:
                    return result
                    
            return Result(True, "Directory setup completed successfully")
            
        except Exception as e:
            self.error_handler.handle_error(
                e,
                ErrorCategory.FILE,
                ErrorLevel.ERROR,
                {'operation': 'directory_setup'}
            )
            return Result(False, f"Directory setup failed: {str(e)}", error=e)

    def ensure_directory(self, path: PathLike) -> Result:
        """Ensure directory exists."""
        try:
            Path(path).mkdir(parents=True, exist_ok=True)
            return Result(True, f"Directory ensured: {path}")
        except Exception as e:
            self.error_handler.handle_error(
                e,
                ErrorCategory.FILE,
                ErrorLevel.ERROR,
                {'operation': 'ensure_directory', 'path': str(path)}
            )
            return Result(False, f"Failed to create directory: {str(e)}", error=e)

    async def save_character(self,
                           character: CharacterData,
                           path: Optional[PathLike] = None,
                           create_backup: bool = True) -> Result[Path]:
        """Save character data to file."""
        try:
            # Determine save path
            if path is None:
                path = self._get_default_save_path(character)
            path = Path(path)
            
            context = FileOperationContext(
                operation='save_character',
                path=path,
                create_backup=create_backup
            )

            async with self._file_lock:
                # Create backup if requested
                if create_backup and path.exists():
                    backup_result = await self._create_backup(path)
                    if not backup_result.success:
                        return backup_result

                # Save to temporary file first
                temp_path = self.config.temp_dir / f"temp_{datetime.now().timestamp()}.json"
                
                try:
                    # Convert character data to dictionary
                    data = character.to_dict()
                    
                    async with aiofiles.open(temp_path, 'w', encoding='utf-8') as f:
                        await f.write(json.dumps(data, indent=2))

                    # Move temporary file to final location
                    shutil.move(str(temp_path), str(path))
                    
                    self.logger.info(f"Character saved to {path}")
                    return Result(True, "Character saved successfully", path)
                    
                finally:
                    # Cleanup temp file if it exists
                    if temp_path.exists():
                        temp_path.unlink()

        except Exception as e:
            self.error_handler.handle_error(
                e,
                ErrorCategory.FILE,
                ErrorLevel.ERROR,
                {'operation': 'save_character', 'path': str(path)}
            )
            return Result(False, f"Failed to save character: {str(e)}", error=e)

    async def load_character(self, path: PathLike) -> Result[CharacterData]:
        """Load character data from file."""
        try:
            path = Path(path)
            if not path.exists():
                return Result(False, f"File not found: {path}")

            async with self._file_lock:
                async with aiofiles.open(path, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    data = json.loads(content)
                    character = CharacterData.from_dict(data)
                    return Result(True, "Character loaded successfully", character)

        except Exception as e:
            self.error_handler.handle_error(
                e,
                ErrorCategory.FILE,
                ErrorLevel.ERROR,
                {'operation': 'load_character', 'path': str(path)}
            )
            return Result(False, f"Failed to load character: {str(e)}", error=e)

    async def _create_backup(self, path: PathLike) -> Result:
        """Create backup of existing file."""
        try:
            path = Path(path)
            if not path.exists():
                return Result(True, "No file to backup")

            # Create backup filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.config.backup_dir / f"{path.stem}_{timestamp}{path.suffix}"
            
            # Copy file to backup location
            shutil.copy2(str(path), str(backup_path))
            
            # Clean up old backups
            await self._cleanup_old_backups(path.stem)
            
            return Result(True, f"Backup created: {backup_path}", backup_path)

        except Exception as e:
            self.error_handler.handle_error(
                e,
                ErrorCategory.FILE,
                ErrorLevel.WARNING,
                {'operation': 'create_backup', 'path': str(path)}
            )
            return Result(False, f"Failed to create backup: {str(e)}", error=e)

    async def _cleanup_old_backups(self, character_name: str) -> Result:
        """Remove old backups exceeding max_backups."""
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
            
            return Result(True, "Old backups cleaned up successfully")

        except Exception as e:
            self.error_handler.handle_error(
                e,
                ErrorCategory.FILE,
                ErrorLevel.WARNING,
                {'operation': 'cleanup_backups', 'character': character_name}
            )
            return Result(False, f"Failed to cleanup backups: {str(e)}", error=e)

    async def auto_save(self, character: CharacterData) -> Result:
        """Perform auto-save operation."""
        try:
            if not self.config.auto_save_enabled:
                return Result(True, "Auto-save is disabled")

            auto_save_path = self.config.temp_dir / f"auto_save_{character.name}.json"
            return await self.save_character(
                character=character,
                path=auto_save_path,
                create_backup=False
            )

        except Exception as e:
            self.error_handler.handle_error(
                e,
                ErrorCategory.FILE,
                ErrorLevel.WARNING,
                {'operation': 'auto_save', 'character': character.name}
            )
            return Result(False, f"Auto-save failed: {str(e)}", error=e)

    def _get_default_save_path(self, character: CharacterData) -> Path:
        """Generate default save path for character."""
        safe_name = "".join(c for c in character.name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_name = safe_name.replace(' ', '_')
        return self.config.save_dir / f"{safe_name}.json"

    async def get_recent_files(self, max_count: int = 10) -> Result[List[Path]]:
        """Get list of recently modified character files."""
        try:
            files = list(self.config.save_dir.glob("*.json"))
            files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            return Result(True, "Recent files retrieved", files[:max_count])

        except Exception as e:
            self.error_handler.handle_error(
                e,
                ErrorCategory.FILE,
                ErrorLevel.WARNING,
                {'operation': 'get_recent_files'}
            )
            return Result(False, f"Failed to get recent files: {str(e)}", error=e)

    async def cleanup_temp_files(self) -> Result:
        """Clean up temporary files."""
        try:
            cutoff = datetime.now().timestamp() - (24 * 60 * 60)  # 24 hours
            
            for temp_file in self.config.temp_dir.glob("*"):
                if temp_file.stat().st_mtime < cutoff:
                    temp_file.unlink()
            
            return Result(True, "Temporary files cleaned up successfully")

        except Exception as e:
            self.error_handler.handle_error(
                e,
                ErrorCategory.FILE,
                ErrorLevel.WARNING,
                {'operation': 'cleanup_temp_files'}
            )
            return Result(False, f"Failed to cleanup temp files: {str(e)}", error=e)