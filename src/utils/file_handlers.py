from typing import Dict, Any, Optional, List
from pathlib import Path
import json
import yaml
import shutil
from datetime import datetime

from ..core.exceptions import FileError
from ..core.config import PathConfig

class JsonHandler:
    """Handles JSON file operations with error handling"""
    
    @staticmethod
    def load(file_path: Path) -> Dict[str, Any]:
        """Load data from JSON file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise FileError(f"Invalid JSON in {file_path}: {str(e)}")
        except Exception as e:
            raise FileError(f"Error loading {file_path}: {str(e)}")
    
    @staticmethod
    def save(data: Dict[str, Any], file_path: Path, pretty: bool = True) -> None:
        """Save data to JSON file"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                if pretty:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                else:
                    json.dump(data, f, ensure_ascii=False)
        except Exception as e:
            raise FileError(f"Error saving to {file_path}: {str(e)}")

class YamlHandler:
    """Handles YAML file operations with error handling"""
    
    @staticmethod
    def load(file_path: Path) -> Dict[str, Any]:
        """Load data from YAML file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise FileError(f"Invalid YAML in {file_path}: {str(e)}")
        except Exception as e:
            raise FileError(f"Error loading {file_path}: {str(e)}")
    
    @staticmethod
    def save(data: Dict[str, Any], file_path: Path) -> None:
        """Save data to YAML file"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.safe_dump(data, f, default_flow_style=False)
        except Exception as e:
            raise FileError(f"Error saving to {file_path}: {str(e)}")

class BackupManager:
    """Manages file backups"""
    
    def __init__(self, backup_dir: Path):
        self.backup_dir = backup_dir
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def create_backup(self, file_path: Path) -> Path:
        """Create a backup of a file"""
        if not file_path.exists():
            raise FileError(f"File does not exist: {file_path}")
        
        try:
            # Create timestamp-based backup name
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{file_path.stem}_{timestamp}{file_path.suffix}"
            backup_path = self.backup_dir / backup_name
            
            # Copy file to backup location
            shutil.copy2(file_path, backup_path)
            
            # Clean up old backups
            self._cleanup_old_backups(file_path.stem)
            
            return backup_path
            
        except Exception as e:
            raise FileError(f"Error creating backup: {str(e)}")
    
    def restore_backup(self, backup_path: Path, target_path: Path) -> None:
        """Restore a file from backup"""
        try:
            if not backup_path.exists():
                raise FileError(f"Backup file not found: {backup_path}")
            
            shutil.copy2(backup_path, target_path)
            
        except Exception as e:
            raise FileError(f"Error restoring backup: {str(e)}")
    
    def list_backups(self, file_stem: str) -> List[Path]:
        """List available backups for a file"""
        try:
            return sorted(
                [f for f in self.backup_dir.glob(f"{file_stem}_*")],
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )
        except Exception as e:
            raise FileError(f"Error listing backups: {str(e)}")
    
    def _cleanup_old_backups(self, file_stem: str, keep: int = 5) -> None:
        """Clean up old backups, keeping only the most recent ones"""
        backups = self.list_backups(file_stem)
        for backup in backups[keep:]:
            try:
                backup.unlink()
            except Exception:
                continue

class FileWatcher:
    """Watches for file changes"""
    
    def __init__(self):
        self._watched_files: Dict[Path, float] = {}
    
    def add_file(self, file_path: Path) -> None:
        """Add a file to watch"""
        if file_path.exists():
            self._watched_files[file_path] = file_path.stat().st_mtime
    
    def remove_file(self, file_path: Path) -> None:
        """Remove a file from watching"""
        self._watched_files.pop(file_path, None)
    
    def check_changes(self) -> List[Path]:
        """Check for changed files"""
        changed_files = []
        
        for file_path, last_modified in list(self._watched_files.items()):
            try:
                if file_path.exists():
                    current_mtime = file_path.stat().st_mtime
                    if current_mtime > last_modified:
                        changed_files.append(file_path)
                        self._watched_files[file_path] = current_mtime
                else:
                    # File was deleted
                    changed_files.append(file_path)
                    self._watched_files.pop(file_path)
            except Exception:
                continue
        
        return changed_files

class DirectoryManager:
    """Manages directory operations"""
    
    def __init__(self, config: PathConfig):
        self.config = config
        self._ensure_directories()
    
    def _ensure_directories(self) -> None:
        """Ensure all required directories exist"""
        required_dirs = [
            self.config.characters_dir,
            self.config.base_prompts_dir,
            self.config.config_dir
        ]
        
        for directory in required_dirs:
            directory.mkdir(parents=True, exist_ok=True)
    
    def get_unique_filename(self, directory: Path, base_name: str, 
                          extension: str) -> Path:
        """Get a unique filename in the specified directory"""
        counter = 1
        file_path = directory / f"{base_name}{extension}"
        
        while file_path.exists():
            file_path = directory / f"{base_name}_{counter}{extension}"
            counter += 1
        
        return file_path
    
    def cleanup_temp_files(self, directory: Path, pattern: str = "*") -> None:
        """Clean up temporary files in a directory"""
        try:
            for file_path in directory.glob(pattern):
                if file_path.is_file():
                    try:
                        file_path.unlink()
                    except Exception:
                        continue
        except Exception as e:
            raise FileError(f"Error cleaning up temp files: {str(e)}")
