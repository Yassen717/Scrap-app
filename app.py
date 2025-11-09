from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                           QLineEdit, QPushButton, QTextEdit, QLabel, QComboBox,
                           QMessageBox, QFileDialog, QFrame, QProgressDialog, QApplication, QToolBar)
from PyQt6.QtCore import QSettings, Qt, QTimer, QSize
from PyQt6.QtGui import QPainter, QColor, QPen, QAction, QKeySequence
from urllib.parse import urlparse
from theme import ThemeWindow
from scraper import ScraperThread
import os
import math

class LoadingSpinner(QWidget):
    def __init__(self, parent=None, centerOnParent=True, disableParentWhenSpinning=True):
        super().__init__(parent)
        
        self.centerOnParent = centerOnParent
        self.disableParentWhenSpinning = disableParentWhenSpinning
        
        self.spinning = False
        self.angle = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.rotate)
        self.steps = 12
        self.timer_delay = 80
        
        self.setMinimumSize(QSize(40, 40))
        self.setMaximumSize(QSize(40, 40))
        
        self.hide()
        
    def start(self):
        self.angle = 0
        self.spinning = True
        self.show()
        
        if self.parentWidget() and self.disableParentWhenSpinning:
            self.parentWidget().setEnabled(False)
            
        if self.centerOnParent:
            self.center_on_parent()
            
        self.timer.start(self.timer_delay)
        
    def stop(self):
        self.spinning = False
        self.hide()
        
        if self.parentWidget() and self.disableParentWhenSpinning:
            self.parentWidget().setEnabled(True)
            
        self.timer.stop()
        
    def rotate(self):
        self.angle = (self.angle + 360/self.steps) % 360
        self.update()
        
    def center_on_parent(self):
        if self.parentWidget():
            parent = self.parentWidget()
            px = parent.width()
            py = parent.height()
            x = (px - self.width()) / 2
            y = (py - self.height()) / 2
            self.move(int(x), int(y))
            
    def paintEvent(self, event):
        if not self.spinning:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        
        outer_radius = (min(self.width(), self.height()) - 1) / 2
        inner_radius = outer_radius * 0.5
        
        center = self.rect().center()
        
        for i in range(self.steps):
            angle = math.pi * (-self.angle + (i * 360/self.steps)) / 180.0
            color = QColor(0, 0, 0)
            color.setAlphaF(1.0 - (i / self.steps))
            
            painter.setPen(QPen(color, 3))
            x1 = center.x() + math.cos(angle) * inner_radius
            y1 = center.y() + math.sin(angle) * inner_radius
            x2 = center.x() + math.cos(angle) * outer_radius
            y2 = center.y() + math.sin(angle) * outer_radius
            
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))

class WebScraperApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Modern Web Scraper")
        self.setMinimumSize(1000, 600)  
        self.theme_window = None
        self.about_window = None
        self.help_window = None
        self.settings = QSettings('ScrapApp', 'WebScraper')
        self.current_image_data = None
        self.current_image_url = None
        
        # Create loading spinner
        self.loading_spinner = LoadingSpinner(self)
        
        self.setup_ui()
        self.apply_theme(self.settings.value('theme', 'Light'))

    def setup_ui(self):
        # Status bar
        self.statusBar().showMessage("Ready")

        # Top toolbar
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        act_scrape = QAction("Scrape", self)
        act_scrape.setShortcut(QKeySequence("Ctrl+Enter"))
        act_scrape.triggered.connect(self.start_scraping)
        toolbar.addAction(act_scrape)

        act_clear = QAction("Clear", self)
        act_clear.setShortcut(QKeySequence("Ctrl+K"))
        act_clear.triggered.connect(self.clear_results)
        toolbar.addAction(act_clear)

        act_copy = QAction("Copy", self)
        act_copy.setShortcut(QKeySequence("Ctrl+C"))
        act_copy.triggered.connect(self.copy_results)
        toolbar.addAction(act_copy)

        act_save = QAction("Save", self)
        act_save.setShortcut(QKeySequence("Ctrl+S"))
        act_save.triggered.connect(self.save_results_to_file)
        toolbar.addAction(act_save)

        toolbar.addSeparator()

        act_focus_url = QAction("Focus URL", self)
        act_focus_url.setShortcut(QKeySequence("Ctrl+L"))
        act_focus_url.triggered.connect(self.focus_url)
        toolbar.addAction(act_focus_url)

        toolbar.addSeparator()

        act_themes = QAction("Themes", self)
        act_themes.triggered.connect(self.open_theme_window)
        toolbar.addAction(act_themes)

        act_help = QAction("Help", self)
        act_help.triggered.connect(self.show_help)
        toolbar.addAction(act_help)

        act_about = QAction("About", self)
        act_about.triggered.connect(self.show_about)
        toolbar.addAction(act_about)

        # Create main widget and layout
        main_widget = QWidget()
        main_layout = QHBoxLayout()

        # Create and setup sidebar
        self.sidebar = QWidget()
        self.sidebar.setMaximumWidth(200)
        self.sidebar.setMinimumWidth(200)
        sidebar_layout = QVBoxLayout()

        # Sidebar buttons
        theme_btn = QPushButton("🎨 Themes")
        theme_btn.clicked.connect(self.open_theme_window)
        help_btn = QPushButton("❓ Help")
        help_btn.clicked.connect(self.show_help)
        about_btn = QPushButton("About")
        about_btn.clicked.connect(self.show_about)

        sidebar_layout.addWidget(theme_btn)
        sidebar_layout.addWidget(help_btn)
        sidebar_layout.addWidget(about_btn)
        sidebar_layout.addStretch()
        self.sidebar.setLayout(sidebar_layout)

        # Create content widget for the main scraping interface
        content_widget = QWidget()
        content_layout = QVBoxLayout()

        # Header
        header_title = QLabel("Modern Web Scraper")
        header_title.setStyleSheet("font-size: 20px; font-weight: 600; margin: 4px 0;")
        header_sub = QLabel("Enter a URL, choose content type, and press Scrape")
        header_sub.setStyleSheet("color: #6b6b6b; margin-bottom: 8px;")
        content_layout.addWidget(header_title)
        content_layout.addWidget(header_sub)

        # URL row
        url_layout = QHBoxLayout()
        url_label = QLabel("URL:")
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("example.com or https://example.com")
        url_layout.addWidget(url_label)
        url_layout.addWidget(self.url_input)

        self.data_type_combo = QComboBox()
        self.data_type_combo.addItems(["Headings", "Links", "Text Content", "Images"])

        last_url = self.settings.value('last_url', '')
        if last_url:
            self.url_input.setText(last_url)
        last_type = self.settings.value('last_data_type', None)
        if last_type:
            idx = self.data_type_combo.findText(last_type)
            if idx >= 0:
                self.data_type_combo.setCurrentIndex(idx)

        self.url_input.editingFinished.connect(lambda: self.settings.setValue('last_url', self.url_input.text().strip()))
        self.data_type_combo.currentTextChanged.connect(lambda t: self.settings.setValue('last_data_type', t))

        url_layout.addWidget(self.data_type_combo)

        self.scrape_button = QPushButton("Scrape Website")
        self.scrape_button.clicked.connect(self.start_scraping)
        url_layout.addWidget(self.scrape_button)

        content_layout.addLayout(url_layout)

        # Inline validation/error label
        self.url_error = QLabel("")
        self.url_error.setStyleSheet("color: #c0392b; font-size: 12px;")
        content_layout.addWidget(self.url_error)

        # Utility buttons row
        utils_layout = QHBoxLayout()
        btn_clear = QPushButton("Clear")
        btn_clear.clicked.connect(self.clear_results)
        btn_copy = QPushButton("Copy")
        btn_copy.clicked.connect(self.copy_results)
        btn_save = QPushButton("Save")
        btn_save.clicked.connect(self.save_results_to_file)
        utils_layout.addWidget(btn_clear)
        utils_layout.addWidget(btn_copy)
        utils_layout.addWidget(btn_save)
        utils_layout.addStretch()
        content_layout.addLayout(utils_layout)

        # Results area
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setPlaceholderText("Scraped data will appear here...")
        content_layout.addWidget(self.results_text)

        content_widget.setLayout(content_layout)

        # Add sidebar and content to main layout
        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(content_widget)

        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

    def open_theme_window(self):
        if not self.theme_window:
            self.theme_window = ThemeWindow(self)
        self.theme_window.show()

    def clear_results(self):
        self.results_text.clear()
        self.statusBar().showMessage("Cleared", 1500)

    def copy_results(self):
        self.results_text.selectAll()
        self.results_text.copy()
        cursor = self.results_text.textCursor()
        cursor.clearSelection()
        self.results_text.setTextCursor(cursor)
        self.statusBar().showMessage("Copied", 1500)

    def save_results_to_file(self):
        text = self.results_text.toPlainText()
        if not text.strip():
            self.statusBar().showMessage("Nothing to save", 2000)
            return
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Results", "results.txt", "Text Files (*.txt)")
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(text)
                self.statusBar().showMessage(f"Saved to {file_path}", 3000)
            except Exception as e:
                QMessageBox.critical(self, "Save Error", str(e))
                self.statusBar().showMessage("Save failed", 3000)

    def focus_url(self):
        self.url_input.setFocus()
        self.url_input.selectAll()

    def closeEvent(self, event):
        try:
            self.settings.setValue('last_url', self.url_input.text().strip())
            self.settings.setValue('last_data_type', self.data_type_combo.currentText())
        finally:
            super().closeEvent(event)

    def apply_theme(self, theme):
        base_styles = """
            QWidget {
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QMainWindow {
                border: none;
            }
            QToolBar {
                spacing: 6px;
                padding: 4px 8px;
            }
            QStatusBar {
                padding: 2px 6px;
            }
            QPushButton {
                border: none;
                border-radius: 5px;
                padding: 8px 15px;
                font-weight: bold;
                min-width: 80px;
            }
            QLineEdit, QComboBox, QTextEdit {
                border-radius: 5px;
                padding: 8px;
                selection-background-color: #0078d4;
                selection-color: white;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                width: 12px;
                height: 12px;
            }
            QScrollBar:vertical {
                border: none;
                width: 12px;
                margin: 15px 0 15px 0;
            }
            QScrollBar::handle:vertical {
                border-radius: 6px;
                min-height: 30px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
        """

        if theme == "Dark":
            self.setStyleSheet(base_styles + """
                QMainWindow, QWidget {
                    background-color: #1a1a1a;
                    color: #ffffff;
                }
                QLineEdit, QComboBox, QTextEdit {
                    background-color: #2d2d2d;
                    border: 1px solid #404040;
                    color: #ffffff;
                }
                QLineEdit:focus, QComboBox:focus, QTextEdit:focus {
                    border: 2px solid #0078d4;
                }
                QPushButton {
                    background-color: #0078d4;
                    color: white;
                }
                QPushButton:hover {
                    background-color: #1084d8;
                }
                QPushButton:pressed {
                    background-color: #006cbd;
                }
                QScrollBar:vertical {
                    background-color: #2d2d2d;
                }
                QScrollBar::handle:vertical {
                    background-color: #404040;
                }
                QScrollBar::handle:vertical:hover {
                    background-color: #4d4d4d;
                }
                QComboBox {
                    background-color: #2d2d2d;
                }
                QComboBox:hover {
                    border: 1px solid #0078d4;
                }
                QComboBox::drop-down {
                    background-color: #404040;
                }
            """)
            self.sidebar.setStyleSheet("""
                QWidget {
                    background-color: #2d2d2d;
                    color: #ffffff;
                }
                QPushButton {
                    background-color: #3b3b3b;
                    color: #ffffff;
                }
                QPushButton:hover {
                    background-color: #4b4b4b;
                }
            """)
        elif theme == "Nord":
            self.setStyleSheet(base_styles + """
                QMainWindow, QWidget {
                    background-color: #2e3440;
                    color: #eceff4;
                }
                QLineEdit, QComboBox, QTextEdit {
                    background-color: #3b4252;
                    border: 1px solid #4c566a;
                    color: #eceff4;
                }
                QLineEdit:focus, QComboBox:focus, QTextEdit:focus {
                    border: 2px solid #0078d4;
                }
                QPushButton {
                    background-color: #0078d4;
                    color: white;
                }
                QPushButton:hover {
                    background-color: #1084d8;
                }
                QPushButton:pressed {
                    background-color: #006cbd;
                }
                QScrollBar:vertical {
                    background-color: #3b4252;
                }
                QScrollBar::handle:vertical {
                    background-color: #4c566a;
                }
                QScrollBar::handle:vertical:hover {
                    background-color: #5c6bc0;
                }
                QComboBox {
                    background-color: #3b4252;
                }
                QComboBox:hover {
                    border: 1px solid #0078d4;
                }
                QComboBox::drop-down {
                    background-color: #4c566a;
                }
            """)
            self.sidebar.setStyleSheet("""
                QWidget {
                    background-color: #3b4252;
                    color: #eceff4;
                }
                QPushButton {
                    background-color: #434c5e;
                    color: #eceff4;
                }
                QPushButton:hover {
                    background-color: #4c566a;
                }
            """)
        elif theme == "Solarized":
            self.setStyleSheet(base_styles + """
                QMainWindow, QWidget {
                    background-color: #002b36;
                    color: #839496;
                }
                QLineEdit, QComboBox, QTextEdit {
                    background-color: #073642;
                    border: 1px solid #586e75;
                    color: #839496;
                }
                QLineEdit:focus, QComboBox:focus, QTextEdit:focus {
                    border: 2px solid #0078d4;
                }
                QPushButton {
                    background-color: #0078d4;
                    color: white;
                }
                QPushButton:hover {
                    background-color: #1084d8;
                }
                QPushButton:pressed {
                    background-color: #006cbd;
                }
                QScrollBar:vertical {
                    background-color: #073642;
                }
                QScrollBar::handle:vertical {
                    background-color: #586e75;
                }
                QScrollBar::handle:vertical:hover {
                    background-color: #65737e;
                }
                QComboBox {
                    background-color: #073642;
                }
                QComboBox:hover {
                    border: 1px solid #0078d4;
                }
                QComboBox::drop-down {
                    background-color: #586e75;
                }
            """)
            self.sidebar.setStyleSheet("""
                QWidget {
                    background-color: #073642;
                    color: #839496;
                }
                QPushButton {
                    background-color: #094856;
                    color: #839496;
                }
                QPushButton:hover {
                    background-color: #586e75;
                }
            """)
        elif theme == "Dracula":
            self.setStyleSheet(base_styles + """
                QMainWindow, QWidget {
                    background-color: #282a36;
                    color: #f8f8f2;
                }
                QLineEdit, QComboBox, QTextEdit {
                    background-color: #3b3b4d;
                    border: 1px solid #44475a;
                    color: #f8f8f2;
                }
                QLineEdit:focus, QComboBox:focus, QTextEdit:focus {
                    border: 2px solid #0078d4;
                }
                QPushButton {
                    background-color: #0078d4;
                    color: white;
                }
                QPushButton:hover {
                    background-color: #1084d8;
                }
                QPushButton:pressed {
                    background-color: #006cbd;
                }
                QScrollBar:vertical {
                    background-color: #3b3b4d;
                }
                QScrollBar::handle:vertical {
                    background-color: #44475a;
                }
                QScrollBar::handle:vertical:hover {
                    background-color: #5c6bc0;
                }
                QComboBox {
                    background-color: #3b3b4d;
                }
                QComboBox:hover {
                    border: 1px solid #0078d4;
                }
                QComboBox::drop-down {
                    background-color: #44475a;
                }
            """)
            self.sidebar.setStyleSheet("""
                QWidget {
                    background-color: #44475a;
                    color: #f8f8f2;
                }
                QPushButton {
                    background-color: #4a4d64;
                    color: #f8f8f2;
                }
                QPushButton:hover {
                    background-color: #6272a4;
                }
            """)
        else:  # Light
            self.setStyleSheet(base_styles + """
                QMainWindow, QWidget {
                    background-color: #ffffff;
                    color: #333333;
                }
                QLineEdit, QComboBox, QTextEdit {
                    background-color: white;
                    border: 1px solid #dddddd;
                    color: #333333;
                }
                QLineEdit:focus, QComboBox:focus, QTextEdit:focus {
                    border: 2px solid #0078d4;
                }
                QPushButton {
                    background-color: #0078d4;
                    color: white;
                }
                QPushButton:hover {
                    background-color: #1084d8;
                }
                QPushButton:pressed {
                    background-color: #006cbd;
                }
                QScrollBar:vertical {
                    background-color: #f5f5f5;
                }
                QScrollBar::handle:vertical {
                    background-color: #dddddd;
                }
                QScrollBar::handle:vertical:hover {
                    background-color: #c1c1c1;
                }
                QComboBox {
                    background-color: white;
                }
                QComboBox:hover {
                    border: 1px solid #0078d4;
                }
                QComboBox::drop-down {
                    background-color: #dddddd;
                }
            """)
            self.sidebar.setStyleSheet("""
                QWidget {
                    background-color: #f0f0f0;
                    color: #333333;
                }
                QPushButton {
                    background-color: #e0e0e0;
                    color: #333333;
                }
                QPushButton:hover {
                    background-color: #d0d0d0;
                }
            """)

    def start_scraping(self):
        raw = self.url_input.text().strip()
        if not raw:
            self.url_error.setText("Please enter a URL.")
            self.url_input.setFocus()
            return

        if not raw.startswith(("http://", "https://")):
            candidate = "https://" + raw
        else:
            candidate = raw

        parsed = urlparse(candidate)
        if not parsed.netloc:
            self.url_error.setText("Invalid URL. Try e.g. https://example.com")
            self.url_input.setFocus()
            return

        self.url_error.clear()
        url = candidate

        self.scrape_button.setEnabled(False)
        self.results_text.clear()
        self.results_text.setPlaceholderText("Scraping in progress...")

        # Start the loading spinner
        self.loading_spinner.start()
        self.statusBar().showMessage("Scraping...")

        data_type = self.data_type_combo.currentText()
        self.settings.setValue('last_url', url)
        self.settings.setValue('last_data_type', data_type)
        self.scraper_thread = ScraperThread(url, data_type)
        self.scraper_thread.finished.connect(self.on_scraping_finished)
        self.scraper_thread.error.connect(self.on_scraping_error)
        self.scraper_thread.images_found.connect(self.on_images_found)
        self.scraper_thread.start()
        self.results_text.setText("Scraping in progress...")

    def on_scraping_finished(self, result):
        # Stop the loading spinner
        self.loading_spinner.stop()
        self.results_text.setPlainText(result)
        self.scrape_button.setEnabled(True)
        self.results_text.setPlaceholderText("Scraped data will appear here...")
        self.statusBar().showMessage("Done", 3000)

    def on_scraping_error(self, error_msg):
        # Stop the loading spinner
        self.loading_spinner.stop()
        self.results_text.setPlainText(f"Error: {error_msg}")
        self.scrape_button.setEnabled(True)
        self.results_text.setPlaceholderText("Scraped data will appear here...")
        self.statusBar().showMessage("Error", 4000)

    def on_images_found(self, image_list):
        # Stop the loading spinner before showing dialog
        self.loading_spinner.stop()
        
        reply = QMessageBox.question(
            self,
            'Save Images',
            f'Would you like to save {len(image_list)} images?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Start spinner again for saving process
            self.loading_spinner.start()
            
            save_dir = QFileDialog.getExistingDirectory(
                self,
                "Select Directory to Save Images",
                "",
                QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks
            )
            
            if save_dir:
                progress = QProgressDialog("Saving images...", "Cancel", 0, len(image_list), self)
                progress.setWindowTitle("Saving Images")
                progress.setWindowModality(Qt.WindowModality.WindowModal)
                progress.setValue(0)

                saved_count = 0
                for i, (img_url, img_data) in enumerate(image_list):
                    if progress.wasCanceled():
                        break
                    try:
                        filename = os.path.basename(img_url.split('?')[0])
                        if not filename:
                            filename = f"image_{saved_count + 1}.jpg"

                        file_path = os.path.join(save_dir, filename)

                        base, ext = os.path.splitext(filename)
                        counter = 1
                        while os.path.exists(file_path):
                            file_path = os.path.join(save_dir, f"{base}_{counter}{ext}")
                            counter += 1

                        with open(file_path, 'wb') as f:
                            f.write(img_data)
                        saved_count += 1
                    except Exception as e:
                        self.results_text.append(f"\nError saving image {img_url}: {str(e)}")
                    finally:
                        progress.setValue(i + 1)
                        QApplication.processEvents()

                progress.close()
                self.results_text.append(f"\nSuccessfully saved {saved_count} images to {save_dir}")

            # Stop spinner after saving is complete
            self.loading_spinner.stop()

    def show_about(self):
        # Create about window
        self.about_window = QWidget()
        self.about_window.setWindowTitle("About")
        self.about_window.setMinimumSize(500, 400)
        
        # Create layout
        layout = QVBoxLayout()
        
        # Add title and description
        title = QLabel("Modern Web Scraper")
        title.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 10px;")
        
        description = QLabel("A powerful and user-friendly web scraping tool built with PyQt6.")
        description.setWordWrap(True)
        
        # Add work/demo button
        work_btn = QPushButton("🚀 See How It Works")
        work_btn.clicked.connect(self.show_demo)
        
        # Add widgets to layout
        layout.addWidget(title)
        layout.addWidget(description)
        layout.addWidget(work_btn)
        layout.addStretch()
        
        self.about_window.setLayout(layout)
        self.about_window.show()
    
    def show_demo(self):
        # Set demo URL and configuration
        self.url_input.setText("https://example.com")
        self.data_type_combo.setCurrentText("Headings")
        
        # Add demo instructions to results
        demo_text = """Demo Mode:
1. We've pre-filled a sample URL (example.com)
2. Selected 'Headings' as the content type to scrape
3. Click 'Scrape Website' to see it in action!

This demo shows how to:
- Enter a URL to scrape
- Select content type (Headings, Links, Text, Images)
- Get structured results from any webpage"""
        
        self.results_text.setPlainText(demo_text)

    def show_help(self):
        # Create help window
        self.help_window = QWidget()
        self.help_window.setWindowTitle("Help - How to Use")
        self.help_window.setMinimumSize(600, 500)
        
        # Create layout
        layout = QVBoxLayout()
        
        # Add title
        title = QLabel("How to Use the Web Scraper")
        title.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 20px;")
        
        # Add help content
        help_text = QTextEdit()
        help_text.setReadOnly(True)
        help_text.setHtml("""
            <h2>Quick Start Guide</h2>
            <ol>
                <li><b>Enter a URL:</b> Type or paste the website URL you want to scrape in the URL input field.</li>
                <li><b>Select Content Type:</b> Choose what type of content you want to extract:
                    <ul>
                        <li><b>Headings:</b> Extracts all H1, H2, and H3 headings</li>
                        <li><b>Links:</b> Gets all hyperlinks with their text and URLs</li>
                        <li><b>Text Content:</b> Extracts paragraph text from the page</li>
                        <li><b>Images:</b> Gets URLs of all images on the page</li>
                    </ul>
                </li>
                <li><b>Click "Scrape Website":</b> The app will fetch and display the requested content.</li>
            </ol>

            <h2>Features</h2>
            <ul>
                <li><b>Themes:</b> Click the Themes button to customize the app's appearance</li>
                <li><b>Auto URL Fix:</b> The app automatically adds 'https://' if needed</li>
                <li><b>Error Handling:</b> Clear error messages if something goes wrong</li>
            </ul>

            <h2>Tips</h2>
            <ul>
                <li>Make sure you have permission to scrape the target website</li>
                <li>Some websites may block automated scraping</li>
                <li>For best results, use complete URLs including 'https://'</li>
                <li>The results area is scrollable for viewing long content</li>
            </ul>

            <h2>Troubleshooting</h2>
            <ul>
                <li><b>No Results:</b> Check your internet connection and URL</li>
                <li><b>Access Denied:</b> The website might be blocking scrapers</li>
                <li><b>Incomplete Data:</b> Try a different content type</li>
            </ul>
        """)
        
        # Add widgets to layout
        layout.addWidget(title)
        layout.addWidget(help_text)
        
        # Set the layout
        self.help_window.setLayout(layout)
        self.help_window.show()
