import sys
import logging
import asyncio
import aiofiles
import yaml
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from qasync import QEventLoop, asyncSlot, asyncClose

from config.app_config import AppConfig
from core.errors import ErrorHandler, ErrorCategory, ErrorLevel
from core.state.character import CharacterStateManager
from core.state.ui import UIStateManager
from core.state.config import ConfigurationManager
from core.state.metadata import MetadataManager
from core.services.file import FileService
from core.services.validation import ValidationService
from core.services.character_handler import CharacterDataHandler
from core.services.prompt import PromptManager
from core.services.generation_tracking import GenerationTrackingService
from core.services.queue import GenerationQueueManager
from core.services.dependency import DependencyManager
from core.services.versioning import VersioningService
from core.services.context_preservation import ContextPreservationService
from ui.windows.main_window import MainWindow

class CharacterGenApp:
    """Main application class"""
    
    def __init__(self):
        # Initialize Qt Application
        self.app = QApplication(sys.argv)
        
        # Create event loop
        self.loop = QEventLoop(self.app)
        asyncio.set_event_loop(self.loop)
        
        # Setup logging
        self._setup_logging()
        self.logger = logging.getLogger('CharacterGen')
        
        # Initialize core components
        self.loop.create_task(self._init_core_components())
    
        # Register cleanup
        self.app.aboutToQuit.connect(self._cleanup)

    def _setup_logging(self):
        """Initialize logging configuration"""
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('charactergen.log'),
                logging.StreamHandler()
            ]
        )

    async def _init_core_components(self):
        """Initialize all core application components"""
        try:
            # Setup config
            config_path = Path('config/app_config.yaml')
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create default config if it doesn't exist
            if not config_path.exists():
                self._create_default_config(config_path)
            
            # Load configuration
            self.config = AppConfig.load(config_path)
            
            # Create required directories
            Path(self.config.files.save_dir).mkdir(parents=True, exist_ok=True)
            Path(self.config.files.backup_dir).mkdir(parents=True, exist_ok=True)
            Path(self.config.files.temp_dir).mkdir(parents=True, exist_ok=True)
            
            # Initialize managers and services
            await self._init_managers_and_services()
            
            # Create main window
            self.main_window = MainWindow(
                character_manager=self.character_manager,
                ui_manager=self.ui_manager,
                config_manager=self.config_manager
            )
            
            # Show window
            self.main_window.show()
            
        except Exception as e:
            self.logger.critical(f"Failed to initialize core components: {str(e)}")
            raise
            
        except Exception as e:
            self.logger.critical(f"Failed to initialize core components: {str(e)}")
            raise
    
    async def _init_managers_and_services(self):
        """Initialize managers and services"""
        try:
            # Initialize error handler first
            self.error_handler = ErrorHandler()
            
            # Initialize services in correct order
            self.validation_service = ValidationService(
                error_handler=self.error_handler
            )
            
            self.file_service = FileService(
                config=self.config.files,
                error_handler=self.error_handler
            )
            
            self.prompt_manager = PromptManager(
                error_handler=self.error_handler
            )
            
            self.dependency_manager = DependencyManager(
                error_handler=self.error_handler
            )
            
            self.generation_tracking = GenerationTrackingService(
                error_handler=self.error_handler
            )
            
            self.generation_queue = GenerationQueueManager(
                prompt_manager=self.prompt_manager,
                dependency_manager=self.dependency_manager,
                error_handler=self.error_handler,
                max_concurrent=self.config.generation.max_concurrent
            )
            
            self.context_service = ContextPreservationService(
                error_handler=self.error_handler,
                storage_path=self.config.files.temp_dir / "contexts"
            )
            
            self.versioning_service = VersioningService(
                error_handler=self.error_handler
            )
            
            self.character_handler = CharacterDataHandler(
                file_service=self.file_service,
                validation_service=self.validation_service,
                error_handler=self.error_handler
            )
            
            # Initialize managers in correct order
            self.config_manager = ConfigurationManager(
                config_path=Path('config/app_config.yaml'),
                error_handler=self.error_handler
            )
            
            self.metadata_manager = MetadataManager(
                error_handler=self.error_handler
            )
            
            self.ui_manager = UIStateManager(
                error_handler=self.error_handler
            )
            
            self.character_manager = CharacterStateManager(
                validation_service=self.validation_service,
                file_service=self.file_service,
                error_handler=self.error_handler
            )
            
            # Connect manager signals
            self._connect_managers()
            
            # Initialize character manager
            await self.character_manager.initialize()
            
            # Setup auto-save timer
            self._setup_auto_save()
            
        except Exception as e:
            self.logger.error(f"Failed to initialize managers and services: {str(e)}")
            raise

    def _create_default_config(self, config_path: Path):
        """Create default configuration file"""
        default_config = {
            "api": {
                "endpoint": "http://localhost:5000",
                "api_key": None,
                "timeout": 30,
                "retry_attempts": 3,
                "batch_size": 10
            },
            "files": {
                "save_dir": "saves",
                "backup_dir": "backups",
                "temp_dir": "temp",
                "max_backups": 5,
                "auto_save_interval": 300,
                "auto_save_enabled": True
            },
            "ui": {
                "theme": "default",
                "font_size": 12,
                "auto_expand_threshold": 1000,
                "max_field_height": 600,
                "show_line_numbers": True
            },
            "generation": {
                "max_concurrent": 3,
                "timeout": 30,
                "max_retries": 3,
                "batch_size": 5,
                "preserve_history": True
            },
            "debug": {
                "enabled": False,
                "log_level": "INFO",
                "performance_logging": False
            }
        }
        
        with open(config_path, 'w') as f:
            yaml.safe_dump(default_config, f, default_flow_style=False)
            
    def _connect_managers(self):
        """Connect inter-manager signals"""
        # Character -> UI updates
        self.character_manager.state_changed.connect(
            self.ui_manager.handle_character_state_change
        )
        
        # Metadata -> Character updates
        self.metadata_manager.state_changed.connect(
            self.character_manager.handle_metadata_change
        )
        
        # Generation -> Character updates
        self.generation_queue.generation_completed.connect(
            self.character_manager.handle_generation_result
        )

    def _setup_auto_save(self):
        """Setup auto-save timer"""
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self._auto_save)
        self.auto_save_timer.start(self.config.files.auto_save_interval * 1000)

    def _auto_save(self):
        """Perform auto-save operation"""
        try:
            if self.character_manager.has_unsaved_changes():
                current_char = self.character_manager.get_current_character()
                if current_char:
                    asyncio.create_task(self.file_service.auto_save(current_char))
        except Exception as e:
            self.logger.error(f"Auto-save failed: {str(e)}")

    @asyncClose
    async def _cleanup(self):
        """Perform cleanup before application exit"""
        try:
            # Final auto-save
            if self.character_manager.has_unsaved_changes():
                current_char = self.character_manager.get_current_character()
                if current_char:
                    await self.file_service.auto_save(current_char)
            
            # Cleanup temp files
            await self.file_service.cleanup_temp_files()
            
            # Additional cleanup
            await self.context_service.cleanup()
            
        except Exception as e:
            self.logger.error(f"Cleanup failed: {str(e)}")

    def run(self):
        """Run the application"""
        try:
            with self.loop:  # This ensures proper cleanup
                return self.loop.run_forever()
        except Exception as e:
            self.logger.critical(f"Application crashed: {str(e)}")
            return 1

def main():
    """Application entry point"""
    try:
        app = CharacterGenApp()
        return app.run()
    except Exception as e:
        logging.critical(f"Failed to start application: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())