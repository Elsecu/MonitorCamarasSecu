"""Ejecuta tareas largas en un hilo y entrega resultados por una cola
(la ventana la consulta con after(); tkinter no es seguro entre hilos)."""
from __future__ import annotations

import logging
import queue
import threading
from typing import Any, Callable

from ..pinger import EscaneoCancelado

log = logging.getLogger(__name__)


class Trabajador:
    def __init__(self) -> None:
        self.cola: queue.Queue = queue.Queue()

    def lanzar(self, tarea: str, fn: Callable[..., Any], *args: Any) -> None:
        def _run() -> None:
            try:
                self.cola.put(("ok", tarea, fn(*args)))
            except EscaneoCancelado:
                self.cola.put(("cancel", tarea, None))
            except Exception as e:  # noqa: BLE001
                log.exception("Fallo la tarea %s", tarea)
                self.cola.put(("err", tarea, e))

        threading.Thread(target=_run, daemon=True).start()

    def progreso(self, hecho: int, total: int) -> None:
        self.cola.put(("prog", "ping", (hecho, total)))


def es_error_permisos(e: Exception) -> bool:
    txt = f"{type(e).__name__} {e}".lower()
    return any(k in txt for k in ("permission", "privilege", "administr", "denied"))
