from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QSpinBox, QDoubleSpinBox, QDialogButtonBox,
    QFormLayout, QGroupBox, QMessageBox, QScrollArea, QWidget,
    QCheckBox, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal

from ...core.enums import ThemeType, StatusLevel
from ...core.managers import SettingsManager, UIStateManager

class PreferencesDialog(QDialog):
    """Dialog for application preferences"""
    settings_updated = pyqtSignal()
    
    def __init__(self, 
                settings_manager: SettingsManager,
                ui_manager: UIStateManager,
                parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.ui_manager = ui_manager
        self.setWindowTitle("Preferences")
        self.setMinimumWidth(600)
        self._init_ui()
        self._load_settings()
    
    def _init_ui(self):
        main_layout = QVBoxLayout()
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(20)
        
        # API Settings
        api_group = QGroupBox("API Settings")
        api_layout = QFormLayout()
        
        self.api_url = QLineEdit()
        self.api_url.setPlaceholderText("http://127.0.0.1:5000/v1/chat/completions")
        api_layout.addRow("API URL:", self.api_url)
        
        self.api_key = QLineEdit()
        self.api_key.setPlaceholderText("Optional")
        api_layout.addRow("API Key:", self.api_key)
        
        self.timeout = QSpinBox()
        self.timeout.setRange(30, 9999)
        self.timeout.setSuffix(" seconds")
        api_layout.addRow("Timeout:", self.timeout)
        
        self.max_retries = QSpinBox()
        self.max_retries.setRange(1, 10)
        api_layout.addRow("Max Retries:", self.max_retries)
        
        self.retry_delay = QSpinBox()
        self.retry_delay.setRange(1, 30)
        self.retry_delay.setSuffix(" seconds")
        api_layout.addRow("Retry Delay:", self.retry_delay)
        
        api_group.setLayout(api_layout)
        layout.addWidget(api_group)
        
        # Generation Settings
        gen_group = QGroupBox("Generation Settings")
        gen_layout = QFormLayout()
        
        self.max_tokens = QSpinBox()
        self.max_tokens.setRange(100, 8192)
        self.max_tokens.setSingleStep(128)
        gen_layout.addRow("Max Tokens:", self.max_tokens)
        
        self.auto_save = QCheckBox("Enable Auto-save")
        gen_layout.addRow("Auto-save:", self.auto_save)
        
        self.auto_save_interval = QSpinBox()
        self.auto_save_interval.setRange(30, 3600)
        self.auto_save_interval.setSuffix(" seconds")
        self.auto_save_interval.setEnabled(False)
        gen_layout.addRow("Auto-save Interval:", self.auto_save_interval)
        
        self.auto_save.stateChanged.connect(
            lambda state: self.auto_save_interval.setEnabled(state == Qt.CheckState.Checked)
        )
        
        gen_group.setLayout(gen_layout)
        layout.addWidget(gen_group)
        
        # User Settings
        user_group = QGroupBox("User Settings")
        user_layout = QFormLayout()
        
        self.creator_name = QLineEdit()
        self.creator_name.setPlaceholderText("Anonymous")
        user_layout.addRow("Default Creator Name:", self.creator_name)
        
        self.default_save_format = QComboBox()
        self.default_save_format.addItems(['json', 'png'])
        user_layout.addRow("Default Save Format:", self.default_save_format)
        
        user_group.setLayout(user_layout)
        layout.addWidget(user_group)
        
        # UI Settings
        ui_group = QGroupBox("UI Settings")
        ui_layout = QFormLayout()
        
        self.theme = QComboBox()
        self.theme.addItems([theme.value for theme in ThemeType])
        ui_layout.addRow("Theme:", self.theme)
        
        self.font_size = QSpinBox()
        self.font_size.setRange(8, 24)
        self.font_size.setValue(10)
        ui_layout.addRow("Font Size:", self.font_size)
        
        self.show_status_bar = QCheckBox()
        self.show_status_bar.setChecked(True)
        ui_layout.addRow("Show Status Bar:", self.show_status_bar)
        
        self.show_toolbar = QCheckBox()
        self.show_toolbar.setChecked(True)
        ui_layout.addRow("Show Toolbar:", self.show_toolbar)
        
        ui_group.setLayout(ui_layout)
        layout.addWidget(ui_group)
        
        scroll.setWidget(container)
        main_layout.addWidget(scroll)
        
        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | 
            QDialogButtonBox.StandardButton.Cancel |
            QDialogButtonBox.StandardButton.Reset
        )
        button_box.accepted.connect(self._save_settings)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.StandardButton.Reset).clicked.connect(
            self._reset_settings
        )
        main_layout.addWidget(button_box)
        
        self.setLayout(main_layout)
    
    def _load_settings(self):
        """Load current settings"""
        try:
            # API settings
            self.api_url.setText(self.settings_manager.get("api.url", ""))
            self.api_key.setText(self.settings_manager.get("api.key", ""))
            self.timeout.setValue(self.settings_manager.get("api.timeout", 420))
            self.max_retries.setValue(self.settings_manager.get("api.max_retries", 3))
            self.retry_delay.setValue(self.settings_manager.get("api.retry_delay", 1))
            
            # Generation settings
            self.max_tokens.setValue(self.settings_manager.get("generation.max_tokens", 2048))
            self.auto_save.setChecked(self.settings_manager.get("generation.auto_save", False))
            self.auto_save_interval.setValue(
                self.settings_manager.get("generation.auto_save_interval", 300)
            )
            
            # User settings
            self.creator_name.setText(
                self.settings_manager.get("user.creator_name", "Anonymous")
            )
            self.default_save_format.setCurrentText(
                self.settings_manager.get("user.default_save_format", "json")
            )
            
            # UI settings
            self.theme.setCurrentText(
                self.settings_manager.get("ui.theme", ThemeType.LIGHT.value)
            )
            self.font_size.setValue(self.settings_manager.get("ui.font_size", 10))
            self.show_status_bar.setChecked(
                self.settings_manager.get("ui.show_status_bar", True)
            )
            self.show_toolbar.setChecked(
                self.settings_manager.get("ui.show_toolbar", True)
            )
            
        except Exception as e:
            # Use QMessageBox instead of status message for dialog errors
            QMessageBox.warning(
                self,
                "Settings Error",
                f"Error loading settings: {str(e)}"
            )
    
    def _save_settings(self):
        """Save current settings"""
        try:
            # Validate API URL
            if not self.api_url.text().strip():
                raise ValueError("API URL cannot be empty")
            
            # API settings
            self.settings_manager.set("api.url", self.api_url.text().strip())
            self.settings_manager.set("api.key", self.api_key.text().strip() or None)
            self.settings_manager.set("api.timeout", self.timeout.value())
            self.settings_manager.set("api.max_retries", self.max_retries.value())
            self.settings_manager.set("api.retry_delay", self.retry_delay.value())
            
            # Generation settings
            self.settings_manager.set("generation.max_tokens", self.max_tokens.value())
            self.settings_manager.set("generation.auto_save", self.auto_save.isChecked())
            self.settings_manager.set(
                "generation.auto_save_interval",
                self.auto_save_interval.value()
            )
            
            # User settings
            self.settings_manager.set(
                "user.creator_name",
                self.creator_name.text().strip() or "Anonymous"
            )
            self.settings_manager.set(
                "user.default_save_format",
                self.default_save_format.currentText()
            )
            
            # UI settings
            self.settings_manager.set("ui.theme", self.theme.currentText())
            self.settings_manager.set("ui.font_size", self.font_size.value())
            self.settings_manager.set("ui.show_status_bar", self.show_status_bar.isChecked())
            self.settings_manager.set("ui.show_toolbar", self.show_toolbar.isChecked())
            
            self.settings_updated.emit()
            self.ui_manager.show_status_message(
                "Settings saved successfully",
                StatusLevel.SUCCESS
            )
            self.accept()
            
        except Exception as e:
            self.ui_manager.show_status_message(
                f"Error saving settings: {str(e)}",
                StatusLevel.ERROR
            )
            QMessageBox.critical(
                self,
                "Save Error",
                f"Error saving settings: {str(e)}"
            )
    
    def _reset_settings(self):
        """Reset settings to defaults"""
        reply = QMessageBox.question(
            self,
            "Reset Settings",
            "Are you sure you want to reset all settings to defaults?",
            QMessageBox.StandardButton.Yes | 
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.settings_manager.reset_all()
            self._load_settings()
            self.ui_manager.show_status_message(
                "Settings reset to defaults",
                StatusLevel.SUCCESS
            )