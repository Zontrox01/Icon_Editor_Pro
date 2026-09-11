"""
Representa una capa del editor de iconos: una imagen (QImage) independiente,
con su propio nombre, visibilidad y su propio historial de deshacer/rehacer.

Cada capa tiene su historial PROPIO (no uno compartido para todo el canvas):
deshacer/rehacer actúa sobre la capa activa en cada momento, igual que en la
mayoría de editores de imagen por capas.
"""


class Layer:
    """Una capa individual del canvas."""

    def __init__(self, name, image):
        self.name = name
        self.image = image      # QImage RGBA de esta capa
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
        """Guardar el estado actual de la capa en su propio historial."""
        # Si estábamos a mitad del historial (tras deshacer alguna vez),
        # descartamos el "futuro" antes de añadir el nuevo estado
        self.history = self.history[:self.history_index + 1]
        self.history.append(self.image.copy())
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
            self.image = self.history[self.history_index].copy()
            return True
        return False

    def redo(self):
        if self.can_redo():
            self.history_index += 1
            self.image = self.history[self.history_index].copy()
            return True
        return False
