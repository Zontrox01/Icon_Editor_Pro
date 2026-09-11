from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QToolBar, QMenuBar, QMenu, QStatusBar, QSplitter,
    QDockWidget, QPushButton, QComboBox, QSpinBox,
    QColorDialog, QLabel, QGroupBox, QCheckBox,
    QListWidget, QListWidgetItem, QFileDialog,
    QMessageBox, QScrollArea, QTabWidget, QSlider,
    QLineEdit, QGridLayout, QInputDialog
)
from PySide6.QtCore import Qt, QSize, QPoint, QRect, Signal, QTimer
from PySide6.QtGui import (
    QAction, QIcon, QColor, QPixmap, QImage,
    QKeySequence, QPainter, QPen, QBrush
)
from canvas import Canvas
from preview_widget import PreviewWidget
from project_manager import ProjectManager
from icon_exporter import IconExporter
from image_importer import ImageImporter
from tools.drawing_tools import DrawingTools
from tools.shape_tools import ShapeTools
from text_tool import TextInputDialog, render_text_to_image
from ui.styles import MODERN_STYLE, LIGHT_STYLE, DARK_STYLE
import os
import json

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Icon Editor Pro")
        self.setMinimumSize(1200, 800)

        ruta_icono = os.path.join(os.path.dirname(__file__), "recursos", "icono_app.png")
        self.setWindowIcon(QIcon(ruta_icono))
        
        # Inicializar managers
        self.project_manager = ProjectManager()
        self.icon_exporter = IconExporter()
        self.image_importer = ImageImporter()
        
        self.setup_ui()
        self.setup_menu()
        self.setup_toolbar()
        self.setup_statusbar()
        self.connect_signals()
        
        # Rellenar la lista de capas y las vistas previas con el estado inicial
        self.refresh_layers_list()
        self.update_previews()
        
        # Cargar estilos
        self.setStyleSheet(MODERN_STYLE)
    
    def setup_ui(self):
        """Configurar la interfaz principal"""
        # Widget central con splitter
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # Splitter principal
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # Panel izquierdo - Herramientas
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)
        
        # Panel central - Canvas
        canvas_container = self.create_canvas_container()
        splitter.addWidget(canvas_container)
        
        # Panel derecho - Vista previa
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)
        
        # Configurar proporciones del splitter
        splitter.setSizes([250, 600, 350])

    def create_left_panel(self):
        """Crear panel de herramientas, dentro de una barra deslizadora vertical
        (igual que la vista previa de tamaños a la derecha) para que, al hacer
        la ventana más pequeña, aparezca scroll en vez de comprimir los botones
        hasta hacerlos ilegibles."""
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(10)
        
        # Tamaño del lienzo
        size_group = QGroupBox("Tamaño del Lienzo")
        size_layout = QVBoxLayout(size_group)
        
        size_combo = QComboBox()
        sizes = [16, 24, 32, 48, 64, 128, 256]
        size_combo.addItems([f"{s}x{s}" for s in sizes])
        size_combo.setCurrentText("256x256")
        size_combo.currentTextChanged.connect(self.on_canvas_size_changed)
        size_layout.addWidget(size_combo)
        self.size_combo = size_combo
        
        # Botón aplicar tamaño personalizado
        custom_size_layout = QHBoxLayout()
        self.custom_size_input = QLineEdit()
        self.custom_size_input.setPlaceholderText("Ej: 128")
        custom_size_layout.addWidget(self.custom_size_input)
        
        apply_size_btn = QPushButton("Aplicar")
        apply_size_btn.clicked.connect(self.apply_custom_size)
        custom_size_layout.addWidget(apply_size_btn)
        size_layout.addLayout(custom_size_layout)
        
        layout.addWidget(size_group)
        
        # Herramientas de dibujo
        tools_group = QGroupBox("Herramientas")
        tools_layout = QVBoxLayout(tools_group)
        
        # Botones de herramientas
        tool_buttons = [
            ("✋ Mover", "move"),
            ("✏️ Lápiz", "pencil"),
            ("🧹 Borrador", "eraser"),
            ("⬜ Rectángulo", "rectangle"),
            ("⭕ Círculo", "circle"),
            ("🔺 Triángulo", "triangle"),
            ("➖ Línea", "line"),
            ("🔤 Texto", "text"),
            ("🔲 Relleno", "fill")
        ]
        
        self.tool_buttons = []
        for text, tool in tool_buttons:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setProperty("tool", tool)
            btn.clicked.connect(lambda checked, t=tool: self.set_active_tool(t))
            tools_layout.addWidget(btn)
            self.tool_buttons.append(btn)
        
        # Seleccionar Lápiz como herramienta por defecto (coincide con Canvas.__init__)
        for btn in self.tool_buttons:
            if btn.property("tool") == "pencil":
                btn.setChecked(True)
        self.current_tool = "pencil"
        
        self.fill_transparent_check = QCheckBox("Relleno → transparente")
        self.fill_transparent_check.setToolTip(
            "Con esta opción activada, la herramienta de Relleno vacía la zona\n"
            "seleccionada a transparente en vez de usar el color de dibujo."
        )
        self.fill_transparent_check.stateChanged.connect(
            lambda state: self.canvas.set_fill_transparent(state != 0)
        )
        tools_layout.addWidget(self.fill_transparent_check)
        
        fill_tolerance_layout = QHBoxLayout()
        fill_tolerance_layout.addWidget(QLabel("Tolerancia:"))
        self.fill_tolerance_spin = QSpinBox()
        self.fill_tolerance_spin.setRange(0, 255)
        self.fill_tolerance_spin.setValue(100)
        self.fill_tolerance_spin.setToolTip(
            "Cuánto puede diferir un píxel del color donde haces clic para\n"
            "considerarse parte de la misma zona a rellenar. Súbela si el\n"
            "relleno deja un borde de color sin vaciar (bordes suavizados)."
        )
        self.fill_tolerance_spin.valueChanged.connect(lambda v: self.canvas.set_fill_tolerance(v))
        fill_tolerance_layout.addWidget(self.fill_tolerance_spin)
        tools_layout.addLayout(fill_tolerance_layout)
        
        layout.addWidget(tools_group)
        
        # Configuración del pincel
        brush_group = QGroupBox("Pincel")
        brush_layout = QVBoxLayout(brush_group)
        
        # Color
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("Color:"))
        self.color_button = QPushButton()
        self.color_button.setFixedSize(30, 30)
        self.color_button.setStyleSheet("background-color: #000000; border: 2px solid #888;")
        self.color_button.clicked.connect(self.choose_color)
        color_layout.addWidget(self.color_button)
        
        # Input hexadecimal
        self.hex_input = QLineEdit()
        self.hex_input.setPlaceholderText("#000000")
        self.hex_input.setText("#000000")
        self.hex_input.textChanged.connect(self.on_hex_changed)
        color_layout.addWidget(self.hex_input)
        
        brush_layout.addLayout(color_layout)
        
        # Grosor
        thickness_layout = QHBoxLayout()
        thickness_layout.addWidget(QLabel("Grosor:"))
        self.thickness_slider = QSlider(Qt.Horizontal)
        self.thickness_slider.setRange(1, 20)
        self.thickness_slider.setValue(2)
        self.thickness_slider.valueChanged.connect(self.on_thickness_changed)
        thickness_layout.addWidget(self.thickness_slider)
        
        self.thickness_label = QLabel("2")
        thickness_layout.addWidget(self.thickness_label)
        brush_layout.addLayout(thickness_layout)
        
        layout.addWidget(brush_group)
        
        # Fondo
        bg_group = QGroupBox("Fondo")
        bg_layout = QVBoxLayout(bg_group)
        
        self.bg_transparent_check = QCheckBox("Fondo transparente")
        self.bg_transparent_check.setChecked(True)
        self.bg_transparent_check.stateChanged.connect(self.on_bg_changed)
        bg_layout.addWidget(self.bg_transparent_check)
        
        bg_color_layout = QHBoxLayout()
        bg_color_layout.addWidget(QLabel("Color:"))
        self.bg_color_button = QPushButton()
        self.bg_color_button.setFixedSize(30, 30)
        self.bg_color_button.setStyleSheet("background-color: #ffffff; border: 2px solid #888;")
        self.bg_color_button.clicked.connect(self.choose_bg_color)
        bg_color_layout.addWidget(self.bg_color_button)
        
        self.bg_color_input = QLineEdit()
        self.bg_color_input.setPlaceholderText("#FFFFFF")
        self.bg_color_input.setText("#FFFFFF")
        self.bg_color_input.textChanged.connect(self.on_bg_hex_changed)
        bg_color_layout.addWidget(self.bg_color_input)
        
        bg_layout.addLayout(bg_color_layout)
        layout.addWidget(bg_group)
        
        # Imagen importada (imagen flotante pendiente de ajustar/fijar)
        floating_group = QGroupBox("Imagen importada")
        floating_layout = QVBoxLayout(floating_group)
        
        self.keep_aspect_check = QCheckBox("Mantener proporción")
        self.keep_aspect_check.setChecked(True)
        self.keep_aspect_check.setToolTip(
            "Al arrastrar una esquina, mantiene el ancho/alto original de la imagen.\n"
            "Los bordes (no esquinas) siempre estiran solo en un eje."
        )
        self.keep_aspect_check.stateChanged.connect(
            lambda state: self.canvas.set_keep_aspect_ratio(state != 0)
        )
        floating_layout.addWidget(self.keep_aspect_check)
        
        layout.addWidget(floating_group)
        
        # Acciones rápidas
        actions_group = QGroupBox("Acciones")
        actions_layout = QVBoxLayout(actions_group)
        
        clear_btn = QPushButton("🗑️ Limpiar lienzo")
        clear_btn.clicked.connect(self.clear_canvas)
        actions_layout.addWidget(clear_btn)
        
        undo_redo_layout = QHBoxLayout()
        undo_btn = QPushButton("↩️ Deshacer")
        undo_btn.clicked.connect(self.undo_action)
        undo_redo_layout.addWidget(undo_btn)
        
        redo_btn = QPushButton("↪️ Rehacer")
        redo_btn.clicked.connect(self.redo_action)
        undo_redo_layout.addWidget(redo_btn)
        actions_layout.addLayout(undo_redo_layout)
        
        layout.addWidget(actions_group)
        
        layout.addStretch()
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setMinimumWidth(220)
        scroll.setWidget(content)
        return scroll
   
    def create_canvas_container(self):
        """Crear contenedor del canvas"""
        container = QWidget()
        layout = QVBoxLayout(container)
        
        # Scroll area para el canvas
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setAlignment(Qt.AlignCenter)
        
        self.canvas = Canvas(self)
        scroll.setWidget(self.canvas)
        layout.addWidget(scroll)
        
        return container
    
    def create_right_panel(self):
        """Crear panel de vista previa"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Título
        title_label = QLabel("Vista Previa de Tamaños")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(title_label)
        
        # Área de vista previa
        preview_scroll = QScrollArea()
        preview_scroll.setWidgetResizable(True)
        
        preview_container = QWidget()
        preview_layout = QVBoxLayout(preview_container)
        preview_layout.setSpacing(15)
        
        # Widgets de vista previa para diferentes tamaños
        self.preview_widgets = []
        for size in [256, 128, 64, 48, 32, 24, 16]:
            preview_widget = PreviewWidget(size)
            preview_widget.setFixedSize(200, 200)
            preview_layout.addWidget(preview_widget)
            self.preview_widgets.append(preview_widget)
        
        preview_scroll.setWidget(preview_container)
        layout.addWidget(preview_scroll)
        
        # Botones de exportación
        export_group = QGroupBox("Exportar")
        export_layout = QVBoxLayout(export_group)
        
        # Selección de tamaños
        export_layout.addWidget(QLabel("Seleccionar tamaños:"))
        
        self.size_checkboxes = {}
        size_layout = QGridLayout()
        for i, size in enumerate([16, 24, 32, 48, 64, 128, 256]):
            checkbox = QCheckBox(f"{size}x{size}")
            checkbox.setChecked(size == 256)  # Solo el tamaño actual por defecto
            self.size_checkboxes[size] = checkbox
            size_layout.addWidget(checkbox, i // 4, i % 4)
        export_layout.addLayout(size_layout)
        
        # Botones de exportación
        export_btns_layout = QHBoxLayout()
        export_ico_btn = QPushButton("💾 Exportar ICO")
        export_ico_btn.clicked.connect(self.export_ico)
        export_btns_layout.addWidget(export_ico_btn)
        
        export_png_btn = QPushButton("🖼️ Exportar PNG")
        export_png_btn.clicked.connect(self.export_png)
        export_btns_layout.addWidget(export_png_btn)
        
        export_layout.addLayout(export_btns_layout)
        
        layout.addWidget(export_group)
        
        # Panel de Capas (abajo a la derecha)
        layers_group = QGroupBox("Capas")
        layers_layout = QVBoxLayout(layers_group)
        
        self.layers_list = QListWidget()
        self.layers_list.setMinimumHeight(120)
        self.layers_list.setMaximumHeight(200)
        self.layers_list.currentRowChanged.connect(self.on_layer_row_selected)
        self.layers_list.itemChanged.connect(self.on_layer_item_changed)
        self.layers_list.itemDoubleClicked.connect(self.on_layer_double_clicked)
        layers_layout.addWidget(self.layers_list)
        
        layers_btns_layout = QHBoxLayout()
        add_layer_btn = QPushButton("➕")
        add_layer_btn.setToolTip("Nueva capa")
        add_layer_btn.clicked.connect(lambda: self.canvas.add_layer())
        layers_btns_layout.addWidget(add_layer_btn)
        
        delete_layer_btn = QPushButton("🗑️")
        delete_layer_btn.setToolTip("Eliminar capa")
        delete_layer_btn.clicked.connect(
            lambda: self.canvas.delete_layer(self.layers_list.currentRow())
        )
        layers_btns_layout.addWidget(delete_layer_btn)
        
        move_up_btn = QPushButton("🔼")
        move_up_btn.setToolTip("Subir capa")
        move_up_btn.clicked.connect(
            lambda: self.canvas.move_layer_up(self.layers_list.currentRow())
        )
        layers_btns_layout.addWidget(move_up_btn)
        
        move_down_btn = QPushButton("🔽")
        move_down_btn.setToolTip("Bajar capa")
        move_down_btn.clicked.connect(
            lambda: self.canvas.move_layer_down(self.layers_list.currentRow())
        )
        layers_btns_layout.addWidget(move_down_btn)
        
        layers_layout.addLayout(layers_btns_layout)
        
        layers_hint = QLabel("Doble clic en el nombre para renombrar.\nEl check muestra/oculta la capa.")
        layers_hint.setStyleSheet("color: #888; font-size: 11px;")
        layers_layout.addWidget(layers_hint)
        
        layout.addWidget(layers_group)
        layout.addStretch()
        
        return panel
    
    def setup_menu(self):
        """Configurar menú principal"""
        menubar = self.menuBar()
        
        # Archivo
        file_menu = menubar.addMenu("Archivo")
        
        new_action = QAction("Nuevo Proyecto", self)
        new_action.setShortcut(QKeySequence.New)
        new_action.triggered.connect(self.new_project)
        file_menu.addAction(new_action)
        
        open_action = QAction("Abrir Proyecto...", self)
        open_action.setShortcut(QKeySequence.Open)
        open_action.triggered.connect(self.open_project)
        file_menu.addAction(open_action)
        
        save_action = QAction("Guardar Proyecto", self)
        save_action.setShortcut(QKeySequence.Save)
        save_action.triggered.connect(self.save_project)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        import_action = QAction("Importar Imagen...", self)
        import_action.setShortcut("Ctrl+I")
        import_action.triggered.connect(self.import_image)
        file_menu.addAction(import_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Salir", self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Editar
        edit_menu = menubar.addMenu("Editar")
        
        undo_action = QAction("Deshacer", self)
        undo_action.setShortcut(QKeySequence.Undo)  # Ctrl+Z
        undo_action.triggered.connect(self.undo_action)
        edit_menu.addAction(undo_action)
        
        redo_action = QAction("Rehacer", self)
        redo_action.setShortcut(QKeySequence.Redo)  # Ctrl+Shift+Z / Ctrl+Y según SO
        redo_action.triggered.connect(self.redo_action)
        edit_menu.addAction(redo_action)
        
        edit_menu.addSeparator()
        
        clear_action = QAction("Limpiar lienzo", self)
        clear_action.triggered.connect(self.clear_canvas)
        edit_menu.addAction(clear_action)
        
        # Ver
        view_menu = menubar.addMenu("Ver")
        
        self.dark_theme_action = QAction("Tema oscuro", self)
        self.dark_theme_action.setCheckable(True)
        self.dark_theme_action.setChecked(True)  # el tema oscuro es el que se usa por defecto
        self.dark_theme_action.triggered.connect(self.toggle_theme)
        view_menu.addAction(self.dark_theme_action)
    
    def setup_toolbar(self):
        """Configurar barra de herramientas"""
        toolbar = self.addToolBar("Herramientas")
        toolbar.setMovable(False)
        
        # Acciones de la barra de herramientas
        actions = [
            ("Nuevo", "new", self.new_project),
            ("Abrir", "open", self.open_project),
            ("Guardar", "save", self.save_project),
            (None, None, None),  # Separador
            ("Deshacer", "undo", self.undo_action),
            ("Rehacer", "redo", self.redo_action),
            (None, None, None),  # Separador
            ("Importar Imagen", "import", self.import_image),
            (None, None, None),  # Separador
            ("Exportar ICO", "export_ico", self.export_ico),
            ("Exportar PNG", "export_png", self.export_png)
        ]
        
        for text, icon_name, callback in actions:
            if text is None:
                toolbar.addSeparator()
                continue
            
            action = QAction(text, self)
            if callback:
                action.triggered.connect(callback)
            toolbar.addAction(action)
    
    def setup_statusbar(self):
        """Configurar barra de estado"""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self.statusbar.showMessage("Listo")
        
        # Información adicional en la barra de estado
        self.size_label = QLabel("Tamaño: 256x256")
        self.statusbar.addPermanentWidget(self.size_label)
        
        self.position_label = QLabel("Posición: 0, 0")
        self.statusbar.addPermanentWidget(self.position_label)
    
    def connect_signals(self):
        """Conectar señales del canvas"""
        self.canvas.position_changed.connect(self.update_position_label)
        self.canvas.image_changed.connect(self.update_previews)
        self.canvas.text_tool_requested.connect(self.handle_text_tool_click)
        self.canvas.layers_changed.connect(self.refresh_layers_list)
        self.canvas.status_message.connect(self.statusbar.showMessage)
    
    # ... Continuará con más métodos
    
    def on_canvas_size_changed(self, size_text):
        """Cambiar tamaño del canvas"""
        size = int(size_text.split("x")[0])
        self.canvas.set_canvas_size(size)
        self.size_label.setText(f"Tamaño: {size}x{size}")
        self.update_previews()
    
    def apply_custom_size(self):
        """Aplicar tamaño personalizado"""
        try:
            size = int(self.custom_size_input.text())
            if 1 <= size <= 1024:
                self.canvas.set_canvas_size(size)
                self.size_label.setText(f"Tamaño: {size}x{size}")
                self.update_previews()
            else:
                QMessageBox.warning(self, "Error", "El tamaño debe estar entre 1 y 1024")
        except ValueError:
            QMessageBox.warning(self, "Error", "Ingresa un número válido")
    
    def set_active_tool(self, tool):
        """Establecer herramienta activa"""
        self.current_tool = tool
        self.canvas.set_tool(tool)
        
        # Actualizar botones
        for btn in self.tool_buttons:
            btn.setChecked(btn.property("tool") == tool)
    
    def choose_color(self):
        """Seleccionar color de dibujo"""
        color = QColorDialog.getColor(QColor(self.hex_input.text()))
        if color.isValid():
            self.color_button.setStyleSheet(f"background-color: {color.name()}; border: 2px solid #888;")
            self.hex_input.setText(color.name())
            self.canvas.set_draw_color(color)
    
    def on_hex_changed(self, hex_color):
        """Actualizar color desde input hexadecimal"""
        if QColor(hex_color).isValid():
            self.color_button.setStyleSheet(f"background-color: {hex_color}; border: 2px solid #888;")
            self.canvas.set_draw_color(QColor(hex_color))
    
    def on_thickness_changed(self, value):
        """Cambiar grosor del pincel"""
        self.thickness_label.setText(str(value))
        self.canvas.set_brush_size(value)
    
    def choose_bg_color(self):
        """Seleccionar color de fondo"""
        color = QColorDialog.getColor(QColor(self.bg_color_input.text()))
        if color.isValid():
            self.bg_color_button.setStyleSheet(f"background-color: {color.name()}; border: 2px solid #888;")
            self.bg_color_input.setText(color.name())
            if not self.bg_transparent_check.isChecked():
                self.canvas.set_background_color(color)
    
    def on_bg_hex_changed(self, hex_color):
        """Actualizar color de fondo desde input hexadecimal"""
        if QColor(hex_color).isValid():
            self.bg_color_button.setStyleSheet(f"background-color: {hex_color}; border: 2px solid #888;")
            if not self.bg_transparent_check.isChecked():
                self.canvas.set_background_color(QColor(hex_color))
    
    def on_bg_changed(self, state):
        """Cambiar entre fondo transparente y con color"""
        if state != 0:
            self.canvas.set_background_transparent(True)
            self.bg_color_button.setEnabled(False)
            self.bg_color_input.setEnabled(False)
        else:
            self.canvas.set_background_transparent(False)
            self.bg_color_button.setEnabled(True)
            self.bg_color_input.setEnabled(True)
            color = QColor(self.bg_color_input.text())
            if color.isValid():
                self.canvas.set_background_color(color)
    
    def toggle_theme(self):
        """Alternar entre tema oscuro y tema claro"""
        if self.dark_theme_action.isChecked():
            self.setStyleSheet(DARK_STYLE)
            self.statusbar.showMessage("Tema oscuro")
        else:
            self.setStyleSheet(LIGHT_STYLE)
            self.statusbar.showMessage("Tema claro")
    
    def clear_canvas(self):
        """Limpiar el lienzo (TODAS las capas, no solo la activa)"""
        reply = QMessageBox.question(
            self, "Limpiar lienzo",
            "Esto borrará TODAS las capas (todas las figuras, textos e imágenes\n"
            "insertadas), no solo la capa activa. ¿Continuar?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.canvas.clear_canvas()
    
    def undo_action(self):
        """Deshacer última acción"""
        self.canvas.undo()
    
    def redo_action(self):
        """Rehacer última acción deshecha"""
        self.canvas.redo()
    
    def update_position_label(self, x, y):
        """Actualizar posición en barra de estado"""
        self.position_label.setText(f"Posición: {x}, {y}")
    
    def update_previews(self):
        """Actualizar todas las vistas previas"""
        image = self.canvas.get_preview_image()
        for preview_widget in self.preview_widgets:
            preview_widget.update_preview(image)
    
    def refresh_layers_list(self):
        """Reconstruir la lista de capas a partir del estado real del canvas.
        self.canvas.layers[0] es la capa superior, y así se muestra: primera
        de la lista = arriba del todo."""
        self.layers_list.blockSignals(True)
        self.layers_list.clear()
        for layer in self.canvas.layers:
            item = QListWidgetItem(layer.name)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if layer.visible else Qt.Unchecked)
            self.layers_list.addItem(item)
        if self.canvas.layers:
            self.layers_list.setCurrentRow(self.canvas.active_layer_index)
        self.layers_list.blockSignals(False)
    
    def on_layer_row_selected(self, row):
        """El usuario ha seleccionado otra fila de la lista: esa capa pasa a ser
        la activa y queda lista para mover/redimensionar (mismos handles que al
        insertar un objeto nuevo)."""
        if row < 0:
            return
        self.canvas.enter_layer_edit_mode(row)
    
    def on_layer_item_changed(self, item):
        """Se ha marcado/desmarcado el check de una capa: cambia su visibilidad"""
        index = self.layers_list.row(item)
        if not (0 <= index < len(self.canvas.layers)):
            return
        self.canvas.set_layer_visibility(index, item.checkState() != Qt.Unchecked)
    
    def on_layer_double_clicked(self, item):
        """Doble clic sobre una capa: si es una capa de texto, reabre el editor
        de texto (contenido, tipografía, estilo, color); si no, permite renombrarla"""
        index = self.layers_list.row(item)
        if not (0 <= index < len(self.canvas.layers)):
            return
        layer = self.canvas.layers[index]
        if layer.layer_type == "text":
            self.edit_text_layer(index)
            return
        new_name, ok = QInputDialog.getText(self, "Renombrar capa", "Nombre:", text=layer.name)
        if ok and new_name.strip():
            self.canvas.rename_layer(index, new_name)
    
    def edit_text_layer(self, index):
        """Reabre el diálogo de texto con el contenido/formato ACTUALES de esa
        capa, para poder cambiar las palabras, la tipografía, el tamaño, el
        estilo o el color — no solo mover/redimensionar el render ya hecho."""
        layer = self.canvas.layers[index]
        if layer.layer_type != "text":
            return
        data = layer.data or {}
        
        dialog = TextInputDialog(
            self,
            initial_color=data.get('color', self.canvas.draw_color),
            initial_text=data.get('text', ''),
            initial_font=data.get('font')
        )
        if dialog.exec():
            text = dialog.get_text()
            if not text.strip():
                return
            font = dialog.get_font()
            color = dialog.get_color()
            image = render_text_to_image(text, font, color)
            
            self.canvas.edit_layer_content(index, image)
            layer.layer_type = "text"
            layer.data = {'text': text, 'font': font, 'color': color}
            self.canvas.rename_layer(index, f"Texto: {text.strip()}"[:30])
            self.statusbar.showMessage("Texto actualizado")
    
    def handle_text_tool_click(self, click_point):
        """Abrir el diálogo de texto al hacer clic con la herramienta de Texto,
        y colocar el resultado como imagen flotante (se puede mover/redimensionar
        y fijar igual que una imagen importada)."""
        dialog = TextInputDialog(self, initial_color=self.canvas.draw_color)
        if dialog.exec():
            text = dialog.get_text()
            if not text.strip():
                return
            font = dialog.get_font()
            color = dialog.get_color()
            image = render_text_to_image(text, font, color)
            
            # Centrar el texto sobre el punto donde se hizo clic
            rect_x = int(click_point.x() - image.width() / 2)
            rect_y = int(click_point.y() - image.height() / 2)
            initial_rect = QRect(rect_x, rect_y, image.width(), image.height())
            
            layer_name = f"Texto: {text.strip()}"[:30]
            self.canvas.start_floating_image(
                image, initial_rect, name=layer_name,
                object_type="text", data={'text': text, 'font': font, 'color': color}
            )
            self.statusbar.showMessage(
                "Texto insertado — ajusta el tamaño/posición; "
                "Enter o «Fijar» lo deja listo sin perder la edición"
            )
    
    def new_project(self):
        """Crear nuevo proyecto"""
        if self.canvas.is_modified():
            reply = QMessageBox.question(
                self, "Guardar cambios",
                "¿Quieres guardar los cambios antes de crear un nuevo proyecto?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )
            if reply == QMessageBox.Yes:
                self.save_project()
            elif reply == QMessageBox.Cancel:
                return
        
        self.canvas.clear_canvas()
        self.statusbar.showMessage("Nuevo proyecto creado")
    
    def open_project(self):
        """Abrir proyecto guardado"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Abrir Proyecto",
            "", "Proyectos de Iconos (*.ico_proj);;Todos los archivos (*.*)"
        )
        if file_path:
            try:
                self.project_manager.load_project(file_path, self.canvas)
                self.statusbar.showMessage(f"Proyecto cargado: {os.path.basename(file_path)}")
                self.update_previews()
            except json.JSONDecodeError:
                QMessageBox.critical(
                    self, "Error",
                    f"'{os.path.basename(file_path)}' no es un archivo de proyecto "
                    "válido (el contenido no se puede leer como texto/JSON)."
                )
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo cargar el proyecto:\n{str(e)}")
    
    def save_project(self):
        """Guardar proyecto actual"""
        if self.project_manager.current_file:
            try:
                self.project_manager.save_project(self.project_manager.current_file, self.canvas)
                self.statusbar.showMessage("Proyecto guardado")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo guardar el proyecto:\n{str(e)}")
        else:
            self.save_project_as()
    
    def save_project_as(self):
        """Guardar proyecto como..."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Guardar Proyecto",
            "", "Proyectos de Iconos (*.ico_proj)"
        )
        if file_path:
            if not file_path.endswith('.ico_proj'):
                file_path += '.ico_proj'
            try:
                self.project_manager.save_project(file_path, self.canvas)
                self.statusbar.showMessage(f"Proyecto guardado: {os.path.basename(file_path)}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo guardar el proyecto:\n{str(e)}")
    
    def import_image(self):
        """Importar imagen desde archivo"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Importar Imagen",
            "", "Imágenes (*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.webp);;Todos los archivos (*.*)"
        )
        if file_path:
            try:
                self.image_importer.import_image(file_path, self.canvas)
                self.statusbar.showMessage(
                    f"Imagen importada: {os.path.basename(file_path)} — "
                    "ajusta el tamaño/posición; Enter o «Fijar» la deja lista sin perder la edición"
                )
                self.update_previews()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo importar la imagen:\n{str(e)}")
    
    def export_ico(self):
        """Exportar como ICO"""
        # Obtener tamaños seleccionados
        selected_sizes = [size for size, checkbox in self.size_checkboxes.items() if checkbox.isChecked()]
        
        if not selected_sizes:
            QMessageBox.warning(self, "Error", "Selecciona al menos un tamaño para exportar")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Exportar Icono",
            "", "Iconos (*.ico)"
        )
        
        if file_path:
            if not file_path.endswith('.ico'):
                file_path += '.ico'
            
            try:
                image = self.canvas.get_image()
                self.icon_exporter.export_ico(file_path, image, selected_sizes)
                self.statusbar.showMessage(f"Icono exportado: {os.path.basename(file_path)}")
                QMessageBox.information(self, "Éxito", "Icono exportado correctamente")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo exportar el icono:\n{str(e)}")
    
    def export_png(self):
        """Exportar como PNG. Si se selecciona más de un tamaño, se exporta un
        archivo por cada uno, añadiendo el tamaño al nombre (p. ej.
        icono_128x128.png, icono_256x256.png). Si solo se selecciona uno, se
        exporta un único archivo con el nombre tal cual, sin sufijo."""
        selected_sizes = [size for size, checkbox in self.size_checkboxes.items() if checkbox.isChecked()]
        
        if not selected_sizes:
            QMessageBox.warning(self, "Error", "Selecciona al menos un tamaño para exportar")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Exportar PNG",
            "", "PNG (*.png)"
        )
        
        if file_path:
            if not file_path.endswith('.png'):
                file_path += '.png'
            
            try:
                image = self.canvas.get_image()
                base_path, ext = os.path.splitext(file_path)
                exported_paths = []
                
                if len(selected_sizes) == 1:
                    size = selected_sizes[0]
                    scaled = image.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    scaled.save(file_path, "PNG")
                    exported_paths.append(file_path)
                else:
                    for size in sorted(selected_sizes):
                        scaled = image.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        sized_path = f"{base_path}_{size}x{size}{ext}"
                        scaled.save(sized_path, "PNG")
                        exported_paths.append(sized_path)
                
                names = "\n".join(os.path.basename(p) for p in exported_paths)
                self.statusbar.showMessage(f"PNG exportado: {len(exported_paths)} archivo(s)")
                QMessageBox.information(self, "Éxito", f"Exportado(s):\n{names}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo exportar el PNG:\n{str(e)}")