from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QSpinBox, QDoubleSpinBox, QDialogButtonBox,
    QFormLayout, QGroupBox, QMessageBox, QScrollArea, QWidget
)
import json
from PyQt6.QtCore import Qt, pyqtSignal
from ...core.config import AppConfig, get_config
from ...core.exceptions import ConfigError

class PreferencesDialog(QDialog):
    settings_updated = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = get_config()
        self._init_ui()
        self._load_settings()
    
    def _init_ui(self):
        self.setWindowTitle("Preferences")
        self.setMinimumWidth(500)
        
        # Create main layout
        main_layout = QVBoxLayout()
        
        # Create scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Create container for settings
        container = QWidget()
        layout = QVBoxLayout(container)
        
        # API Settings Group
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
        
        # Generation Settings Group
        gen_group = QGroupBox("Generation Settings")
        gen_layout = QFormLayout()
        
        self.max_tokens = QSpinBox()
        self.max_tokens.setRange(100, 8192)
        self.max_tokens.setSingleStep(128)
        gen_layout.addRow("Max Tokens:", self.max_tokens)
        
        gen_group.setLayout(gen_layout)
        layout.addWidget(gen_group)
        
        # User Settings Group
        user_group = QGroupBox("User Settings")
        user_layout = QFormLayout()
        
        self.creator_name = QLineEdit()
        self.creator_name.setPlaceholderText("Anonymous")
        user_layout.addRow("Default Creator Name:", self.creator_name)
        
        user_group.setLayout(user_layout)
        layout.addWidget(user_group)
        
        # Set container as scroll area widget
        scroll.setWidget(container)
        main_layout.addWidget(scroll)
        
        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._save_settings)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)
        
        self.setLayout(main_layout)
    
    def _load_settings(self):
        try:
            # Load API settings
            self.api_url.setText(self.config.api.url)
            self.api_key.setText(self.config.api.key or "")
            self.timeout.setValue(self.config.api.timeout)
            self.max_retries.setValue(self.config.api.max_retries)
            self.retry_delay.setValue(self.config.api.retry_delay)
            
            # Load generation settings
            self.max_tokens.setValue(self.config.generation.max_tokens)
            
            # Load user settings
            self.creator_name.setText(self.config.user.creator_name)
            
        except Exception as e:
            QMessageBox.warning(
                self,
                "Load Error",
                f"Error loading settings: {str(e)}"
            )
    
    def _save_settings(self):
        try:
            # Validate URL
            if not self.api_url.text().strip():
                raise ValueError("API URL cannot be empty")
            
            # Update API configuration
            self.config.api.url = self.api_url.text().strip()
            self.config.api.key = self.api_key.text().strip() or None
            self.config.api.timeout = self.timeout.value()
            self.config.api.max_retries = self.max_retries.value()
            self.config.api.retry_delay = self.retry_delay.value()
            
            # Update generation settings
            self.config.generation.max_tokens = self.max_tokens.value()
            
            # Update user settings
            self.config.user.creator_name = self.creator_name.text().strip() or "Anonymous"
            
            # Save configuration
            self.config.save(self.config.paths.config_dir / "config.yaml")
            
            # Update template.json
            template_path = self.config.paths.config_dir / "template.json"
            if template_path.exists():
                with open(template_path, 'r') as f:
                    template_data = json.load(f)
                
                template_data['data']['creator'] = self.config.user.creator_name
                
                with open(template_path, 'w') as f:
                    json.dump(template_data, f, indent=2)
            
            self.settings_updated.emit()
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Save Error",
                f"Error saving settings: {str(e)}"
            )