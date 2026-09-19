# canvas.py
from PySide6.QtWidgets import QWidget, QSizePolicy
from PySide6.QtCore import Qt, QPoint, QPointF, QRect, QRectF, QBuffer, Signal, QSize
from PySide6.QtGui import (
    QPainter, QPen, QBrush, QColor, QImage,
    QPixmap, QMouseEvent, QPaintEvent, QResizeEvent,
    QTransform, QCursor
)
import numpy as np
import io
from copy import deepcopy
from PIL import Image, ImageDraw, ImageFilter

# Añadir estos imports para las herramientas
from tools.drawing_tools import DrawingTools
from tools.shape_tools import ShapeTools
from layer import Layer

class Canvas(QWidget):
    position_changed = Signal(int, int)
    image_changed = Signal()
    modified = Signal()
    floating_state_changed = Signal()  # se emite al iniciar/alternar/fijar/cancelar la imagen flotante
    text_tool_requested = Signal(QPoint)  # se emite al hacer clic con la herramienta de texto activa
    layers_changed = Signal()  # se emite al añadir/eliminar/reordenar/mostrar-ocultar una capa, o cambiar la activa
    status_message = Signal(str)  # mensajes de diagnóstico/estado para la barra de estado de la ventana
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(300, 300)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Configuración del canvas
        self.canvas_size = 256  # Tamaño en píxeles del lienzo lógico
        self.display_pixmap = None
        self.scale_factor = 1.0
        self.offset_x = 0
        self.offset_y = 0
        
        # Estado de dibujo
        self.drawing = False
        self.last_point = None
        self.current_tool = "pencil"
        self.draw_color = QColor(0, 0, 0)
        self.brush_size = 2
        
        # Fondo: es solo un telón visual que se compone POR DEBAJO de todas las
        # capas al mostrar/exportar; no forma parte de los píxeles de ninguna capa.
        self.bg_transparent = True
        self.bg_color = QColor(255, 255, 255)
        
        # Capas: self.layers[0] es la capa SUPERIOR (se dibuja última, encima de
        # las demás); self.layers[-1] es la INFERIOR. self.active_layer_index
        # indica sobre cuál actúan el lápiz, las formas, el relleno, el texto, etc.
        self.layers = []
        self.active_layer_index = 0
        
        # Imagen flotante: la imagen recién importada se mantiene como un objeto
        # independiente y editable (se puede mover y redimensionar arrastrando sus
        # handles) hasta que se fija sobre el lienzo con apply_floating_image().
        self.floating_image = None       # QImage RGBA de la imagen importada, sin fijar
        self.floating_layer_name = "Objeto"  # nombre que tendrá la capa nueva al fijarla
        self.floating_object_type = "generic"  # "generic" o "text": se guarda en la capa
                                                # resultante para poder reeditar el objeto
        self.floating_object_data = None       # metadatos del objeto (texto/fuente/color...)
        self.floating_edit_layer_index = None  # si no es None, estamos REEDITANDO esa capa
                                                # existente (no se creará una capa nueva al
                                                # fijar, se sustituirá el contenido de esa)
        self._layer_edit_backup = None   # contenido original de la capa, para restaurar si se cancela
        self.floating_rect = None        # QRect (coords. de canvas) con su posición/tamaño actual
        self.floating_aspect = 1.0       # ancho/alto original, para el bloqueo de proporción
        self.keep_aspect_ratio = True    # si los handles deben mantener proporción
        self.floating_locked = False     # True = "fijada visualmente" (sin handles), pero
                                          # todavía SIN fusionar con los píxeles del canvas
        self.floating_handle = None      # handle bajo el que se está arrastrando ahora mismo
        self.floating_moving = False     # True si se está desplazando (no redimensionando)
        self.floating_drag_start_mouse = None  # posición (coords. canvas) al iniciar el arrastre
        self.floating_drag_start_rect = None   # floating_rect al iniciar el arrastre
        self.image_rect = None  # Rectángulo que ocupa la imagen en el canvas
        self.image_offset = QPoint(0, 0)  # Offset de la imagen dentro del canvas
        self.image_scale = 1.0  # Escala de la imagen
        
        # Arrastre de formas (línea, rectángulo, círculo, triángulo): se pulsa en el
        # punto de inicio, se arrastra viendo una previsualización en vivo (como un
        # overlay flotante, sin tocar ninguna capa), y solo al soltar el botón se
        # crea una CAPA NUEVA con esa forma (cada forma es su propio "objeto").
        self.shape_start_point = None    # QPoint (coords. canvas) donde empezó el arrastre
        self.shape_preview_image = None  # imagen (tamaño canvas, fondo transparente) con
                                          # la forma dibujada en su posición actual del arrastre
        
        # Herramienta "Mover/Seleccionar": clic sobre cualquier píxel no transparente
        # de cualquier capa visible la selecciona (aunque no sea la última editada,
        # ni la que esté activa ahora mismo) y la deja lista para mover/redimensionar
        # (ver enter_layer_edit_mode: reutiliza el mismo mecanismo de imagen flotante).
        
        # Herramienta "Seleccionar": arrastra un rectángulo (coords. de canvas,
        # absolutas) que queda marcado hasta que se recorta (ver crop_selection)
        # o se vuelve a seleccionar otra zona. Si la selección se sale de los
        # límites de la capa activa, se avisa (no se impide).
        self.selection_start_point = None    # QPoint donde empezó el arrastre de selección
        self.selection_preview_rect = None   # QRect en vivo mientras se arrastra
        self.selection_rect = None           # QRect ya confirmado (al soltar)
        
        self.fill_transparent = False    # si el relleno (flood fill) usa transparente en vez del color activo
        self.fill_tolerance = 100        # tolerancia de color del relleno (ver drawing_tools.flood_fill)
        
        # Inicializar herramientas
        self.drawing_tools = DrawingTools()
        self.shape_tools = ShapeTools()
        
        # Inicializar la capa inicial
        self.initialize_image()
        
        # Configurar evento de mouse tracking
        self.setMouseTracking(True)
        # Foco de teclado para poder usar Enter/Esc al ajustar una imagen flotante
        self.setFocusPolicy(Qt.StrongFocus)
    
    @property
    def current_image(self):
        """La imagen (QImage) de la capa activa. El lápiz, las formas, el relleno,
        el texto y la imagen flotante trabajan siempre sobre esta capa; para ver el
        resultado final compuesto de TODAS las capas, usar composite_layers()."""
        return self.layers[self.active_layer_index].image
    
    @current_image.setter
    def current_image(self, value):
        self.layers[self.active_layer_index].image = value
    
    def initialize_image(self):
        """Crear la capa inicial del canvas"""
        image = QImage(self.canvas_size, self.canvas_size, QImage.Format_ARGB32)
        image.fill(Qt.transparent)
        self.layers = [Layer("Capa 1", image)]
        self.active_layer_index = 0
        self.image_rect = QRect(0, 0, self.canvas_size, self.canvas_size)
        self.image_offset = QPoint(0, 0)
        self.image_scale = 1.0
        self.update_display()
    
    def clear_canvas(self):
        """Limpiar TODO el lienzo: como cada forma/texto/imagen vive en su
        propia capa, "limpiar" tiene que actuar sobre TODAS ellas, no solo
        sobre la activa. Elimina todas las capas y las sustituye por una
        única capa en blanco (el mismo estado que al empezar un proyecto)."""
        if self.floating_image is not None:
            self.cancel_floating_image()
        blank = QImage(self.canvas_size, self.canvas_size, QImage.Format_ARGB32)
        blank.fill(Qt.transparent)
        self.layers = [Layer("Capa 1", blank)]
        self.active_layer_index = 0
        self.update_display()
        self.image_changed.emit()
        self.layers_changed.emit()
    
    def set_canvas_size(self, size):
        """Cambiar tamaño del canvas: cada capa conserva su imagen tal cual
        (no se recorta ni se vuelve a hornear), solo se desplaza su posición
        para mantenerla centrada respecto al nuevo tamaño del lienzo. Antes,
        cambiar el tamaño (sobre todo encoger) podía recortar contenido de las
        capas; ahora, al guardar cada una su propia posición, nada se pierde."""
        if self.floating_image is not None:
            self.apply_floating_image()
        if size == self.canvas_size:
            return
        
        offset = (size - self.canvas_size) // 2
        
        for layer in self.layers:
            layer.position = QPoint(layer.position.x() + offset, layer.position.y() + offset)
            # El historial de cada capa se reinicia con el nuevo tamaño/posición
            layer.history = []
            layer.history_index = -1
            layer.save_history()
        
        self.canvas_size = size
        self.image_rect = QRect(0, 0, size, size)
        self.update_display()
        self.image_changed.emit()
        self.layers_changed.emit()
    
    def set_tool(self, tool):
        """Establecer herramienta activa"""
        # Si hay una imagen flotante pendiente de ajustar, la fijamos antes de
        # empezar a usar otra herramienta (dibujar, formas, etc.)
        if self.floating_image is not None:
            self.apply_floating_image()
        self.shape_start_point = None
        self.shape_preview_image = None
        self.selection_start_point = None
        self.selection_preview_rect = None
        self.current_tool = tool
        # Actualizar las herramientas
        self.drawing_tools.set_tool(tool)
        self.shape_tools.set_shape(tool)
        self.update_tool_cursor()
    
    def set_draw_color(self, color):
        """Establecer color de dibujo"""
        self.draw_color = color
        self.drawing_tools.set_color(color)
        self.shape_tools.set_color(color)
    
    def set_brush_size(self, size):
        """Establecer tamaño del pincel"""
        self.brush_size = size
        self.drawing_tools.set_brush_size(size)
        self.shape_tools.set_stroke_width(size)
        self.update_tool_cursor()
    
    def update_tool_cursor(self):
        """Actualizar el cursor del lienzo según la herramienta activa. Para
        lápiz y borrador, se muestra un círculo del tamaño real del pincel (en
        píxeles de pantalla, según el zoom actual), para hacerte una idea del
        grosor antes de pintar. El resto de herramientas usan cursores fijos;
        "Mover" y el ajuste de imagen flotante gestionan su propio cursor
        dinámicamente durante la interacción (handles, manita, etc.) y no se
        tocan aquí."""
        if self.current_tool in ("pencil", "eraser"):
            self.setCursor(self._brush_cursor())
        elif self.current_tool == "move":
            self.setCursor(Qt.ArrowCursor)
        else:
            self.setCursor(Qt.CrossCursor)
    
    def _brush_cursor(self):
        """Construye un QCursor circular con el diámetro real del pincel,
        escalado a píxeles de pantalla según el zoom actual del lienzo."""
        diameter = max(4, min(200, round(self.brush_size * self.scale_factor)))
        margin = 4  # para que el trazo del borde no se recorte en los extremos
        pixmap_size = diameter + margin * 2
        
        pixmap = QPixmap(pixmap_size, pixmap_size)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(margin, margin, diameter, diameter)
        # Doble trazo (blanco por fuera, negro por dentro) para que se vea
        # bien tanto sobre fondos claros como oscuros del lienzo
        painter.setPen(QPen(QColor(255, 255, 255), 3))
        painter.drawEllipse(rect)
        painter.setPen(QPen(QColor(0, 0, 0), 1))
        painter.drawEllipse(rect)
        painter.end()
        
        center = pixmap_size // 2
        return QCursor(pixmap, center, center)
    
    def set_background_color(self, color):
        """Establecer color de fondo (solo visual: no forma parte de ninguna capa)"""
        self.bg_color = color
        if not self.bg_transparent:
            self.update_display()
            self.image_changed.emit()
    
    def set_background_transparent(self, transparent):
        """Establecer si el fondo es transparente (solo visual: no modifica
        ninguna capa, solo cómo se componen/muestran)"""
        if self.bg_transparent != transparent:
            self.bg_transparent = transparent
            self.update_display()
            self.image_changed.emit()
    
    def composite_layers(self):
        """Compone el fondo (transparente o de color) y todas las capas VISIBLES
        (de abajo a arriba) en una única QImage del tamaño del lienzo. Esto es
        lo que se ve en pantalla y lo que se exporta/guarda; ninguna capa
        individual incluye el fondo. Cada capa se dibuja en SU PROPIA posición
        (puede ser negativa o salirse del lienzo): aquí es donde se recorta la
        VISUALIZACIÓN al tamaño del lienzo (QPainter recorta automáticamente lo
        que quede fuera), pero la imagen de la capa en sí nunca se toca."""
        result = QImage(self.canvas_size, self.canvas_size, QImage.Format_ARGB32)
        if self.bg_transparent:
            result.fill(Qt.transparent)
        else:
            result.fill(self.bg_color)
        
        painter = QPainter(result)
        painter.setRenderHint(QPainter.Antialiasing)
        # self.layers[0] es la capa superior: se compone de abajo (última de la
        # lista) a arriba (primera), para que la superior quede encima del todo.
        for layer in reversed(self.layers):
            if layer.visible:
                painter.drawImage(layer.position, layer.image)
        painter.end()
        return result
    
    def get_image(self):
        """Obtener la imagen final compuesta (todas las capas visibles + fondo).
        Si hay una imagen flotante sin fijar, se fija primero en la capa activa."""
        if self.floating_image is not None:
            self.apply_floating_image()
        return self.composite_layers()
    
    def get_preview_image(self):
        """Como composite_layers(), pero superponiendo también la imagen flotante
        (si la hay) SIN fijarla. Se usa para refrescar las vistas previas mientras
        el usuario todavía está ajustando la imagen importada (a diferencia de
        get_image(), que sí la fija)."""
        image = self.composite_layers()
        if self.floating_image is not None and self.floating_rect is not None:
            scaled = self.floating_image.scaled(
                max(1, self.floating_rect.width()), max(1, self.floating_rect.height()),
                Qt.IgnoreAspectRatio, Qt.SmoothTransformation
            )
            painter = QPainter(image)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.drawImage(self.floating_rect.topLeft(), scaled)
            painter.end()
        return image
    
    def set_image(self, image):
        """Reemplazar TODAS las capas por una única capa nueva con esta imagen.
        Se usa para cargar un proyecto antiguo (guardado sin capas) o una imagen
        suelta como icono base."""
        if self.floating_image is not None:
            self.cancel_floating_image()
        
        if image.width() != self.canvas_size or image.height() != self.canvas_size:
            # Redimensionar manteniendo proporción y centrar en el canvas
            scaled = image.scaled(self.canvas_size, self.canvas_size,
                                 Qt.KeepAspectRatio, Qt.SmoothTransformation)
            new_image = QImage(self.canvas_size, self.canvas_size, QImage.Format_ARGB32)
            new_image.fill(Qt.transparent)
            x_offset = (self.canvas_size - scaled.width()) // 2
            y_offset = (self.canvas_size - scaled.height()) // 2
            painter = QPainter(new_image)
            painter.drawImage(x_offset, y_offset, scaled)
            painter.end()
            final_image = new_image
        else:
            final_image = image.copy()
        
        self.layers = [Layer("Capa 1", final_image)]
        self.active_layer_index = 0
        self.image_rect = QRect(0, 0, self.canvas_size, self.canvas_size)
        self.update_display()
        self.image_changed.emit()
        self.layers_changed.emit()
    
    def load_layers_data(self, layers_data, active_index=0):
        """Reemplazar las capas actuales a partir de una lista de datos ya
        deserializados: [{'name', 'visible', 'image', 'layer_type', 'data'}, ...].
        'layer_type'/'data' son opcionales (compatibilidad hacia atrás).
        self.layers[0] es la capa superior (ver composite_layers). Usado por
        ProjectManager al cargar un proyecto guardado CON capas."""
        if self.floating_image is not None:
            self.cancel_floating_image()
        
        new_layers = []
        for data in layers_data:
            layer = Layer(data['name'], data['image'], position=data.get('position'))
            layer.visible = data.get('visible', True)
            layer.layer_type = data.get('layer_type', 'generic')
            layer.data = data.get('data', {}) or {}
            new_layers.append(layer)
        
        if not new_layers:
            # Salvaguarda: nunca nos quedamos sin capas
            blank = QImage(self.canvas_size, self.canvas_size, QImage.Format_ARGB32)
            blank.fill(Qt.transparent)
            new_layers = [Layer("Capa 1", blank)]
        
        self.layers = new_layers
        self.active_layer_index = max(0, min(active_index, len(self.layers) - 1))
        self.image_rect = QRect(0, 0, self.canvas_size, self.canvas_size)
        self.update_display()
        self.image_changed.emit()
        self.layers_changed.emit()
    
    # ============ MÉTODOS DE GESTIÓN DE CAPAS ============
    
    def add_layer(self, name=None):
        """Añadir una nueva capa transparente encima de todas las demás, y
        convertirla en la capa activa."""
        if self.floating_image is not None:
            self.apply_floating_image()
        
        if name is None:
            existing_names = {layer.name for layer in self.layers}
            n = len(self.layers) + 1
            name = f"Capa {n}"
            while name in existing_names:
                n += 1
                name = f"Capa {n}"
        
        image = QImage(self.canvas_size, self.canvas_size, QImage.Format_ARGB32)
        image.fill(Qt.transparent)
        new_layer = Layer(name, image)
        self.layers.insert(0, new_layer)  # índice 0 = capa superior
        self.active_layer_index = 0
        self.update_display()
        self.image_changed.emit()
        self.layers_changed.emit()
    
    def delete_layer(self, index):
        """Eliminar la capa en la posición dada. Nunca se elimina si es la
        única capa que queda (se vacía en su lugar)."""
        if not (0 <= index < len(self.layers)):
            return
        if self.floating_image is not None:
            self.cancel_floating_image()
        
        if len(self.layers) == 1:
            # No podemos quedarnos sin ninguna capa: la vaciamos en su lugar
            # (reseteada a un lienzo completo en blanco en (0,0), no solo
            # transparentada tal cual estuviera, que podía quedar con un
            # tamaño/posición residual de antes)
            blank = QImage(self.canvas_size, self.canvas_size, QImage.Format_ARGB32)
            blank.fill(Qt.transparent)
            self.layers[0].image = blank
            self.layers[0].position = QPoint(0, 0)
            self.layers[0].save_history()
            self.update_display()
            self.image_changed.emit()
            self.layers_changed.emit()
            return
        
        del self.layers[index]
        self.active_layer_index = max(0, min(self.active_layer_index, len(self.layers) - 1))
        self.update_display()
        self.image_changed.emit()
        self.layers_changed.emit()
    
    def move_layer_up(self, index):
        """Subir una capa (la acerca a la parte superior de la pila, es decir,
        reduce su índice en self.layers)."""
        if index <= 0 or index >= len(self.layers):
            return
        if self.floating_image is not None:
            # Si había una edición flotante pendiente (p. ej. la propia
            # selección de la capa ya la "levantó" para poder redimensionarla),
            # la fijamos ANTES de reordenar. Si no, reordenaríamos una capa
            # vacía mientras su contenido real sigue flotando con un índice
            # que quedaría caducado tras el cambio de posición.
            self.apply_floating_image()
        self.layers[index - 1], self.layers[index] = self.layers[index], self.layers[index - 1]
        if self.active_layer_index == index:
            self.active_layer_index = index - 1
        elif self.active_layer_index == index - 1:
            self.active_layer_index = index
        self.update_display()
        self.image_changed.emit()
        self.layers_changed.emit()
    
    def move_layer_down(self, index):
        """Bajar una capa (la acerca a la parte inferior de la pila, es decir,
        aumenta su índice en self.layers)."""
        if index < 0 or index >= len(self.layers) - 1:
            return
        if self.floating_image is not None:
            self.apply_floating_image()
        self.layers[index + 1], self.layers[index] = self.layers[index], self.layers[index + 1]
        if self.active_layer_index == index:
            self.active_layer_index = index + 1
        elif self.active_layer_index == index + 1:
            self.active_layer_index = index
        self.update_display()
        self.image_changed.emit()
        self.layers_changed.emit()
    
    def set_active_layer(self, index):
        """Cambiar cuál es la capa activa (sobre la que actúan las herramientas)"""
        if not (0 <= index < len(self.layers)) or index == self.active_layer_index:
            return
        if self.floating_image is not None:
            self.apply_floating_image()
        self.shape_start_point = None
        self.shape_preview_image = None
        self.active_layer_index = index
        self.layers_changed.emit()
    
    def set_layer_visibility(self, index, visible):
        """Mostrar u ocultar una capa (no afecta a sus píxeles, solo a si se
        compone en el resultado final)"""
        if not (0 <= index < len(self.layers)):
            return
        self.layers[index].visible = bool(visible)
        self.update_display()
        self.image_changed.emit()
    
    def rename_layer(self, index, name):
        """Renombrar una capa"""
        if not (0 <= index < len(self.layers)) or not name.strip():
            return
        self.layers[index].name = name.strip()
        self.layers_changed.emit()
    
    def crop_selection(self):
        """Recorta la CAPA ACTIVA a la zona actualmente seleccionada (ver
        herramienta "Seleccionar"). Si no hay ninguna selección, o no se
        solapa en absoluto con la capa activa, avisa y no hace nada. Si la
        selección se sale parcialmente de la capa, se recorta solo a la parte
        que sí se solapa."""
        if self.selection_rect is None:
            self.status_message.emit("Recortar: no hay ninguna zona seleccionada")
            return False
        
        if self.floating_image is not None:
            self.apply_floating_image()
        
        layer = self.layers[self.active_layer_index]
        intersection = self.selection_rect.intersected(layer.bounds())
        
        if intersection.isEmpty():
            self.status_message.emit(
                f"Recortar: la selección no se solapa con la capa activa '{layer.name}'"
            )
            return False
        
        local_rect = QRect(
            intersection.x() - layer.position.x(), intersection.y() - layer.position.y(),
            intersection.width(), intersection.height()
        )
        layer.image = layer.image.copy(local_rect)
        layer.position = intersection.topLeft()
        
        self.selection_rect = None
        self.save_to_history()
        self.update_display()
        self.image_changed.emit()
        self.layers_changed.emit()
        self.status_message.emit(f"Recortado a {intersection.width()}x{intersection.height()} px")
        return True
    
    def clear_selection(self):
        """Descartar la selección actual sin recortar nada"""
        self.selection_rect = None
        self.selection_start_point = None
        self.selection_preview_rect = None
        self.update_display()
    
    def set_image_with_transform(self, image, offset=None, scale=None):
        """Establecer imagen con transformación (offset y escala)"""
        if offset is not None:
            self.image_offset = offset
        if scale is not None:
            self.image_scale = scale
        
        # Crear imagen transformada
        new_image = QImage(self.canvas_size, self.canvas_size, QImage.Format_ARGB32)
        if self.bg_transparent:
            new_image.fill(Qt.transparent)
        else:
            new_image.fill(self.bg_color)
        
        painter = QPainter(new_image)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Calcular el tamaño escalado
        width = int(image.width() * self.image_scale)
        height = int(image.height() * self.image_scale)
        
        # Escalar la imagen
        scaled = image.scaled(width, height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        
        # Dibujar en la posición offset
        painter.drawImage(self.image_offset.x(), self.image_offset.y(), scaled)
        painter.end()
        
        self.current_image = new_image
        self.image_rect = QRect(self.image_offset.x(), self.image_offset.y(), width, height)
        self.update_display()
        self.image_changed.emit()
    
    def save_to_history(self):
        """Guardar el estado actual de la CAPA ACTIVA en su propio historial"""
        self.layers[self.active_layer_index].save_history()
        self.modified.emit()
    
    def undo(self):
        """Deshacer la última acción de la capa activa"""
        if self.floating_image is not None:
            self.cancel_floating_image()
            return
        if self.layers[self.active_layer_index].undo():
            self.update_display()
            self.image_changed.emit()
    
    def redo(self):
        """Rehacer en la capa activa"""
        if self.floating_image is not None:
            return
        if self.layers[self.active_layer_index].redo():
            self.update_display()
            self.image_changed.emit()
    
    def is_modified(self):
        """Verificar si alguna capa ha sido modificada, o si hay más de una capa"""
        return len(self.layers) > 1 or any(len(layer.history) > 1 for layer in self.layers)
    
    def update_display(self):
        """Actualizar la visualización del canvas"""
        self.update()
    
    def resizeEvent(self, event):
        """Al cambiar de tamaño, scale_factor varía (se recalcula en paintEvent)
        así que refrescamos el cursor del pincel para que siga representando
        su grosor real en píxeles de pantalla."""
        super().resizeEvent(event)
        self.update_tool_cursor()
    
    def paintEvent(self, event):
        """Evento de pintado"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Calcular factor de escala para mostrar la imagen en el widget
        widget_width = self.width()
        widget_height = self.height()
        
        # Calcular escala para mantener proporción
        scale_x = widget_width / self.canvas_size
        scale_y = widget_height / self.canvas_size
        self.scale_factor = min(scale_x, scale_y, 8.0)  # Máximo 8x de zoom
        
        # Calcular offset para centrar
        display_width = int(self.canvas_size * self.scale_factor)
        display_height = int(self.canvas_size * self.scale_factor)
        self.offset_x = (widget_width - display_width) // 2
        self.offset_y = (widget_height - display_height) // 2
        
        # Dibujar fondo de cuadrícula (para transparencia)
        if self.bg_transparent:
            grid_size = 10 * self.scale_factor
            if grid_size > 1:
                painter.save()
                # Recortar exactamente al recuadro real del lienzo: sin esto,
                # la última celda de cada fila/columna puede "pasarse" un poco
                # del borde por redondeo (int(grid_size) no divide siempre
                # exacto a display_width/height). Normalmente no se nota
                # porque ese sobrante cae fuera del widget, pero cuando el
                # ancho manda sobre el alto (por ejemplo al estrechar los
                # paneles laterales) sobra espacio vertical alrededor del
                # lienzo, y ahí sí se veía ese sobrante de cuadrícula.
                painter.setClipRect(self.offset_x, self.offset_y, display_width, display_height)
                # Dibujar patrón de cuadrícula
                for x in range(0, display_width, int(grid_size)):
                    for y in range(0, display_height, int(grid_size)):
                        color = QColor(200, 200, 200) if (x // int(grid_size) + y // int(grid_size)) % 2 == 0 else QColor(240, 240, 240)
                        painter.fillRect(
                            self.offset_x + x,
                            self.offset_y + y,
                            int(grid_size),
                            int(grid_size),
                            color
                        )
                painter.restore()
        
        # Dibujar la imagen (composición de todas las capas visibles)
        composed = self.composite_layers()
        if composed:
            scaled = composed.scaled(
                display_width, display_height,
                Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            painter.drawImage(self.offset_x, self.offset_y, scaled)
        
        # Dibujar borde del canvas
        painter.setPen(QPen(QColor(150, 150, 150), 1))
        painter.drawRect(self.offset_x - 1, self.offset_y - 1,
                        display_width + 1, display_height + 1)
        
        # Dibujar la imagen flotante (pendiente de fijar) y sus handles, si hay una
        if self.floating_image is not None and self.floating_rect is not None:
            self.draw_floating_overlay(painter)
        
        # Dibujar la previsualización de una forma en curso de arrastre (línea,
        # rectángulo, círculo, triángulo): se muestra encima de todo, sin haberse
        # fusionado todavía con ninguna capa
        if self.shape_preview_image is not None:
            scaled_shape = self.shape_preview_image.scaled(
                display_width, display_height, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            painter.drawImage(self.offset_x, self.offset_y, scaled_shape)
        
        # Dibujar el rectángulo de selección (en vivo mientras se arrastra, o
        # ya confirmado tras soltar) en naranja discontinuo, para distinguirlo
        # del azul de la imagen flotante
        rect_to_draw = self.selection_preview_rect if self.selection_preview_rect is not None else self.selection_rect
        if rect_to_draw is not None:
            wx = self.offset_x + rect_to_draw.x() * self.scale_factor
            wy = self.offset_y + rect_to_draw.y() * self.scale_factor
            ww = rect_to_draw.width() * self.scale_factor
            wh = rect_to_draw.height() * self.scale_factor
            painter.save()
            painter.setPen(QPen(QColor(255, 140, 0), 2, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(int(wx), int(wy), int(ww), int(wh))
            painter.restore()
    
    def draw_floating_overlay(self, painter):
        """Dibuja la imagen flotante en su posición/tamaño actual, con un borde
        discontinuo y handles en esquinas y bordes para poder moverla/redimensionarla."""
        rect = self.floating_rect
        
        # Convertir el rectángulo (coords. de canvas) a coords. del widget
        wx = self.offset_x + rect.x() * self.scale_factor
        wy = self.offset_y + rect.y() * self.scale_factor
        ww = max(1, rect.width() * self.scale_factor)
        wh = max(1, rect.height() * self.scale_factor)
        
        scaled_floating = self.floating_image.scaled(
            int(ww), int(wh), Qt.IgnoreAspectRatio, Qt.SmoothTransformation
        )
        painter.drawImage(int(wx), int(wy), scaled_floating)
        
        if self.floating_locked:
            # Fijada visualmente: no se muestran handles ni borde, aunque aún
            # no se ha fusionado con los píxeles del canvas
            return
        
        # Borde discontinuo alrededor de la imagen flotante
        painter.save()
        pen = QPen(QColor(30, 144, 255), 2, Qt.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(int(wx), int(wy), int(ww), int(wh))
        
        # Handles: cuadraditos blancos con borde azul en esquinas y en el punto
        # medio de cada lado
        handle_visual_size = 8
        handle_positions = {
            'top-left': (wx, wy),
            'top-right': (wx + ww, wy),
            'bottom-left': (wx, wy + wh),
            'bottom-right': (wx + ww, wy + wh),
            'top': (wx + ww / 2, wy),
            'bottom': (wx + ww / 2, wy + wh),
            'left': (wx, wy + wh / 2),
            'right': (wx + ww, wy + wh / 2),
        }
        painter.setPen(QPen(QColor(30, 144, 255), 1))
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        for hx, hy in handle_positions.values():
            painter.drawRect(
                int(hx - handle_visual_size / 2), int(hy - handle_visual_size / 2),
                handle_visual_size, handle_visual_size
            )
        painter.restore()
    
    def mousePressEvent(self, event):
        """Evento de presión del mouse"""
        if event.button() == Qt.LeftButton:
            if self.floating_image is not None:
                if not self.floating_locked:
                    # 1) ¿Se ha pulsado sobre un handle? -> iniciar redimensionamiento
                    handle = self.get_floating_handle_at(event.pos())
                    if handle:
                        self.floating_handle = handle
                        self.floating_moving = False
                        self.floating_drag_start_mouse = self.widget_to_canvas(event.pos())
                        self.floating_drag_start_rect = QRect(self.floating_rect)
                        self.setCursor(self.get_cursor_for_handle(handle))
                        return
                    # 2) ¿Se ha pulsado dentro de la imagen (pero no en un handle)? -> mover
                    if self.is_point_inside_floating(event.pos()):
                        self.floating_handle = None
                        self.floating_moving = True
                        self.floating_drag_start_mouse = self.widget_to_canvas(event.pos())
                        self.floating_drag_start_rect = QRect(self.floating_rect)
                        self.setCursor(Qt.SizeAllCursor)
                        return
                # 3) Bloqueada, o clic fuera de la imagen flotante: la fusionamos con
                # el canvas y seguimos con el flujo normal de dibujo (el clic no se pierde)
                self.apply_floating_image()
            
            if self.current_tool in ("line", "rectangle", "circle", "triangle"):
                # Herramientas de forma: cada forma se dibuja sobre un lienzo
                # transparente aparte (overlay, ver paintEvent), sin tocar ninguna
                # capa; al soltar el botón se crea una CAPA NUEVA con la forma
                # (cada forma es su propio objeto, igual que en Photoshop).
                self.shape_start_point = self.widget_to_canvas_point(event.pos())
                self.shape_preview_image = self._blank_canvas_image()
                return
            
            if self.current_tool == "move":
                # Herramienta Mover/Seleccionar: el clic selecciona la capa VISIBLE
                # más alta cuyo recuadro de contenido incluya ese punto, sin importar
                # si es la capa activa ahora mismo ni cuándo se creó, y arranca el
                # arrastre EN EL MISMO gesto (clic y arrastro sin soltar), igual que
                # antes. Si sueltas sin arrastrar apenas, se queda con los handles
                # visibles para poder redimensionarla o volver a moverla después.
                point = self.widget_to_canvas_point(event.pos())
                hit_index = self.hit_test_layer(point, prefer_bbox=True)
                if hit_index is not None:
                    self.enter_layer_edit_mode(hit_index)
                    self.floating_handle = None
                    self.floating_moving = True
                    self.floating_drag_start_mouse = self.widget_to_canvas(event.pos())
                    self.floating_drag_start_rect = QRect(self.floating_rect)
                    self.setCursor(Qt.SizeAllCursor)
                return
            
            if self.current_tool == "select":
                # Herramienta Seleccionar: arrastra un rectángulo (marca la
                # zona para luego recortarla con "Recortar"). No pertenece a
                # ninguna capa en particular hasta que se recorta.
                self.selection_start_point = self.widget_to_canvas_point(event.pos())
                self.selection_preview_rect = QRect(self.selection_start_point, self.selection_start_point)
                return
            
            if self.current_tool == "fill":
                # Relleno: se ejecuta UNA sola vez en el punto de clic, no en cada
                # movimiento del mouse, y sin dejar una marca de pincel antes de
                # rellenar (antes se pintaba un punto con draw_point y luego, si el
                # color ya coincidía, el flood fill no hacía nada visible).
                #
                # La ZONA a rellenar se calcula sobre la imagen COMPUESTA (todas
                # las capas visibles + fondo), no sobre la capa activa en solitario:
                # como cada forma vive en su propia capa (casi toda ella
                # transparente), calcularla solo con esa capa haría que el relleno
                # se extendiera por CASI TODA la capa en vez de respetar el
                # contorno tal y como se ve en pantalla. El COLOR resultante sí se
                # aplica solo en la capa activa (no se tocan las demás).
                point = self.map_to_canvas(event.pos())
                if point:
                    try:
                        composite = self.composite_layers()
                        region = self.drawing_tools.flood_fill_region(composite, point, self.fill_tolerance)
                        self.status_message.emit(
                            f"Relleno: {len(region)} píxel(es) encontrados en "
                            f"({point.x()},{point.y()}), tolerancia={self.fill_tolerance}, "
                            f"capa activa='{self.layers[self.active_layer_index].name}'"
                        )
                        if region:
                            fill_color = QColor(0, 0, 0, 0) if self.fill_transparent else self.draw_color
                            layer = self.layers[self.active_layer_index]
                            image = layer.image.copy()
                            lw, lh = image.width(), image.height()
                            px, py = layer.position.x(), layer.position.y()
                            for (x, y) in region:
                                lx, ly = x - px, y - py
                                if 0 <= lx < lw and 0 <= ly < lh:
                                    image.setPixelColor(lx, ly, fill_color)
                            layer.image = image
                            self.update_display()
                            self.save_to_history()
                            self.image_changed.emit()
                    except Exception as e:
                        import traceback
                        traceback.print_exc()
                        self.status_message.emit(f"Relleno: ERROR — {e}")
                return
            
            if self.current_tool == "text":
                # Herramienta de texto: no se dibuja nada aquí; se avisa a la
                # ventana principal (que gestiona el diálogo de texto) con el
                # punto donde se ha hecho clic.
                click_point = self.widget_to_canvas_point(event.pos())
                self.text_tool_requested.emit(click_point)
                return
            
            if self.current_tool == "pencil":
                # El lápiz pinta sobre la capa activa (no crea una capa nueva
                # por cada trazo, para no llenar la lista). PERO si la capa
                # activa es un OBJETO (imagen importada, texto o forma:
                # cualquier layer_type != "generic"), no queremos que el trazo
                # se funda con él —perderías la posibilidad de mover/editar el
                # objeto por separado más adelante—. En ese caso, se crea (una
                # sola vez) una capa de dibujo nueva y en blanco, que pasa a ser
                # la activa; los trazos siguientes mientras siga activa esa
                # misma capa se acumulan ahí con normalidad.
                #
                # El borrador NO entra aquí a propósito: si borras parte de una
                # imagen/forma, tiene que borrar ESA capa, no una en blanco
                # donde no habría nada que borrar.
                active_layer = self.layers[self.active_layer_index]
                if active_layer.layer_type != "generic":
                    self.add_layer()
            
            self.drawing = True
            self.last_point = self.map_to_canvas(event.pos())
            if self.last_point:
                # Iniciar dibujo con la herramienta
                self.drawing_tools.start_drawing(self.last_point)
                self.draw_point(self.last_point)
                self.save_to_history()
    
    def mouseMoveEvent(self, event):
        """Evento de movimiento del mouse"""
        pos = self.map_to_canvas(event.pos())
        if pos:
            self.position_changed.emit(pos.x(), pos.y())
        
        if self.floating_image is not None and not self.floating_locked:
            if (self.floating_handle or self.floating_moving) and event.buttons() & Qt.LeftButton:
                self.update_floating_transform(event.pos())
                return
            # Aunque no se esté arrastrando, actualizamos el cursor al pasar
            # por encima de los handles o del cuerpo de la imagen flotante
            handle = self.get_floating_handle_at(event.pos())
            if handle:
                self.setCursor(self.get_cursor_for_handle(handle))
            elif self.is_point_inside_floating(event.pos()):
                self.setCursor(Qt.SizeAllCursor)
            else:
                self.setCursor(Qt.CrossCursor)
            return
        
        if self.current_tool == "move":
            # Sin nada en edición todavía: solo damos pista visual de si hay un
            # objeto debajo del cursor (al hacer clic entrará en modo edición)
            point = self.widget_to_canvas_point(event.pos())
            self.setCursor(Qt.OpenHandCursor if self.hit_test_layer(point) is not None else Qt.ArrowCursor)
            return
        
        if self.selection_start_point is not None and event.buttons() & Qt.LeftButton:
            current_point = self.widget_to_canvas_point(event.pos())
            self.selection_preview_rect = QRect(self.selection_start_point, current_point).normalized()
            self.update_display()
            return
        
        if self.shape_start_point is not None and self.shape_preview_image is not None \
                and event.buttons() & Qt.LeftButton:
            current_point = self.widget_to_canvas_point(event.pos())
            self.shape_preview_image = self.render_shape(
                self._blank_canvas_image(), self.shape_start_point, current_point
            )
            self.update_display()
            return
        
        if self.drawing and self.last_point:
            new_point = self.map_to_canvas(event.pos())
            if new_point:
                self.draw_line(self.last_point, new_point)
                self.last_point = new_point
                self.update_display()
    
    def mouseReleaseEvent(self, event):
        """Evento de liberación del mouse"""
        if event.button() == Qt.LeftButton:
            if self.floating_image is not None and not self.floating_locked and (self.floating_handle or self.floating_moving):
                self.floating_handle = None
                self.floating_moving = False
                self.floating_drag_start_mouse = None
                self.floating_drag_start_rect = None
                return
            
            if self.selection_start_point is not None:
                end_point = self.widget_to_canvas_point(event.pos())
                rect = QRect(self.selection_start_point, end_point).normalized()
                self.selection_start_point = None
                self.selection_preview_rect = None
                
                if rect.width() < 2 or rect.height() < 2:
                    # Arrastre insignificante (casi un clic): se descarta sin marcar nada
                    self.selection_rect = None
                    self.update_display()
                    return
                
                self.selection_rect = rect
                layer = self.layers[self.active_layer_index]
                if not layer.bounds().contains(rect):
                    self.status_message.emit(
                        f"Selección de {rect.width()}x{rect.height()} px — OJO: parte "
                        f"queda fuera de la capa activa '{layer.name}'. Al recortar, solo "
                        "se conservará la parte que se solape con ella."
                    )
                else:
                    self.status_message.emit(f"Selección: {rect.width()}x{rect.height()} px")
                self.update_display()
                return
            
            if self.shape_start_point is not None:
                # Fijar la forma definitiva entre el punto de inicio y el de soltar,
                # como CAPA NUEVA (no se mezcla con ninguna capa existente)
                end_point = self.widget_to_canvas_point(event.pos())
                shape_image = self.render_shape(
                    self._blank_canvas_image(), self.shape_start_point, end_point
                )
                self.shape_start_point = None
                self.shape_preview_image = None
                self.create_object_layer(self._shape_layer_name(), shape_image)
                return
            
            if self.drawing:
                self.drawing = False
                self.last_point = None
                self.drawing_tools.is_drawing = False
                self.save_to_history()
                self.image_changed.emit()
    
    def hit_test_layer(self, point, prefer_bbox=False):
        """Devuelve el índice de la capa VISIBLE más alta (más cercana al frente)
        que hay en `point` (coords. de canvas), o None si ninguna coincide.
        self.layers[0] es la superior, así que se recorre en ese mismo orden.
        
        Primero se prueba con el píxel EXACTO (rápido, sin conversiones de
        formato: válido para el simple paso del cursor en cada mouseMoveEvent).
        Solo si no encuentra nada Y `prefer_bbox` es True —se usa así únicamente
        en el clic real, nunca en el hover— se repite comprobando el RECUADRO de
        contenido de cada capa (más costoso), para poder seleccionar formas SIN
        relleno haciendo clic en su interior, no solo justo sobre el borde."""
        if not (0 <= point.x() < self.canvas_size and 0 <= point.y() < self.canvas_size):
            return None
        
        for index, layer in enumerate(self.layers):
            if not layer.visible:
                continue
            local_x = point.x() - layer.position.x()
            local_y = point.y() - layer.position.y()
            if 0 <= local_x < layer.image.width() and 0 <= local_y < layer.image.height():
                if layer.image.pixelColor(local_x, local_y).alpha() > 0:
                    return index
        
        if not prefer_bbox:
            return None
        
        for index, layer in enumerate(self.layers):
            if not layer.visible:
                continue
            bbox = self._bounding_box_of_content(layer.image)
            if bbox is not None:
                absolute_bbox = QRect(
                    layer.position.x() + bbox.x(), layer.position.y() + bbox.y(),
                    bbox.width(), bbox.height()
                )
                if absolute_bbox.contains(point):
                    return index
        return None
    
    def enter_layer_edit_mode(self, index):
        """Vuelve a mostrar los tiradores de mover/redimensionar sobre el contenido
        de una capa YA EXISTENTE —por ejemplo, tras seleccionarla en el panel de
        capas o con la herramienta Mover—, para poder seguir editándola como si
        acabara de insertarse. Reutiliza el mismo mecanismo de "imagen flotante":
        el contenido se recorta de la capa y se muestra flotando con handles, en
        su posición ABSOLUTA real (la capa puede estar parcialmente fuera del
        lienzo); al fijarlo (Enter / «Fijar») se sustituye el contenido de ESA
        MISMA capa, no se crea una nueva."""
        if not (0 <= index < len(self.layers)):
            return
        if self.floating_image is not None:
            self.apply_floating_image()
        
        layer = self.layers[index]
        bbox = self._bounding_box_of_content(layer.image)
        if bbox is None:
            # Capa en blanco: no hay nada que recortar, partimos de toda su imagen
            bbox = QRect(0, 0, layer.image.width(), layer.image.height())
        cropped = layer.image.copy(bbox)
        absolute_rect = QRect(
            layer.position.x() + bbox.x(), layer.position.y() + bbox.y(),
            bbox.width(), bbox.height()
        )
        
        # "Levantamos" el contenido de la capa: su contenido real pasa a vivir
        # en la imagen flotante mientras se edita, y se restaura (con los
        # cambios) al fijarla de nuevo. Guardamos una copia (imagen + posición)
        # para poder restaurarla tal cual si se cancela. Como su contenido ya
        # no importa mientras esté "levantada", la dejamos con un marcador
        # mínimo en vez de un lienzo entero en blanco (ya no hace falta asumir
        # que las capas ocupan siempre todo el lienzo).
        self._layer_edit_backup = (layer.image.copy(), QPoint(layer.position))
        placeholder = QImage(1, 1, QImage.Format_ARGB32)
        placeholder.fill(Qt.transparent)
        layer.image = placeholder
        
        self.active_layer_index = index
        self.floating_edit_layer_index = index
        self.floating_image = cropped
        self.floating_rect = absolute_rect
        self.floating_aspect = (bbox.width() / bbox.height()) if bbox.height() else 1.0
        self.floating_layer_name = layer.name
        self.floating_locked = False
        self.setCursor(Qt.SizeAllCursor)
        self.setFocus()
        self.update_display()
        self.image_changed.emit()
        self.floating_state_changed.emit()
        self.layers_changed.emit()
    
    def edit_layer_content(self, index, new_image, at_point=None):
        """Sustituye el contenido de una capa YA EXISTENTE por `new_image`,
        colocada en `at_point` (o donde estaba antes, si no se indica). A
        diferencia de enter_layer_edit_mode (que solo mueve/redimensiona lo ya
        renderizado), esto se usa cuando el propio objeto cambia de contenido
        —por ejemplo, al reeditar un texto con otras palabras, tipografía o
        color— y hace falta volver a renderizarlo."""
        if not (0 <= index < len(self.layers)):
            return
        layer = self.layers[index]
        
        # Si había un mover/redimensionar a medias sobre ESTA capa —por ejemplo,
        # el clic simple de selección que siempre precede a un doble clic ya la
        # puso en modo edición—, lo resolvemos AQUÍ, ANTES de mirar dónde estaba
        # su contenido (si no, leeríamos el marcador vacío temporal en vez de
        # la posición real).
        if self.floating_image is not None:
            if self.floating_edit_layer_index == index:
                self.cancel_floating_image()
            else:
                self.apply_floating_image()
        
        if at_point is None:
            # Posición ABSOLUTA del contenido ajustado (sin márgenes
            # transparentes) de la capa, tal y como estaba antes de reeditarla.
            old_bbox = self._bounding_box_of_content(layer.image)
            if old_bbox is None:
                old_bbox = QRect(0, 0, layer.image.width(), layer.image.height())
            at_point = QPoint(layer.position.x() + old_bbox.x(), layer.position.y() + old_bbox.y())
        
        # `at_point` representa dónde debe quedar el contenido AJUSTADO (sin
        # márgenes transparentes) del objeto anterior. Pero `new_image` puede
        # tener su propio margen interno alrededor del contenido real (p. ej.
        # el texto renderizado siempre lleva un pequeño margen, que cambia con
        # el tamaño de fuente). Alineamos el recuadro AJUSTADO de `new_image`
        # con `at_point`, no su esquina, para no ir desplazando el contenido
        # en cada reedición.
        new_bbox = self._bounding_box_of_content(new_image)
        if new_bbox is not None:
            draw_point = QPoint(at_point.x() - new_bbox.x(), at_point.y() - new_bbox.y())
        else:
            draw_point = at_point
        
        # Ya no hace falta "encajar" el contenido dentro del lienzo ni
        # recortarlo si ha crecido (p. ej. añadiste letras al texto): cada
        # capa tiene su propia posición y tamaño libremente, y solo se recorta
        # la VISUALIZACIÓN (ver composite_layers), nunca los datos.
        layer.image = new_image
        layer.position = draw_point
        self.active_layer_index = index
        self.save_to_history()
        self.update_display()
        self.image_changed.emit()
        self.layers_changed.emit()
    
    def _bounding_box_of_content(self, image):
        """Devuelve el QRect que encierra los píxeles no transparentes de `image`,
        o None si la imagen está totalmente vacía/transparente (o algo falla en
        la conversión). Importante: NO se devuelve "todo el lienzo" como
        alternativa aquí — cada llamador decide qué hacer con None, porque para
        hit_test_layer una capa vacía debe IGNORARSE (si devolviéramos aquí el
        lienzo entero, cualquier clic en cualquier sitio "encontraría" esa capa
        vacía como si ocupara toda la imagen).
        
        Se convierte a PIL para calcular el recuadro (Image.getbbox() sobre el
        canal alfa) en vez de tocar los bytes de la QImage directamente: es el
        mismo patrón que ya usa icon_exporter.py y evita depender de una API de
        bajo nivel (QImage.bits()) que varía entre versiones de PySide6."""
        bbox = None
        try:
            buffer = QBuffer()
            buffer.open(QBuffer.ReadWrite)
            image.save(buffer, "PNG")
            byte_array = buffer.data()
            buffer.close()
            
            pil_image = Image.open(io.BytesIO(byte_array.data())).convert("RGBA")
            alpha = pil_image.split()[-1]
            bbox = alpha.getbbox()
        except Exception:
            bbox = None
        
        if bbox is None:
            return None
        
        x_min, y_min, x_max, y_max = bbox
        return QRect(x_min, y_min, x_max - x_min, y_max - y_min)
    
    def _blank_canvas_image(self):
        """Nueva QImage del tamaño del canvas, totalmente transparente"""
        image = QImage(self.canvas_size, self.canvas_size, QImage.Format_ARGB32)
        image.fill(Qt.transparent)
        return image
    
    def _shape_layer_name(self):
        names = {
            "line": "Línea",
            "rectangle": "Rectángulo",
            "circle": "Círculo",
            "triangle": "Triángulo",
        }
        return names.get(self.current_tool, "Forma")
    
    def create_object_layer(self, name, image, layer_type="generic", data=None):
        """Crea una capa nueva (arriba de todas) a partir de una imagen en
        coordenadas de canvas (tamaño canvas_size x canvas_size, resto
        transparente): se recorta a su contenido real y se guarda junto con su
        posición absoluta, para no arrastrar de por vida un lienzo entero de
        margen transparente alrededor de cada objeto. La deja como capa activa
        y la registra en su propio historial. Se usa para que cada
        forma/texto/imagen importada sea su propio objeto/capa, igual que en
        Photoshop. `layer_type`/`data` guardan metadatos (p. ej. texto/fuente/
        color original) para poder reeditar el objeto más adelante, no solo
        moverlo/redimensionarlo."""
        bbox = self._bounding_box_of_content(image)
        if bbox is None:
            bbox = QRect(0, 0, image.width(), image.height())
        cropped = image.copy(bbox)
        
        layer = Layer(self._unique_layer_name(name), cropped, position=bbox.topLeft())
        layer.layer_type = layer_type
        layer.data = data or {}
        self.layers.insert(0, layer)
        self.active_layer_index = 0
        self.update_display()
        self.image_changed.emit()
        self.layers_changed.emit()
    
    def _unique_layer_name(self, base_name):
        """Evita nombres de capa duplicados: 'Rectángulo', 'Rectángulo 2', ..."""
        existing = {layer.name for layer in self.layers}
        if base_name not in existing:
            return base_name
        n = 2
        while f"{base_name} {n}" in existing:
            n += 1
        return f"{base_name} {n}"
    
    def render_shape(self, base_image, start, end):
        """Devuelve una copia de base_image con la forma de la herramienta actual
        dibujada entre start y end. No modifica base_image ni self.current_image."""
        image = base_image.copy()
        if self.current_tool == "line":
            image = self.shape_tools.draw_line(image, start, end)
        elif self.current_tool == "rectangle":
            image = self.shape_tools.draw_rectangle(image, start, end)
        elif self.current_tool == "circle":
            image = self.shape_tools.draw_ellipse(image, start, end)
        elif self.current_tool == "triangle":
            image = self.shape_tools.draw_triangle(image, start, end)
        return image
    
    def keyPressEvent(self, event):
        """Atajos de teclado: Enter/Esc para la imagen flotante, Esc también cancela
        un arrastre de forma en curso (línea/rectángulo/círculo/triángulo)"""
        if self.floating_image is not None:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                self.toggle_floating_lock()
                return
            elif event.key() == Qt.Key_Escape:
                self.cancel_floating_image()
                return
        
        if self.shape_start_point is not None and event.key() == Qt.Key_Escape:
            self.shape_start_point = None
            self.shape_preview_image = None
            self.update_display()
            return
        
        if event.key() == Qt.Key_Escape and (self.selection_rect is not None or self.selection_start_point is not None):
            self.clear_selection()
            return
        
        super().keyPressEvent(event)
    
    def map_to_canvas(self, pos):
        """Mapear posición del widget al canvas, acotado al área visible del lienzo
        (usado por las herramientas de dibujo: fuera del lienzo no se dibuja)"""
        x = (pos.x() - self.offset_x) / self.scale_factor
        y = (pos.y() - self.offset_y) / self.scale_factor
        
        if 0 <= x < self.canvas_size and 0 <= y < self.canvas_size:
            return QPoint(int(x), int(y))
        return None
    
    def widget_to_canvas(self, pos):
        """Igual que map_to_canvas pero sin acotar al lienzo: necesario para poder
        arrastrar la imagen flotante o sus handles aunque el cursor quede momentáneamente
        fuera del área del canvas."""
        x = (pos.x() - self.offset_x) / self.scale_factor
        y = (pos.y() - self.offset_y) / self.scale_factor
        return QPointF(x, y)
    
    def widget_to_canvas_point(self, pos):
        """Como widget_to_canvas, pero como QPoint entero. Se usa para arrastrar formas
        (línea/rectángulo/círculo/triángulo): a diferencia de map_to_canvas, no se acota
        al lienzo, para poder empezar o terminar el arrastre justo en el borde o fuera
        de él, como en cualquier editor de imagen."""
        p = self.widget_to_canvas(pos)
        return QPoint(int(p.x()), int(p.y()))
    
    def _ensure_point_within_layer(self, layer, point):
        """Si `point` (coords. de canvas) cae fuera de los límites actuales de
        `layer`, agranda su imagen (y ajusta su posición) lo justo para que
        quepa, conservando todo su contenido actual en su sitio. Hace falta
        porque una capa puede haberse movido y haber quedado más pequeña que
        el lienzo (recortada a su contenido real), pero se debe poder seguir
        dibujando en cualquier parte, igual que si nunca se hubiera movido."""
        local_x = point.x() - layer.position.x()
        local_y = point.y() - layer.position.y()
        w, h = layer.image.width(), layer.image.height()
        
        if 0 <= local_x < w and 0 <= local_y < h:
            return  # ya cabe, no hace falta agrandar nada
        
        margin = 4  # margen extra, para no tener que agrandar en cada píxel
        new_left = min(0, local_x - margin)
        new_top = min(0, local_y - margin)
        new_right = max(w, local_x + margin + 1)
        new_bottom = max(h, local_y + margin + 1)
        
        grown = QImage(new_right - new_left, new_bottom - new_top, QImage.Format_ARGB32)
        grown.fill(Qt.transparent)
        painter = QPainter(grown)
        painter.drawImage(-new_left, -new_top, layer.image)
        painter.end()
        
        layer.image = grown
        layer.position = QPoint(layer.position.x() + new_left, layer.position.y() + new_top)
    
    def draw_point(self, point):
        """Dibujar un punto en la capa activa (lápiz/borrador; el relleno y las
        formas se gestionan aparte, ver mousePressEvent). `point` está en
        coordenadas de canvas; se traduce a coordenadas locales de la capa
        activa, ya que esta puede no estar en (0,0) ni ocupar todo el lienzo
        (p. ej. el borrador puede actuar directamente sobre una imagen
        importada más pequeña que el lienzo)."""
        if self.current_tool in ["pencil", "eraser"]:
            layer = self.layers[self.active_layer_index]
            if self.current_tool == "pencil":
                self._ensure_point_within_layer(layer, point)
            local_point = QPoint(point.x() - layer.position.x(), point.y() - layer.position.y())
            layer.image = self.drawing_tools.draw_point(layer.image, local_point)
        self.update_display()
    
    def draw_line(self, start, end):
        """Dibujar un trazo a mano alzada (lápiz/borrador) mientras se arrastra.
        `start`/`end` están en coordenadas de canvas; se traducen a locales de
        la capa activa (ver draw_point)."""
        if self.current_tool in ["pencil", "eraser"]:
            layer = self.layers[self.active_layer_index]
            if self.current_tool == "pencil":
                self._ensure_point_within_layer(layer, end)
            local_start = QPoint(start.x() - layer.position.x(), start.y() - layer.position.y())
            local_end = QPoint(end.x() - layer.position.x(), end.y() - layer.position.y())
            layer.image = self.drawing_tools.draw_line(layer.image, local_start, local_end)
        self.update_display()
    
    def set_fill_transparent(self, enabled):
        """Si está activado, la herramienta de relleno rellena con transparente
        en vez de con el color de dibujo actual."""
        self.fill_transparent = bool(enabled)
    
    def set_fill_tolerance(self, value):
        """Tolerancia de color del relleno (0-255): cuánto puede diferir un
        píxel del color de origen para considerarse parte de la misma zona."""
        self.fill_tolerance = int(value)
    
    # ============ MÉTODOS DE LA IMAGEN FLOTANTE (importar + ajustar) ============
    
    def start_floating_image(self, qimage, initial_rect=None, name="Objeto", object_type="generic", data=None):
        """Coloca una imagen recién importada (o un texto renderizado) como objeto
        flotante editable sobre el canvas: no se fusiona con ninguna capa hasta
        llamar a apply_floating_image() (o pulsar Enter / el botón «Aplicar»),
        momento en el que se convierte en una CAPA NUEVA con el nombre `name`.
        `object_type`/`data` se guardan en esa capa para poder reeditar el
        objeto más adelante (p. ej. reabrir el diálogo de texto), no solo
        moverlo/redimensionarlo."""
        # Si ya había una imagen flotante sin fijar, la fijamos antes de sustituirla
        if self.floating_image is not None:
            self.apply_floating_image()
        
        if qimage.format() != QImage.Format_ARGB32:
            qimage = qimage.convertToFormat(QImage.Format_ARGB32)
        
        self.floating_image = qimage
        self.floating_layer_name = name
        self.floating_object_type = object_type
        self.floating_object_data = data or {}
        self.floating_edit_layer_index = None  # es contenido nuevo, no una capa reeditada
        w, h = qimage.width(), qimage.height()
        self.floating_aspect = (w / h) if h else 1.0
        
        if initial_rect is None:
            # Encaje inicial centrado, manteniendo proporción (el usuario podrá
            # ajustarlo libremente después arrastrando los handles)
            if w and h:
                scale = min(self.canvas_size / w, self.canvas_size / h)
            else:
                scale = 1.0
            new_w = max(8, int(w * scale))
            new_h = max(8, int(h * scale))
            x = (self.canvas_size - new_w) // 2
            y = (self.canvas_size - new_h) // 2
            initial_rect = QRect(x, y, new_w, new_h)
        
        self.floating_rect = initial_rect
        self.floating_locked = False
        self.setCursor(Qt.SizeAllCursor)
        self.setFocus()
        self.update_display()
        self.image_changed.emit()
        self.floating_state_changed.emit()
    
    def get_floating_handle_at(self, widget_pos):
        """Handle de la imagen flotante bajo una posición del widget, o None"""
        if not self.floating_rect:
            return None
        
        p = self.widget_to_canvas(widget_pos)
        handle_size = 10 / self.scale_factor
        rect = self.floating_rect
        x, y = p.x(), p.y()
        left, right, top, bottom = rect.left(), rect.right(), rect.top(), rect.bottom()
        
        def near(a, b):
            return abs(a - b) <= handle_size
        
        # Esquinas
        if near(x, left) and near(y, top):
            return 'top-left'
        if near(x, right) and near(y, top):
            return 'top-right'
        if near(x, left) and near(y, bottom):
            return 'bottom-left'
        if near(x, right) and near(y, bottom):
            return 'bottom-right'
        # Bordes
        if near(x, left) and top - handle_size <= y <= bottom + handle_size:
            return 'left'
        if near(x, right) and top - handle_size <= y <= bottom + handle_size:
            return 'right'
        if near(y, top) and left - handle_size <= x <= right + handle_size:
            return 'top'
        if near(y, bottom) and left - handle_size <= x <= right + handle_size:
            return 'bottom'
        
        return None
    
    def is_point_inside_floating(self, widget_pos):
        """True si la posición del widget cae dentro del cuerpo de la imagen flotante"""
        if not self.floating_rect:
            return False
        p = self.widget_to_canvas(widget_pos)
        return self.floating_rect.contains(int(p.x()), int(p.y()))
    
    def get_cursor_for_handle(self, handle):
        """Obtener el cursor para un handle específico"""
        cursors = {
            'top-left': Qt.SizeFDiagCursor,
            'bottom-right': Qt.SizeFDiagCursor,
            'top-right': Qt.SizeBDiagCursor,
            'bottom-left': Qt.SizeBDiagCursor,
            'top': Qt.SizeVerCursor,
            'bottom': Qt.SizeVerCursor,
            'left': Qt.SizeHorCursor,
            'right': Qt.SizeHorCursor,
        }
        return cursors.get(handle, Qt.CrossCursor)
    
    def update_floating_transform(self, widget_pos):
        """Recalcula floating_rect mientras se arrastra un handle (redimensionar)
        o el cuerpo de la imagen (mover)."""
        if self.floating_drag_start_mouse is None or self.floating_drag_start_rect is None:
            return
        
        current = self.widget_to_canvas(widget_pos)
        dx = current.x() - self.floating_drag_start_mouse.x()
        dy = current.y() - self.floating_drag_start_mouse.y()
        start_rect = self.floating_drag_start_rect
        
        if self.floating_moving:
            new_rect = QRect(start_rect)
            new_rect.moveTo(int(start_rect.left() + dx), int(start_rect.top() + dy))
            self.floating_rect = new_rect
            self.update_display()
            self.image_changed.emit()
            return
        
        handle = self.floating_handle
        min_size = 8
        left, top = start_rect.left(), start_rect.top()
        right, bottom = start_rect.right(), start_rect.bottom()
        
        if 'left' in handle:
            left = min(right - min_size, left + dx)
        if 'right' in handle:
            right = max(left + min_size, right + dx)
        if 'top' in handle:
            top = min(bottom - min_size, top + dy)
        if 'bottom' in handle:
            bottom = max(top + min_size, bottom + dy)
        
        if self.keep_aspect_ratio and self.floating_aspect:
            # Anclamos el borde/esquina OPUESTO al que se arrastra, y derivamos
            # la dimensión que falta para respetar la proporción original.
            fixed_x = start_rect.right() if 'left' in handle else start_rect.left()
            fixed_y = start_rect.bottom() if 'top' in handle else start_rect.top()
            
            new_w = right - left
            new_h = bottom - top
            
            has_horizontal = ('left' in handle) or ('right' in handle)
            has_vertical = ('top' in handle) or ('bottom' in handle)
            
            if has_horizontal and not has_vertical:
                # Lateral izquierdo/derecho: la altura se deriva del nuevo ancho
                new_h = new_w / self.floating_aspect
            elif has_vertical and not has_horizontal:
                # Lateral superior/inferior: el ancho se deriva de la nueva altura
                new_w = new_h * self.floating_aspect
            else:
                # Esquina: domina el eje que ha cambiado proporcionalmente más
                if abs(new_w) >= abs(new_h * self.floating_aspect):
                    new_h = new_w / self.floating_aspect
                else:
                    new_w = new_h * self.floating_aspect
            
            if 'left' in handle:
                left = fixed_x - new_w
            else:
                right = fixed_x + new_w
            if 'top' in handle:
                top = fixed_y - new_h
            else:
                bottom = fixed_y + new_h
        
        self.floating_rect = QRect(
            int(left), int(top),
            max(min_size, int(right - left)), max(min_size, int(bottom - top))
        )
        self.update_display()
        self.image_changed.emit()
    
    def set_keep_aspect_ratio(self, keep):
        """Activar/desactivar el bloqueo de proporción al redimensionar desde una esquina"""
        self.keep_aspect_ratio = bool(keep)
    
    def toggle_floating_lock(self):
        """Alterna entre modo de ajuste (con handles visibles e interactivos) y
        vista «fijada» (sin handles) de la imagen flotante, SIN fusionarla todavía
        con el canvas: se puede volver a llamar para recuperar los handles y seguir
        ajustando. La fusión real de píxeles ocurre más adelante, de forma automática,
        al cambiar de herramienta, exportar, guardar, etc. (ver apply_floating_image)."""
        if self.floating_image is None:
            return
        self.floating_locked = not self.floating_locked
        self.floating_handle = None
        self.floating_moving = False
        self.setCursor(Qt.CrossCursor if self.floating_locked else Qt.SizeAllCursor)
        self.update_display()
        self.floating_state_changed.emit()
    
    def apply_floating_image(self):
        """Fija la imagen/texto/objeto flotante en su posición y tamaño
        actuales, SIN recortar nada aunque quede parcialmente fuera del
        lienzo: la capa guarda su propia posición absoluta; solo la
        VISUALIZACIÓN se recorta al tamaño del lienzo (ver composite_layers),
        nunca los datos. Si venía de reeditar una capa existente
        (enter_layer_edit_mode), sustituye el contenido y la posición de ESA
        MISMA capa; si es una imagen/texto/forma nueva, crea una CAPA NUEVA
        (cada objeto insertado es su propio objeto, como en Photoshop)."""
        if self.floating_image is None or self.floating_rect is None:
            return
        
        scaled = self.floating_image.scaled(
            max(1, self.floating_rect.width()), max(1, self.floating_rect.height()),
            Qt.IgnoreAspectRatio, Qt.SmoothTransformation
        )
        position = QPoint(self.floating_rect.topLeft())
        
        name = self.floating_layer_name
        object_type = self.floating_object_type
        object_data = self.floating_object_data
        edit_index = self.floating_edit_layer_index
        
        self.floating_image = None
        self.floating_rect = None
        self.floating_locked = False
        self.floating_handle = None
        self.floating_moving = False
        self.floating_edit_layer_index = None
        self.floating_object_type = "generic"
        self.floating_object_data = None
        self._layer_edit_backup = None
        self.setCursor(Qt.CrossCursor)
        
        if edit_index is not None and 0 <= edit_index < len(self.layers):
            # Reeditando una capa existente: se sustituye su contenido Y su
            # posición, no se crea ninguna capa nueva
            self.layers[edit_index].image = scaled
            self.layers[edit_index].position = position
            self.active_layer_index = edit_index
            self.save_to_history()
            self.update_display()
            self.image_changed.emit()
            self.layers_changed.emit()
        else:
            # Objeto nuevo: `scaled` ya es su contenido ajustado (sin margen
            # extra que recortar), así que construimos la capa directamente
            # con su posición, sin pasar por create_object_layer.
            layer = Layer(self._unique_layer_name(name), scaled, position=position)
            layer.layer_type = object_type
            layer.data = object_data or {}
            self.layers.insert(0, layer)
            self.active_layer_index = 0
            self.update_display()
            self.image_changed.emit()
            self.layers_changed.emit()
        
        self.floating_state_changed.emit()
    
    def cancel_floating_image(self):
        """Descarta la imagen flotante sin fusionarla con el canvas. Si venía de
        reeditar una capa existente, esa capa recupera el contenido que tenía
        antes de entrar en modo edición (no se pierde el objeto)."""
        if self.floating_image is None:
            return
        
        edit_index = self.floating_edit_layer_index
        if edit_index is not None and 0 <= edit_index < len(self.layers) and self._layer_edit_backup is not None:
            backup_image, backup_position = self._layer_edit_backup
            self.layers[edit_index].image = backup_image
            self.layers[edit_index].position = backup_position
        
        self.floating_image = None
        self.floating_rect = None
        self.floating_locked = False
        self.floating_handle = None
        self.floating_moving = False
        self.floating_edit_layer_index = None
        self._layer_edit_backup = None
        self.setCursor(Qt.CrossCursor)
        self.update_display()
        self.image_changed.emit()
        self.layers_changed.emit()
        self.floating_state_changed.emit()