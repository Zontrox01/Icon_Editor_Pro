"""
Representa una capa del editor de iconos: una imagen (QImage) independiente,
con su propia posición, nombre, visibilidad y su propio historial de
deshacer/rehacer.

`position` es la esquina superior izquierda de `image` en coordenadas del
lienzo: puede ser negativa, o hacer que la capa se extienda más allá del
lienzo por cualquier lado. La imagen de la capa NUNCA se recorta por quedar
fuera del lienzo — solo se recorta la VISUALIZACIÓN y la exportación (ver
Canvas.composite_layers). Así, si mueves un objeto parcialmente fuera del
lienzo y luego lo vuelves a traer dentro, no se pierde nada de su contenido.

Cada capa tiene su historial PROPIO (no uno compartido para todo el canvas):
deshacer/rehacer actúa sobre la capa activa en cada momento, e incluye tanto
su imagen como su posición (mover una capa también se puede deshacer).
"""

from PySide6.QtCore import QPoint, QRect


class Layer:
    """Una capa individual del canvas."""

    def __init__(self, name, image, position=None):
        self.name = name
        self.image = image      # QImage RGBA de esta capa
        if position is None:
            self.position = QPoint(0, 0)
        elif isinstance(position, QPoint):
            self.position = QPoint(position)
        else:
            # tupla/lista (x, y), p. ej. al deserializar desde JSON
            self.position = QPoint(position[0], position[1])
        self.visible = True
        self.layer_type = "generic"  # "generic" o "text"; permite reabrir el
                                      # diálogo de texto en vez de solo mover/redimensionar
        self.data = {}                # metadatos del objeto (p. ej. texto/fuente/color original)
        self.history = []
        self.history_index = -1
        self.max_history = 50
        # Guardamos el estado inicial para poder deshacer hasta el principio
        self.save_history()

    def save_history(self):
        """Guardar el estado actual (imagen + posición) en el historial propio de la capa."""
        # Si estábamos a mitad del historial (tras deshacer alguna vez),
        # descartamos el "futuro" antes de añadir el nuevo estado
        self.history = self.history[:self.history_index + 1]
        self.history.append((self.image.copy(), QPoint(self.position)))
        if len(self.history) > self.max_history:
            self.history.pop(0)
        self.history_index = len(self.history) - 1

    def can_undo(self):
        return self.history_index > 0

    def can_redo(self):
        return self.history_index < len(self.history) - 1

    def undo(self):
        if self.can_undo():
            self.history_index -= 1
            image, position = self.history[self.history_index]
            self.image = image.copy()
            self.position = QPoint(position)
            return True
        return False

    def redo(self):
        if self.can_redo():
            self.history_index += 1
            image, position = self.history[self.history_index]
            self.image = image.copy()
            self.position = QPoint(position)
            return True
        return False

    def bounds(self):
        """QRect absoluto (coords. de canvas) que ocupa esta capa."""
        return QRect(self.position, self.image.size())
