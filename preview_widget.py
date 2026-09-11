from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPainter, QColor, QImage, QPixmap

class PreviewWidget(QWidget):
    # Tamaño de icono más grande que se puede previsualizar, y cuántos píxeles
    # de pantalla ocupa a ese tamaño. El resto de tamaños se escalan de forma
    # PROPORCIONAL a este, para que un icono de 16x16 se vea realmente pequeño
    # comparado con uno de 256x256 (antes todas las previews medían ~128px en
    # pantalla sin importar el tamaño real que representaban).
    MAX_REFERENCE_SIZE = 256
    MAX_DISPLAY_PX = 128
    
    def __init__(self, size, parent=None):
        super().__init__(parent)
        self.size = size
        self.image = None
        
        layout = QVBoxLayout(self)
        layout.setSpacing(5)
        
        # Etiqueta del tamaño
        self.size_label = QLabel(f"{size}x{size}")
        self.size_label.setAlignment(Qt.AlignCenter)
        self.size_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.size_label)
        
        # Área de previsualización
        self.preview_area = QLabel()
        self.preview_area.setAlignment(Qt.AlignCenter)
        self.preview_area.setMinimumSize(150, 150)
        self.preview_area.setStyleSheet("""
            border: 1px solid #888;
            background-color: #f0f0f0;
        """)
        layout.addWidget(self.preview_area)
    
    def update_preview(self, source_image):
        """Actualizar la vista previa con la imagen fuente"""
        if source_image is None:
            return
        
        # Tamaño en pantalla PROPORCIONAL al tamaño real de icono que representa
        # esta tarjeta (self.size), no un tamaño fijo igual para todas las tarjetas.
        target_size = max(4, round(self.size * self.MAX_DISPLAY_PX / self.MAX_REFERENCE_SIZE))
        target_size = min(target_size, self.preview_area.width() - 10)
        scaled = source_image.scaled(
            target_size, target_size,
            Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        
        # Crear fondo con cuadrícula para transparencia
        preview_pixmap = QPixmap(scaled.size())
        preview_pixmap.fill(QColor(255, 255, 255))
        
        # Dibujar cuadrícula
        painter = QPainter(preview_pixmap)
        grid_size = 10
        for x in range(0, scaled.width(), grid_size):
            for y in range(0, scaled.height(), grid_size):
                if (x // grid_size + y // grid_size) % 2 == 0:
                    painter.fillRect(x, y, grid_size, grid_size, QColor(200, 200, 200))
        
        # Dibujar imagen redimensionada
        painter.drawImage(0, 0, scaled)
        painter.end()
        
        self.preview_area.setPixmap(preview_pixmap)