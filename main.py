"""Punto de entrada: arma las dependencias y abre la ventana."""
import ctypes
import logging

from monitor.config import Settings, asegurar_directorios
from monitor.database import Repositorio
from monitor.logging_setup import configurar_logging
from monitor.pinger import IcmpPinger
from monitor.service import MonitorService
from monitor.ui.main_window import VentanaPrincipal


def main() -> None:
    asegurar_directorios()
    configurar_logging()
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:  # noqa: BLE001
        pass
    repo = Repositorio()
    service = MonitorService(repo, IcmpPinger())
    VentanaPrincipal(Settings.cargar(), repo, service).mainloop()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logging.getLogger(__name__).exception("Error fatal")
        raise
