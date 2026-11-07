"""Logica de negocio: nodos -> ping -> clasificacion -> guardado."""
from __future__ import annotations

import threading
from dataclasses import replace
from datetime import datetime
from typing import Callable, Optional

from .config import DIAS_RETENCION, FMT_TS
from .database import Repositorio
from .models import EstadisticaPing, Estado, Nodo, ParametrosPing, Resultado
from .pinger import EscaneoCancelado, Pinger
from .utils import normalizar_ip


def clasificar(
    nodos: list[Nodo],
    stats: dict[str, EstadisticaPing],
    lento_ms: float,
    ts: str,
) -> list[Resultado]:
    """Convierte las estadisticas de ping en resultados con estado (funcion pura)."""
    salida: list[Resultado] = []
    for n in nodos:
        if not n.ip:
            salida.append(Resultado(ts, n.nombre, "", None, None, Estado.SIN_IP))
            continue
        ip = normalizar_ip(n.ip)
        if ip is None:
            salida.append(Resultado(ts, n.nombre, n.ip, None, None, Estado.IP_INVALIDA))
            continue
        st = stats.get(ip)
        if st is None or not st.vivo:
            salida.append(Resultado(ts, n.nombre, ip, None, 100, Estado.SIN_RESPUESTA))
            continue
        lento = st.rtt_prom > lento_ms or st.perdida > 0
        salida.append(
            Resultado(
                ts, n.nombre, ip, round(st.rtt_prom, 2), round(st.perdida * 100),
                Estado.LENTO if lento else Estado.OK,
            )
        )
    return salida


class MonitorService:
    def __init__(self, repo: Repositorio, pinger: Pinger):
        self.repo = repo
        self.pinger = pinger

    def ejecutar(
        self,
        nodos: list[Nodo],
        params: ParametrosPing,
        progreso: Optional[Callable[[int, int], None]] = None,
        lista: str = "",
        cancelar: Optional[threading.Event] = None,
    ) -> list[Resultado]:
        ts = datetime.now().strftime(FMT_TS)
        ips = sorted({ip for n in nodos if (ip := normalizar_ip(n.ip))})
        stats = self.pinger.ping(ips, params, progreso, cancelar)
        if cancelar is not None and cancelar.is_set():
            raise EscaneoCancelado()   # cancelado: no se guarda nada
        resultados = [replace(r, lista=lista)
                      for r in clasificar(nodos, stats, params.lento_ms, ts)]
        self.repo.guardar(resultados)
        self.repo.purgar(DIAS_RETENCION)
        return resultados
