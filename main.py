import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from main_window import MainWindow

def main():
    # Habilitar High DPI para mejor visualización
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    app = QApplication(sys.argv)
    app.setApplicationName("Icon Editor Pro")
    app.setOrganizationName("IconEditor")
    
    # Estilo moderno
    app.setStyle("Fusion")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()