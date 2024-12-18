import sys
from PyQt6.QtWidgets import QApplication
from app import WebScraperApp

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = WebScraperApp()
    window.show()
    sys.exit(app.exec())