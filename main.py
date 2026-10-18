import sys

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import QApplication


def _make_icon():
    """Draw a simple rounded-square app icon."""
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor("#0078d4"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(2, 2, 60, 60, 14, 14)
    painter.setPen(QColor("#ffffff"))
    painter.setFont(QFont("Segoe UI", 30, QFont.Weight.Bold))
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "S")
    painter.end()
    return QIcon(pixmap)


def main():
    app = QApplication(sys.argv)
    app.setOrganizationName("ScrapApp")
    app.setApplicationName("WebScraper")
    app.setApplicationDisplayName("Modern Web Scraper")
    app.setWindowIcon(_make_icon())

    from app import WebScraperApp
    window = WebScraperApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
