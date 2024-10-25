#!/usr/bin/env python3
import sys
import logging
import json
from pathlib import Path
from datetime import datetime
from PyQt6.QtWidgets import QApplication, QMessageBox, QSplashScreen
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt
from src.core.config import AppConfig, get_config
from src.ui.main_window import MainWindow
from src.core.exceptions import ConfigError, FileError

def setup_logging():
    """Configure application logging"""
    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Set up log file with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"charactergen_{timestamp}.log"
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Create logger for this module
    logger = logging.getLogger(__name__)
    return logger

def check_dependencies() -> bool:
    """Check if all required dependencies are available"""
    required_packages = {
        "PyQt6": "GUI framework",
        "PIL": "Image processing",  # Changed from "Pillow" to "PIL"
        "requests": "API communication",
        "yaml": "Configuration handling"  # Changed from "pyyaml" to "yaml"
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

def check_directories() -> bool:
    """Check and create required directories"""
    try:
        data_dir = Path("data")
        required_dirs = [
            data_dir / "characters",
            data_dir / "base_prompts",
            data_dir / "config",
            data_dir / "logs"
        ]
        
        for directory in required_dirs:
            directory.mkdir(parents=True, exist_ok=True)
            
        # Check for template.json
        template_path = data_dir / "config" / "template.json"
        if not template_path.exists():
            with open(template_path, 'w') as f:
                json.dump({
                    "data": {
                        "name": "",
                        "description": "",
                        "personality": "",
                        "first_mes": "",
                        "mes_example": "",
                        "scenario": "",
                        "creator_notes": "",
                        "system_prompt": "",
                        "post_history_instructions": "",
                        "alternate_greetings": [],
                        "tags": []
                    },
                    "spec": "chara_card_v2",
                    "spec_version": "2.0"
                }, f, indent=2)
        return True
    except Exception as e:
        QMessageBox.critical(
            None,
            "Directory Error",
            f"Error creating required directories: {str(e)}"
        )
        return False
    
def check_config() -> bool:
    """Check configuration file"""
    config_path = Path("data/config/config.yaml")
    
    if not config_path.exists():
        try:
            # Create default configuration
            default_config = {
                "API_URL": "http://127.0.0.1:5000/v1/chat/completions",
                "API_KEY": "",
                "generation": {
                    "max_tokens": 2048,
                }
            }
            
            import yaml
            with open(config_path, 'w') as f:
                yaml.safe_dump(default_config, f, default_flow_style=False)
            
            QMessageBox.information(
                None,
                "Configuration Created",
                f"Default configuration file created at {config_path}\n"
                "Please edit it with your API settings before continuing."
            )
            return False
            
        except Exception as e:
            QMessageBox.critical(
                None,
                "Configuration Error",
                f"Error creating default configuration: {str(e)}"
            )
            return False
    
    return True

def create_splash_screen() -> QSplashScreen:
    """Create and return a splash screen"""
    # Create a basic splash screen
    # In practice, you might want to replace this with an actual image
    pixmap = QPixmap(400, 200)
    pixmap.fill(Qt.GlobalColor.white)
    
    splash = QSplashScreen(pixmap)
    splash.show()
    return splash

def main():
    """Main application entry point"""
    # Create application instance
    app = QApplication(sys.argv)
    app.setApplicationName("Character Generator")
    app.setApplicationVersion("2.3.0")
    app.setOrganizationName("CharacterGen")
    
    # Set up logging
    logger = setup_logging()
    logger.info("Starting Character Generator")
    
    # Show splash screen
    splash = create_splash_screen()
    splash.showMessage("Checking dependencies...", 
                      Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter)
    app.processEvents()
    
    try:
        # Perform startup checks
        checks = [
            (check_dependencies, "Checking dependencies..."),
            (check_directories, "Creating directories..."),
            (check_config, "Checking configuration...")
        ]
        
        for check_func, message in checks:
            splash.showMessage(message, 
                             Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter)
            app.processEvents()
            
            if not check_func():
                logger.error(f"Startup check failed: {message}")
                return 1
        
        # Load configuration
        splash.showMessage("Loading configuration...", 
                         Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter)
        app.processEvents()
        
        config = get_config()
        
        # Create and show main window
        splash.showMessage("Starting application...", 
                         Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter)
        app.processEvents()
        
        window = MainWindow()
        window.show()
        
        # Close splash screen
        splash.finish(window)
        
        # Start event loop
        logger.info("Application started successfully")
        return app.exec()
        
    except ConfigError as e:
        logger.error(f"Configuration error: {str(e)}")
        QMessageBox.critical(
            None,
            "Configuration Error",
            f"Error in configuration: {str(e)}"
        )
        return 1
        
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
