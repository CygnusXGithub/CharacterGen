from typing import Optional, Dict, Any
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QMenuBar, QMenu, QToolBar, QStatusBar
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction

from core.state import (
    CharacterStateManager, 
    UIStateManager, 
    ConfigurationManager
)
from core.models.ui import TabType, StatusLevel
from ..widgets.layout.tab_container import TabContainer
from ..widgets.layout.status_display import StatusDisplay

class MainWindow(QMainWindow):
    """Main application window"""

    def __init__(self, 
                 character_manager: CharacterStateManager,
                 ui_manager: UIStateManager,
                 config_manager: ConfigurationManager,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self.character_manager = character_manager
        self.ui_manager = ui_manager
        self.config_manager = config_manager
        
        self.setWindowTitle("CharacterGen")
        self.resize(1200, 800)  # Default size
        
        # Setup UI
        self._setup_ui()
        self._setup_menubar()
        self._setup_toolbar()
        self._setup_statusbar()
        self._connect_signals()

    def _setup_ui(self):
        """Setup main UI layout"""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Tab container
        self._tab_container = TabContainer(self.ui_manager)
        main_layout.addWidget(self._tab_container)
        
        # Setup tabs
        self._setup_tabs()
        
        # Status display
        self._status_display = StatusDisplay(self.ui_manager)
        main_layout.addWidget(self._status_display)

    def _setup_menubar(self):
        """Setup menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        new_action = QAction("&New Character", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self._new_character)
        file_menu.addAction(new_action)
        
        open_action = QAction("&Open...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._open_character)
        file_menu.addAction(open_action)
        
        save_action = QAction("&Save", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self._save_character)
        file_menu.addAction(save_action)
        
        save_as_action = QAction("Save &As...", self)
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.triggered.connect(self._save_character_as)
        file_menu.addAction(save_as_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Alt+F4")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit menu
        edit_menu = menubar.addMenu("&Edit")
        
        undo_action = QAction("&Undo", self)
        undo_action.setShortcut("Ctrl+Z")
        undo_action.triggered.connect(self._undo)
        edit_menu.addAction(undo_action)
        
        redo_action = QAction("&Redo", self)
        redo_action.setShortcut("Ctrl+Y")
        redo_action.triggered.connect(self._redo)
        edit_menu.addAction(redo_action)
        
        # View menu
        view_menu = menubar.addMenu("&View")
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _setup_toolbar(self):
        """Setup toolbar"""
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        
        # Add common actions
        toolbar.addAction(QAction("New", self, triggered=self._new_character))
        toolbar.addAction(QAction("Open", self, triggered=self._open_character))
        toolbar.addAction(QAction("Save", self, triggered=self._save_character))
        
        toolbar.addSeparator()
        
        toolbar.addAction(QAction("Undo", self, triggered=self._undo))
        toolbar.addAction(QAction("Redo", self, triggered=self._redo))

    def _setup_statusbar(self):
        """Setup status bar"""
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)
        
        # Add permanent widgets if needed
        self._status_label = QStatusBar()
        status_bar.addPermanentWidget(self._status_label)

    def _setup_tabs(self):
        """Setup main tabs"""
        # Editor tab
        editor_widget = QWidget()  # Placeholder for now
        self._tab_container.add_tab(
            "editor",
            "Editor",
            editor_widget
        )
        
        # Generation tab
        generation_widget = QWidget()  # Placeholder for now
        self._tab_container.add_tab(
            "generation",
            "Generation",
            generation_widget
        )
        
        # Settings tab
        settings_widget = QWidget()  # Placeholder for now
        self._tab_container.add_tab(
            "settings",
            "Settings",
            settings_widget
        )

    def _connect_signals(self):
        """Connect signals to slots"""
        # Connect UI manager signals
        self.ui_manager.status_updated.connect(self._update_status)
        self.ui_manager.dialog_requested.connect(self._show_dialog)
        
        # Connect character manager signals
        self.character_manager.state_changed.connect(self._handle_character_state_change)

    # Action handlers
    def _new_character(self):
        """Create new character"""
        # TODO: Implement
        self.ui_manager.show_status("Creating new character...", StatusLevel.INFO)

    def _open_character(self):
        """Open character file"""
        # TODO: Implement
        self.ui_manager.show_status("Opening character...", StatusLevel.INFO)

    def _save_character(self):
        """Save current character"""
        # TODO: Implement
        self.ui_manager.show_status("Saving character...", StatusLevel.INFO)

    def _save_character_as(self):
        """Save character with new name"""
        # TODO: Implement
        self.ui_manager.show_status("Saving character as...", StatusLevel.INFO)

    def _undo(self):
        """Undo last action"""
        if self.character_manager.can_undo():
            self.character_manager.undo()
            self.ui_manager.show_status("Undo", StatusLevel.INFO)

    def _redo(self):
        """Redo last undone action"""
        if self.character_manager.can_redo():
            self.character_manager.redo()
            self.ui_manager.show_status("Redo", StatusLevel.INFO)

    def _show_about(self):
        """Show about dialog"""
        # TODO: Implement
        self.ui_manager.show_status("Showing about dialog...", StatusLevel.INFO)

    # Signal handlers
    def _update_status(self, message: str, level: StatusLevel):
        """Update status bar message"""
        self._status_label.showMessage(message)

    def _show_dialog(self, dialog_info):
        """Show requested dialog"""
        # TODO: Implement dialog system
        pass

    def _handle_character_state_change(self, key: str, value: Any):
        """Handle character state changes"""
        # TODO: Implement state change handling
        pass

    def closeEvent(self, event):
        """Handle window close event"""
        # TODO: Check for unsaved changes
        event.accept()