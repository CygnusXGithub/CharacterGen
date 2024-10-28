#!/usr/bin/env python3
import sys
import logging
import json
import os
from pathlib import Path
from datetime import datetime
from PyQt6.QtWidgets import QApplication, QMessageBox, QSplashScreen
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt

from src.core.config import AppConfig, get_config
from src.core.enums import StatusLevel, EventType
from src.core.managers import (
    CharacterStateManager,
    GenerationManager,
    SettingsManager,
    UIStateManager
)

from src.services.api_service import ApiService
from src.services.character_service import CharacterService
from src.services.generation_service import GenerationService
from src.services.prompt_service import PromptService
from src.ui.main_window import MainWindow
from src.core.exceptions import ConfigError, FileError

def setup_logging(config: AppConfig) -> logging.Logger:
    """Configure application logging based on config"""
    # Create logs directory
    log_dir = config.paths.logs_dir
    log_dir.mkdir(exist_ok=True)
    
    # Set up log file with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"charactergen_{timestamp}.log"
    
    # Configure logging based on debug settings
    handlers = []
    
    if config.debug.enable_file_logging:
        handlers.append(logging.FileHandler(log_file))
    
    if config.debug.enable_console_logging:
        handlers.append(logging.StreamHandler(sys.stdout))
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, config.debug.logging_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )
    
    # Create logger for this module
    logger = logging.getLogger(__name__)
    return logger

def check_dependencies() -> bool:
    """Check if all required dependencies are available"""
    required_packages = {
        "PyQt6": "GUI framework",
        "PIL": "Image processing",
        "requests": "API communication",
        "yaml": "Configuration handling"
    }
    
    missing_packages = []
    
    for package, description in required_packages.items():
        try:
            __import__(package)
        except ImportError:
            # Map internal package names to pip install names
            pip_name = "Pillow" if package == "PIL" else "pyyaml" if package == "yaml" else package
            missing_packages.append(f"{pip_name} ({description})")
    
    if missing_packages:
        error_message = (
            "The following required packages are missing:\n\n"
            f"{chr(10).join(missing_packages)}\n\n"
            "Please install them using pip:\n"
            "pip install " + " ".join(p.split()[0] for p in missing_packages)
        )
        QMessageBox.critical(None, "Missing Dependencies", error_message)
        return False
    
    return True

def check_directories(config: AppConfig) -> bool:
    """Check and create required directories"""
    try:
        # Directories are created in PathConfig initialization
        # Just verify they exist and are writable
        required_dirs = [
            config.paths.characters_dir,
            config.paths.base_prompts_dir,
            config.paths.config_dir,
            config.paths.logs_dir
        ]
        
        for directory in required_dirs:
            if not directory.exists():
                raise FileError(f"Required directory does not exist: {directory}")
            if not os.access(directory, os.W_OK):
                raise FileError(f"Directory is not writable: {directory}")
            
        return True
        
    except Exception as e:
        QMessageBox.critical(
            None,
            "Directory Error",
            f"Error with application directories: {str(e)}"
        )
        return False

def create_splash_screen() -> QSplashScreen:
    """Create and return a splash screen"""
    # Create a basic splash screen
    pixmap = QPixmap(400, 200)
    pixmap.fill(Qt.GlobalColor.white)
    
    splash = QSplashScreen(pixmap)
    splash.show()
    return splash

def initialize_managers(config: AppConfig, logger: logging.Logger):
    """Initialize all managers and services"""
    try:
        # Initialize services first
        api_service = ApiService(config)
        character_service = CharacterService(config.paths)
        prompt_service = PromptService(config.paths)
        generation_service = GenerationService(api_service, prompt_service)
        
        # Create managers in dependency order
        settings_manager = SettingsManager()
        ui_manager = UIStateManager()
        character_manager = CharacterStateManager(character_service)
        generation_manager = GenerationManager(generation_service, character_manager)
        
        # Connect manager signals for logging
        ui_manager.status_message.connect(
            lambda msg, level: logger.log(
                logging.INFO if level == StatusLevel.INFO else logging.WARNING,
                msg
            )
        )
        
        return {
            'managers': {
                'settings_manager': settings_manager,
                'ui_manager': ui_manager,
                'character_manager': character_manager,
                'generation_manager': generation_manager
            },
            'services': {
                'api_service': api_service,
                'character_service': character_service,
                'prompt_service': prompt_service,
                'generation_service': generation_service
            }
        }
    
    except Exception as e:
        logger.error(f"Error initializing managers: {str(e)}")
        raise

def main():
    """Main application entry point"""
    # Create application instance
    app = QApplication(sys.argv)
    app.setApplicationName("Character Generator")
    app.setApplicationVersion("2.3.0")
    app.setOrganizationName("CharacterGen")
    
    try:
        # Show splash screen
        splash = create_splash_screen()
        splash.showMessage(
            "Starting Character Generator...",
            Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter
        )
        app.processEvents()
        
        # Load configuration
        splash.showMessage(
            "Loading configuration...",
            Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter
        )
        config = get_config()
        
        # Set up logging
        logger = setup_logging(config)
        logger.info("Starting Character Generator")
        
        # Perform startup checks
        checks = [
            ("Checking dependencies...", check_dependencies),
            ("Checking directories...", lambda: check_directories(config))
        ]
        
        for message, check_func in checks:
            splash.showMessage(
                message,
                Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter
            )
            app.processEvents()
            
            if not check_func():
                logger.error(f"Startup check failed: {message}")
                return 1
        
        # Initialize managers
        splash.showMessage(
            "Initializing managers...",
            Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter
        )
        app.processEvents()
        
        initialized = initialize_managers(config, logger)
        managers = initialized['managers']
        services = initialized['services']
        
        # Create and show main window
        splash.showMessage(
            "Creating main window...",
            Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter
        )
        app.processEvents()
        
        window = MainWindow(
            settings_manager=managers['settings_manager'],
            ui_manager=managers['ui_manager'],
            character_manager=managers['character_manager'],
            generation_manager=managers['generation_manager'],
            api_service=services['api_service'],
            character_service=services['character_service'],
            prompt_service=services['prompt_service'],
            generation_service=services['generation_service']
        )
        window.show()
        
        # Close splash screen
        splash.finish(window)
        
        # Start event loop
        logger.info("Application started successfully")
        return app.exec()
        
    except Exception as e:
        logger.critical(f"Unhandled exception: {str(e)}", exc_info=True)
        QMessageBox.critical(
            None,
            "Critical Error",
            f"An unexpected error occurred:\n\n{str(e)}\n\n"
            "Please check the logs for more information."
        )
        return 1

if __name__ == "__main__":
    sys.exit(main())