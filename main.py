import sys
import logging
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

from config.app_config import AppConfig
from core.errors.handler import ErrorHandler
from core.state.character import CharacterStateManager
from core.state.ui import UIStateManager
from core.state.generation import GenerationManager
from core.state.config import ConfigurationManager
from core.services.file import FileService
from core.services.validation import ValidationService
from core.services.generation_tracking import GenerationService
from ui.windows.main import MainWindow

class CharacterGenApp:
    """Main application class"""
    
    def __init__(self):
        # Initialize Qt Application
        self.app = QApplication(sys.argv)
        
        # Setup logging
        self._setup_logging()
        self.logger = logging.getLogger('CharacterGen')
        
        # Initialize core components
        self._init_core_components()
        
        # Create and show main window
        self.main_window = MainWindow(
            character_manager=self.character_manager,
            ui_manager=self.ui_manager,
            generation_manager=self.generation_manager,
            config_manager=self.config_manager
        )
        
        # Setup auto-save timer
        self._setup_auto_save()

    def _setup_logging(self):
        """Initialize logging configuration"""
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('log'),
                logging.StreamHandler()
            ]
        )

    def _init_core_components(self):
        """Initialize all core application components"""
        try:
            # Load configuration
            config_path = Path('config/app_config.yaml')
            self.config = AppConfig.load(config_path)
            
            # Initialize error handler first
            self.error_handler = ErrorHandler()
            
            # Initialize managers
            self.config_manager = ConfigurationManager(
                config=self.config,
                error_handler=self.error_handler
            )
            
            self.character_manager = CharacterStateManager(
                error_handler=self.error_handler
            )
            
            self.ui_manager = UIStateManager(
                error_handler=self.error_handler
            )
            
            self.generation_manager = GenerationManager(
                error_handler=self.error_handler
            )
            
            # Initialize services
            self.file_service = FileService(
                config=self.config.files,
                error_handler=self.error_handler
            )
            
            self.validation_service = ValidationService(
                error_handler=self.error_handler
            )
            
            self.generation_service = GenerationService(
                config=self.config.generation,
                error_handler=self.error_handler
            )
            
            # Connect manager signals
            self._connect_managers()
            
        except Exception as e:
            self.logger.critical(f"Failed to initialize core components: {str(e)}")
            raise

    def _connect_managers(self):
        """Connect inter-manager signals"""
        # Character -> UI updates
        self.character_manager.state_changed.connect(
            self.ui_manager.handle_character_state_change
        )
        
        # Generation -> UI updates
        self.generation_manager.state_changed.connect(
            self.ui_manager.handle_generation_state_change
        )
        
        # Generation -> Character updates
        self.generation_manager.generation_completed.connect(
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
                self.file_service.auto_save(
                    self.character_manager.get_current_character()
                )
        except Exception as e:
            self.logger.error(f"Auto-save failed: {str(e)}")

    def run(self):
        """Run the application"""
        try:
            self.main_window.show()
            return self.app.exec()
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