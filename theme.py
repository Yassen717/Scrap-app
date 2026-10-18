from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QComboBox,
                             QPushButton, QApplication)
from PyQt6.QtCore import QSettings, Qt
from PyQt6.QtGui import QFont

# Single source of truth for themes: palette data, not per-window QSS.
THEMES = {
    "Light": {
        "window": "#ffffff", "fg": "#333333", "muted": "#6b6b6b",
        "input_bg": "#ffffff", "input_border": "#d0d0d0",
        "accent": "#0078d4", "accent_hover": "#1a8fe0",
        "accent_pressed": "#006cbd", "accent_fg": "#ffffff",
        "error": "#c0392b",
        "scroll_bg": "#f5f5f5", "scroll_handle": "#d0d0d0",
        "scroll_hover": "#c1c1c1", "spinner": "#333333",
    },
    "Dark": {
        "window": "#1a1a1a", "fg": "#f0f0f0", "muted": "#a0a0a0",
        "input_bg": "#2d2d2d", "input_border": "#454545",
        "accent": "#2f9be8", "accent_hover": "#4aaaf0",
        "accent_pressed": "#1a7fc4", "accent_fg": "#ffffff",
        "error": "#e74c3c",
        "scroll_bg": "#262626", "scroll_handle": "#454545",
        "scroll_hover": "#555555", "spinner": "#f0f0f0",
    },
    "Nord": {
        "window": "#2e3440", "fg": "#eceff4", "muted": "#d8dee9",
        "input_bg": "#3b4252", "input_border": "#4c566a",
        "accent": "#88c0d0", "accent_hover": "#8fbcbb",
        "accent_pressed": "#81a1c1", "accent_fg": "#2e3440",
        "error": "#bf616a",
        "scroll_bg": "#3b4252", "scroll_handle": "#4c566a",
        "scroll_hover": "#5c6a80", "spinner": "#eceff4",
    },
    "Solarized": {
        "window": "#002b36", "fg": "#839496", "muted": "#586e75",
        "input_bg": "#073642", "input_border": "#586e75",
        "accent": "#268bd2", "accent_hover": "#35a2e8",
        "accent_pressed": "#1e6fae", "accent_fg": "#fdf6e3",
        "error": "#dc322f",
        "scroll_bg": "#073642", "scroll_handle": "#586e75",
        "scroll_hover": "#657b83", "spinner": "#93a1a1",
    },
    "Dracula": {
        "window": "#282a36", "fg": "#f8f8f2", "muted": "#b0b7d1",
        "input_bg": "#44475a", "input_border": "#6272a4",
        "accent": "#bd93f9", "accent_hover": "#caa9fa",
        "accent_pressed": "#a579e0", "accent_fg": "#282a36",
        "error": "#ff5555",
        "scroll_bg": "#383a46", "scroll_handle": "#44475a",
        "scroll_hover": "#6272a4", "spinner": "#f8f8f2",
    },
}

_QSS = """
QWidget {
    font-family: 'Segoe UI', Arial, sans-serif;
    color: %(fg)s;
}
QMainWindow, QDialog {
    background-color: %(window)s;
}
QLabel { background: transparent; }
QLabel#mutedLabel { color: %(muted)s; }
QLabel#errorLabel { color: %(error)s; font-size: 12px; }

QToolBar {
    background-color: %(window)s;
    border: none;
    spacing: 6px;
    padding: 6px 8px;
}
QToolBar::separator {
    background: %(input_border)s;
    width: 1px;
    margin: 4px 6px;
}
QToolButton {
    background-color: transparent;
    color: %(fg)s;
    border: 1px solid transparent;
    border-radius: 5px;
    padding: 6px 10px;
}
QToolButton:hover { background-color: %(input_bg)s; border-color: %(input_border)s; }
QToolButton:pressed { background-color: %(input_border)s; }
QToolButton:disabled { color: %(muted)s; }

QPushButton {
    background-color: %(input_bg)s;
    color: %(fg)s;
    border: 1px solid %(input_border)s;
    border-radius: 6px;
    padding: 8px 16px;
}
QPushButton:hover { border-color: %(accent)s; }
QPushButton:pressed { background-color: %(input_border)s; }
QPushButton:disabled { color: %(muted)s; }
QPushButton#primaryButton {
    background-color: %(accent)s;
    color: %(accent_fg)s;
    border-color: %(accent)s;
    font-weight: 600;
}
QPushButton#primaryButton:hover {
    background-color: %(accent_hover)s; border-color: %(accent_hover)s;
}
QPushButton#primaryButton:pressed {
    background-color: %(accent_pressed)s; border-color: %(accent_pressed)s;
}
QPushButton#primaryButton:disabled {
    background-color: %(input_border)s; color: %(muted)s;
}

QLineEdit, QComboBox, QPlainTextEdit, QTextEdit {
    background-color: %(input_bg)s;
    color: %(fg)s;
    border: 1px solid %(input_border)s;
    border-radius: 6px;
    padding: 8px;
    selection-background-color: %(accent)s;
    selection-color: %(accent_fg)s;
}
QLineEdit:focus, QComboBox:focus, QPlainTextEdit:focus, QTextEdit:focus,
QPushButton:focus, QToolButton:focus {
    border-color: %(accent)s;
}
QComboBox::drop-down { border: none; width: 26px; }
QComboBox QAbstractItemView {
    background-color: %(input_bg)s;
    color: %(fg)s;
    border: 1px solid %(input_border)s;
    selection-background-color: %(accent)s;
    selection-color: %(accent_fg)s;
    outline: none;
}
QMenu {
    background-color: %(input_bg)s;
    color: %(fg)s;
    border: 1px solid %(input_border)s;
}
QMenu::item:selected { background-color: %(accent)s; color: %(accent_fg)s; }

QFrame#saveBanner {
    background-color: %(input_bg)s;
    border: 1px solid %(input_border)s;
    border-radius: 6px;
}

QStatusBar { background-color: %(window)s; color: %(muted)s; }
QStatusBar::item { border: none; }
QProgressBar {
    background-color: %(input_bg)s;
    color: %(fg)s;
    border: 1px solid %(input_border)s;
    border-radius: 5px;
    text-align: center;
}
QProgressBar::chunk { background-color: %(accent)s; border-radius: 4px; }

QScrollBar:vertical {
    background-color: %(scroll_bg)s;
    width: 12px; border: none; margin: 2px;
}
QScrollBar::handle:vertical {
    background-color: %(scroll_handle)s; border-radius: 5px; min-height: 30px;
}
QScrollBar::handle:vertical:hover { background-color: %(scroll_hover)s; }
QScrollBar:horizontal {
    background-color: %(scroll_bg)s;
    height: 12px; border: none; margin: 2px;
}
QScrollBar::handle:horizontal {
    background-color: %(scroll_handle)s; border-radius: 5px; min-width: 30px;
}
QScrollBar::handle:horizontal:hover { background-color: %(scroll_hover)s; }
QScrollBar::add-line, QScrollBar::sub-line {
    width: 0; height: 0; background: none; border: none;
}
QScrollBar::add-page, QScrollBar::sub-page { background: none; }

QFrame[frameShape="4"], QFrame[frameShape="5"] { color: %(input_border)s; }
QToolTip {
    background-color: %(input_bg)s;
    color: %(fg)s;
    border: 1px solid %(input_border)s;
    padding: 4px 6px;
}
"""


def theme_names():
    return list(THEMES)


def palette_for(name):
    return THEMES.get(name, THEMES["Light"])


def current_theme(settings=None):
    settings = settings or QSettings()
    name = settings.value("theme", "Light")
    return name if name in THEMES else "Light"


def apply_theme(name):
    """Apply a theme to the whole application. Returns the palette used."""
    palette = palette_for(name)
    app = QApplication.instance()
    if app is not None:
        app.setStyleSheet(_QSS % palette)
    return palette


class ThemeWindow(QDialog):
    """Theme picker dialog. Parented to the main window so it inherits the
    application stylesheet, closes with it, and stays on top of it."""

    def __init__(self, main_app):
        super().__init__(main_app)
        self.main_app = main_app
        self.setWindowTitle("Theme")
        self.setModal(False)
        self.setMinimumWidth(380)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        header = QLabel("Choose a theme")
        header.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        layout.addWidget(header)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(theme_names())
        self.theme_combo.setCurrentText(
            current_theme(self.main_app.settings))
        self.theme_combo.currentTextChanged.connect(self._theme_changed)
        self.theme_combo.setMinimumHeight(36)
        layout.addWidget(self.theme_combo)

        note = QLabel("Applied instantly to all windows.")
        note.setObjectName("mutedLabel")
        layout.addWidget(note)

        layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)

    def _theme_changed(self, name):
        self.main_app.apply_theme(name)
