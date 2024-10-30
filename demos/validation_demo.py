import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QPushButton, QWidget
from PyQt6.QtCore import QTimer

from core.state import UIStateManager
from core.errors import ErrorHandler
from ui.widgets.content_edit import EditableContentWidget

class DemoWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Validation Demo")
        self.setGeometry(100, 100, 600, 400)

        # Create managers
        self.error_handler = ErrorHandler()
        self.ui_manager = UIStateManager(self.error_handler)

        # Create central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Create content widget
        self.content_widget = EditableContentWidget(
            self.ui_manager,
            field_name="test_field",
            multiline=True,
            placeholder_text="Enter some text..."
        )
        layout.addWidget(self.content_widget)

        # Add test buttons
        error_button = QPushButton("Show Error")
        error_button.clicked.connect(self.show_error)
        layout.addWidget(error_button)

        warning_button = QPushButton("Show Warning")
        warning_button.clicked.connect(self.show_warning)
        layout.addWidget(warning_button)

        clear_button = QPushButton("Clear Validation")
        clear_button.clicked.connect(self.clear_validation)
        layout.addWidget(clear_button)

    def show_error(self):
        self.content_widget.set_validation_state(False, "This is an error message!")

    def show_warning(self):
        self.content_widget.set_validation_state(True, "This is a warning message!")

    def clear_validation(self):
        self.content_widget.set_validation_state(True, "")

def main():
    app = QApplication(sys.argv)
    window = DemoWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()