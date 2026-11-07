import threading
import time
from types import SimpleNamespace

import pytest

from monitor.database import Repositorio
from monitor.models import EstadisticaPing, Nodo, ParametrosPing
from monitor.pinger import EscaneoCancelado, IcmpPinger
from monitor.service import MonitorService
from monitor.ui.worker import Trabajador


def _host(ip):
    return SimpleNamespace(address=ip, is_alive=True, avg_rtt=5.0, packet_loss=0.0)


def test_ping_normal_con_progreso(monkeypatch):
    async def falso(ips, **kw):
        return [_host(i) for i in ips]
    monkeypatch.setattr("icmplib.async_multiping", falso)
    avances = []
    r = IcmpPinger(lote=2).ping(["1.1.1.1", "1.1.1.2", "1.1.1.3"], ParametrosPing(),
                                lambda a, b: avances.append((a, b)), threading.Event())
    assert set(r) == {"1.1.1.1", "1.1.1.2", "1.1.1.3"} and avances == [(2, 3), (3, 3)]


def test_cancelar_en_medio_de_una_tanda(monkeypatch):
    import asyncio

    async def lento(ips, **kw):
        await asyncio.sleep(30)
    monkeypatch.setattr("icmplib.async_multiping", lento)
    ev = threading.Event()
    threading.Timer(0.3, ev.set).start()
    t0 = time.time()
    with pytest.raises(EscaneoCancelado):
        IcmpPinger().ping(["1.1.1.1"], ParametrosPing(), None, ev)
    assert time.time() - t0 < 3


def test_cancelar_antes_de_empezar_no_hace_ping(monkeypatch):
    llamadas = []

    async def falso(ips, **kw):
        llamadas.append(ips)
        return []
    monkeypatch.setattr("icmplib.async_multiping", falso)
    ev = threading.Event()
    ev.set()
    with pytest.raises(EscaneoCancelado):
        IcmpPinger().ping(["1.1.1.1"], ParametrosPing(), None, ev)
    assert llamadas == []


def test_servicio_cancelado_no_guarda_nada(tmp_path):
    ev = threading.Event()

    class Pinger:
        def ping(self, ips, params, progreso=None, cancelar=None):
            ev.set()      # el usuario cancela justo al terminar el ping
            return {"1.1.1.1": EstadisticaPing(True, 5.0, 0.0)}

    repo = Repositorio(tmp_path / "t.db")
    with pytest.raises(EscaneoCancelado):
        MonitorService(repo, Pinger()).ejecutar([Nodo("a", "1.1.1.1")], ParametrosPing(), cancelar=ev)
    assert repo.contar() == 0


def test_trabajador_reporta_cancelacion():
    t = Trabajador()

    def tarea():
        raise EscaneoCancelado()
    t.lanzar("ping", tarea)
    assert t.cola.get(timeout=2) == ("cancel", "ping", None)
