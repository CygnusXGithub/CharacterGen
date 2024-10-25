from typing import Dict, Optional
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QTabWidget, QVBoxLayout,
    QMessageBox, QMenuBar, QMenu, QApplication,
    QDialog, QDialogButtonBox, QLabel
)
from PyQt6.QtCore import Qt, QSettings

from ..core.config import AppConfig, get_config
from ..services.api_service import ApiService
from ..services.character_service import CharacterService
from ..services.generation_service import GenerationService
from ..services.prompt_service import PromptService
from .tabs.base_prompts_tab import BasePromptsTab
from .tabs.generation_tab import GenerationTab

class AboutDialog(QDialog):
    """About dialog showing version and information"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About Character Generator")
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout()
        
        # Add version info
        layout.addWidget(QLabel("Character Generator"))
        layout.addWidget(QLabel("Version 2.3.0"))
        layout.addWidget(QLabel("Created By Cygnus"))
        
        # Add description
        desc = QLabel(
            "An AI-powered character card generator with intelligent "
            "context handling and cascading regeneration capabilities."
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        # Add button box
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
        )
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)
        
        self.setLayout(layout)

class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Character Generator")
        
        # Initialize services
        self.config = get_config()
        self._init_services()
        
        # Load settings
        self.settings = QSettings("CharacterGen", "CharacterGenerator")
        self._load_settings()
        
        self._init_ui()
        self._create_menus()
    
    def _init_services(self):
        """Initialize all services"""
        self.api_service = ApiService(self.config.api)
        self.character_service = CharacterService(self.config.paths)
        self.prompt_service = PromptService(self.config.paths)
        self.generation_service = GenerationService(
            self.api_service,
            self.prompt_service
        )
    
    def _init_ui(self):
        """Initialize the main UI"""
        self.setMinimumSize(1024, 768)
        
        # Create tab widget
        self.tabs = QTabWidget()
        
        # Add base prompts tab
        self.base_prompts_tab = BasePromptsTab(self.prompt_service)
        self.tabs.addTab(self.base_prompts_tab, "Base Prompts")
        
        # Add generation tab
        self.generation_tab = GenerationTab(
            self.character_service,
            self.generation_service
        )
        self.tabs.addTab(self.generation_tab, "Generation")
        
        # Set central widget
        self.setCentralWidget(self.tabs)

        # Set initial tab to Generation
        self.tabs.setCurrentIndex(1)
    
    def _create_menus(self):
        """Create application menus"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        new_action = file_menu.addAction("New Character")
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self._handle_new_character)
        
        save_action = file_menu.addAction("Save")
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self._handle_save)
        
        file_menu.addSeparator()
        
        exit_action = file_menu.addAction("Exit")
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        
        # Edit menu
        edit_menu = menubar.addMenu("Edit")
        
        preferences_action = edit_menu.addAction("Preferences")
        preferences_action.triggered.connect(self._handle_preferences)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        about_action = help_menu.addAction("About")
        about_action.triggered.connect(self._handle_about)
    
    def _handle_new_character(self):
        """Handle new character request"""
        if self.generation_tab.prompt_save_if_modified():
            self.generation_tab.clear_all()
            self.tabs.setCurrentWidget(self.generation_tab)
    
    def _handle_save(self):
        """Handle save request"""
        current_tab = self.tabs.currentWidget()
        if isinstance(current_tab, GenerationTab):
            current_tab._handle_save_character()
    
    def _handle_preferences(self):
        """Handle preferences request"""
        # TODO: Implement preferences dialog
        QMessageBox.information(
            self,
            "Preferences",
            "Preferences dialog coming soon!"
        )
    
    def _handle_about(self):
        """Handle about request"""
        dialog = AboutDialog(self)
        dialog.exec()

    # Removed so as to not auto swap tabs on Prompt load
    # def _handle_prompt_set_loaded(self, prompt_set):
    #     """Handle when a prompt set is loaded"""
    #     # Switch to generation tab when prompts are loaded
    #     self.tabs.setCurrentWidget(self.generation_tab)
    
    def _load_settings(self):
        """Load application settings"""
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        
        state = self.settings.value("windowState")
        if state:
            self.restoreState(state)
    
    def _save_settings(self):
        """Save application settings"""
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())
    
    def closeEvent(self, event):
        """Handle application closing"""
        # Check for unsaved changes
        if not self.generation_tab.prompt_save_if_modified():
            event.ignore()
            return
        
        # Save settings
        self._save_settings()
        
        # Close all tabs properly
        self.generation_tab.closeEvent(event)
        event.accept()

def create_main_window() -> MainWindow:
    """Create and configure the main window"""
    window = MainWindow()
    window.show()
    return window

def main():
    """Main application entry point"""
    import sys
    
    app = QApplication(sys.argv)
    app.setApplicationName("Character Generator")
    app.setOrganizationName("CharacterGen")
    
    try:
        window = create_main_window()
        sys.exit(app.exec())
    except Exception as e:
        QMessageBox.critical(
            None,
            "Error",
            f"Critical error: {str(e)}\n\nApplication will now close."
        )
        sys.exit(1)

if __name__ == "__main__":
    main()
