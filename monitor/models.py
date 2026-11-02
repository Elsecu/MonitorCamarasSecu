"""Modelos de datos puros (sin dependencias de UI, red ni disco)."""
from __future__ import annotations

from dataclasses import dataclass


class Estado:
    OK = "OK"
    LENTO = "Lento"
    SIN_RESPUESTA = "Sin respuesta"
    SIN_IP = "No hay IP"
    IP_INVALIDA = "IP invalida"

    TODOS = (OK, LENTO, SIN_RESPUESTA, SIN_IP, IP_INVALIDA)
    CON_LATENCIA = (OK, LENTO)


@dataclass(frozen=True)
class Nodo:
    nombre: str
    ip: str


@dataclass(frozen=True)
class ParametrosPing:
    count: int = 4
    timeout: float = 1.0
    concurrentes: int = 500
    lento_ms: float = 150.0


@dataclass(frozen=True)
class EstadisticaPing:
    vivo: bool
    rtt_prom: float   # ms
    perdida: float    # 0.0 - 1.0


@dataclass(frozen=True)
class Resultado:
    ts: str
    nombre: str
    ip: str
    ms: float | None
    perdida: int | None   # porcentaje 0-100
    estado: str
    lista: str = ""   # nombre del archivo Excel de origen

    def a_fila(self) -> tuple:
        return (self.ts, self.nombre, self.ip, self.ms, self.perdida, self.estado, self.lista)
