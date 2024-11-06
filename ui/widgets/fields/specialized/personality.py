from typing import Optional, Dict
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame,
    QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal

from ..editor import FieldEditor
from core.state import UIStateManager

class PersonalityField(FieldEditor):
    """Field for structured personality descriptions"""
    
    format_changed = pyqtSignal(str)  # New format selected
    
    def __init__(self, 
                 ui_manager: UIStateManager,
                 parent: Optional[QWidget] = None):
        super().__init__(
            ui_manager=ui_manager,
            field_name="personality",
            label="Personality",
            help_text="The character's personality traits and behaviors. Choose a format for structured input.",
            required=True,
            parent=parent
        )
        self._format = "free"  # Default format
        self._setup_format_controls()

    def _setup_format_controls(self):
        """Setup personality format controls"""
        controls = QFrame(self)
        controls.setObjectName("format_controls")
        layout = QHBoxLayout(controls)
        layout.setContentsMargins(0, 4, 0, 4)
        
        # Format selector
        format_label = QLabel("Format:")
        layout.addWidget(format_label)
        
        self._format_combo = QComboBox()
        self._format_combo.addItems([
            "Free Form",
            "Traits List",
            "Structured",
            "Keywords"
        ])
        self._format_combo.currentTextChanged.connect(self._handle_format_change)
        layout.addWidget(self._format_combo)
        
        layout.addStretch()
        
        # Template button
        self._template_btn = QPushButton("Apply Template")
        self._template_btn.setObjectName("template_button")
        self._template_btn.clicked.connect(self._apply_template)
        layout.addWidget(self._template_btn)
        
        # Add to layout
        self._content_layout.insertWidget(1, controls)  # Add after label, before editor
        
        # Add guidelines frame
        self._guidelines = QFrame()
        self._guidelines.setObjectName("guidelines_frame")
        self._guidelines_layout = QVBoxLayout(self._guidelines)
        self._content_layout.addWidget(self._guidelines)
        self._guidelines.hide()
        
        self._setup_format_styling()
        
    def _setup_format_styling(self):
        """Setup format-specific styling"""
        self.setStyleSheet(self.styleSheet() + """
            QFrame#format_controls {
                background-color: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 4px;
                margin-bottom: 8px;
            }
            
            QComboBox {
                padding: 4px 8px;
                border: 1px solid #ced4da;
                border-radius: 4px;
                min-width: 120px;
            }
            
            QComboBox:hover {
                border-color: #3498db;
            }
            
            QPushButton#template_button {
                padding: 4px 8px;
                border: 1px solid #3498db;
                border-radius: 4px;
                color: #3498db;
            }
            
            QPushButton#template_button:hover {
                background-color: #3498db;
                color: white;
            }
            
            QFrame#guidelines_frame {
                background-color: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 4px;
                margin-top: 8px;
                padding: 8px;
            }
        """)

    def _handle_format_change(self, format_name: str):
        """Handle format selection change"""
        self._format = format_name.lower().replace(" ", "_")
        self._update_guidelines()
        self.format_changed.emit(self._format)
        
    def _update_guidelines(self):
        """Update format guidelines display"""
        # Clear current guidelines
        while self._guidelines_layout.count():
            item = self._guidelines_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        # Add new guidelines based on format
        if self._format == "traits_list":
            guidelines = [
                "• List each trait on a new line",
                "• Start with key trait words",
                "• Add brief explanations after traits",
                "• Include both positive and negative traits",
                "• Aim for 5-10 main traits"
            ]
        elif self._format == "structured":
            guidelines = [
                "Core Traits:",
                "• List fundamental personality aspects",
                "Behavior Patterns:",
                "• Describe typical behaviors and reactions",
                "Social Interactions:",
                "• Detail how they interact with others",
                "Emotional Responses:",
                "• Explain emotional tendencies"
            ]
        elif self._format == "keywords":
            guidelines = [
                "• Use comma-separated keywords",
                "• Include personality adjectives",
                "• Add emotional tendencies",
                "• Note behavioral patterns",
                "• Mark important traits with *"
            ]
        else:  # free_form
            self._guidelines.hide()
            return
            
        # Add guidelines
        for guideline in guidelines:
            label = QLabel(guideline)
            label.setStyleSheet("color: #666666;")
            self._guidelines_layout.addWidget(label)
            
        self._guidelines.show()

    def _apply_template(self):
        """Apply format template to content"""
        templates = {
            "traits_list": """Confident: Shows strong self-assurance in decisions
Empathetic: Deeply understands others' feelings
Creative: Thinks outside conventional boundaries
Cautious: Carefully considers consequences
Loyal: Forms strong, lasting bonds""",
            
            "structured": """Core Traits:
- Primary traits that define personality
- Key characteristics and values

Behavior Patterns:
- Typical reactions to situations
- Common habits and tendencies

Social Interactions:
- How they relate to others
- Communication style

Emotional Responses:
- Typical emotional reactions
- Emotional processing style""",
            
            "keywords": "confident, empathetic, *creative, cautious, loyal, thoughtful, adaptable, curious",
            
            "free_form": "A detailed description of the character's personality..."
        }
        
        if self._format in templates:
            self.set_content(templates[self._format])

    def get_format(self) -> str:
        """Get current personality format"""
        return self._format

    def set_format(self, format_name: str):
        """Set personality format"""
        index = self._format_combo.findText(
            format_name.replace("_", " ").title(),
            Qt.MatchFlag.MatchExactly
        )
        if index >= 0:
            self._format_combo.setCurrentIndex(index)

    def validate(self) -> bool:
        """Validate personality content"""
        content = self.get_content().strip()
        
        # Basic validation
        if not content:
            self.set_validation_state(False, "Personality description is required")
            return False
            
        # Format-specific validation
        if self._format == "traits_list":
            lines = content.split("\n")
            if len(lines) < 3:
                self.set_validation_state(False, "List at least 3 personality traits")
                return False
        elif self._format == "structured":
            if "Core Traits:" not in content:
                self.set_validation_state(False, "Must include Core Traits section")
                return False
        elif self._format == "keywords":
            keywords = [k.strip() for k in content.split(",")]
            if len(keywords) < 5:
                self.set_validation_state(False, "Include at least 5 keywords")
                return False
                
        self.set_validation_state(True)
        return True