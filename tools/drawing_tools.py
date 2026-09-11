"""
Herramientas de dibujo básicas: lápiz, línea, relleno, etc.
"""

from PySide6.QtCore import Qt, QPoint, QRect
from PySide6.QtGui import QPainter, QPen, QColor, QBrush
import queue
import numpy as np

class DrawingTools:
    """Clase que contiene las herramientas básicas de dibujo"""
    
    def __init__(self):
        self.current_tool = "pencil"
        self.draw_color = QColor(0, 0, 0)   # color efectivo con el que se pinta ahora mismo
        self.user_color = QColor(0, 0, 0)   # último color elegido por el usuario (persiste
                                             # aunque se pase por el borrador o se cambie de herramienta)
        self.brush_size = 2
        self.fill_color = QColor(0, 0, 0)
        self.is_drawing = False
        self.last_point = None
        
    def set_tool(self, tool):
        """Establecer la herramienta activa"""
        valid_tools = ["pencil", "line", "fill", "eraser"]
        if tool in valid_tools:
            self.current_tool = tool
            # Ajustar comportamiento según la herramienta
            if tool == "eraser":
                self.draw_color = QColor(255, 255, 255, 0)  # Transparente para borrar
            else:
                # Restaurar el último color que había elegido el usuario, NO un
                # negro fijo (antes, cambiar de herramienta —incluso volver a
                # seleccionar el lápiz— borraba silenciosamente el color elegido)
                self.draw_color = QColor(self.user_color)
    
    def set_color(self, color):
        """Establecer color de dibujo"""
        self.user_color = QColor(color)
        if self.current_tool != "eraser":
            self.draw_color = color
            self.fill_color = color
    
    def set_brush_size(self, size):
        """Establecer tamaño del pincel"""
        self.brush_size = max(1, min(size, 50))  # Limitar entre 1 y 50
    
    def start_drawing(self, point):
        """Iniciar dibujo en un punto"""
        self.is_drawing = True
        self.last_point = point
        
    def draw_point(self, image, point):
        """Dibujar un punto en la imagen"""
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing)
        
        if self.current_tool == "eraser":
            # Para el borrador, usar composición para hacer transparente
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            painter.setPen(QPen(Qt.transparent, self.brush_size, Qt.SolidLine, Qt.RoundCap))
            painter.drawPoint(point)
        else:
            painter.setPen(QPen(self.draw_color, self.brush_size, Qt.SolidLine, Qt.RoundCap))
            painter.drawPoint(point)
            
        painter.end()
        return image
    
    def draw_line(self, image, start, end):
        """Dibujar una línea entre dos puntos"""
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing)
        
        if self.current_tool == "eraser":
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            painter.setPen(QPen(Qt.transparent, self.brush_size, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        else:
            painter.setPen(QPen(self.draw_color, self.brush_size, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            
        painter.drawLine(start, end)
        painter.end()
        return image
    
    def flood_fill(self, image, start, fill_color, tolerance=32):
        """
        Algoritmo de relleno por inundación (flood fill), con tolerancia de color.
        Usa BFS para evitar recursión infinita.
        
        La tolerancia es necesaria porque las formas se dibujan con antialiasing:
        los píxeles del borde son una mezcla del color de la forma y el fondo, no
        coinciden EXACTAMENTE con el color del interior. Sin tolerancia, el
        relleno solo llega hasta esos píxeles de borde y deja un contorno de
        color sin rellenar (muy visible al "vaciar a transparente", ya que
        contrasta con el patrón de cuadros del fondo).
        """
        width = image.width()
        height = image.height()
        
        if not (0 <= start.x() < width and 0 <= start.y() < height):
            return image
        
        # Obtener color original en el punto de inicio
        original_color = image.pixelColor(start)
        
        def matches(color):
            return (
                abs(color.red() - original_color.red()) <= tolerance and
                abs(color.green() - original_color.green()) <= tolerance and
                abs(color.blue() - original_color.blue()) <= tolerance and
                abs(color.alpha() - original_color.alpha()) <= tolerance
            )
        
        # Si el color de relleno ya "coincide" (dentro de la tolerancia) con el
        # original, no hay nada que rellenar
        if matches(fill_color):
            return image
        
        # Si es borrador, usar transparente
        if self.current_tool == "eraser":
            fill_color = QColor(0, 0, 0, 0)
        
        # BFS para rellenar
        q = queue.Queue()
        q.put((start.x(), start.y()))
        visited = set()
        
        while not q.empty():
            x, y = q.get()
            
            if (x, y) in visited:
                continue
            
            if not (0 <= x < width and 0 <= y < height):
                continue
            
            current_color = image.pixelColor(x, y)
            
            # Si el color actual no coincide (dentro de la tolerancia) con el
            # original, saltar
            if not matches(current_color):
                continue
            
            visited.add((x, y))
            
            # Cambiar el color del píxel
            image.setPixelColor(x, y, fill_color)
            
            # Añadir vecinos (4-direccional)
            q.put((x+1, y))
            q.put((x-1, y))
            q.put((x, y+1))
            q.put((x, y-1))
            
            # También añadir vecinos diagonales para un relleno más suave
            q.put((x+1, y+1))
            q.put((x-1, y-1))
            q.put((x+1, y-1))
            q.put((x-1, y+1))
        
        return image
    
    def flood_fill_region(self, image, start, tolerance=32):
        """
        Calcula qué píxeles de `image` pertenecen a la misma zona conectada que
        `start` (mismo algoritmo BFS que flood_fill), SIN modificar `image` ni
        necesitar un color de relleno. Devuelve un set de (x, y).
        
        Se usa para calcular la zona a rellenar sobre la imagen COMPUESTA
        (todas las capas visibles + fondo) en vez de sobre una única capa: en
        un editor por capas donde cada forma vive en su propia capa (casi toda
        ella transparente), calcular la zona sobre una sola capa haría que el
        relleno se extendiera por CASI TODA esa capa en vez de respetar el
        contorno tal y como se ve en pantalla.
        """
        width = image.width()
        height = image.height()
        
        if not (0 <= start.x() < width and 0 <= start.y() < height):
            return set()
        
        original_color = image.pixelColor(start)
        
        def matches(color):
            return (
                abs(color.red() - original_color.red()) <= tolerance and
                abs(color.green() - original_color.green()) <= tolerance and
                abs(color.blue() - original_color.blue()) <= tolerance and
                abs(color.alpha() - original_color.alpha()) <= tolerance
            )
        
        q = queue.Queue()
        q.put((start.x(), start.y()))
        visited = set()
        
        while not q.empty():
            x, y = q.get()
            
            if (x, y) in visited:
                continue
            if not (0 <= x < width and 0 <= y < height):
                continue
            if not matches(image.pixelColor(x, y)):
                continue
            
            visited.add((x, y))
            
            q.put((x+1, y))
            q.put((x-1, y))
            q.put((x, y+1))
            q.put((x, y-1))
            q.put((x+1, y+1))
            q.put((x-1, y-1))
            q.put((x+1, y-1))
            q.put((x-1, y+1))
        
        return visited
    
    def apply_effect(self, image, effect_type):
        """
        Aplicar efectos especiales a la imagen
        """
        if effect_type == "blur":
            # Crear una copia de la imagen
            from PySide6.QtGui import QImage, QPainter
            import math
            
            # Implementación simple de blur (promedio de vecinos)
            width = image.width()
            height = image.height()
            new_image = QImage(width, height, image.format())
            
            # Copiar el contenido original
            new_image.fill(QColor(0, 0, 0, 0))
            painter = QPainter(new_image)
            painter.drawImage(0, 0, image)
            painter.end()
            
            # Aplicar blur simple (3x3 kernel)
            for y in range(1, height-1):
                for x in range(1, width-1):
                    r_sum = g_sum = b_sum = a_sum = 0
                    count = 0
                    
                    for dy in range(-1, 2):
                        for dx in range(-1, 2):
                            if 0 <= x+dx < width and 0 <= y+dy < height:
                                pixel = image.pixelColor(x+dx, y+dy)
                                r_sum += pixel.red()
                                g_sum += pixel.green()
                                b_sum += pixel.blue()
                                a_sum += pixel.alpha()
                                count += 1
                    
                    if count > 0:
                        new_color = QColor(
                            r_sum // count,
                            g_sum // count,
                            b_sum // count,
                            a_sum // count
                        )
                        new_image.setPixelColor(x, y, new_color)
            
            return new_image
            
        elif effect_type == "sharpen":
            # Implementación simple de sharpen
            width = image.width()
            height = image.height()
            new_image = QImage(width, height, image.format())
            new_image.fill(QColor(0, 0, 0, 0))
            
            # Kernel de sharpen (5x5)
            kernel = [
                [0, -1, -1, -1, 0],
                [-1, 1, 2, 1, -1],
                [-1, 2, 4, 2, -1],
                [-1, 1, 2, 1, -1],
                [0, -1, -1, -1, 0]
            ]
            
            for y in range(2, height-2):
                for x in range(2, width-2):
                    r_sum = g_sum = b_sum = a_sum = 0
                    total_weight = 0
                    
                    for dy in range(-2, 3):
                        for dx in range(-2, 3):
                            weight = kernel[dy+2][dx+2]
                            if weight != 0:
                                pixel = image.pixelColor(x+dx, y+dy)
                                r_sum += pixel.red() * weight
                                g_sum += pixel.green() * weight
                                b_sum += pixel.blue() * weight
                                a_sum += pixel.alpha() * weight
                                total_weight += abs(weight)
                    
                    if total_weight > 0:
                        new_color = QColor(
                            max(0, min(255, r_sum // 4)),
                            max(0, min(255, g_sum // 4)),
                            max(0, min(255, b_sum // 4)),
                            max(0, min(255, a_sum // 4))
                        )
                        new_image.setPixelColor(x, y, new_color)
            
            return new_image
            
        return image
    
    def get_tool_info(self):
        """Obtener información sobre la herramienta actual"""
        return {
            'tool': self.current_tool,
            'color': self.draw_color.name(),
            'brush_size': self.brush_size,
            'is_drawing': self.is_drawing
        }