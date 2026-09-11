"""
Módulo para importar imágenes desde archivos externos.
Soporta JPG, PNG, BMP, GIF y otros formatos comunes.

La imagen importada se coloca en el canvas como un objeto flotante editable
(ver Canvas.start_floating_image): el propio usuario ajusta su posición y
tamaño arrastrando los handles directamente sobre el lienzo, en vez de tener
que elegir un modo de ajuste (fit/stretch/center/manual) en un diálogo previo.
"""

from PIL import Image
from PySide6.QtGui import QImage
import numpy as np
import os


class ImageImporter:
    """Clase para importar imágenes desde archivos y colocarlas en el canvas"""

    def __init__(self):
        self.supported_formats = ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.webp']
        self.last_imported_path = None

    def get_supported_formats(self):
        """Obtener lista de formatos soportados"""
        return self.supported_formats

    def get_filter_string(self):
        """Obtener string de filtro para QFileDialog"""
        filters = [f"*{ext}" for ext in self.supported_formats]
        return f"Imágenes ({' '.join(filters)});;Todos los archivos (*.*)"

    def import_image(self, file_path, canvas, parent=None):
        """
        Importar imagen desde archivo y colocarla en el canvas como imagen
        flotante editable (el usuario la ajusta luego arrastrando los handles).

        Args:
            file_path: Ruta del archivo a importar
            canvas: Widget canvas donde colocar la imagen
            parent: Sin uso actualmente (se mantiene por compatibilidad de firma)

        Returns:
            bool: True si la importación fue exitosa
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"El archivo {file_path} no existe")

        extension = os.path.splitext(file_path)[1].lower()
        if extension not in self.supported_formats:
            raise ValueError(f"Formato no soportado: {extension}")

        try:
            pil_image = Image.open(file_path)
            if pil_image.mode != 'RGBA':
                pil_image = pil_image.convert('RGBA')

            qimage = self.pil_to_qimage(pil_image)

            # Colocar como imagen flotante: el canvas se encarga de mostrarla
            # con handles para moverla/redimensionarla antes de fijarla (al
            # fijarla se convierte en su propia capa nueva).
            layer_name = os.path.splitext(os.path.basename(file_path))[0][:30] or "Imagen"
            canvas.start_floating_image(qimage, name=layer_name)

            self.last_imported_path = file_path
            return True

        except Exception as e:
            raise Exception(f"Error al importar la imagen: {str(e)}")

    def pil_to_qimage(self, pil_image):
        """
        Convertir PIL Image a QImage

        Args:
            pil_image: PIL Image object

        Returns:
            QImage: Imagen convertida
        """
        if pil_image.mode != 'RGBA':
            pil_image = pil_image.convert('RGBA')

        arr = np.array(pil_image)
        height, width, channel = arr.shape

        qimage = QImage(arr.data, width, height, width * 4, QImage.Format_RGBA8888)
        return qimage.copy()

    def get_image_info(self, file_path):
        """
        Obtener información de la imagen sin cargarla completamente

        Returns:
            dict: Información de la imagen (dimensiones, formato, etc.)
        """
        if not os.path.exists(file_path):
            return None

        try:
            with Image.open(file_path) as img:
                info = {
                    'width': img.width,
                    'height': img.height,
                    'format': img.format,
                    'mode': img.mode,
                    'is_square': img.width == img.height,
                    'size_mb': os.path.getsize(file_path) / (1024 * 1024)
                }
                return info
        except Exception:
            return None
