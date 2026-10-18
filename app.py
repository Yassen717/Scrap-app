import math
import os
import re
from urllib.parse import unquote, urlparse, urlunparse

from PyQt6.QtCore import (QEvent, QSettings, QSize, Qt, QThread, QTimer,
                          pyqtSignal)
from PyQt6.QtGui import (QAction, QColor, QFont, QKeySequence, QPainter,
                         QPen)
from PyQt6.QtWidgets import (QApplication, QComboBox, QDialog, QFileDialog,
                             QFrame, QHBoxLayout, QLabel, QLineEdit,
                             QMainWindow, QPlainTextEdit, QProgressBar,
                             QPushButton, QSizePolicy, QTextEdit, QToolBar,
                             QVBoxLayout, QWidget)

import theme as theme_mod
from theme import ThemeWindow
from scraper import ScraperThread

STATUS_SHORT = 2000
STATUS_LONG = 5000

_WINDOWS_RESERVED = ({"CON", "PRN", "AUX", "NUL", "CLOCK$"}
                     | {f"{p}{i}" for p in ("COM", "LPT") for i in range(1, 10)})
_BAD_FILENAME_CHARS = re.compile(
    r'[<>:\"/\\|?*\x00-\x1f]|[\u200e\u200f\u202a-\u202e\u2066-\u2069]')
_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".ico",
               ".svg", ".avif", ".tif", ".tiff"}


def _image_extension(url, data):
    """Pick a safe extension, preferring magic bytes over the URL."""
    head = data[:16]
    if head[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if head[:3] == b"\xff\xd8\xff":
        return ".jpg"
    if head[:6] in (b"GIF87a", b"GIF89a"):
        return ".gif"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return ".webp"
    if head[:2] == b"BM":
        return ".bmp"
    if head[:4] == b"\x00\x00\x01\x00":
        return ".ico"
    if head[:4] in (b"II*\x00", b"MM\x00*"):
        return ".tiff"
    if head[4:8] == b"ftyp" and head[8:12] in (b"avif", b"avis"):
        return ".avif"
    stripped = data[:512].lstrip().lower()
    if stripped.startswith(b"<svg") or (stripped.startswith(b"<?xml")
                                       and b"<svg" in stripped):
        return ".svg"
    ext = os.path.splitext(urlparse(url).path)[1].lower()
    return ext if ext in _IMAGE_EXTS else ".jpg"


def _safe_image_name(url, data, index):
    """Build a Windows-safe filename from a remote-controlled URL."""
    raw = unquote(urlparse(url).path.rsplit("/", 1)[-1])
    stem = _BAD_FILENAME_CHARS.sub("_", os.path.splitext(raw)[0])
    stem = stem.rstrip(" .")[:80]
    if not stem or stem.upper() in _WINDOWS_RESERVED:
        stem = f"image_{index}"
    return stem + _image_extension(url, data)


class ImageSaverThread(QThread):
    """Writes downloaded image bytes to disk off the UI thread."""

    progress = pyqtSignal(int, int)
    done = pyqtSignal(int, int, str)  # saved, failed, directory

    def __init__(self, items, dest_dir, parent=None):
        super().__init__(parent)
        self._items = items
        self._dest = dest_dir

    def run(self):
        saved = 0
        failed = 0
        total = len(self._items)
        for i, (url, data) in enumerate(self._items, 1):
            try:
                name = _safe_image_name(url, data, i)
                path = os.path.join(self._dest, name)
                stem, ext = os.path.splitext(name)
                counter = 1
                while os.path.exists(path):
                    path = os.path.join(self._dest,
                                        f"{stem}_{counter}{ext}")
                    counter += 1
                with open(path, "wb") as fh:
                    fh.write(data)
                saved += 1
            except OSError:
                failed += 1
            self.progress.emit(i, total)
        self.done.emit(saved, failed, self._dest)


class LoadingSpinner(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.spinning = False
        self.angle = 0
        self.color = QColor(0, 0, 0)
        self.steps = 12
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._rotate)
        self.setMinimumSize(QSize(40, 40))
        self.setMaximumSize(QSize(40, 40))
        if parent is not None:
            parent.installEventFilter(self)
        self.hide()

    def set_color(self, color):
        self.color = QColor(color)
        self.update()

    def start(self):
        self.angle = 0
        self.spinning = True
        self._center_on_parent()
        self.show()
        self.raise_()
        self.timer.start(80)

    def stop(self):
        self.spinning = False
        self.timer.stop()
        self.hide()

    def eventFilter(self, obj, event):
        if (obj is self.parentWidget()
                and event.type() == QEvent.Type.Resize):
            self._center_on_parent()
        return super().eventFilter(obj, event)

    def _rotate(self):
        self.angle = (self.angle + 360 / self.steps) % 360
        self.update()

    def _center_on_parent(self):
        parent = self.parentWidget()
        if parent:
            x = (parent.width() - self.width()) / 2
            y = (parent.height() - self.height()) / 2
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
            angle = math.pi * (-self.angle + i * 360 / self.steps) / 180.0
            color = QColor(self.color)
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
        self.setMinimumSize(780, 520)
        self.settings = QSettings("ScrapApp", "WebScraper")
        self.scraper_thread = None
        self.saver_thread = None
        self._pending_images = None
        self.theme_window = None
        self.about_dialog = None
        self.help_dialog = None

        self.loading_spinner = LoadingSpinner(self)

        self._build_actions()
        self._build_ui()
        self._restore_state()
        self.apply_theme(self.settings.value("theme", "Light"))

    # ------------------------------------------------------------------ UI

    def _build_actions(self):
        def make(text, shortcut, tip, slot):
            action = QAction(text, self)
            if shortcut is not None:
                action.setShortcut(shortcut)
            action.setToolTip(tip)
            action.setStatusTip(tip)
            action.triggered.connect(slot)
            return action

        self.act_scrape = make("Scrape", QKeySequence("Ctrl+Return"),
                               "Scrape the entered URL (Ctrl+Enter)",
                               self.start_scraping)
        self.act_cancel = make("Cancel", None,
                               "Cancel the running scrape",
                               self.cancel_scrape)
        self.act_cancel.setEnabled(False)
        self.act_clear = make("Clear", QKeySequence("Ctrl+K"),
                              "Clear results (Ctrl+K)", self.clear_results)
        self.act_copy = make("Copy All", QKeySequence("Ctrl+Shift+C"),
                             "Copy all results (Ctrl+Shift+C)",
                             self.copy_results)
        self.act_save = make("Save", QKeySequence("Ctrl+S"),
                             "Save results to a file (Ctrl+S)",
                             self.save_results_to_file)
        self.act_themes = make("Themes", None, "Change the color theme",
                               self.open_theme_window)
        self.act_help = make(
            "Help", QKeySequence(QKeySequence.StandardKey.HelpContents),
            "How to use the app (F1)", self.show_help)
        self.act_about = make("About", None, "About Modern Web Scraper",
                              self.show_about)
        self.act_focus_url = make("Focus URL", QKeySequence("Ctrl+L"),
                                  "Jump to the URL field (Ctrl+L)",
                                  self.focus_url)
        # Shortcut-only action: registered on the window, not the toolbar.
        self.addAction(self.act_focus_url)

    def _build_ui(self):
        self.statusBar().showMessage("Ready")
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(220)
        self.progress_bar.hide()
        self.statusBar().addPermanentWidget(self.progress_bar)

        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        for action in (self.act_scrape, self.act_cancel):
            toolbar.addAction(action)
        toolbar.addSeparator()
        for action in (self.act_clear, self.act_copy, self.act_save):
            toolbar.addAction(action)
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding,
                             QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)
        for action in (self.act_themes, self.act_help, self.act_about):
            toolbar.addAction(action)
        self.addToolBar(toolbar)

        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(8)

        url_row = QHBoxLayout()
        url_row.setSpacing(8)
        url_label = QLabel("&URL:")
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("example.com or https://example.com")
        self.url_input.setAccessibleName("Website URL")
        url_label.setBuddy(self.url_input)
        self.url_input.returnPressed.connect(self.start_scraping)
        self.url_input.textChanged.connect(lambda _t: self.url_error.clear())
        self.url_input.editingFinished.connect(
            lambda: self.settings.setValue(
                "last_url", self.url_input.text().strip()))

        self.data_type_combo = QComboBox()
        self.data_type_combo.addItems(
            ["Headings", "Links", "Text Content", "Images"])
        self.data_type_combo.setAccessibleName("Content type")
        self.data_type_combo.currentTextChanged.connect(
            lambda t: self.settings.setValue("last_data_type", t))

        self.scrape_button = QPushButton("Scrape Website")
        self.scrape_button.setObjectName("primaryButton")
        self.scrape_button.clicked.connect(self._primary_clicked)

        url_row.addWidget(url_label)
        url_row.addWidget(self.url_input, 1)
        url_row.addWidget(self.data_type_combo)
        url_row.addWidget(self.scrape_button)
        root.addLayout(url_row)

        self.url_error = QLabel("")
        self.url_error.setObjectName("errorLabel")
        root.addWidget(self.url_error)

        self.save_banner = QFrame()
        self.save_banner.setObjectName("saveBanner")
        banner_layout = QHBoxLayout(self.save_banner)
        banner_layout.setContentsMargins(10, 6, 10, 6)
        self.banner_label = QLabel("")
        save_button = QPushButton("Save to folder…")
        save_button.clicked.connect(self._save_pending_images)
        dismiss_button = QPushButton("Dismiss")
        dismiss_button.clicked.connect(self.save_banner.hide)
        banner_layout.addWidget(self.banner_label, 1)
        banner_layout.addWidget(save_button)
        banner_layout.addWidget(dismiss_button)
        self.save_banner.hide()
        root.addWidget(self.save_banner)

        self.results_text = QPlainTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setPlaceholderText("Scraped data will appear here…")
        self.results_text.setAccessibleName("Results")
        root.addWidget(self.results_text, 1)

        self.setCentralWidget(central)

    def _restore_state(self):
        last_url = self.settings.value("last_url", "")
        if last_url:
            self.url_input.setText(last_url)
        last_type = self.settings.value("last_data_type", None)
        if last_type:
            idx = self.data_type_combo.findText(last_type)
            if idx >= 0:
                self.data_type_combo.setCurrentIndex(idx)
        geometry = self.settings.value("geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)

    # ------------------------------------------------------------- Theming

    def apply_theme(self, name):
        if name not in theme_mod.THEMES:
            name = "Light"
        palette = theme_mod.apply_theme(name)
        self.loading_spinner.set_color(QColor(palette["spinner"]))
        self.settings.setValue("theme", name)

    def open_theme_window(self):
        if self.theme_window is None:
            self.theme_window = ThemeWindow(self)
        self.theme_window.show()
        self.theme_window.raise_()
        self.theme_window.activateWindow()

    # ----------------------------------------------------------- Scraping

    def _running(self):
        return (self.scraper_thread is not None
                and self.scraper_thread.isRunning())

    def _primary_clicked(self):
        if self._running():
            self.cancel_scrape()
        else:
            self.start_scraping()

    def _validated_url(self):
        raw = self.url_input.text().strip()
        if not raw:
            self.url_error.setText("Please enter a URL.")
            return None
        if re.search(r"\s", raw):
            self.url_error.setText("URL must not contain spaces.")
            return None
        if "://" in raw and not raw.lower().startswith(("http://", "https://")):
            self.url_error.setText(
                "Only http:// and https:// URLs are supported.")
            return None
        candidate = (raw if raw.lower().startswith(("http://", "https://"))
                     else "https://" + raw)
        try:
            parsed = urlparse(candidate)
            if parsed.scheme not in ("http", "https") or not parsed.hostname:
                raise ValueError("bad scheme or missing host")
            if parsed.username or parsed.password:
                netloc = parsed.hostname
                if parsed.port:
                    netloc += f":{parsed.port}"
                parsed = parsed._replace(netloc=netloc)
                self.statusBar().showMessage(
                    "Removed credentials from the URL", STATUS_LONG)
            candidate = urlunparse(parsed)
        except ValueError:
            self.url_error.setText(
                "Invalid URL — try e.g. https://example.com")
            return None
        return candidate

    def _set_busy(self, busy):
        self.url_input.setEnabled(not busy)
        self.data_type_combo.setEnabled(not busy)
        self.act_scrape.setEnabled(not busy)
        self.act_cancel.setEnabled(busy)
        self.scrape_button.setText("Cancel" if busy else "Scrape Website")

    def start_scraping(self):
        if self._running():
            return
        url = self._validated_url()
        if url is None:
            self.url_input.setFocus()
            return

        self.url_error.clear()
        self.url_input.setText(url)
        self.settings.setValue("last_url", url)
        data_type = self.data_type_combo.currentText()
        self.settings.setValue("last_data_type", data_type)

        self.save_banner.hide()
        self._pending_images = None
        self.results_text.clear()
        self.results_text.setPlaceholderText("Scraping in progress…")
        self.progress_bar.hide()
        self.loading_spinner.start()
        self.statusBar().showMessage("Scraping…")
        self._set_busy(True)

        thread = ScraperThread(url, data_type)
        thread.result_ready.connect(self._on_result)
        thread.error.connect(self._on_error)
        thread.images_found.connect(self._on_images_found)
        thread.progress.connect(self._on_download_progress)
        thread.finished.connect(self._on_thread_done)
        thread.finished.connect(thread.deleteLater)
        self.scraper_thread = thread
        thread.start()

    def cancel_scrape(self):
        if self._running():
            self.scraper_thread.requestInterruption()
            self.statusBar().showMessage("Cancelling…")

    # ------------------------------------------------------------ Slots

    def _on_result(self, text):
        self.results_text.setPlainText(text)
        self.statusBar().showMessage("Done", STATUS_SHORT)

    def _on_error(self, message):
        self.results_text.setPlainText(f"Error: {message}")
        self.statusBar().showMessage("Scrape failed", STATUS_LONG)

    def _on_images_found(self, images, summary):
        self.results_text.setPlainText(summary)
        self.statusBar().showMessage("Done", STATUS_SHORT)
        self._pending_images = images or None
        if images:
            count = len(images)
            self.banner_label.setText(
                f"{count} image{'s' if count != 1 else ''} "
                "downloaded — save them to a folder?")
            self.save_banner.show()

    def _on_download_progress(self, done, total):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(done)
        if not self.progress_bar.isVisible():
            self.progress_bar.show()
        self.statusBar().showMessage(f"Downloading images… {done}/{total}")

    def _on_save_progress(self, done, total):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(done)
        if not self.progress_bar.isVisible():
            self.progress_bar.show()
        self.statusBar().showMessage(f"Saving images… {done}/{total}")

    def _on_thread_done(self):
        self.loading_spinner.stop()
        self._set_busy(False)
        self.progress_bar.hide()
        self.results_text.setPlaceholderText(
            "Scraped data will appear here…")
        if not self.results_text.toPlainText().strip():
            self.results_text.setPlainText("Cancelled.")
            self.statusBar().showMessage("Cancelled", STATUS_SHORT)
        self.scraper_thread = None

    def _save_pending_images(self):
        if not self._pending_images:
            return
        if self.saver_thread is not None and self.saver_thread.isRunning():
            return
        dest = QFileDialog.getExistingDirectory(
            self, "Select folder to save images")
        if not dest:
            return
        self.save_banner.hide()
        items = self._pending_images
        self._pending_images = None
        saver = ImageSaverThread(items, dest, self)
        saver.progress.connect(self._on_save_progress)
        saver.done.connect(self._on_save_done)
        saver.finished.connect(saver.deleteLater)
        self.saver_thread = saver
        saver.start()

    def _on_save_done(self, saved, failed, dest):
        message = f"Saved {saved} image{'s' if saved != 1 else ''} to {dest}"
        if failed:
            message += f" ({failed} failed)"
        self.results_text.appendPlainText(f"\n{message}")
        self.statusBar().showMessage(message, STATUS_LONG)
        self.progress_bar.hide()
        self.saver_thread = None

    # ------------------------------------------------------------ Actions

    def clear_results(self):
        self.results_text.clear()
        self.results_text.setPlaceholderText(
            "Scraped data will appear here…")
        self.save_banner.hide()
        self._pending_images = None
        self.statusBar().showMessage("Cleared", STATUS_SHORT)

    def copy_results(self):
        text = self.results_text.toPlainText()
        if not text.strip():
            self.statusBar().showMessage("Nothing to copy", STATUS_SHORT)
            return
        QApplication.clipboard().setText(text)
        self.statusBar().showMessage("Copied all results", STATUS_SHORT)

    def save_results_to_file(self):
        text = self.results_text.toPlainText()
        if not text.strip():
            self.statusBar().showMessage("Nothing to save", STATUS_SHORT)
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Results", "results.txt", "Text Files (*.txt)")
        if not file_path:
            return
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(text)
            self.statusBar().showMessage(
                f"Saved to {file_path}", STATUS_LONG)
        except OSError as e:
            self.url_error.setText(f"Save failed: {e}")
            self.statusBar().showMessage("Save failed", STATUS_LONG)

    def focus_url(self):
        self.url_input.setFocus()
        self.url_input.selectAll()

    def closeEvent(self, event):
        self.settings.setValue("last_url", self.url_input.text().strip())
        self.settings.setValue("last_data_type",
                               self.data_type_combo.currentText())
        self.settings.setValue("geometry", self.saveGeometry())

        thread = self.scraper_thread
        if thread is not None and thread.isRunning():
            thread.requestInterruption()
            if not thread.wait(3000):
                thread.terminate()
                thread.wait(1000)
        saver = self.saver_thread
        if saver is not None and saver.isRunning():
            if not saver.wait(3000):
                saver.terminate()
                saver.wait(1000)
        super().closeEvent(event)

    # ------------------------------------------------------------ Dialogs

    def show_about(self):
        if self.about_dialog is None:
            self.about_dialog = self._build_about_dialog()
        self.about_dialog.show()
        self.about_dialog.raise_()
        self.about_dialog.activateWindow()

    def _build_about_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("About")
        dialog.setMinimumWidth(420)

        layout = QVBoxLayout(dialog)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("Modern Web Scraper")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        layout.addWidget(title)

        description = QLabel(
            "A web scraping tool built with PyQt6. Enter a URL, choose what "
            "to extract, and get headings, links, text, or images from any "
            "web page — all without freezing the UI.")
        description.setWordWrap(True)
        layout.addWidget(description)

        demo_button = QPushButton("Try a demo")
        demo_button.clicked.connect(self.show_demo)
        layout.addWidget(demo_button)

        license_note = QLabel(
            "Code under MIT. Uses PyQt6 (GPL-3.0/commercial) — "
            "distributing binaries triggers GPL terms.")
        license_note.setObjectName("mutedLabel")
        license_note.setWordWrap(True)
        layout.addWidget(license_note)

        layout.addStretch()
        close_button = QPushButton("Close")
        close_button.clicked.connect(dialog.close)
        layout.addWidget(close_button, alignment=Qt.AlignmentFlag.AlignRight)
        return dialog

    def show_demo(self):
        if self._running():
            return
        self.url_input.setText("https://example.com")
        self.data_type_combo.setCurrentText("Headings")
        self.results_text.setPlainText(
            "Demo mode:\n"
            "1. A sample URL (example.com) is filled in above\n"
            "2. 'Headings' is selected as the content type\n"
            "3. Press 'Scrape Website' or Ctrl+Enter to run it")
        self.statusBar().showMessage(
            "Demo ready — press Scrape", STATUS_LONG)
        self.focus_url()
        self.url_input.end(False)

    def show_help(self):
        if self.help_dialog is None:
            self.help_dialog = self._build_help_dialog()
        self.help_dialog.show()
        self.help_dialog.raise_()
        self.help_dialog.activateWindow()

    def _build_help_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Help")
        dialog.setMinimumSize(560, 480)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel("How to use Modern Web Scraper")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        layout.addWidget(title)

        help_text = QTextEdit()
        help_text.setReadOnly(True)
        help_text.setHtml("""
            <h3>Quick start</h3>
            <ol>
                <li><b>Enter a URL</b> — type or paste the site to scrape
                    (the <code>https://</code> prefix is added for you).</li>
                <li><b>Pick a content type:</b>
                    <ul>
                        <li><b>Headings</b> — all headings H1–H6, indented
                            by level</li>
                        <li><b>Links</b> — every link as
                            <i>text - absolute URL</i></li>
                        <li><b>Text Content</b> — paragraphs, quotes and
                            list items</li>
                        <li><b>Images</b> — downloads up to 50 images in
                            parallel, then lets you save them to a folder
                            with clean filenames</li>
                    </ul></li>
                <li><b>Click Scrape</b> (or press Enter) — results appear
                    below; press Cancel to abort a slow scrape.</li>
            </ol>

            <h3>Keyboard shortcuts</h3>
            <table cellspacing="6">
                <tr><td><b>Ctrl+Enter</b></td><td>Scrape</td></tr>
                <tr><td><b>Ctrl+L</b></td><td>Focus the URL field</td></tr>
                <tr><td><b>Ctrl+K</b></td><td>Clear results</td></tr>
                <tr><td><b>Ctrl+Shift+C</b></td><td>Copy all results</td></tr>
                <tr><td><b>Ctrl+S</b></td><td>Save results to a file</td></tr>
                <tr><td><b>F1</b></td><td>This help</td></tr>
            </table>

            <h3>Tips</h3>
            <ul>
                <li>Make sure you have permission to scrape the target
                    site and respect its robots.txt and rate limits.</li>
                <li>Some sites block automated tools — an HTTP 403 usually
                    means the site refused.</li>
                <li>Very large pages and images are skipped past 20 MB.</li>
                <li>Themes apply instantly to every window.</li>
            </ul>

            <h3>Troubleshooting</h3>
            <ul>
                <li><b>No results:</b> check the URL and your
                    connection.</li>
                <li><b>HTTP 4xx/5xx:</b> the site blocked the request or
                    the page doesn't exist.</li>
                <li><b>Timeout:</b> the server is slow — try again or pick
                    a lighter page.</li>
            </ul>
        """)
        layout.addWidget(help_text, 1)

        close_button = QPushButton("Close")
        close_button.clicked.connect(dialog.close)
        layout.addWidget(close_button,
                         alignment=Qt.AlignmentFlag.AlignRight)
        return dialog
