# Icon Editor Pro — Estructura de archivos y carpetas e Histórico de cambios y pendientes

## Estructura de carpetas

```
======================================================================

- FILES.md
- README.md
- canvas.py
- icon_exporter.py
- image_importer.py
- layer.py
- main.py
- main_window.py
- preview_widget.py
- project_manager.py
- requirements.txt
- text_tool.py
[CARPETA] recursos
    - icono_app.ico
    - icono_app.png
    - screenshot.png
[CARPETA] tools
    - __init__.py
    - drawing_tools.py
    - shape_tools.py
[CARPETA] ui
    - __init__.py
    - styles.py
```

## Detalle estructurado

- 📄 FILES.md
- 📄 README.md
- 📄 canvas.py
- 📄 icon_exporter.py
- 📄 image_importer.py
- 📄 layer.py
- 📄 main.py
- 📄 main_window.py
- 📄 preview_widget.py
- 📄 project_manager.py
- 📄 requirements.txt
- 📄 text_tool.py
- 📁 recursos
  - 📄 icono_app.ico
  - 📄 icono_app.png
  - 📄 screenshot.png
- 📁 tools
  - 📄 __init__.py
  - 📄 drawing_tools.py
  - 📄 shape_tools.py
- 📁 ui
  - 📄 __init__.py
  - 📄 styles.py

Seguimiento de la sesión de revisión/pulido del proyecto. Se actualiza en cada ronda de cambios.

## ✅ Hecho

### 1. `canvas.py` — Bug de degradación en el redimensionado de imagen
- **Problema:** en `handle_resize_move`, cada evento de arrastre del mouse tomaba `self.current_image` (ya modificada por el frame anterior) como imagen base y la volvía a reescalar. Al arrastrar, se reescalaba una imagen ya reescalada una y otra vez → pérdida de nitidez progresiva.
- **Fix:** se captura la imagen fuente una sola vez al iniciar el arrastre (`self.resize_source_image`, en `handle_resize_start`) y todo el redimensionado durante el drag parte siempre de esa copia original. Se libera en `handle_resize_end`.

### 2. `main_window.py` — Rehacer (redo) no estaba conectado
- `canvas.redo()` existía pero no había forma de invocarlo desde la UI.
- **Fix:** botón "↪️ Rehacer" en el panel izquierdo (junto a Deshacer), botón "Rehacer" en la toolbar, y método `redo_action()`.

### 3. `main_window.py` — Atajos de teclado
- No había menú Editar ni atajos más allá de los del menú Archivo.
- **Fix:** nuevo menú **Editar** con:
  - Deshacer → `Ctrl+Z`
  - Rehacer → `Ctrl+Shift+Z` / `Ctrl+Y` (según SO)
  - Limpiar lienzo

### 4. `main_window.py` — Guardar proyecto sin manejo de errores
- `save_project` / `save_project_as` no tenían try/except, a diferencia de abrir/importar/exportar. Un fallo al guardar (permisos, disco lleno) habría reventado la app sin avisar.
- **Fix:** ambos métodos envueltos en try/except con `QMessageBox.critical`, igual que el resto de acciones de archivo.

### 5. `icon_exporter.py` — Código muerto
- `qimage_to_pil` tenía un if/else donde ambas ramas hacían exactamente lo mismo.
- **Fix:** simplificado a una sola línea.

### 6. Redimensionado de imagen importada — REDISEÑO (`canvas.py`, `image_importer.py`, `main_window.py`)
- **Problema real (más allá del bug de calidad ya arreglado en el punto 1):** el enfoque anterior trataba TODO el lienzo como un único bloque a estirar, en vez de tratar la imagen importada como un objeto independiente. No era lo que buscabas.
- **Rediseño:** ahora, al importar una imagen (`Archivo > Importar Imagen...` o `Ctrl+I`), esta aparece sobre el lienzo como una **imagen flotante editable**, con un borde discontinuo azul y 8 handles (4 esquinas + 4 lados):
  - Arrastrar una **esquina** redimensiona en ambos ejes. Si el checkbox **"Mantener proporción"** (nuevo, en el panel izquierdo, grupo "Imagen importada") está activado, respeta el ancho/alto original; si no, deforma libremente.
  - Arrastrar un **lateral** (no esquina) estira solo en ese eje, siempre, tenga o no activado el bloqueo de proporción (comportamiento estándar en editores de imagen).
  - Arrastrar el **interior** de la imagen la mueve de sitio.
  - **Enter** o el botón "✅ Aplicar" fija la imagen sobre el lienzo (se añade al historial de deshacer). **Esc** o "❌ Cancelar" la descarta.
  - Si cambias de herramienta, exportas, guardas, cambias el tamaño del lienzo o limpias el lienzo con una imagen flotante pendiente, se fija (o se descarta, en el caso de "limpiar") automáticamente para no perder trabajo ni dejar el estado a medias.
- Se ha quitado el diálogo modal de "Opciones de Importación" (fit/estirar/centrar/manual): ya no hace falta, el ajuste se hace directamente y a ojo sobre el lienzo.
- Se ha quitado el botón "↔️ Redimensionar Imagen" (ya no existe ese modo aparte; el ajuste ocurre automáticamente nada más importar).
- **Nota técnica:** las vistas previas (panel derecho) usan un nuevo método `get_preview_image()` que compone la imagen flotante sin fijarla, para poder refrescarse en vivo mientras ajustas sin forzar el "Aplicar" antes de tiempo.

### 7. Imagen flotante — 3 correcciones tras tus pruebas (`canvas.py`, `main_window.py`)
- **"Mantener proporción" no funcionaba:** el bloqueo de proporción solo se aplicaba al arrastrar una ESQUINA; los laterales (arriba/abajo/izq/dcha) tenían su propio camino de código que ni miraba el checkbox. Unifiqué la lógica: ahora, con el checkbox activado, tanto esquinas como laterales derivan la dimensión que falta a partir de la proporción original (ancla el lado opuesto al que arrastras). Verificado con una simulación aparte antes de tocar el código real (ver más abajo si quieres los números).
- **No se podía volver a ajustar tras "Aplicar":** el botón "Aplicar (Enter)" y "Cancelar" se han fusionado en **un único botón que alterna**: "✅ Fijar (Enter)" → "✏️ Volver a ajustar (Enter)" → ... Al "fijar" se ocultan los handles pero la imagen sigue sin fusionarse de verdad con los píxeles del canvas (solo se ve "colocada"); puedes volver a pulsarlo (o Enter) para que reaparezcan los handles y seguir ajustando. La fusión real en píxeles solo ocurre cuando de verdad hace falta: al cambiar de herramienta, exportar, guardar, o redimensionar/limpiar el lienzo.
- **Botón "Cancelar" quitado:** tenías razón, era redundante — Deshacer (Ctrl+Z / botón ↩️) ya cancela la imagen flotante mientras esté pendiente de fijar. Esc en el teclado se mantiene como atajo directo por si acaso, pero no hay botón dedicado.

### 8. Herramientas de forma (línea, rectángulo, círculo, triángulo) — previsualización de arrastre (`canvas.py`)
- **Problema:** al arrastrar con estas herramientas, `draw_line()` se ejecutaba en cada `mouseMoveEvent` y estampaba la forma directamente sobre `current_image` cada vez, dejando decenas de rectángulos/círculos/líneas superpuestos según ibas moviendo el mouse.
- **Fix:** ahora funciona como en cualquier editor de imagen — click en el punto de inicio, arrastras viendo una previsualización en vivo, sueltas para fijar la forma definitiva (una sola vez) entre esos dos puntos:
  - Al pulsar, se guarda el punto de inicio y una copia del canvas tal cual estaba antes (`shape_preview_base`).
  - Mientras arrastras, cada `mouseMove` redibuja la forma sobre esa copia (nunca sobre el canvas real) y solo se muestra en pantalla.
  - Al soltar, se fija la forma final sobre el canvas real y se añade al historial de deshacer.
  - **Bonus:** `Esc` cancela el arrastre a medio hacer y vuelve al estado anterior sin dibujar nada.
- Esto aplica a línea, rectángulo, círculo y triángulo (las únicas formas conectadas a la UI hoy; estrella/polígono siguen sin exponerse, ver pendientes).

### 9. Relleno, Texto y Borrador (`canvas.py`, `main_window.py`, nuevo `text_tool.py`)
- **Relleno (fill):**
  - **Bug arreglado:** antes de rellenar, el flujo genérico de clic pintaba primero un punto suelto con el color activo (como si fuera el lápiz) y LUEGO, al arrastrar, repetía el flood fill en cada movimiento — pero como el punto ya había cambiado el color de ese píxel, el flood fill real muchas veces no llegaba a rellenar nada visible. Ahora el relleno es una acción de UN SOLO click: se ejecuta una vez, sin marca previa, y no vuelve a ejecutarse si arrastras el mouse.
  - **Nuevo:** checkbox "Relleno → transparente" (panel izquierdo, grupo Herramientas). Con esta opción activada, el relleno vacía la zona seleccionada a transparente en vez de usar el color de dibujo — útil para "agujerear" zonas del icono.
- **Herramienta de Texto (nueva):** botón "🔤 Texto". Al hacer clic sobre el lienzo se abre un diálogo con: texto, tipografía (cualquier fuente instalada en el sistema), tamaño, negrita, cursiva, subrayado, color y vista previa en vivo. Al insertar, el texto se coloca como **imagen flotante** — se reutiliza el mismo mecanismo que al importar una imagen (arrastrar para mover/redimensionar, checkbox de proporción, botón Fijar/Ajustar, Deshacer para cancelar). Importante: como se renderiza a imagen, si lo agrandas mucho después de escribirlo se escala como un bitmap (puede perder nitidez) en vez de volver a dibujar el texto a mayor resolución.
- **Borrador:** la lógica de borrado a transparente (`CompositionMode_Clear` en `drawing_tools.py`) **ya existía**, pero no había ningún botón en la interfaz para seleccionar la herramienta. Añadido botón "🧹 Borrador".
- **Bonus:** de paso añadí el botón "🔺 Triángulo" — el motor de arrastre de formas ya lo soportaba internamente desde el punto 8, solo le faltaba el botón.

### 10. Color del lápiz no persistía al cambiar de herramienta (`tools/drawing_tools.py`)
- **Bug:** `set_tool()` reseteaba `draw_color` a negro fijo en CADA cambio de herramienta (incluso al volver a pulsar el propio Lápiz), descartando el color que hubieras elegido.
- **Fix:** se añadió `user_color` (el último color elegido por el usuario, independiente de la herramienta). Al cambiar de herramienta se restaura `user_color`, no negro fijo. El borrador sigue forzando transparente como antes, pero ya no "olvida" tu color al volver a una herramienta de dibujo.

### 11. Relleno a transparente dejaba un borde sin vaciar (`tools/drawing_tools.py`, `canvas.py`, `main_window.py`)
- **Causa:** el flood fill exigía coincidencia EXACTA de color; los bordes de las formas llevan antialiasing (píxeles ligeramente mezclados, no exactamente iguales al interior), así que el relleno paraba justo antes del borde, dejando un contorno de color sin vaciar — muy visible contra el fondo a cuadros al "vaciar a transparente".
- **Fix:** `flood_fill()` ahora acepta una `tolerance` (por defecto 32) y compara colores dentro de ese margen, no de forma exacta. Nuevo control "Tolerancia" (spinbox, panel izquierdo) para ajustarla si hace falta más o menos margen.

### 12. Sistema de capas (nuevo `layer.py`; reescrito `project_manager.py`; `canvas.py`, `main_window.py`)
Cambio de fondo, no un simple parche. Resumen del diseño:
- **`Layer`** (nuevo módulo): una capa = una `QImage` + nombre + visibilidad + su PROPIO historial de deshacer/rehacer (deshacer actúa sobre la capa activa en cada momento, no sobre todo el canvas globalmente).
- **`Canvas.current_image`** pasó a ser una *property* que apunta siempre a la imagen de la capa activa (`self.layers[self.active_layer_index]`). Esto significa que TODO el código de dibujo existente (lápiz, formas, relleno, texto, imagen flotante) sigue funcionando sin cambios: sin darse cuenta, ahora actúa sobre "la capa activa" en vez de "la única imagen".
- **`composite_layers()`**: compone el fondo (transparente o color) + todas las capas VISIBLES (de abajo arriba) en una sola imagen. Es lo que se ve en pantalla (`paintEvent`) y lo que se exporta/guarda (`get_image()`).
- **El fondo ya NO se guarda dentro de ninguna capa** — antes, activar/desactivar "fondo transparente" modificaba directamente los píxeles de la imagen; ahora es un ajuste puramente visual que se aplica al componer, y cada capa puede quedarse con transparencia real en sus propios píxeles.
- **Convención de orden:** `canvas.layers[0]` = capa SUPERIOR (se dibuja encima de todas), `canvas.layers[-1]` = INFERIOR. Coincide con cómo se listan en el panel (arriba de la lista = arriba del todo).
- **Panel "Capas"** (abajo a la derecha, como pediste): lista con checkbox de visibilidad por capa, botones ➕ nueva capa, 🗑️ eliminar (si es la última, se vacía en vez de desaparecer), 🔼 subir, 🔽 bajar, y doble clic sobre el nombre para renombrar.
- **Guardar/cargar proyecto:** formato nuevo v2.0 guarda cada capa por separado (nombre, visibilidad, PNG en base64). Los proyectos antiguos (v1.0, una sola imagen) se siguen pudiendo abrir con total normalidad — se cargan como una única capa.
- **Sin probar en un runtime real** (sigo sin PySide6 en este entorno): revisado a fondo a mano y compila sin errores, pero es el cambio más grande de toda la sesión — pruébalo con calma (crear/eliminar/reordenar capas, deshacer dentro de una capa concreta, ocultar una capa, guardar y volver a abrir un proyecto con varias capas).

### 13. Cada objeto = su propia capa + herramienta "Mover/Seleccionar" (`canvas.py`, `main_window.py`, `image_importer.py`)
Como en Photoshop: ahora, al dibujar una forma, insertar texto o importar una imagen, se crea automáticamente una **capa nueva** para ese objeto (ya no se mezcla con la capa que tuvieras activa). Y puedes seleccionar y arrastrar CUALQUIER objeto en cualquier momento, sin depender de cuál sea la capa activa ni de cuándo lo creaste:

- **Formas (línea/rectángulo/círculo/triángulo):** al soltar el arrastre, se crea una capa nueva llamada "Línea", "Rectángulo", etc. (con número si ya existe una con ese nombre). Mientras arrastras, la forma se previsualiza flotando encima de todo, sin tocar ninguna capa.
- **Texto:** al fijarlo, la capa se nombra con las primeras palabras del texto insertado (ej. "Texto: Hola mundo").
- **Imagen importada:** la capa se nombra según el nombre del archivo.
- **Nueva herramienta "✋ Mover":** haz clic en cualquier punto del lienzo y selecciona automáticamente la capa VISIBLE más alta que tenga contenido (no transparente) justo ahí — sin importar si es la capa activa ahora mismo — y la arrastra. El cursor cambia a manita al pasar por encima de un objeto.
- **Lápiz, Borrador y Relleno siguen actuando sobre la capa activa** (no crean una capa por cada trazo o clic) — igual que el pincel de Photoshop pinta sobre la capa seleccionada, mientras que sus herramientas de forma/texto sí crean capa nueva por defecto. Me pareció el equilibrio correcto para no llenar la lista de capas con decenas de entradas por cada pincelada.
- **Limitación actual:** la herramienta Mover solo desplaza (traslada) el objeto; no vuelve a mostrar handles de redimensionar una vez ya es una capa fijada (los handles de tamaño/proporción solo están disponibles ANTES de fijar, en el momento de importar/insertar). Si quieres poder redimensionar un objeto ya fijado más adelante, es una ampliación razonable a futuro — dímelo y lo añado.

### 14. Poder volver a editar (mover/redimensionar) un objeto ya fijado (`canvas.py`, `main_window.py`)
La ronda anterior dejaba la herramienta Mover limitada a solo desplazar, y no había forma de recuperar los tiradores de redimensionar tras fijar un objeto. Ahora sí:
- **Seleccionar una capa** (por el panel de Capas, o con la herramienta "✋ Mover" haciendo clic sobre el objeto en el lienzo) la deja lista para **mover Y redimensionar**, con los mismos tiradores y el mismo checkbox de "mantener proporción" que al insertarlo por primera vez.
- Por dentro, reutiliza el mecanismo de imagen flotante: el contenido de la capa se "levanta" temporalmente (recortado a su recuadro real de contenido, no transparente), se edita como flotante, y al fijarlo (Enter / botón "Fijar") se vuelve a guardar EN LA MISMA capa (no crea una capa nueva). Si cancelas (Esc / Deshacer), la capa recupera exactamente el contenido que tenía antes de tocarla.
- Cambiar de selección mientras editas un objeto (clic en otra capa del panel, o en otro objeto del lienzo) fija automáticamente el que tenías a medias antes de pasar al siguiente, para no perder cambios.

### 15. Bug real de por qué no funcionaba nada de "seleccionar y editar" (`canvas.py`)
El punto 14 introducía `enter_layer_edit_mode`, pero usaba `QImage.bits().setsize(...)` para calcular el recuadro de contenido no transparente del objeto — una API de bajo nivel que varía entre versiones de PySide6/Qt6 y muy probablemente fallaba silenciosamente en tu entorno (la excepción no llega a verse, simplemente no pasa nada: ni la herramienta Mover selecciona nada arrastrable, ni el círculo del ejemplo se vuelve editable). Por eso "no funcionaba, no movía nada".
- **Fix:** cálculo del recuadro reescrito usando PIL (`Image.getbbox()` sobre el canal alfa), el mismo patrón de conversión QImage↔PIL que ya usa `icon_exporter.py` desde el principio del proyecto — nada de manipulación de bytes de bajo nivel. Verificado con una prueba aislada antes de aplicarlo.
- Con esto, tanto seleccionar una capa en el panel como hacer clic con "✋ Mover" sobre un objeto (círculo, rectángulo, texto, imagen...) debería devolver los tiradores de mover/redimensionar correctamente, sin importar cuánto tiempo haya pasado desde que se creó.

### 16. Reeditar el CONTENIDO de un texto (no solo mover/redimensionarlo) (`layer.py`, `canvas.py`, `text_tool.py`, `main_window.py`)
El punto 14 dejaba mover/redimensionar cualquier objeto, pero un texto ya fijado se trataba como una imagen rasterizada cualquiera — no había forma de volver a cambiar las palabras, la tipografía, el tamaño, el estilo o el color.
- Cada `Layer` ahora guarda `layer_type` ("generic" o "text") y `data` (metadatos: texto, fuente, color originales) cuando el objeto es un texto.
- **Doble clic sobre una capa de texto** en el panel de Capas reabre el diálogo de texto **precargado** con el contenido actual (texto, tipografía, tamaño, negrita/cursiva/subrayado, color) — lo cambias y se vuelve a renderizar en el mismo sitio donde estaba. Doble clic sobre cualquier otra capa (forma, imagen) sigue sirviendo para renombrarla, como antes.
- Mover/redimensionar (seleccionando la capa en el panel o con "✋ Mover") sigue funcionando igual para CUALQUIER objeto, incluido el texto — ambas cosas (reeditar contenido y transformar) son ahora posibles y no se pisan entre sí.

### 17. Reeditar texto "no se aplicaba" — bug de orden de operaciones (`canvas.py`, `main_window.py`)
- **Causa exacta:** al hacer doble clic sobre una capa de texto, Qt dispara primero un clic simple de selección (que ya "levanta" el contenido a modo edición flotante, dejando la capa momentáneamente vacía) y LUEGO el doble clic que abre el diálogo. `main_window.py` calculaba dónde estaba el texto anterior ANTES de resolver esa edición pendiente, así que leía la capa todavía vacía y anclaba el texto nuevo en la esquina (0,0) — donde normalmente queda tapado por otra capa. El resultado SÍ se aplicaba, pero era invisible, y parecía que "no pasaba nada".
- **Fix:** `canvas.edit_layer_content()` ahora resuelve primero cualquier edición flotante pendiente sobre esa misma capa (restaurando su contenido real) y SOLO DESPUÉS calcula dónde colocar el texto reeditado. `main_window.py` ya no calcula esa posición por su cuenta, se lo deja todo a `edit_layer_content`.

### 18. Mover se rompió de verdad: faltaba iniciar el arrastre en el mismo gesto (`canvas.py`)
Tenías razón: al unificar "seleccionar" con "poder redimensionar" (punto 14), el primer clic pasó a limitarse a SELECCIONAR el objeto (dejarlo flotante con handles), pero ya no arrancaba el arrastre — hacía falta soltar y volver a hacer clic-y-arrastrar por separado. Antes (sistema más simple de la ronda anterior) sí lo hacía todo en un solo gesto. Eso es lo que se sintió como "se ha estropeado".
- **Fix:** al seleccionar un objeto con "✋ Mover" (clic sobre él), ahora se arranca el arrastre EN EL MISMO gesto (clic y arrastro sin soltar, como antes), sin perder la capacidad de soltar con los handles visibles para redimensionar/ajustar después si quieres.
- **Bonus relacionado:** `hit_test_layer` ahora usa el RECUADRO de contenido del objeto, no el píxel exacto — así que una forma SIN relleno (solo contorno, p. ej. un rectángulo sin "Relleno" activado) también se puede seleccionar haciendo clic en su interior, no solo justo sobre la línea del borde. Esto podía ser otra causa de que "no seleccionara nada" al hacer clic dentro de una figura.

### Sobre el texto que sigue sin aplicarse
He repasado la lógica de `edit_layer_content` línea por línea varias veces y, sobre el papel, el orden ya es correcto (restaura la capa antes de calcular su posición, como arreglé en el punto 17). No he encontrado un bug adicional por análisis estático. Antes de seguir buscando a ciegas, **por favor comprueba que tienes las 4 versiones más recientes a la vez**: `canvas.py`, `main_window.py`, `layer.py` y `text_tool.py` — si se mezcla alguno antiguo con los nuevos, esta función concreta puede fallar de forma silenciosa. Si sigue sin ir con los 4 archivos actualizados, dime exactamente qué ves (¿el texto desaparece?, ¿se queda igual?, ¿sale algún error en la consola/terminal si ejecutas `python main.py` desde ahí?) para poder localizarlo con más precisión.

### 19. LA causa raíz real de todo (texto, Mover, "no funciona nada") (`canvas.py`)
Gracias por pegar el error de la consola — sin él no lo habría encontrado. El problema: en una edición anterior, a `_bounding_box_of_content` se le perdió su propia línea `def` y su cuerpo quedó **pegado por accidente dentro de `enter_layer_edit_mode`**, justo después de su código real. Resultado:
- `_bounding_box_of_content` **no existía como método** — cualquier llamada a `self._bounding_box_of_content(...)` (desde `hit_test_layer`, `edit_layer_content`, o la propia `enter_layer_edit_mode`) lanzaba `AttributeError`.
- Python/Qt6 no hace explotar la aplicación cuando un evento de ratón lanza una excepción — solo la imprime por consola y sigue — así que todo fallaba **en silencio**: el objeto se seleccionaba a medias (lo que ya se ejecutaba antes del fallo sí surtía efecto) pero el resto del gesto (arrastrar, o aplicar el texto reeditado) nunca llegaba a ejecutarse.
- Esto explica de una vez tanto lo del texto como lo de Mover — ambos dependían de esa misma función rota.
- **Fix:** restaurada la línea `def _bounding_box_of_content(self, image):`, con el cuerpo envuelto además en un `try/except` por si la conversión QImage→PIL fallara por otro motivo, y usando exactamente el mismo patrón (`QBuffer` → `QByteArray.data()` → `PIL.Image.open`) que ya usa `icon_exporter.py` con éxito.
- **Verificado:** con `ast.parse` sobre el archivo completo, confirmando que el método existe exactamente una vez y que `enter_layer_edit_mode` termina donde debe.
- **Lección para el futuro:** si algo vuelve a comportarse como "no hace nada" de forma inexplicable, el paso más útil que puedes darme es exactamente lo que hiciste ahora — ejecutar `python main.py` desde una terminal (no haciendo doble clic en el archivo) y pegarme el traceback completo de la consola. Sin eso, solo puedo revisar el código a ojo, que es mucho más lento y menos fiable.

### 20. Tres bugs relacionados, mismo origen: cómo se trataba una capa "en blanco" (`canvas.py`)
- **"Capa fantasma" que ocupa todo el lienzo con la herramienta Mover, infinitas veces:** `_bounding_box_of_content` devolvía "todo el lienzo" cuando una capa estaba vacía. Como `hit_test_layer` usa ese recuadro para saber qué hay bajo el cursor, CUALQUIER capa vacía "coincidía" con un clic en cualquier punto del lienzo — y al seleccionarla con Mover, aparecían handles alrededor de todo el canvas (aunque no se viera nada, por estar vacía), una y otra vez. **Fix:** ahora devuelve `None` cuando no hay contenido, y `hit_test_layer` ignora esas capas en vez de "encontrarlas" en cualquier sitio.
- **El texto reeditado se insertaba más abajo (y más a la derecha) cada vez:** el texto renderizado siempre lleva un pequeño margen transparente interno alrededor de las letras (para que no se corten los extremos en cursiva, etc.), y ese margen cambia de tamaño según el tamaño de fuente. Al reeditar, se anclaba la ESQUINA de la imagen nueva (con su margen incluido) a la posición del contenido AJUSTADO (sin margen) del texto anterior — un desplazamiento que además se acumulaba en cada reedición. **Fix:** ahora se alinea el recuadro ajustado (sin margen) del texto nuevo con el recuadro ajustado del texto anterior, no las esquinas exteriores.
- **Una capa se quedaba vacía pero seguía en la lista (el elemento "desaparecía"):** consecuencia directa del primer bug — la selección repetida de capas fantasma en blanco probablemente pisaba la copia de seguridad (`_layer_edit_backup`) de un objeto real que estabas editando de verdad, con una copia en blanco, perdiendo el contenido original al cancelar. Al arreglar la causa raíz (el primer punto), esto debería quedar resuelto también.

### 21. Texto recortado al crecer, y panel izquierdo con scroll (`canvas.py`, `text_tool.py`, `main_window.py`)
- **Texto reeditado con más letras no se veía:** si el texto nuevo (más largo/grande que el anterior) se salía del lienzo por la derecha o por abajo, quedaba recortado —invisible— en vez de reajustarse. `edit_layer_content` ahora desplaza el punto de colocación lo justo hacia dentro del lienzo para que el contenido nuevo quepa entero, sin mover nada si ya cabía sin problema.
- **Vista previa del diálogo de texto tampoco crecía:** el `QLabel` de previsualización no tenía salto de línea activado, así que el texto largo se cortaba visualmente dentro del propio diálogo (aparte del problema anterior). Añadido `setWordWrap(True)` y una llamada a `adjustSize()` tras cada cambio, para que el diálogo crezca con el texto.
- **Panel izquierdo (Tamaño del lienzo, Herramientas, Pincel, Fondo, Capas...) ahora tiene su propia barra deslizadora vertical**, igual que la vista previa de tamaños de la derecha. Antes, al hacer la ventana más pequeña, el `QSplitter` comprimía todos los botones hasta una tira ilegible sin icono ni texto; ahora aparece scroll en su lugar y el panel nunca baja de un ancho mínimo usable (220px).

### 22. Relleno "robaba" el contenido de otra capa; reordenar capas no se veía (`canvas.py`, `tools/drawing_tools.py`)
- **Relleno hacía desaparecer figuras de otras capas:** el relleno calculaba la zona a rellenar mirando solo la capa activa. Como ahora cada forma vive en su propia capa (casi toda ella transparente, salvo la forma en sí), rellenar dentro de un círculo —por ejemplo— hacía que la "zona conectada" fuera CASI TODA esa capa, no solo el interior visual del círculo, y el color de relleno cubría casi todo el canvas en esa capa. Si esa capa estaba encima de otras en la pila, tapaba visualmente su contenido (parecía que "la figura de la capa anterior había desaparecido y el dibujo a lápiz se había cambiado de capa" — en realidad ninguna capa cambió de contenido por sí sola, pero una tapaba a la otra con un relleno enorme).
  - **Fix:** nuevo `flood_fill_region()` en `drawing_tools.py`, que calcula qué píxeles pertenecen a la zona a rellenar SIN modificar nada. El relleno ahora calcula esa zona sobre la imagen COMPUESTA (todas las capas visibles + fondo, tal y como se ve en pantalla), y aplica el color resultante únicamente en la capa activa. Así, rellenar "dentro del círculo" respeta el contorno que ves, sin importar en qué capa esté cada cosa.
- **Subir/bajar capas no se reflejaba en la vista (solo en la lista):** seleccionar una capa en el panel ya la "levanta" a modo edición (para poder redimensionarla) — eso deja su contenido real temporalmente fuera de `self.layers` (flotando aparte) y el hueco en blanco en su sitio. Si acto seguido pulsabas subir/bajar SIN fijarla antes, se reordenaban las capas (ahora vacías) de la lista, pero el contenido real seguía flotando —siempre se dibuja encima de todo, sin importar el orden— así que visualmente no cambiaba nada, y el índice de esa edición pendiente quedaba apuntando a la capa equivocada tras el reordenamiento.
  - **Fix:** `move_layer_up`/`move_layer_down` ahora fijan cualquier edición flotante pendiente ANTES de reordenar, igual que ya hacía `delete_layer`.

### 23. Vistas previas de tamaño todas iguales (`preview_widget.py`)
- **Causa:** `update_preview()` escalaba SIEMPRE a un tamaño fijo (~128px), ignorando por completo `self.size` (el tamaño de icono real que representa cada tarjeta: 16, 32, 256...). Por eso todas se veían igual de grandes.
- **Fix:** cada preview ahora se escala de forma PROPORCIONAL a su tamaño real: 256x256 se muestra a 128px (el máximo), y el resto a escala —16x16 se ve realmente pequeño, como debe ser—, en vez de forzarse todas al mismo tamaño en pantalla.

### Sobre el relleno que "ahora no rellena nada"
He revisado la lógica del punto 22 línea por línea y, sobre el papel, sigue siendo correcta (debería devolver al menos el propio píxel de partida, nunca una zona vacía). No he encontrado el fallo por análisis estático esta vez. Le he añadido manejo de errores visible: si algo falla, ahora debería aparecer un traceback en la consola (como pasó con el bug del punto 19, que resultó ser LA clave para encontrarlo). **Por favor, si al probarlo el relleno sigue sin hacer nada, ejecuta `python main.py` desde una terminal, prueba a rellenar, y pégame cualquier cosa que aparezca en la consola** — con eso lo encuentro mucho más rápido que a ciegas.

### 24. "Limpiar lienzo" ahora limpia TODAS las capas, no solo la activa (`canvas.py`, `main_window.py`)
Tenías toda la razón: como cada figura/texto/imagen vive en su propia capa, "limpiar" tiene que actuar sobre TODAS, no solo la que esté activa. `clear_canvas()` ahora elimina TODAS las capas y las sustituye por una única capa en blanco (el mismo estado que al empezar un proyecto). Como es un cambio bastante más destructivo que antes, añadí una confirmación ("esto borrará TODAS las capas, ¿continuar?") antes de ejecutarlo.

### Relleno: diagnóstico añadido (aún sin encontrar la causa)
No he logrado encontrar el fallo por análisis estático tras varias revisiones a fondo. Como no me llegó ningún traceback de consola la vez anterior, le añadí un canal de diagnóstico que no depende de la terminal: ahora, cada vez que uses la herramienta Relleno, aparecerá un mensaje en la **barra de estado de la propia aplicación** (abajo) indicando cuántos píxeles ha encontrado, en qué coordenadas, con qué tolerancia, y sobre qué capa — o el error exacto si algo falla. **Por favor, prueba a rellenar y dime literalmente qué pone esa barra de estado** (aunque sea "0 píxeles" o un mensaje de error) — con ese dato debería poder localizar la causa real en la siguiente ronda, en vez de seguir revisando código a ciegas.

### 25. No se podía volver a "fondo transparente" tras elegir un color (`main_window.py`)
- **Causa:** `on_bg_changed` comparaba `state == Qt.Checked`, una comparación que no es fiable en todas las versiones de PySide6 (ya me había pasado antes con otro checkbox). Al volver a marcar "Fondo transparente", la comparación fallaba, caía siempre en la rama de "con color" y volvía a aplicar el último color elegido.
- **Fix:** cambiado a `state != 0` (robusto independientemente de la versión). De paso, apliqué el mismo arreglo preventivo a los otros dos checkboxes que quedaban con la comparación frágil: "Mantener proporción" y la visibilidad de capas en el panel — por si acaso, aunque no se habían reportado como rotos.

### 26. El lápiz manchaba la capa de un objeto (imagen/texto/forma) en vez de tener la suya propia (`canvas.py`)
- **Causa:** el lápiz pinta sobre la capa activa a propósito (para no crear una capa nueva por cada trazo). Pero si justo antes habías importado/fijado una imagen (o texto, o una forma), esa capa se queda como activa — y el siguiente trazo de lápiz se fundía directamente con ella, perdiendo la posibilidad de mover/editar la imagen por separado más adelante sin arrastrar también el trazo.
- **Fix:** antes de que el lápiz empiece a pintar, si la capa activa es un OBJETO (`layer_type != "generic"`: imagen, texto o forma), se crea automáticamente una capa de dibujo nueva y en blanco, que pasa a ser la activa. Los trazos siguientes, mientras sigas con esa misma capa activa, se acumulan ahí con normalidad (no se crea una capa por cada trazo).
- **El borrador queda excluido a propósito:** si borras parte de una imagen o forma, tiene que borrar ESA capa de verdad, no una en blanco donde no habría nada que borrar. Solo el lápiz redirige a una capa nueva.

### 27. Cuatro ajustes de visualización (`main_window.py`, `canvas.py`)
- Botón de la barra de herramientas: "Importar" → "Importar Imagen" (el menú Archivo ya decía "Importar Imagen...", esto solo afectaba al icono de la barra).
- Panel de imagen importada: quitado el texto de ayuda ("Arrastra esquinas/bordes...") y el botón "✅ Fijar (Enter)". La función se mantiene intacta: clicar fuera de la imagen la fija, y volver a seleccionarla (panel de Capas o herramienta Mover) la deja editable de nuevo; Enter sigue alternando fijar/ajustar por teclado.
- Tolerancia de relleno por defecto: 32 → 100 (tanto en el spinbox como en `canvas.py`, para que coincidan).
- Vistas previas de tamaño: orden invertido, ahora de mayor a menor (256, 128, 64, 48, 32, 24, 16).

### 28. Guardar proyecto daba error (QBuffer que faltaba); quitado "Guardar Como" (`project_manager.py`, `canvas.py`, `main_window.py`)
- **Bug real:** `QImage.save()` necesita un `QIODevice` (un `QBuffer`) o una ruta de archivo — el código le pasaba un `QByteArray` directamente, lo cual nunca fue válido. Por eso guardar proyecto fallaba siempre con ese error de "wrong argument types". Arreglado usando `QBuffer` correctamente (mismo patrón que ya se usa en `icon_exporter.py` y en `canvas.py`).
- **De paso, guardar proyecto ahora también conserva el tipo/datos de las capas de texto** (texto, tipografía, tamaño, negrita/cursiva/subrayado, color): al reabrir un proyecto guardado, las capas de texto se pueden seguir reeditando con doble clic, no solo mover/redimensionar. Antes de este arreglo, esto nunca había llegado a probarse de verdad porque guardar fallaba antes de completarse.
- **Quitado "Guardar Como..." del menú Archivo** (era redundante con "Guardar Proyecto"). La función interna se mantiene: si guardas un proyecto que todavía no tiene archivo asignado, sigue preguntando dónde guardarlo la primera vez.

### 29. Cursor del lienzo según la herramienta y el grosor (`canvas.py`)
Con lápiz o borrador activos, el cursor ahora es un círculo con el diámetro REAL del pincel (en píxeles de pantalla, según el zoom actual), con doble trazo blanco/negro para que se vea bien sobre cualquier fondo. Se actualiza automáticamente al cambiar de herramienta, al cambiar el grosor del pincel, y al redimensionar la ventana (el zoom cambia el tamaño en pantalla). El resto de herramientas mantienen sus cursores de siempre (cruz, flecha, manita al pasar sobre un objeto con "Mover", etc.) — nada de eso se ha tocado.

### 30. Validación al cargar proyecto, tema claro/oscuro, y documentación del repo (`project_manager.py`, `main_window.py`, nuevos `README.md` y `requirements.txt`)
- **Validación al cargar:** `project_manager.py` ahora comprueba la forma del archivo ANTES de tocar nada del canvas (que sea JSON válido, que tenga tamaño de lienzo, que las capas —si las hay— no estén vacías o corruptas). Si algo falla, se lanza un `ValueError` con un mensaje en español legible, en vez de un `KeyError`/`TypeError` críptico de Python. `main_window.py` también distingue ahora un archivo que directamente no es JSON (mensaje específico) del resto de errores.
- **Tema claro/oscuro:** nuevo menú **Ver** con la opción "Tema oscuro" (marcable). Al desmarcarla se aplica `LIGHT_STYLE`, al marcarla `DARK_STYLE` — ambas ya existían completas en `ui/styles.py`, solo faltaba el interruptor.
- **`README.md`** (nuevo): documentación de presentación para subir a GitHub — características, instalación, uso, estructura del proyecto, formatos de exportación, formato de proyecto, e ideas pendientes.
- **`requirements.txt`** (nuevo): `PySide6`, `Pillow`, `numpy` — las tres únicas dependencias externas reales de todo el proyecto (el resto son módulos de la librería estándar: `json`, `base64`, `io`, `os`, `math`, `queue`, `copy`, `sys`).

## ✅ Decisiones tomadas sobre los pendientes (cerrado, no se toca)
- **Guardado en base64 para proyectos grandes:** se deja como está — viable de sobra para tamaños de icono normales.
- **Desenfoque/nitidez sin conectar a la UI:** se deja como está, documentado por si se quiere retomar en el futuro (ver README).
- **Formas sin exponer (estrella, polígono, rectángulo redondeado, flecha):** se dejan como están, no hacen falta para crear iconos.
- **Historial de deshacer al cargar imagen/proyecto:** se deja como está (comportamiento estándar: cargar un archivo empieza un historial nuevo).

### 31. Exportar PNG ignoraba los tamaños seleccionados (`main_window.py`)
- **Bug:** `export_png()` ni siquiera miraba los checkboxes de tamaño — siempre exportaba un único PNG al tamaño actual del lienzo, sin importar qué marcaras.
- **Fix:** ahora respeta la selección tal y como pediste: si marcas **un solo tamaño**, exporta un único archivo con el nombre tal cual (sin sufijo). Si marcas **varios**, exporta un archivo por cada tamaño, añadiendo el tamaño al nombre (`icono_128x128.png`, `icono_256x256.png`...).
- **Nota sobre el `.ico`:** no lo he tocado, y quiero que sepas por qué antes de que lo pruebes y te extrañe: el formato `.ico` está pensado precisamente para llevar VARIOS tamaños dentro de un mismo archivo (así es como Windows elige automáticamente la resolución según dónde se use el icono) — por eso, si marcas 128 y 256 y exportas a `.ico`, obtienes **un solo archivo** `icono.ico` que lleva las dos resoluciones embebidas, no dos archivos sueltos. Es el comportamiento estándar y probablemente el que quieres para un `.ico` real. Si en cambio prefieres que también genere un `.ico` separado por cada tamaño (en vez de uno combinado), dímelo y lo cambio.

### 32. Nueva función: Importar ICO (`image_importer.py`, `main_window.py`)
- **"Importar ICO..."** añadido al menú Archivo (`Ctrl+Shift+I`) y a la barra de herramientas, justo entre Rehacer e Importar Imagen, tal y como pediste.
- **Diseño (dos decisiones que tomé y te explico):**
  1. **Reemplaza el proyecto, no lo añade como objeto flotante** — a diferencia de "Importar Imagen" (que añade la imagen como un objeto más sobre lo que ya tuvieras), "Importar ICO" trata el archivo como si "abrieras" ese icono para seguir editándolo: sustituye todo el lienzo por su contenido, y ajusta el tamaño del lienzo a la resolución nativa del icono. Por eso, si hay cambios sin guardar, se ofrece guardar el proyecto actual primero — exactamente el comportamiento que pediste, y el mismo patrón que ya usaba "Nuevo Proyecto" (ahora compartido mediante un pequeño helper `confirm_discard_changes()`).
  2. **Si el `.ico` lleva varias resoluciones embebidas** (lo habitual), se usa automáticamente la más grande para partir del mejor detalle posible — no se pregunta cuál usar. Si prefieres poder elegir tú la resolución de partida cuando haya varias, dímelo y añado un selector.

### 33. Cada capa guarda su propia posición: ya no se recorta contenido al mover fuera del lienzo (`layer.py`, `canvas.py`, `project_manager.py`)
Este era el fondo del problema: el modelo asumía que toda capa ocupaba EXACTAMENTE el tamaño del lienzo, ancladas en (0,0). Al mover un objeto parcialmente fuera y fijarlo, se "horneaba" dentro de un lienzo del tamaño del canvas, y QPainter recortaba silenciosamente lo que sobresalía — para siempre, sin poder recuperarlo.
- **`Layer` ahora tiene `position`** (esquina superior izquierda, puede ser negativa o salirse del lienzo por cualquier lado) además de su imagen, que ya no tiene por qué medir el lienzo entero — se recorta a su contenido real. El historial de cada capa guarda también la posición (mover también se puede deshacer).
- **Solo se recorta la VISUALIZACIÓN, nunca los datos:** `composite_layers()` dibuja cada capa en su posición real; lo que quede fuera del lienzo se recorta de la imagen final compuesta (para ver/exportar), pero la capa en sí conserva TODO su contenido intacto. Si mueves el objeto de vuelta dentro, aparece completo.
- Simplifica de paso `edit_layer_content` (reeditar texto) y `set_canvas_size` (cambiar el tamaño del lienzo), que antes tenían que "encajar a la fuerza" el contenido y podían recortar por el mismo motivo.
- Lápiz, borrador y relleno traducen correctamente sus coordenadas a la posición de la capa activa (por si no está en (0,0) — p. ej. el borrador actuando directamente sobre una imagen importada). El lápiz, además, agranda automáticamente la capa si dibujas justo en su borde, para poder seguir pintando en cualquier parte tras haber movido una capa de dibujo.
- **Guardar/cargar proyecto** ahora también persiste la posición de cada capa (compatible con proyectos antiguos: se asume (0,0) si no la traen).

### 34. Nuevas herramientas: Seleccionar y Recortar (`canvas.py`, `main_window.py`)
- **"▭ Seleccionar"**: arrastra un rectángulo sobre el lienzo (independiente de qué capa esté activa). Si al soltar la selección se sale de los límites de la capa activa, aparece un aviso en la barra de estado — no se impide, solo se advierte (al recortar, solo se conservará la parte que se solape). `Esc` descarta la selección.
- **"✂️ Recortar selección"** (botón, no una herramienta persistente): recorta la CAPA ACTIVA a la zona seleccionada. Si no hay ninguna selección hecha, avisa y no hace nada. Si la selección solo se solapa parcialmente con la capa, recorta solo esa parte solapada.

### 35. Cuadrícula de transparencia se salía del lienzo al redimensionar los paneles (`canvas.py`)
- **Causa:** la cuadrícula se dibuja en pasos de tamaño de celda (`int(grid_size)`), y la última celda de cada fila/columna puede "pasarse" un poco del borde real por redondeo — normalmente invisible porque ese sobrante cae fuera del widget, pero cuando el ancho de la ventana manda sobre el alto (justo lo que pasa al estrechar los paneles laterales), sobra espacio vertical alrededor del lienzo cuadrado, y ahí sí se veía ese sobrante de cuadrícula por encima/debajo de la línea gris que marca el tamaño real.
- **Fix:** recortado (`setClipRect`) el dibujo de la cuadrícula exactamente al recuadro real del lienzo, así que nunca puede sobresalir por redondeo, se note o no se note.

## 🔍 Pendiente de revisar (no tocado todavía)

Ninguno por ahora.
