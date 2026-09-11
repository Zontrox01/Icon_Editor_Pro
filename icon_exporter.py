"""
Exportador de iconos a formato ICO.
"""

from PIL import Image
import io
from PySide6.QtCore import Qt, QBuffer, QByteArray
from PySide6.QtGui import QImage

class IconExporter:
    def __init__(self):
        pass
    
    def qimage_to_pil(self, qimage):
        """
        Convertir QImage a PIL Image usando QBuffer
        """
        # Crear un QBuffer para guardar la imagen
        buffer = QBuffer()
        buffer.open(QBuffer.ReadWrite)
        
        # Guardar QImage como PNG en el buffer (siempre PNG conserva el canal alfa si lo hay)
        qimage.save(buffer, "PNG")
        
        # Obtener los datos del buffer
        byte_array = buffer.data()
        buffer.close()
        
        # Crear un BytesIO desde los datos
        bytes_io = io.BytesIO(byte_array.data())
        bytes_io.seek(0)
        
        # Cargar con PIL
        pil_image = Image.open(bytes_io)
        
        # Convertir a RGBA si tiene canal alfa
        if qimage.hasAlphaChannel() and pil_image.mode != 'RGBA':
            pil_image = pil_image.convert('RGBA')
        elif not qimage.hasAlphaChannel() and pil_image.mode != 'RGB':
            pil_image = pil_image.convert('RGB')
        
        return pil_image
    
    def export_ico(self, file_path, qimage, sizes):
        """
        Exportar QImage a formato ICO con múltiples tamaños
        """
        if not sizes:
            sizes = [256]
        
        # Convertir QImage a PIL Image
        pil_image = self.qimage_to_pil(qimage)
        
        # Crear lista de imágenes para diferentes tamaños
        images = []
        # Ordenar tamaños de mayor a menor para el ICO
        sorted_sizes = sorted(sizes, reverse=True)
        
        for size in sorted_sizes:
            if size != pil_image.size[0]:
                # Redimensionar manteniendo proporción
                resized = pil_image.resize((size, size), Image.Resampling.LANCZOS)
                images.append(resized)
            else:
                images.append(pil_image)
        
        # Guardar como ICO
        # La primera imagen debe ser la de mayor tamaño
        images[0].save(
            file_path,
            format='ICO',
            sizes=[(size, size) for size in sorted_sizes],
            append_images=images[1:]
        )
    
    def export_png(self, file_path, qimage, size=None):
        """Exportar QImage a formato PNG"""
        if size and size != qimage.width():
            scaled = qimage.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            scaled.save(file_path, "PNG")
        else:
            qimage.save(file_path, "PNG")
    
    def export_bmp(self, file_path, qimage, size=None):
        """Exportar QImage a formato BMP"""
        if size and size != qimage.width():
            scaled = qimage.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            scaled.save(file_path, "BMP")
        else:
            qimage.save(file_path, "BMP")