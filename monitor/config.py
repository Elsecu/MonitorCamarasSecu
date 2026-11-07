"""Rutas, constantes y configuracion persistente (config.json)."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, fields
from pathlib import Path

APP_NAME = "MonitorCamaras"
DATA_DIR = Path(os.environ.get("APPDATA", str(Path.home()))) / APP_NAME
DB_PATH = DATA_DIR / "pings.db"
SETTINGS_PATH = DATA_DIR / "config.json"
LOG_DIR = DATA_DIR / "logs"

DIAS_RETENCION = 30          # dias que se conservan los registros
LOTE_PING = 200              # IPs por tanda (permite mostrar progreso)
FMT_TS = "%Y-%m-%d %H:%M:%S"
MAX_COLUMNAS_EXCEL = 16_000  # limite de Excel: 16,384 columnas
TRACERT_MAX_SALTOS = 30      # saltos maximos del tracert
TRACERT_TIMEOUT_MS = 4000    # espera por salto (ms)

# Colores por estado (hex sin '#')
COLOR_ESTADO = {
    "OK": "A9D18E",
    "Lento": "FFEB9C",
    "Sin respuesta": "FFC7CE",
    "No hay IP": "DDEBF7",
    "IP invalida": "F4B183",
}


def asegurar_directorios() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class Settings:
    """Preferencias del usuario; se guardan al cerrar la app."""

    excel: str = ""
    count: int = 4
    timeout: float = 1.0
    conc: int = 500
    lento: float = 150.0
    auto: bool = False
    auto_min: int = 15

    @classmethod
    def cargar(cls, ruta: Path = SETTINGS_PATH) -> "Settings":
        base = cls()
        try:
            datos = json.loads(Path(ruta).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return base
        for f in fields(cls):
            if f.name not in datos:
                continue
            defecto = getattr(base, f.name)
            valor = datos[f.name]
            try:
                if isinstance(defecto, bool):
                    valor = valor if isinstance(valor, bool) else defecto
                else:
                    valor = type(defecto)(valor)
                setattr(base, f.name, valor)
            except (TypeError, ValueError):
                pass
        return base

    def guardar(self, ruta: Path = SETTINGS_PATH) -> None:
        datos = {f.name: getattr(self, f.name) for f in fields(self)}
        try:
            Path(ruta).write_text(json.dumps(datos, indent=2), encoding="utf-8")
        except OSError:
            pass
