import sys
import asyncio
import logging
from pathlib import Path
from datetime import datetime

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from qasync import QEventLoop

from config.app_config import AppConfig
from core.errors import ErrorHandler
from core.services import (
    ValidationService, FileService, PromptManager,
    DependencyManager, GenerationTrackingService,
    GenerationQueueManager, ContextPreservationService,
    VersioningService
)
from core.state import (
    CharacterStateManager, UIStateManager,
    ConfigurationManager, MetadataManager
)
from ui.windows.main_window import MainWindow

class ApplicationManager:
    """Manages core application lifecycle and components"""

    def __init__(self):
        # Setup logging first
        self._setup_logging()
        self.logger = logging.getLogger('CharacterGen')
        
        # Core components initialization
        self.error_handler = ErrorHandler()
        self.services = {}
        self.managers = {}
        self.config = None
        
        # Initialize Qt Application
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.loop = QEventLoop(self.app)
        asyncio.set_event_loop(self.loop)

    def _setup_logging(self):
        """Initialize logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('charactergen.log'),
                logging.StreamHandler()
            ]
        )

    async def initialize(self):
        """Initialize application components"""
        try:
            self.logger.info("Starting initialization...")
            
            # Load configuration
            config_path = Path('config/app_config.yaml')
            config_path.parent.mkdir(parents=True, exist_ok=True)
            self.config = await self._load_config(config_path)
            self.logger.info("Configuration loaded")

            # Initialize services
            await self._init_services()
            self.logger.info("Services initialized")
            
            # Initialize state managers
            await self._init_managers()
            self.logger.info("Managers initialized")
            
            # Initialize UI
            await self._init_ui()
            self.logger.info("UI initialized")
            
            return True
            
        except Exception as e:
            self.logger.critical(f"Failed to initialize application: {str(e)}", exc_info=True)
            return False

    async def _load_config(self, config_path: Path) -> AppConfig:
        """Load application configuration"""
        if not config_path.exists():
            self.logger.info("Config file not found, creating default configuration")
            config = AppConfig.create_default()
            config.save(config_path)
        else:
            config = AppConfig.load(config_path)
        return config

    async def _init_services(self):
        """Initialize application services"""
        # Core services
        self.services['validation'] = ValidationService(self.error_handler)
        self.services['file'] = FileService(self.config.files, self.error_handler)
        self.services['prompt'] = PromptManager(self.error_handler)
        self.services['dependency'] = DependencyManager(self.error_handler)
        
        # Context and tracking services
        self.services['context'] = ContextPreservationService(
            self.error_handler,
            self.config.files.temp_dir / "contexts"
        )
        self.services['generation_tracking'] = GenerationTrackingService(
            self.error_handler,
            max_concurrent=self.config.generation.max_concurrent
        )
        
        # Queue management
        self.services['queue'] = GenerationQueueManager(
            self.services['prompt'],
            self.services['dependency'],
            self.error_handler
        )
        
        # Version control
        self.services['versioning'] = VersioningService(self.error_handler)

    async def _init_managers(self):
        """Initialize state managers"""
        # Create UI manager first
        self.ui_manager = UIStateManager(self.error_handler)
        
        # Create metadata manager
        self.metadata_manager = MetadataManager(self.error_handler)
        
        # Create config manager
        self.config_manager = ConfigurationManager(
            Path('config/app_config.yaml'),
            self.error_handler
        )
        
        # Create character manager
        self.character_manager = CharacterStateManager(
            validation_service=self.services['validation'],
            file_service=self.services['file'],
            generation_service=self.services['generation_tracking'],
            error_handler=self.error_handler,
            metadata_manager=self.metadata_manager
        )
        
        # Store managers
        self.managers = {
            'ui': self.ui_manager,
            'character': self.character_manager,
            'config': self.config_manager,
            'metadata': self.metadata_manager
        }

    async def _init_ui(self):
        """Initialize UI"""
        try:
            # Create main window
            self.main_window = MainWindow(
                character_manager=self.character_manager,
                ui_manager=self.ui_manager,
                config_manager=self.config_manager
            )
            
            # Show window
            self.main_window.show()
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize UI: {str(e)}")
            return False

    async def cleanup(self):
        """Perform cleanup before shutdown"""
        try:
            # Cleanup temp files
            await self.services['file'].cleanup_temp_files()
            await self.services['context'].cleanup()
            
        except Exception as e:
            self.logger.error(f"Cleanup failed: {str(e)}")

    def run(self):
        """Run the application"""
        try:
            # Initialize
            self.loop.run_until_complete(self.initialize())
            
            # Run event loop
            with self.loop:
                return self.loop.run_forever()
                
        except Exception as e:
            self.logger.critical(f"Application crashed: {str(e)}")
            return 1
        finally:
            # Ensure cleanup runs
            self.loop.run_until_complete(self.cleanup())

def main():
    """Application entry point"""
    app_manager = ApplicationManager()
    return app_manager.run()

if __name__ == "__main__":
    sys.exit(main())