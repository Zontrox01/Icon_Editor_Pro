"""
Herramientas para dibujar formas geométricas: rectángulos, círculos, polígonos, etc.
"""

from PySide6.QtCore import Qt, QPoint, QRect, QLine
from PySide6.QtGui import QPainter, QPen, QColor, QBrush, QPolygon
import math

class ShapeTools:
    """Clase que contiene las herramientas para dibujar formas geométricas"""
    
    def __init__(self):
        self.current_shape = "rectangle"
        self.draw_color = QColor(0, 0, 0)
        self.fill_color = QColor(0, 0, 0, 0)  # Transparente por defecto
        self.stroke_width = 2
        self.fill_enabled = False
        self.antialiasing = True
        
    def set_shape(self, shape):
        """Establecer el tipo de forma a dibujar"""
        valid_shapes = ["rectangle", "circle", "line", "triangle", "star", "polygon"]
        if shape in valid_shapes:
            self.current_shape = shape
    
    def set_color(self, color):
        """Establecer color de dibujo"""
        self.draw_color = color
        
    def set_fill_color(self, color):
        """Establecer color de relleno"""
        self.fill_color = color
        self.fill_enabled = True
        
    def set_stroke_width(self, width):
        """Establecer grosor del trazo"""
        self.stroke_width = max(1, min(width, 20))
    
    def set_fill_enabled(self, enabled):
        """Activar/desactivar relleno"""
        self.fill_enabled = enabled
    
    def draw_rectangle(self, image, start, end):
        """Dibujar un rectángulo"""
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing, self.antialiasing)
        
        rect = QRect(start, end).normalized()
        
        # Configurar pincel
        pen = QPen(self.draw_color, self.stroke_width, Qt.SolidLine)
        painter.setPen(pen)
        
        # Configurar relleno
        if self.fill_enabled:
            painter.setBrush(QBrush(self.fill_color))
        else:
            painter.setBrush(Qt.NoBrush)
        
        painter.drawRect(rect)
        painter.end()
        return image
    
    def draw_circle(self, image, center, radius):
        """Dibujar un círculo"""
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing, self.antialiasing)
        
        # Configurar pincel
        pen = QPen(self.draw_color, self.stroke_width, Qt.SolidLine)
        painter.setPen(pen)
        
        # Configurar relleno
        if self.fill_enabled:
            painter.setBrush(QBrush(self.fill_color))
        else:
            painter.setBrush(Qt.NoBrush)
        
        painter.drawEllipse(center, radius, radius)
        painter.end()
        return image
    
    def draw_ellipse(self, image, start, end):
        """Dibujar una elipse"""
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing, self.antialiasing)
        
        rect = QRect(start, end).normalized()
        
        # Configurar pincel
        pen = QPen(self.draw_color, self.stroke_width, Qt.SolidLine)
        painter.setPen(pen)
        
        # Configurar relleno
        if self.fill_enabled:
            painter.setBrush(QBrush(self.fill_color))
        else:
            painter.setBrush(Qt.NoBrush)
        
        painter.drawEllipse(rect)
        painter.end()
        return image
    
    def draw_line(self, image, start, end):
        """Dibujar una línea recta"""
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing, self.antialiasing)
        
        pen = QPen(self.draw_color, self.stroke_width, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(pen)
        
        painter.drawLine(start, end)
        painter.end()
        return image
    
    def draw_triangle(self, image, start, end):
        """Dibujar un triángulo"""
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing, self.antialiasing)
        
        # Calcular los tres puntos del triángulo
        center_x = (start.x() + end.x()) // 2
        center_y = (start.y() + end.y()) // 2
        width = abs(end.x() - start.x())
        height = abs(end.y() - start.y())
        
        # Triángulo equilátero con base en la parte inferior
        p1 = QPoint(center_x, start.y())  # Vértice superior
        p2 = QPoint(start.x(), end.y())   # Vértice inferior izquierdo
        p3 = QPoint(end.x(), end.y())     # Vértice inferior derecho
        
        triangle = QPolygon([p1, p2, p3])
        
        # Configurar pincel
        pen = QPen(self.draw_color, self.stroke_width, Qt.SolidLine)
        painter.setPen(pen)
        
        # Configurar relleno
        if self.fill_enabled:
            painter.setBrush(QBrush(self.fill_color))
        else:
            painter.setBrush(Qt.NoBrush)
        
        painter.drawPolygon(triangle)
        painter.end()
        return image
    
    def draw_star(self, image, center, radius_outer=50, radius_inner=20, points=5):
        """Dibujar una estrella"""
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing, self.antialiasing)
        
        star_points = []
        angle_step = 2 * math.pi / (points * 2)
        start_angle = -math.pi / 2
        
        for i in range(points * 2):
            radius = radius_outer if i % 2 == 0 else radius_inner
            angle = start_angle + i * angle_step
            x = center.x() + radius * math.cos(angle)
            y = center.y() + radius * math.sin(angle)
            star_points.append(QPoint(int(x), int(y)))
        
        star = QPolygon(star_points)
        
        # Configurar pincel
        pen = QPen(self.draw_color, self.stroke_width, Qt.SolidLine)
        painter.setPen(pen)
        
        # Configurar relleno
        if self.fill_enabled:
            painter.setBrush(QBrush(self.fill_color))
        else:
            painter.setBrush(Qt.NoBrush)
        
        painter.drawPolygon(star)
        painter.end()
        return image
    
    def draw_polygon(self, image, points):
        """Dibujar un polígono con puntos dados"""
        if len(points) < 3:
            return image
        
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing, self.antialiasing)
        
        polygon = QPolygon(points)
        
        # Configurar pincel
        pen = QPen(self.draw_color, self.stroke_width, Qt.SolidLine)
        painter.setPen(pen)
        
        # Configurar relleno
        if self.fill_enabled:
            painter.setBrush(QBrush(self.fill_color))
        else:
            painter.setBrush(Qt.NoBrush)
        
        painter.drawPolygon(polygon)
        painter.end()
        return image
    
    def draw_rounded_rectangle(self, image, rect, radius=10):
        """Dibujar un rectángulo con esquinas redondeadas"""
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing, self.antialiasing)
        
        # Configurar pincel
        pen = QPen(self.draw_color, self.stroke_width, Qt.SolidLine)
        painter.setPen(pen)
        
        # Configurar relleno
        if self.fill_enabled:
            painter.setBrush(QBrush(self.fill_color))
        else:
            painter.setBrush(Qt.NoBrush)
        
        painter.drawRoundedRect(rect, radius, radius)
        painter.end()
        return image
    
    def draw_arrow(self, image, start, end):
        """Dibujar una flecha"""
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing, self.antialiasing)
        
        # Dibujar la línea principal
        pen = QPen(self.draw_color, self.stroke_width, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(pen)
        painter.drawLine(start, end)
        
        # Calcular la punta de la flecha
        dx = end.x() - start.x()
        dy = end.y() - start.y()
        length = math.sqrt(dx*dx + dy*dy)
        
        if length > 0:
            # Normalizar vector
            dx /= length
            dy /= length
            
            # Tamaño de la punta
            arrow_size = max(10, self.stroke_width * 3)
            
            # Calcular puntos de la punta
            angle = math.atan2(dy, dx)
            p1 = QPoint(
                end.x() - arrow_size * math.cos(angle - 0.5),
                end.y() - arrow_size * math.sin(angle - 0.5)
            )
            p2 = QPoint(
                end.x() - arrow_size * math.cos(angle + 0.5),
                end.y() - arrow_size * math.sin(angle + 0.5)
            )
            
            # Dibujar la punta
            painter.setBrush(QBrush(self.draw_color))
            painter.setPen(QPen(self.draw_color, 1))
            polygon = QPolygon([end, p1, p2])
            painter.drawPolygon(polygon)
        
        painter.end()
        return image
    
    def get_shape_info(self):
        """Obtener información sobre la forma actual"""
        return {
            'shape': self.current_shape,
            'color': self.draw_color.name(),
            'fill_color': self.fill_color.name() if self.fill_enabled else None,
            'fill_enabled': self.fill_enabled,
            'stroke_width': self.stroke_width
        }