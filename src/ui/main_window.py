from typing import Optional, Dict
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout,
    QMessageBox, QMenuBar, QMenu, QApplication, QDialog, 
    QDialogButtonBox, QLabel, QStatusBar
)
from PyQt6.QtCore import Qt, pyqtSignal
from pathlib import Path

from ..core.config import get_config
from ..core.models import CharacterData
from ..core.enums import FieldName, CardFormat, TabType, UIMode, StatusLevel
from ..core.managers import (
    CharacterStateManager,
    GenerationManager,
    SettingsManager,
    UIStateManager
)
from ..services.api_service import ApiService
from ..services.character_service import CharacterService
from ..services.generation_service import GenerationService
from ..services.prompt_service import PromptService
from .tabs.base_prompts_tab import BasePromptsTab
from .tabs.generation_tab import GenerationTab
from .tabs.editor_tab import EditorTab
from .dialogs.preferences_dialog import PreferencesDialog

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
    
    def __init__(self,
                 settings_manager: SettingsManager,
                 ui_manager: UIStateManager,
                 character_manager: CharacterStateManager,
                 generation_manager: GenerationManager,
                 api_service: ApiService,
                 character_service: CharacterService,
                 prompt_service: PromptService,
                 generation_service: GenerationService):
        super().__init__()
        
        # Initialize instance variables first
        self.tabs = None
        self.base_prompts_tab = None
        self.generation_tab = None
        self.editor_tab = None
        
        # Store managers
        self.settings_manager = settings_manager
        self.ui_manager = ui_manager
        self.character_manager = character_manager
        self.generation_manager = generation_manager
        
        # Store services
        self.api_service = api_service
        self.character_service = character_service
        self.prompt_service = prompt_service
        self.generation_service = generation_service
        
        # Set window properties
        self.setWindowTitle("Character Generator")
        self.setMinimumSize(1024, 768)
        
        # Initialize UI
        self._init_ui()
        self._create_menus()
        self._connect_signals()
        
        # Restore window state
        self._restore_window_state()

    def _init_services(self):
        """Initialize all services"""
        self.api_service = ApiService(self.config)
        self.character_service = CharacterService(self.config.paths)
        self.prompt_service = PromptService(self.config.paths)
        self.generation_service = GenerationService(
            self.api_service,
            self.prompt_service
        )
    
    def _init_managers(self):
        """Initialize all managers"""
        # Initialize managers
        self.settings_manager = SettingsManager()
        self.ui_manager = UIStateManager()
        self.character_manager = CharacterStateManager(self.character_service)
        self.generation_manager = GenerationManager(
            self.generation_service,
            self.character_manager
        )
        
        # Apply initial settings
        self._apply_settings()
    
    def _apply_settings(self):
        """Apply settings from settings manager"""
        # Get window size with proper type conversion
        size_dict = self.settings_manager.get("window.size", {"width": 1024, "height": 768})
        if isinstance(size_dict, dict):
            width = int(size_dict.get("width", 1024))
            height = int(size_dict.get("height", 768))
            self.resize(width, height)
        else:
            # Fallback to default size
            self.resize(1024, 768)

        # Apply theme
        theme = self.settings_manager.get("ui.theme", "light")
        self.ui_manager.set_theme(theme)
        
        # Apply other UI settings
        if self.settings_manager.get("ui.show_status_bar", True):
            self.statusBar().show()
        else:
            self.statusBar().hide()
    def _init_ui(self):
        """Initialize the user interface"""
        # Create tab widget
        self.tabs = QTabWidget()
        
        # Add base prompts tab first
        self.base_prompts_tab = BasePromptsTab(
            self.prompt_service,
            self.ui_manager,
            self.settings_manager
        )
        self.tabs.addTab(self.base_prompts_tab, "Base Prompts")
        
        # Create tabs with synchronized content
        self.generation_tab = GenerationTab(
            self.generation_manager,
            self.character_manager,
            self.ui_manager,
            self.settings_manager
        )
        
        self.editor_tab = EditorTab(
            self.character_manager,
            self.ui_manager,
            self.settings_manager
        )
        
        # Initialize base character state
        initial_character = self.character_manager.create_new_character()
        self.generation_tab.set_initial_character(initial_character)
        self.editor_tab.set_initial_character(initial_character)
        
        # Connect cross-tab synchronization
        self._connect_tab_sync()
        
        # Add tabs to widget
        self.tabs.addTab(self.generation_tab, "Generation")
        self.tabs.addTab(self.editor_tab, "Editor")
        
        # Connect tab change signal
        self.tabs.currentChanged.connect(self._handle_tab_changed)
        
        # Set central widget
        self.setCentralWidget(self.tabs)
        
        # Create status bar
        self.statusBar()

    def _restore_window_state(self):
        """Restore window geometry and state"""
        if self.settings_manager:
            # Restore window geometry
            geometry = self.settings_manager.get("window.geometry")
            if geometry:
                self.restoreGeometry(geometry)
            else:
                # Default size if no saved geometry
                self.resize(1024, 768)
            
            # Restore window state (toolbars, docks, etc.)
            state = self.settings_manager.get("window.state")
            if state:
                self.restoreState(state)

    def _connect_signals(self):
        """Connect all signals"""
        # Settings manager signals
        if self.settings_manager:
            self.settings_manager.settings_updated.connect(self._apply_settings)
            self.settings_manager.settings_error.connect(
                lambda msg: self.ui_manager.show_status_message(f"Settings error: {msg}", 5000)
            )
        
        # UI manager signals
        if self.ui_manager:
            self.ui_manager.status_message.connect(self._show_status_message)
            self.ui_manager.theme_changed.connect(self._apply_theme)
            self.ui_manager.dialog_requested.connect(self._handle_dialog_request)
            self.ui_manager.tab_changed.connect(self._switch_tab)
        
        # Character manager signals
        if self.character_manager:
            self.character_manager.character_loaded.connect(self._on_character_loaded)
            self.character_manager.character_updated.connect(self._on_character_updated)
            self.character_manager.operation_started.connect(
                lambda msg: self.ui_manager.show_status_message(msg)
            )
            self.character_manager.operation_completed.connect(
                lambda msg: self.ui_manager.show_status_message(msg, 3000)
            )
            self.character_manager.operation_failed.connect(self._handle_operation_error)

            # Connect tab update signals
        if self.editor_tab:
            self.editor_tab.character_updated.connect(
                self.generation_tab.handle_external_update
            )
        
        if self.generation_tab:
            self.generation_tab.character_updated.connect(
                self.editor_tab.handle_external_update
            )

    def _connect_tab_sync(self):
        """Connect tab synchronization signals"""
        # Connect field updates
        self.editor_tab.character_updated.connect(self.generation_tab.handle_external_update)
        self.generation_tab.character_updated.connect(self.editor_tab.handle_external_update)
        
        # Connect alternate greetings updates
        if hasattr(self.editor_tab, 'alt_greetings'):
            self.editor_tab.alt_greetings.greeting_updated.connect(
                lambda idx, text: self.generation_tab.alt_greetings_widget.update_greeting(idx, text)
            )
            self.editor_tab.alt_greetings.greeting_added.connect(
                lambda text: self.generation_tab.alt_greetings_widget.add_greeting(text)
            )
            self.editor_tab.alt_greetings.greeting_deleted.connect(
                lambda idx: self.generation_tab.alt_greetings_widget.delete_greeting(idx)
            )
        
        if hasattr(self.generation_tab, 'alt_greetings_widget'):
            self.generation_tab.alt_greetings_widget.greeting_updated.connect(
                lambda idx, text: self.editor_tab.alt_greetings.update_greeting(idx, text)
            )
            self.generation_tab.alt_greetings_widget.greeting_added.connect(
                lambda text: self.editor_tab.alt_greetings.add_greeting(text)
            )
            self.generation_tab.alt_greetings_widget.greeting_deleted.connect(
                lambda idx: self.editor_tab.alt_greetings.delete_greeting(idx)
            )
            
    def _show_status_message(self, message: str, timeout: int = 3000):
        """Show status message"""
        self.statusBar().showMessage(message, timeout)

    def _apply_theme(self, theme: str):
        """Apply theme to application"""
        # TODO: Implement theme application
        pass
    
    def _handle_dialog_request(self, dialog_type: str, parameters: dict):
        """Handle dialog requests"""
        if dialog_type == "preferences":
            dialog = PreferencesDialog(self, self.settings_manager)
            dialog.exec()
        elif dialog_type == "about":
            dialog = AboutDialog(self)
            dialog.exec()
        # Add other dialog types as needed

    def _switch_tab(self, tab: TabType):
        """Switch to specified tab"""
        if not self.tabs:
            return
            
        if tab == TabType.EDITOR and self.editor_tab:
            self.tabs.setCurrentWidget(self.editor_tab)
        elif tab == TabType.GENERATION and self.generation_tab:
            self.tabs.setCurrentWidget(self.generation_tab)
        elif tab == TabType.BASE_PROMPTS and self.base_prompts_tab:
            self.tabs.setCurrentWidget(self.base_prompts_tab)

    def _handle_tab_changed(self, index: int):
        """Handle tab changes"""
        current_tab = self.tabs.widget(index)
        
        if not self.tabs or not current_tab:
            return
            
        if current_tab is self.editor_tab:
            self.ui_manager.set_current_tab(TabType.EDITOR)
        elif current_tab is self.generation_tab:
            self.ui_manager.set_current_tab(TabType.GENERATION)
        elif current_tab is self.base_prompts_tab:
            self.ui_manager.set_current_tab(TabType.BASE_PROMPTS)
    
    def _handle_operation_error(self, operation: str, message: str):
        """Handle operation errors"""
        QMessageBox.critical(
            self,
            f"{operation.title()} Error",
            message
        )


    def _create_menus(self):
        """Create application menus"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        new_action = file_menu.addAction("New Character")
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self._handle_new_character)
        
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

    def _handle_load_request(self, file_path: str):
        """Handle character load requests"""
        try:
            character = self.character_manager.load_character(file_path)
            self.ui_manager.show_status_message(
                f"Loaded character: {character.name}",
                StatusLevel.SUCCESS
            )
        except Exception as e:
            self.ui_manager.show_status_message(
                f"Error loading character: {str(e)}",
                StatusLevel.ERROR
            )
            QMessageBox.critical(
                self,
                "Load Error",
                f"Error loading character: {str(e)}"
            )

    def _on_character_loaded(self, character: CharacterData):
        """Handle loaded character"""
        print(f"MainWindow: Loading character {character.name}")
        self.generation_tab.set_initial_character(character)
        self.editor_tab.set_initial_character(character)

    def _on_character_updated(self, character: CharacterData, field: str):
        """Handle character updates"""
        if isinstance(self.sender(), GenerationTab):
            self.editor_tab.handle_external_update(character, field)
        elif isinstance(self.sender(), EditorTab):
            self.generation_tab.handle_external_update(character, field)

    def _on_character_saved(self, path: Path):
        """Handle saved character"""
        self.statusBar().showMessage(f"Saved character to: {path}", 3000)

    def _on_generation_completed(self, field: FieldName, result):
        """Handle generation completion"""
        if result.error:
            self.statusBar().showMessage(f"Error generating {field.value}", 3000)
        else:
            self.statusBar().showMessage(
                f"Generated {field.value} in {result.attempts} attempts", 3000
            )

    def _on_generation_error(self, field: FieldName, error: Exception):
        """Handle generation errors"""
        QMessageBox.warning(
            self,
            "Generation Error",
            f"Error generating {field.value}: {str(error)}"
        )

    def _on_operation_failed(self, operation: str, message: str):
        """Handle operation failures"""
        QMessageBox.critical(
            self,
            f"{operation.title()} Error",
            message
        )

    def _on_settings_updated(self):
        """Handle settings updates"""
        # Reload configuration
        self.config = get_config()
        
        # Reinitialize services with new configuration
        self._init_services()
        
        # Update manager dependencies
        self.generation_manager.generation_service = self.generation_service

    def _handle_new_character(self):
        """Handle new character request"""
        if self.character_manager.is_modified:
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "Do you want to save your changes first?",
                QMessageBox.StandardButton.Yes | 
                QMessageBox.StandardButton.No |
                QMessageBox.StandardButton.Cancel
            )
            
            if reply == QMessageBox.StandardButton.Cancel:
                return
            elif reply == QMessageBox.StandardButton.Yes:
                # Switch to editor tab for saving
                self.tabs.setCurrentWidget(self.editor_tab)
                return
        
        self.character_manager.create_new_character()
        self.tabs.setCurrentWidget(self.editor_tab)
    
    def _handle_preferences(self):
        """Handle preferences dialog"""
        dialog = PreferencesDialog(
            settings_manager=self.settings_manager,
            ui_manager=self.ui_manager,
            parent=self
        )
        dialog.exec()
    
    def _handle_about(self):
        """Handle about dialog"""
        dialog = AboutDialog(self)
        dialog.exec()

    def closeEvent(self, event):
        """Handle application closing"""
        try:
            # Save window state
            if self.settings_manager:
                self.settings_manager.set("window.geometry", self.saveGeometry())
                self.settings_manager.set("window.state", self.saveState())
                self.settings_manager.set("window.size", {
                    "width": self.width(),
                    "height": self.height()
                })
            
            # Check for unsaved changes
            if self.character_manager.is_modified:
                reply = QMessageBox.question(
                    self,
                    "Unsaved Changes",
                    "Do you want to save your changes before exiting?",
                    QMessageBox.StandardButton.Yes | 
                    QMessageBox.StandardButton.No |
                    QMessageBox.StandardButton.Cancel
                )
                
                if reply == QMessageBox.StandardButton.Cancel:
                    event.ignore()
                    return
                elif reply == QMessageBox.StandardButton.Yes:
                    self.ui_manager.set_current_tab(TabType.EDITOR)
                    event.ignore()
                    return
            
            event.accept()
            
        except Exception as e:
            event.accept()  # Accept the close event even if saving fails