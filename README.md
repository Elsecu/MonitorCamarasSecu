# Monitor de Cámaras

Aplicación de escritorio para Windows que mide la **latencia** y la **conexión** desde el equipo central hacia todas las cámaras (nodos) de una lista en Excel.

- Ping masivo en paralelo, pensado para ~1,600 cámaras o más.
- Historial de **30 días** con borrado automático.
- Revisión de escaneos pasados, historial por cámara y **tracert** individual.
- Exportación a Excel (escaneo actual e historial del mes).

## Funciones

| Función | Cómo se usa |
|---|---|
| Escaneo | **Ejecutar escaneo**: ping a todas las IPs del Excel, en paralelo |
| Cancelar | El mismo botón cambia a **Cancelar escaneo** mientras corre. Un escaneo cancelado **no se guarda** |
| Repetición automática | **Repetir cada N min** (la aplicación debe quedar abierta) |
| Filtrar y ordenar | Lista **Estado**, cuadro **Buscar** (cámara o IP) y clic en un encabezado para ordenar |
| Historial de escaneos | **Ver historial de escaneos**: lista de los escaneos de los últimos 30 días. Doble clic (o **Ver este escaneo**) lo carga en el panel principal |
| Historial de una cámara | Doble clic en la cámara, o clic derecho → *Ver historial de la cámara*. Muestra disponibilidad, promedio, mín y máx, con botones **Copiar nombre** y **Copiar IP** |
| Tracert | Selecciona una cámara y pulsa **Tracert** (o clic derecho → *Tracert a esta cámara*). Los saltos aparecen en vivo. Botones: **Detener**, **Repetir**, **Copiar** |
| Copiar | Clic derecho → *Copiar nombre de la cámara* / *Copiar IP* |
| Exportar (Escaneo actual) | Excel con lo que se ve en el panel (incluye un escaneo pasado cargado desde el historial) |
| Exportar historial (30 días) | Excel con una columna por escaneo (ver [Exportar historial](#exportar-historial-30-días)) |
| Carpeta de datos | Abre la carpeta de la base de datos, configuración y logs |

Las ventanas secundarias son **únicas**: el tracert y el historial de una cámara (una por cámara) y el historial de escaneos. Si ya está abierta, se trae al frente en lugar de abrir otra. La lista de escaneos se actualiza sola cuando termina un escaneo nuevo.

## Excel de entrada

| A | B |
|---|---|
| Nodo | IP |
| Cámara 1-A | 10.1.1.10 |

- La fila 1 es el encabezado y se ignora. Hay un ejemplo en `nodos_ejemplo.xlsx`.
- Solo se aceptan **IPs** (IPv4 o IPv6), no nombres de host.
- Los **nombres deben ser únicos** dentro de cada Excel.
- IP vacía → *No hay IP*. IP mal escrita → *IP invalida*. Las filas sin nombre y sin IP se ignoran.
- **El nombre del archivo identifica la lista** (`norte.xlsx` → lista `norte`). El historial se guarda y se exporta por lista. Si renombras el archivo, cuenta como lista nueva.

## Estados y parámetros

| Estado | Significado |
|---|---|
| OK | Respondió, sin pérdida y con latencia ≤ umbral |
| Lento | Latencia > umbral, o pérdida parcial de paquetes |
| Sin respuesta | No respondió ningún ping |
| No hay IP | La fila no tiene IP |
| IP invalida | El texto no es una IP válida |

| Parámetro | Por defecto | Cuándo cambiarlo |
|---|---|---|
| Intentos (Pings) | 4 | Sube a 10 para más precisión (más lento) |
| Tiempo de espera (s) | 1 | Sube a 2-3 en enlaces lentos (VPN, satélite) |
| Dispositivos simultáneos | 500 | Baja a 200 si ves falsos "Sin respuesta" |
| Lento > (ms) | 150 | Ajústalo a tu red |
| Repetir cada (min) | 15 | Ver [tamaño de la base de datos](#datos-guardados) |

Los parámetros y el último Excel usado se recuerdan al cerrar la aplicación.

## Exportar historial (30 días)

Una fila por cámara y **una columna por escaneo**, de izquierda a derecha en orden cronológico:

| Cámara | Dirección IP | 2026-11-01 10:00 | 2026-11-01 10:15 | 2026-11-02 08:00 |
|---|---|---|---|---|
| Cámara 1-A | 10.1.1.10 | 21.5 | 23.0 | Sin respuesta |
| Cámara 1-B | 10.1.1.11 | | 18.0 | 19.5 |

- **Por lista**: se exporta una sola lista por archivo. Si hay varias, aparece un selector con la lista del Excel cargado preseleccionada. Los registros anteriores a que existieran las listas aparecen como *registros anteriores, sin lista*.
- **Por nombre**: si una cámara cambia de IP o se queda sin IP, sigue en la misma fila. La columna IP muestra la más reciente.
- **Orden de filas**: manda el Excel del último escaneo. Una cámara agregada en medio queda en medio, una movida sigue su nueva posición, y una eliminada queda junto a su vecino con las fechas nuevas vacías.
- **Celdas**: latencia numérica, o el texto del estado. Colores por formato condicional: rojo = sin respuesta, gris = sin IP, amarillo = latencia > umbral (la pérdida parcial no se marca en este Excel).
- Cabeceras y primeras 2 columnas congeladas, con filtro. Máximo 16,000 columnas (límite de Excel 16,384); si hay más, se exportan las más recientes.

## Datos guardados

Carpeta `%APPDATA%\MonitorNodos\` (botón **Carpeta de datos**):

| Archivo | Contenido |
|---|---|
| `pings.db` | Historial en SQLite. En cada escaneo se borra lo mayor a 30 días |
| `config.json` | Preferencias de la ventana |
| `logs\monitor.log` | Log rotativo (1 MB por archivo). Aquí se revisan los errores |

Tamaño aproximado de `pings.db` con 1,600 cámaras:

| Intervalo de repetición | Filas en 30 días | Tamaño |
|---|---|---|
| 5 min | ~13.8 M | ~1 GB |
| 15 min | ~4.6 M | ~300-400 MB |
| 30 min | ~2.3 M | ~150-200 MB |
| 60 min | ~1.2 M | ~80-100 MB |

Se recomienda **15 min o más**.

## Instalación y ejecución

Requisitos: Windows y Python 3.10 o superior.

```bat
pip install -r requirements-dev.txt
python main.py                 :: ejecutar (CMD como administrador)
python -m pytest -q            :: pruebas
construir_exe.bat              :: genera dist\MonitorCamaras.exe
```

- El ping ICMP necesita **permisos de administrador**. El `.exe` los pide solo (`--uac-admin`); con `python main.py` abre la consola como administrador.
- El antivirus puede marcar el `.exe` como falso positivo (común con PyInstaller): agrega una excepción.
- El tracert usa `tracert.exe` de Windows (`-d -h 30 -w 1000`) y no necesita administrador.

## Estructura del proyecto

| Archivo | Responsabilidad | Toca aquí si quieres... |
|---|---|---|
| `main.py` | Arma las dependencias y abre la ventana | Cambiar el arranque |
| `monitor/config.py` | Rutas, constantes (retención, lote, tracert), colores, `Settings` | Cambiar días de retención, colores, límites del tracert |
| `monitor/models.py` | `Nodo`, `Resultado`, `Estado`, `ParametrosPing` | Agregar un estado o un campo |
| `monitor/utils.py` | `es_admin`, `normalizar_ip`, `clave_ip` | Utilidades de IP |
| `monitor/pinger.py` | Ping ICMP masivo y cancelación (`EscaneoCancelado`) | Cambiar el motor de ping |
| `monitor/service.py` | `clasificar()` y `MonitorService.ejecutar()` | Reglas de "Lento", alertas |
| `monitor/tracert.py` | `SesionTracert`: ejecuta `tracert.exe` y parsea los saltos | Cambiar el comportamiento del tracert |
| `monitor/database.py` | SQLite: guardar, purgar, escaneos, historial por cámara, matriz del mes | Nuevas consultas o reportes |
| `monitor/excel_reader.py` | Lee el Excel de cámaras | Nuevas columnas de entrada |
| `monitor/excel_exporter.py` | Exporta el escaneo actual y el historial del mes | Formato de los Excel |
| `monitor/logging_setup.py` | Log rotativo | Nivel de log |
| `monitor/ui/main_window.py` | Ventana principal, botones, eventos y ventanas únicas (`_abrir_unica`) | Botones y flujo |
| `monitor/ui/results_table.py` | Tabla de resultados: colores, filtro, orden, menú de clic derecho | Columnas y menú |
| `monitor/ui/history_window.py` | Historial de una cámara (por nombre) | Detalle por cámara |
| `monitor/ui/scans_window.py` | Lista de escaneos guardados | Navegar escaneos pasados |
| `monitor/ui/tracert_window.py` | Ventana de saltos del tracert | Columnas o colores del tracert |
| `monitor/ui/list_picker.py` | Selector de lista para exportar el historial | Selector de lista |
| `monitor/ui/worker.py` | Hilos y cola hacia la interfaz | Tareas en segundo plano |
| `tests/` | Pruebas con pytest | Validar cambios |
| `construir_exe.bat` | Genera el `.exe` con PyInstaller | Nombre o ícono del `.exe` |

Reglas de diseño:

- `ui/` depende de la lógica; la lógica **nunca** importa `ui/`.
- El ping está detrás de la interfaz `Pinger` (`pinger.py`): se reemplaza por un falso en las pruebas.
- Las tareas largas (escaneo, exportación) corren en hilos con `Trabajador`; la ventana lee los resultados con una cola.
- La base de datos abre una conexión por operación, por lo que es segura entre hilos.

Flujo de un escaneo:

```
Excel -> excel_reader -> service (pinger -> clasificar) -> database -> tabla / excel_exporter
```

## Pruebas

`python -m pytest -q` cubre: clasificación de estados, cancelación del escaneo, base de datos (purga, listas, orden de la matriz, migración de bases antiguas), exportaciones a Excel, configuración y el parser del tracert. La interfaz gráfica y el ping real contra equipos no tienen pruebas automáticas.

## Agregar funciones (ejemplos)

| Quiero... | Dónde |
|---|---|
| Un estado nuevo | `models.Estado` + `config.COLOR_ESTADO` + regla en `service.clasificar` |
| Alerta por correo cuando una cámara se cae | Módulo nuevo `monitor/notifier.py`, llamado desde `MonitorService.ejecutar` |
| Otro reporte en Excel | Método en `database.py` + función en `excel_exporter.py` + botón en `main_window.py` |
| Otra ventana secundaria | Clase en `monitor/ui/` y abrirla con `self._abrir_unica(clave, crear)` en `main_window.py` |
| Más saltos o más espera en el tracert | `TRACERT_MAX_SALTOS` y `TRACERT_TIMEOUT_MS` en `config.py` |

## Solución de problemas

| Síntoma | Causa probable | Solución |
|---|---|---|
| Todas "Sin respuesta" | Sin permisos de administrador | Ejecutar como administrador |
| Algunas "Sin respuesta" que sí están vivas | La cámara bloquea ICMP, o hay saturación | Revisar el firewall de la cámara; bajar "Dispositivos simultáneos" |
| Caracteres raros en las notas del tracert | Página de códigos de la consola | Revisar `_codificacion()` en `tracert.py` |
| La aplicación se cierra o falla algo | Error interno | Revisar `%APPDATA%\MonitorNodos\logs\monitor.log` |
| `py` no se reconoce | Python sin PATH | Reinstalar Python marcando *Add python.exe to PATH* |
| El `.bat` falla en `pip` | Sin internet o proxy | Ejecutar `pip install -r requirements-dev.txt` manualmente |