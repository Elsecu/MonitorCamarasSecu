# Monitor de Camaras

Latencia y conectividad desde el nodo central hacia todos los nodos. Historial de 30 dias y exportacion a Excel.
## OJO: Solo funciona para WINDOWS
## Estructura

| Archivo | Responsabilidad | Toca aqui si quieres... |
|---|---|---|
| `main.py` | Arma dependencias y abre la ventana | Cambiar el arranque |
| `monitor/config.py` | Rutas, constantes, `Settings` (config.json) | Cambiar dias de retencion, colores, lote |
| `monitor/models.py` | `Nodo`, `Resultado`, `Estado`, `ParametrosPing` | Agregar un estado o campo |
| `monitor/utils.py` | `es_admin`, `normalizar_ip`, `clave_ip` | Utilidades de IP |
| `monitor/pinger.py` | Ping ICMP masivo (unico modulo con red) | Cambiar el motor de ping |
| `monitor/service.py` | `clasificar()` + `MonitorService.ejecutar()` | Cambiar reglas de "Lento", alertas |
| `monitor/database.py` | SQLite: guardar, purgar, historial, escaneos, matriz | Nuevas consultas/reportes |
| `monitor/excel_reader.py` | Lee Excel de nodos (A = Nodo, B = IP) | Nuevas columnas de entrada |
| `monitor/excel_exporter.py` | Exporta corrida y matriz cronologica (por nombre de nodo) | Formato de los Excel |
| `monitor/logging_setup.py` | Log rotativo en `%APPDATA%\MonitorNodos\logs` | Nivel de log |
| `monitor/ui/main_window.py` | Ventana principal y eventos | Botones, flujo |
| `monitor/ui/results_table.py` | Tabla con colores, filtro, orden | Columnas de la tabla |
| `monitor/ui/history_window.py` | Historial por nodo, por nombre (doble clic) | Detalle por nodo |
| `monitor/ui/list_picker.py` | Dialogo para elegir la lista (Excel) a exportar | Selector de lista |
| `monitor/ui/scans_window.py` | Lista de escaneos guardados; cargar uno en el panel | Navegar escaneos pasados |
| `monitor/ui/worker.py` | Hilos + cola hacia la UI | Tareas en segundo plano |
| `tests/` | Pruebas (pytest) | Validar cambios |

Regla: `ui/` depende de la logica; la logica **nunca** importa `ui/`.

## Flujo
`Excel -> excel_reader -> service (pinger -> clasificar) -> database -> ui / excel_exporter`

## Comandos
```bat
pip install -r requirements-dev.txt
python -m pytest -q          :: pruebas
python main.py               :: ejecutar (como administrador)
construir_exe.bat            :: genera dist\MonitorNodos.exe
```

## Agregar funciones (ejemplos)
- Nuevo estado: `models.Estado` + `config.COLOR_ESTADO` + regla en `service.clasificar`.
- Alerta por correo: nuevo `monitor/notifier.py`, se llama desde `MonitorService.ejecutar`.
- Otro reporte: metodo en `database.py` + funcion en `excel_exporter.py` + boton en `main_window.py`.
