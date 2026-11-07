from monitor.database import Repositorio
from monitor.models import EstadisticaPing, Estado, Nodo, ParametrosPing
from monitor.service import MonitorService, clasificar


class PingerFalso:
    def __init__(self, stats):
        self.stats = stats
        self.recibidas = None

    def ping(self, ips, params, progreso=None, cancelar=None):
        self.recibidas = ips
        if progreso:
            progreso(len(ips), len(ips))
        return self.stats


def test_clasificar_todos_los_estados():
    nodos = [Nodo("a", "10.0.0.1"), Nodo("b", "10.0.0.2"), Nodo("c", "10.0.0.3"),
             Nodo("d", ""), Nodo("e", "10.0.0")]
    stats = {
        "10.0.0.1": EstadisticaPing(True, 20.0, 0.0),
        "10.0.0.2": EstadisticaPing(True, 300.0, 0.0),
        "10.0.0.3": EstadisticaPing(False, 0.0, 1.0),
    }
    r = clasificar(nodos, stats, 150, "2026-11-01 10:00:00")
    assert [x.estado for x in r] == [Estado.OK, Estado.LENTO, Estado.SIN_RESPUESTA,
                                     Estado.SIN_IP, Estado.IP_INVALIDA]
    assert r[0].ms == 20.0 and r[2].perdida == 100 and r[3].perdida is None


def test_lento_por_perdida_parcial():
    r = clasificar([Nodo("a", "1.1.1.1")], {"1.1.1.1": EstadisticaPing(True, 10.0, 0.25)}, 150, "t")
    assert r[0].estado == Estado.LENTO and r[0].perdida == 25


def test_ejecutar_guarda_y_deduplica(tmp_path):
    repo = Repositorio(tmp_path / "t.db")
    pinger = PingerFalso({"1.1.1.1": EstadisticaPing(True, 5.0, 0.0)})
    res = MonitorService(repo, pinger).ejecutar(
        [Nodo("a", "1.1.1.1"), Nodo("b", "1.1.1.1"), Nodo("c", "")], ParametrosPing())
    assert pinger.recibidas == ["1.1.1.1"]
    assert len(res) == 3 and repo.contar() == 3


def test_ejecutar_guarda_el_nombre_de_la_lista(tmp_path):
    repo = Repositorio(tmp_path / "t.db")
    pinger = PingerFalso({"1.1.1.1": EstadisticaPing(True, 5.0, 0.0)})
    MonitorService(repo, pinger).ejecutar([Nodo("a", "1.1.1.1")], ParametrosPing(), lista="norte")
    assert repo.listas() == ["norte"]
