"""
Estilos para la interfaz de usuario.
Incluye temas claro y oscuro.
"""

# Tema oscuro (por defecto)
DARK_STYLE = """
QMainWindow {
    background-color: #1e1e1e;
}

QWidget {
    background-color: #1e1e1e;
    color: #ffffff;
}

QGroupBox {
    font-weight: bold;
    border: 1px solid #3a3a3a;
    border-radius: 5px;
    margin-top: 10px;
    padding-top: 10px;
    background-color: #252526;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px 0 5px;
    color: #ffffff;
}

QPushButton {
    background-color: #3c3c3c;
    border: 1px solid #4a4a4a;
    border-radius: 4px;
    padding: 6px 12px;
    color: #ffffff;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #4a4a4a;
    border-color: #5a5a5a;
}

QPushButton:pressed {
    background-color: #2a2a2a;
}

QPushButton:checked {
    background-color: #0e639c;
    border: 1px solid #1e7ab3;
}

QPushButton:disabled {
    background-color: #2a2a2a;
    color: #6a6a6a;
}

QComboBox, QSpinBox, QLineEdit {
    background-color: #3c3c3c;
    border: 1px solid #4a4a4a;
    border-radius: 4px;
    padding: 5px 8px;
    color: #ffffff;
}

QComboBox:hover, QSpinBox:hover, QLineEdit:hover {
    border-color: #5a5a5a;
}

QComboBox:focus, QSpinBox:focus, QLineEdit:focus {
    border-color: #0e639c;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QComboBox::down-arrow {
    image: url(down_arrow_dark.png);
    width: 12px;
    height: 12px;
}

QSlider::groove:horizontal {
    border: 1px solid #3a3a3a;
    height: 6px;
    background: #3c3c3c;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #0e639c;
    border: 1px solid #1e7ab3;
    width: 16px;
    margin: -5px 0;
    border-radius: 8px;
}

QSlider::handle:horizontal:hover {
    background: #1e7ab3;
    border-color: #2e8ab3;
}

QCheckBox {
    color: #ffffff;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 1px solid #4a4a4a;
    border-radius: 3px;
    background-color: #3c3c3c;
}

QCheckBox::indicator:checked {
    background-color: #0e639c;
    border: 1px solid #1e7ab3;
}

QCheckBox::indicator:hover {
    border-color: #5a5a5a;
}

QScrollBar:vertical {
    background: #252526;
    width: 14px;
    border-radius: 7px;
}

QScrollBar::handle:vertical {
    background: #3c3c3c;
    border-radius: 7px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background: #4a4a4a;
}

QScrollBar:horizontal {
    background: #252526;
    height: 14px;
    border-radius: 7px;
}

QScrollBar::handle:horizontal {
    background: #3c3c3c;
    border-radius: 7px;
    min-width: 20px;
}

QScrollBar::handle:horizontal:hover {
    background: #4a4a4a;
}

QStatusBar {
    background-color: #1e1e1e;
    color: #aaaaaa;
    border-top: 1px solid #3a3a3a;
}

QMenuBar {
    background-color: #1e1e1e;
    color: #ffffff;
    border-bottom: 1px solid #3a3a3a;
}

QMenuBar::item:selected {
    background-color: #3c3c3c;
}

QMenu {
    background-color: #252526;
    border: 1px solid #3a3a3a;
    color: #ffffff;
}

QMenu::item:selected {
    background-color: #0e639c;
}

QLabel {
    color: #ffffff;
}

QTabWidget::pane {
    border: 1px solid #3a3a3a;
    background-color: #252526;
}

QTabBar::tab {
    background-color: #3c3c3c;
    color: #ffffff;
    padding: 8px 16px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}

QTabBar::tab:selected {
    background-color: #0e639c;
}

QTabBar::tab:hover:!selected {
    background-color: #4a4a4a;
}

QDialog {
    background-color: #252526;
}
"""

# Tema claro
LIGHT_STYLE = """
QMainWindow {
    background-color: #f0f0f0;
}

QWidget {
    background-color: #f0f0f0;
    color: #1e1e1e;
}

QGroupBox {
    font-weight: bold;
    border: 1px solid #c0c0c0;
    border-radius: 5px;
    margin-top: 10px;
    padding-top: 10px;
    background-color: #fafafa;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px 0 5px;
    color: #1e1e1e;
}

QPushButton {
    background-color: #e0e0e0;
    border: 1px solid #c0c0c0;
    border-radius: 4px;
    padding: 6px 12px;
    color: #1e1e1e;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #d0d0d0;
    border-color: #a0a0a0;
}

QPushButton:pressed {
    background-color: #c0c0c0;
}

QPushButton:checked {
    background-color: #0078d4;
    border: 1px solid #1060b3;
    color: white;
}

QPushButton:disabled {
    background-color: #e8e8e8;
    color: #808080;
}

QComboBox, QSpinBox, QLineEdit {
    background-color: #ffffff;
    border: 1px solid #c0c0c0;
    border-radius: 4px;
    padding: 5px 8px;
    color: #1e1e1e;
}

QComboBox:hover, QSpinBox:hover, QLineEdit:hover {
    border-color: #a0a0a0;
}

QComboBox:focus, QSpinBox:focus, QLineEdit:focus {
    border-color: #0078d4;
}

QSlider::groove:horizontal {
    border: 1px solid #c0c0c0;
    height: 6px;
    background: #e0e0e0;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #0078d4;
    border: 1px solid #1060b3;
    width: 16px;
    margin: -5px 0;
    border-radius: 8px;
}

QSlider::handle:horizontal:hover {
    background: #1060b3;
}

QCheckBox {
    color: #1e1e1e;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 1px solid #c0c0c0;
    border-radius: 3px;
    background-color: #ffffff;
}

QCheckBox::indicator:checked {
    background-color: #0078d4;
    border: 1px solid #1060b3;
}

QCheckBox::indicator:hover {
    border-color: #a0a0a0;
}

QScrollBar:vertical {
    background: #f0f0f0;
    width: 14px;
    border-radius: 7px;
}

QScrollBar::handle:vertical {
    background: #c0c0c0;
    border-radius: 7px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background: #a0a0a0;
}

QScrollBar:horizontal {
    background: #f0f0f0;
    height: 14px;
    border-radius: 7px;
}

QScrollBar::handle:horizontal {
    background: #c0c0c0;
    border-radius: 7px;
    min-width: 20px;
}

QScrollBar::handle:horizontal:hover {
    background: #a0a0a0;
}

QStatusBar {
    background-color: #f0f0f0;
    color: #606060;
    border-top: 1px solid #d0d0d0;
}

QMenuBar {
    background-color: #f0f0f0;
    color: #1e1e1e;
    border-bottom: 1px solid #d0d0d0;
}

QMenuBar::item:selected {
    background-color: #e0e0e0;
}

QMenu {
    background-color: #fafafa;
    border: 1px solid #d0d0d0;
    color: #1e1e1e;
}

QMenu::item:selected {
    background-color: #0078d4;
    color: white;
}

QLabel {
    color: #1e1e1e;
}

QTabWidget::pane {
    border: 1px solid #d0d0d0;
    background-color: #fafafa;
}

QTabBar::tab {
    background-color: #e0e0e0;
    color: #1e1e1e;
    padding: 8px 16px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}

QTabBar::tab:selected {
    background-color: #0078d4;
    color: white;
}

QTabBar::tab:hover:!selected {
    background-color: #d0d0d0;
}

QDialog {
    background-color: #fafafa;
}
"""

# Versión combinada (la que usamos por defecto)
MODERN_STYLE = DARK_STYLE  # Por defecto usamos el tema oscuro