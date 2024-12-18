from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QLabel, QComboBox, QPushButton, QFrame)
from PyQt6.QtCore import QSettings, Qt
from PyQt6.QtGui import QFont

class ThemeWindow(QMainWindow):
    def __init__(self, main_app):
        super().__init__()
        self.main_app = main_app
        self.setWindowTitle("Theme Customization")
        self.setMinimumSize(400, 300)
        self.settings = QSettings('ScrapApp', 'WebScraper')
        self.setup_ui()
        self.apply_theme(self.settings.value('theme', 'Light'))

    def setup_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        main_widget.setLayout(layout)

        # Header
        header = QLabel("Theme Settings")
        header.setFont(QFont('Segoe UI', 24, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        # Description
        description = QLabel("Choose your preferred theme:")
        description.setFont(QFont('Segoe UI', 12))
        description.setWordWrap(True)
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(description)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)
        
        # Theme Combo Box
        self.theme_combo = QComboBox()
        themes = ["Light", "Dark", "Nord", "Solarized", "Dracula"]
        self.theme_combo.addItems(themes)
        current_theme = self.settings.value('theme', 'Light')
        self.theme_combo.setCurrentText(current_theme)
        self.theme_combo.currentTextChanged.connect(self.theme_changed)
        self.theme_combo.setMinimumHeight(40)
        self.theme_combo.setFont(QFont('Segoe UI', 12))
        layout.addWidget(self.theme_combo)

        layout.addStretch()

    def theme_changed(self, theme):
        self.settings.setValue('theme', theme)
        self.main_app.apply_theme(theme)
        self.apply_theme(theme)

    def apply_theme(self, theme):
        base_styles = """
            QMainWindow, QWidget {
                font-family: 'Segoe UI', sans-serif;
            }
            QLabel {
                padding: 5px;
            }
            QComboBox {
                padding: 8px;
                border-radius: 5px;
                min-width: 200px;
            }
            QPushButton {
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QFrame[frameShape="4"] {
                margin: 10px 0;
            }
        """

        if theme == "Dark":
            self.setStyleSheet(base_styles + """
                QMainWindow, QWidget {
                    background-color: #1a1a1a;
                    color: #ffffff;
                }
                QComboBox {
                    background-color: #2d2d2d;
                    border: 1px solid #404040;
                    color: #ffffff;
                }
                QPushButton {
                    background-color: #0078d4;
                    color: white;
                    border: none;
                }
                QFrame[frameShape="4"] {
                    color: #404040;
                }
            """)
        elif theme == "Nord":
            self.setStyleSheet(base_styles + """
                QMainWindow, QWidget {
                    background-color: #2e3440;
                    color: #eceff4;
                }
                QComboBox {
                    background-color: #3b4252;
                    border: 1px solid #4c566a;
                    color: #eceff4;
                }
                QPushButton {
                    background-color: #88c0d0;
                    color: #2e3440;
                    border: none;
                }
                QFrame[frameShape="4"] {
                    color: #4c566a;
                }
            """)
        elif theme == "Solarized":
            self.setStyleSheet(base_styles + """
                QMainWindow, QWidget {
                    background-color: #002b36;
                    color: #839496;
                }
                QComboBox {
                    background-color: #073642;
                    border: 1px solid #586e75;
                    color: #839496;
                }
                QPushButton {
                    background-color: #268bd2;
                    color: #002b36;
                    border: none;
                }
                QFrame[frameShape="4"] {
                    color: #586e75;
                }
            """)
        elif theme == "Dracula":
            self.setStyleSheet(base_styles + """
                QMainWindow, QWidget {
                    background-color: #282a36;
                    color: #f8f8f2;
                }
                QComboBox {
                    background-color: #3f3f3f;
                    border: 1px solid #44475a;
                    color: #f8f8f2;
                }
                QPushButton {
                    background-color: #bd93f9;
                    color: #282a36;
                    border: none;
                }
                QFrame[frameShape="4"] {
                    color: #44475a;
                }
            """)
        else:  # Light
            self.setStyleSheet(base_styles + """
                QMainWindow, QWidget {
                    background-color: #ffffff;
                    color: #333333;
                }
                QComboBox {
                    background-color: white;
                    border: 1px solid #dddddd;
                    color: #333333;
                }
                QPushButton {
                    background-color: #0078d4;
                    color: white;
                    border: none;
                }
                QFrame[frameShape="4"] {
                    color: #dddddd;
                }
            """)
