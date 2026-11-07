"""Ping masivo ICMP. Unico modulo que toca la red (facil de reemplazar/mockear)."""
from __future__ import annotations

import asyncio
import threading
from typing import Callable, Optional, Protocol

from .config import LOTE_PING
from .models import EstadisticaPing, ParametrosPing

Progreso = Optional[Callable[[int, int], None]]


class EscaneoCancelado(Exception):
    """El usuario cancelo el escaneo; no se guarda ningun resultado."""


class Pinger(Protocol):
    def ping(
        self, ips: list[str], params: ParametrosPing, progreso: Progreso = None,
        cancelar: Optional[threading.Event] = None,
    ) -> dict[str, EstadisticaPing]: ...


class IcmpPinger:
    """Implementacion real con icmplib (requiere administrador en Windows)."""

    def __init__(self, lote: int = LOTE_PING):
        self.lote = lote

    def ping(
        self, ips: list[str], params: ParametrosPing, progreso: Progreso = None,
        cancelar: Optional[threading.Event] = None,
    ) -> dict[str, EstadisticaPing]:
        from icmplib import async_multiping  # import perezoso

        resultado: dict[str, EstadisticaPing] = {}
        loop = asyncio.new_event_loop()
        try:
            for i in range(0, len(ips), self.lote):
                if cancelar is not None and cancelar.is_set():
                    raise EscaneoCancelado()
                tanda = ips[i : i + self.lote]
                hosts = loop.run_until_complete(
                    self._tanda(async_multiping, tanda, params, cancelar)
                )
                for h in hosts:
                    resultado[h.address] = EstadisticaPing(
                        h.is_alive, h.avg_rtt, h.packet_loss
                    )
                if progreso:
                    progreso(min(i + self.lote, len(ips)), len(ips))
        finally:
            loop.close()
        return resultado

    @staticmethod
    async def _tanda(multiping, tanda, params, cancelar):
        """Una tanda de pings; revisa `cancelar` cada 0.1 s para abortar rapido."""
        tarea = asyncio.ensure_future(
            multiping(
                tanda,
                count=params.count,
                interval=0.2,
                timeout=params.timeout,
                concurrent_tasks=params.concurrentes,
                privileged=True,
            )
        )
        while not tarea.done():
            if cancelar is not None and cancelar.is_set():
                tarea.cancel()
                try:
                    await tarea
                except asyncio.CancelledError:
                    pass
                raise EscaneoCancelado()
            await asyncio.wait({tarea}, timeout=0.1)
        return tarea.result()
