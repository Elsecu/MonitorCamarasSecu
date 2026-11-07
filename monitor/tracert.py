"""Tracert individual a un nodo: ejecuta tracert.exe y entrega los saltos en vivo.

Sin dependencias de UI. La ventana consulta `sesion.cola`:
  ("salto", Salto) | ("fin", "completo" | "detenido") | ("error", mensaje)
"""
from __future__ import annotations

import ipaddress
import logging
import queue
import re
import subprocess
import sys
import threading
from dataclasses import dataclass

from .config import TRACERT_MAX_SALTOS, TRACERT_TIMEOUT_MS
from .utils import normalizar_ip

log = logging.getLogger(__name__)

_RE_SALTO = re.compile(r"^\s*(\d+)\s+(.*\S)\s*$")
_RE_SONDEO = re.compile(r"(<\s*\d+|\d+)\s*ms|(\*)")


@dataclass(frozen=True)
class Salto:
    numero: int
    intentos: tuple[str, str, str]   # p. ej. ("1 ms", "<1 ms", "*")
    ip: str                          # "" si el salto no respondio
    nota: str                        # texto extra de tracert (timeouts, errores)


def parsear_linea(linea: str) -> Salto | None:
    """Convierte una linea de salida de tracert (es/en, con -d) en un Salto.
    Devuelve None para encabezados, lineas vacias y 'Traza completa'."""
    m = _RE_SALTO.match(linea)
    if not m:
        return None
    numero, resto = int(m.group(1)), m.group(2)

    sondeos = [("*" if g2 else g1.replace(" ", "") + " ms")
               for g1, g2 in _RE_SONDEO.findall(resto)]
    sondeos = (sondeos + ["", "", ""])[:3]

    residuo = _RE_SONDEO.sub(" ", resto)
    ip, notas = "", []
    for token in residuo.split():
        candidato = token.strip("[]")
        if not ip:
            try:
                ip = str(ipaddress.ip_address(candidato))
                continue
            except ValueError:
                pass
        notas.append(token)
    return Salto(numero, (sondeos[0], sondeos[1], sondeos[2]), ip, " ".join(notas))


def _codificacion() -> str:
    """tracert imprime en la pagina de codigos OEM de la consola (ej. cp850)."""
    if sys.platform == "win32":
        try:
            import ctypes
            cp = f"cp{ctypes.windll.kernel32.GetOEMCP()}"  # type: ignore[attr-defined]
            "".encode(cp)
            return cp
        except Exception:  # noqa: BLE001
            pass
    return "utf-8"


class SesionTracert:
    """Un tracert en un hilo propio. Una sesion por nodo (independientes entre si)."""

    def __init__(
        self,
        ip: str,
        max_saltos: int = TRACERT_MAX_SALTOS,
        timeout_ms: int = TRACERT_TIMEOUT_MS,
        comando: list[str] | None = None,   # solo para pruebas
    ):
        norm = normalizar_ip(ip)
        if norm is None:
            raise ValueError(f"IP invalida: {ip!r}")   # evita pasar texto libre al comando
        self.ip = norm
        self.cola: queue.Queue = queue.Queue()
        self._comando = comando or ["tracert", "-d", "-h", str(max_saltos),
                                    "-w", str(timeout_ms), norm]
        self._proc: subprocess.Popen | None = None
        self._detenido = False

    def iniciar(self) -> None:
        threading.Thread(target=self._run, daemon=True).start()

    def detener(self) -> None:
        self._detenido = True
        p = self._proc
        if p is not None and p.poll() is None:
            try:
                p.terminate()
            except OSError:
                pass

    def _run(self) -> None:
        try:
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)  # sin ventana de consola
            self._proc = subprocess.Popen(
                self._comando, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL, creationflags=flags)
            if self._detenido:
                self._proc.terminate()
            codif = _codificacion()
            for crudo in iter(self._proc.stdout.readline, b""):
                salto = parsear_linea(crudo.decode(codif, errors="replace"))
                if salto:
                    self.cola.put(("salto", salto))
            rc = self._proc.wait()
            if self._detenido:
                self.cola.put(("fin", "detenido"))
            elif rc != 0:
                self.cola.put(("error", f"tracert termino con codigo {rc}"))
            else:
                self.cola.put(("fin", "completo"))
        except FileNotFoundError:
            self.cola.put(("error", "No se encontro tracert.exe (solo disponible en Windows)."))
        except Exception as e:  # noqa: BLE001
            log.exception("Fallo el tracert a %s", self.ip)
            self.cola.put(("error", str(e)))
