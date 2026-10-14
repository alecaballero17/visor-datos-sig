"""
SIG Vector Studio - Main Launcher
Editor cartográfico modular con visión por computadora para VisorDatosSIG.
"""
import sys
import os
from pathlib import Path

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from sig_vector_studio.gui.main_window import MainWindow
from sig_vector_studio.gui.styles import DARK_THEME_QSS

def main():
    # Enable High DPI scaling
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    
    app = QApplication(sys.argv)
    app.setApplicationName("SIG Vector Studio")
    app.setOrganizationName("SIG")
    
    # Apply modern Dark Slate stylesheet
    app.setStyleSheet(DARK_THEME_QSS)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
