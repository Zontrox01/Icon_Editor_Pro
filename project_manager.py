"""
Guardar y cargar proyectos del editor de iconos como JSON.

Desde que existen las capas, el formato de proyecto es v2.0: cada capa se
guarda por separado (nombre, visibilidad, tipo, imagen en PNG/base64, y en el
caso de las capas de texto, también el texto/tipografía/color originales para
poder reeditarlas al reabrir el proyecto), en el mismo orden que canvas.layers
(índice 0 = capa superior). Los proyectos antiguos (v1.0, una sola imagen sin
capas) se siguen pudiendo abrir con normalidad: se cargan como una única capa.
"""

import json
import base64
import os
from PySide6.QtGui import QImage, QColor, QFont
from PySide6.QtCore import QByteArray, QBuffer


class ProjectManager:
    def __init__(self):
        self.current_file = None
    
    def save_project(self, file_path, canvas):
        """Guardar proyecto en archivo JSON, incluyendo todas las capas"""
        layers_data = []
        for layer in canvas.layers:
            # QImage.save() necesita un QIODevice (QBuffer), no un QByteArray
            # directamente -pasarle el QByteArray a pelo es lo que causaba el
            # error "called with wrong argument types".
            buffer = QBuffer()
            buffer.open(QBuffer.ReadWrite)
            layer.image.save(buffer, "PNG")
            image_b64 = base64.b64encode(buffer.data().data()).decode('utf-8')
            buffer.close()
            
            layer_entry = {
                'name': layer.name,
                'visible': layer.visible,
                'layer_type': getattr(layer, 'layer_type', 'generic'),
                'position': [layer.position.x(), layer.position.y()],
                'image_data': image_b64
            }
            
            # Si es una capa de texto, guardamos también el texto/tipografía/
            # color originales, para poder reabrir el diálogo de edición de
            # texto (no solo mover/redimensionar) tras recargar el proyecto.
            if layer_entry['layer_type'] == 'text':
                data = getattr(layer, 'data', {}) or {}
                font = data.get('font')
                color = data.get('color')
                layer_entry['text_data'] = {
                    'text': data.get('text', ''),
                    'font_family': font.family() if font else None,
                    'font_size': font.pointSize() if font else None,
                    'font_bold': bool(font.bold()) if font else False,
                    'font_italic': bool(font.italic()) if font else False,
                    'font_underline': bool(font.underline()) if font else False,
                    'color': color.name() if color else None,
                }
            
            layers_data.append(layer_entry)
        
        project_data = {
            'version': '2.0',
            'canvas_size': canvas.canvas_size,
            'bg_transparent': canvas.bg_transparent,
            'bg_color': canvas.bg_color.name() if canvas.bg_color else None,
            'active_layer_index': canvas.active_layer_index,
            'layers': layers_data
        }
        
        with open(file_path, 'w') as f:
            json.dump(project_data, f, indent=2)
        
        self.current_file = file_path
    
    def _validate_project_data(self, project_data, file_path):
        """Comprobar que el archivo tiene la forma de un proyecto válido antes
        de tocar nada del canvas. Lanza ValueError con un mensaje claro (en
        vez de dejar que salte un KeyError/TypeError críptico de Python) si
        el archivo está corrupto, incompleto, o no es un proyecto de este
        programa."""
        if not isinstance(project_data, dict):
            raise ValueError(
                f"'{os.path.basename(file_path)}' no tiene el formato de un "
                "proyecto de Icon Editor (el contenido no es un objeto JSON válido)."
            )
        
        if 'canvas_size' not in project_data:
            raise ValueError(
                f"'{os.path.basename(file_path)}' no parece un proyecto de "
                "Icon Editor: falta el tamaño del lienzo."
            )
        
        canvas_size = project_data['canvas_size']
        if not isinstance(canvas_size, int) or canvas_size <= 0:
            raise ValueError(
                f"El tamaño de lienzo guardado en '{os.path.basename(file_path)}' "
                "no es válido."
            )
        
        has_layers = 'layers' in project_data
        has_legacy_image = 'image_data' in project_data
        
        if not has_layers and not has_legacy_image:
            raise ValueError(
                f"'{os.path.basename(file_path)}' no contiene ninguna imagen "
                "ni capas — puede estar corrupto o incompleto."
            )
        
        if has_layers:
            layers = project_data['layers']
            if not isinstance(layers, list) or len(layers) == 0:
                raise ValueError(
                    f"'{os.path.basename(file_path)}' dice tener capas pero "
                    "la lista está vacía o corrupta."
                )
            for i, layer_info in enumerate(layers):
                if not isinstance(layer_info, dict) or not layer_info.get('image_data'):
                    raise ValueError(
                        f"La capa nº{i + 1} de '{os.path.basename(file_path)}' "
                        "está corrupta o le falta la imagen."
                    )
    
    def load_project(self, file_path, canvas):
        """Cargar proyecto desde archivo JSON. Admite el formato nuevo (v2.0,
        con capas) y el antiguo (v1.0, una sola imagen). Valida la estructura
        antes de tocar nada del canvas, para dar un mensaje de error claro si
        el archivo está corrupto o no es un proyecto válido."""
        with open(file_path, 'r') as f:
            project_data = json.load(f)
        
        self._validate_project_data(project_data, file_path)
        
        canvas.set_canvas_size(project_data['canvas_size'])
        canvas.bg_transparent = project_data.get('bg_transparent', True)
        
        if project_data.get('bg_color'):
            canvas.bg_color = QColor(project_data['bg_color'])
        
        if 'layers' in project_data:
            # Formato nuevo (v2.0): una o más capas
            layers_data = []
            for layer_info in project_data['layers']:
                image_data = base64.b64decode(layer_info['image_data'])
                qimage = QImage()
                qimage.loadFromData(image_data, "PNG")
                if qimage.isNull():
                    raise ValueError(
                        f"No se pudo leer la imagen de la capa "
                        f"'{layer_info.get('name', '?')}' — datos corruptos."
                    )
                
                layer_type = layer_info.get('layer_type', 'generic')
                data = {}
                if layer_type == 'text' and 'text_data' in layer_info:
                    td = layer_info['text_data']
                    font = QFont(td.get('font_family') or "Arial")
                    if td.get('font_size'):
                        font.setPointSize(td['font_size'])
                    font.setBold(td.get('font_bold', False))
                    font.setItalic(td.get('font_italic', False))
                    font.setUnderline(td.get('font_underline', False))
                    data = {
                        'text': td.get('text', ''),
                        'font': font,
                        'color': QColor(td['color']) if td.get('color') else QColor(0, 0, 0),
                    }
                
                layers_data.append({
                    'name': layer_info.get('name', 'Capa'),
                    'visible': layer_info.get('visible', True),
                    'image': qimage,
                    'layer_type': layer_type,
                    'data': data,
                    'position': layer_info.get('position', [0, 0]),
                })
            canvas.load_layers_data(layers_data, project_data.get('active_layer_index', 0))
        else:
            # Formato antiguo (v1.0): una sola imagen sin capas
            image_data = base64.b64decode(project_data['image_data'])
            qimage = QImage()
            qimage.loadFromData(image_data, "PNG")
            canvas.set_image(qimage)
        
        canvas.update_display()
        self.current_file = file_path
