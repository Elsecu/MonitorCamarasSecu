"""Log rotativo en %APPDATA%\\MonitorNodos\\logs\\monitor.log"""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from .config import LOG_DIR


def configurar_logging(nivel: int = logging.INFO) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        LOG_DIR / "monitor.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    raiz = logging.getLogger()
    raiz.setLevel(nivel)
    raiz.addHandler(handler)
