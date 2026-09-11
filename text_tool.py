"""
Herramienta de texto: diálogo para escribir y dar formato a un texto
(tipografía, tamaño, negrita, cursiva, subrayado, color), y utilidad para
renderizarlo a una QImage con fondo transparente.

El texto resultante se coloca sobre el canvas como una imagen flotante (el
mismo mecanismo que se usa al importar una imagen): se puede mover y
redimensionar arrastrando los handles, y luego fijar. Por eso, si se agranda
mucho después de escribirlo, se escala como una imagen (puede perder nitidez)
en vez de volver a renderizarse el texto a mayor resolución.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QFontComboBox,
    QSpinBox, QPushButton, QColorDialog
)
from PySide6.QtGui import QFont, QColor, QFontMetrics, QImage, QPainter
from PySide6.QtCore import Qt, QRect


class TextInputDialog(QDialog):
    """Diálogo modal para escribir el texto y elegir su formato."""

    def __init__(self, parent=None, initial_color=None, initial_text="", initial_font=None):
        super().__init__(parent)
        self.setWindowTitle("Editar texto" if initial_text else "Insertar texto")
        self.setMinimumWidth(380)
        self._color = QColor(initial_color) if initial_color else QColor(0, 0, 0)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Texto:"))
        self.text_edit = QLineEdit()
        self.text_edit.setPlaceholderText("Escribe el texto...")
        layout.addWidget(self.text_edit)

        # Tipografía y tamaño
        font_layout = QHBoxLayout()
        self.font_combo = QFontComboBox()
        font_layout.addWidget(self.font_combo, 2)

        font_layout.addWidget(QLabel("Tamaño:"))
        self.size_spin = QSpinBox()
        self.size_spin.setRange(4, 400)
        self.size_spin.setValue(48)
        font_layout.addWidget(self.size_spin, 1)
        layout.addLayout(font_layout)

        # Negrita / Cursiva / Subrayado / Color
        style_layout = QHBoxLayout()

        self.bold_btn = QPushButton("N")
        self.bold_btn.setCheckable(True)
        self.bold_btn.setToolTip("Negrita")
        self.bold_btn.setFixedWidth(32)
        bf = self.bold_btn.font()
        bf.setBold(True)
        self.bold_btn.setFont(bf)
        style_layout.addWidget(self.bold_btn)

        self.italic_btn = QPushButton("I")
        self.italic_btn.setCheckable(True)
        self.italic_btn.setToolTip("Cursiva")
        self.italic_btn.setFixedWidth(32)
        itf = self.italic_btn.font()
        itf.setItalic(True)
        self.italic_btn.setFont(itf)
        style_layout.addWidget(self.italic_btn)

        self.underline_btn = QPushButton("S")
        self.underline_btn.setCheckable(True)
        self.underline_btn.setToolTip("Subrayado")
        self.underline_btn.setFixedWidth(32)
        uf = self.underline_btn.font()
        uf.setUnderline(True)
        self.underline_btn.setFont(uf)
        style_layout.addWidget(self.underline_btn)

        style_layout.addStretch()

        style_layout.addWidget(QLabel("Color:"))
        self.color_btn = QPushButton()
        self.color_btn.setFixedWidth(40)
        self.color_btn.clicked.connect(self._pick_color)
        style_layout.addWidget(self.color_btn)

        layout.addLayout(style_layout)

        # Vista previa en vivo
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumHeight(70)
        self.preview_label.setWordWrap(True)
        layout.addWidget(self.preview_label)

        self.text_edit.textChanged.connect(self._update_preview)
        self.font_combo.currentFontChanged.connect(self._update_preview)
        self.size_spin.valueChanged.connect(self._update_preview)
        self.bold_btn.toggled.connect(self._update_preview)
        self.italic_btn.toggled.connect(self._update_preview)
        self.underline_btn.toggled.connect(self._update_preview)

        # Botones OK/Cancelar
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("Insertar")
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        self._update_color_button()
        
        if initial_text:
            self.text_edit.setText(initial_text)
        if initial_font is not None:
            self.font_combo.setCurrentFont(initial_font)
            self.size_spin.setValue(initial_font.pointSize())
            self.bold_btn.setChecked(initial_font.bold())
            self.italic_btn.setChecked(initial_font.italic())
            self.underline_btn.setChecked(initial_font.underline())
        
        self._update_preview()
        self.text_edit.setFocus()
        self.text_edit.selectAll()

    def _update_color_button(self):
        self.color_btn.setStyleSheet(
            f"background-color: {self._color.name()}; border: 1px solid #888;"
        )

    def _pick_color(self):
        color = QColorDialog.getColor(self._color, self, "Color del texto")
        if color.isValid():
            self._color = color
            self._update_color_button()
            self._update_preview()

    def get_font(self):
        font = QFont(self.font_combo.currentFont())
        font.setPointSize(self.size_spin.value())
        font.setBold(self.bold_btn.isChecked())
        font.setItalic(self.italic_btn.isChecked())
        font.setUnderline(self.underline_btn.isChecked())
        return font

    def get_text(self):
        return self.text_edit.text()

    def get_color(self):
        return QColor(self._color)

    def _update_preview(self):
        text = self.text_edit.text() or "Vista previa"
        # Limitamos el tamaño de la vista previa para que no desborde el diálogo,
        # sin afectar al tamaño real que se usará al insertar el texto
        preview_font = self.get_font()
        preview_size = min(preview_font.pointSize(), 32)
        preview_font.setPointSize(preview_size)
        self.preview_label.setFont(preview_font)
        self.preview_label.setStyleSheet(
            f"border: 1px solid #555; background-color: #ffffff; color: {self._color.name()};"
        )
        self.preview_label.setText(text)
        self.adjustSize()


def render_text_to_image(text, font, color):
    """Renderiza el texto a una QImage RGBA con fondo transparente, ajustada a
    su tamaño (más un pequeño margen), lista para colocarse como imagen
    flotante sobre el canvas."""
    metrics = QFontMetrics(font)
    bounding = metrics.boundingRect(
        QRect(0, 0, 4000, 4000), Qt.TextWordWrap | Qt.AlignLeft | Qt.AlignTop, text
    )
    margin = max(4, font.pointSize() // 8)
    width = max(1, bounding.width() + margin * 2)
    height = max(1, bounding.height() + margin * 2)

    image = QImage(width, height, QImage.Format_ARGB32)
    image.fill(Qt.transparent)

    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.TextAntialiasing)
    painter.setFont(font)
    painter.setPen(QColor(color))
    painter.drawText(
        QRect(margin, margin, bounding.width(), bounding.height()),
        Qt.TextWordWrap | Qt.AlignLeft | Qt.AlignTop,
        text
    )
    painter.end()

    return image
