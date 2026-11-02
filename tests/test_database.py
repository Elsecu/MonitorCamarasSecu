from datetime import datetime, timedelta

from monitor.config import FMT_TS
from monitor.database import Repositorio
from monitor.models import Estado, Resultado


def _r(ts, nombre, ip, ms, estado, lista=""):
    return Resultado(ts, nombre, ip, ms, None if ms is None else 0, estado, lista)


def test_purgar_borra_solo_lo_viejo(tmp_path):
    repo = Repositorio(tmp_path / "t.db")
    ahora = datetime(2026, 11, 1, 12, 0, 0)
    viejo = (ahora - timedelta(days=31)).strftime(FMT_TS)
    nuevo = (ahora - timedelta(days=29)).strftime(FMT_TS)
    repo.guardar([_r(viejo, "a", "1.1.1.1", 5.0, Estado.OK), _r(nuevo, "a", "1.1.1.1", 6.0, Estado.OK)])
    assert repo.purgar(30, ahora) == 1 and repo.contar() == 1


def test_matriz_cronologica_y_valores(tmp_path):
    repo = Repositorio(tmp_path / "t.db")
    # se insertan desordenadas a proposito
    repo.guardar([_r("2026-11-01 10:15:00", "a", "1.1.1.1", 7.0, Estado.OK),
                  _r("2026-11-01 10:15:00", "b", "2.2.2.2", None, Estado.SIN_RESPUESTA)])
    repo.guardar([_r("2026-11-01 10:00:00", "a", "1.1.1.1", 5.0, Estado.OK),
                  _r("2026-11-01 10:00:00", "b", "2.2.2.2", 300.0, Estado.LENTO),
                  _r("2026-11-01 10:00:00", "sin ip", "", None, Estado.SIN_IP)])
    tss, filas = repo.matriz()
    assert tss == ["2026-11-01 10:00:00", "2026-11-01 10:15:00"]
    assert filas[0] == ("a", "1.1.1.1", [5.0, 7.0])
    assert filas[1] == ("b", "2.2.2.2", [300.0, "Sin respuesta"])
    assert filas[2] == ("sin ip", "", ["No hay IP", None])


def test_matriz_vacia(tmp_path):
    assert Repositorio(tmp_path / "t.db").matriz() == ([], [])


def test_matriz_respeta_max_columnas(tmp_path):
    repo = Repositorio(tmp_path / "t.db")
    repo.guardar([_r(f"2026-11-01 10:0{i}:00", "a", "1.1.1.1", float(i), Estado.OK) for i in range(5)])
    tss, filas = repo.matriz(max_columnas=2)
    assert len(tss) == 2 and filas[0][2] == [3.0, 4.0]


def test_matriz_por_nombre_ante_cambio_de_ip(tmp_path):
    repo = Repositorio(tmp_path / "t.db")
    repo.guardar([_r("2026-11-01 10:00:00", "a", "1.1.1.1", 5.0, Estado.OK),
                  _r("2026-11-01 10:00:00", "b", "2.2.2.2", 6.0, Estado.OK)])
    # 'a' cambia de IP y 'b' se queda sin IP: deben seguir en SU fila
    repo.guardar([_r("2026-11-01 10:15:00", "a", "9.9.9.9", 7.0, Estado.OK),
                  _r("2026-11-01 10:15:00", "b", "", None, Estado.SIN_IP)])
    tss, filas = repo.matriz()
    assert [f[0] for f in filas] == ["a", "b"]
    assert filas[0] == ("a", "9.9.9.9", [5.0, 7.0])
    assert filas[1] == ("b", "", [6.0, "No hay IP"])


def test_historial_nodo_por_nombre(tmp_path):
    repo = Repositorio(tmp_path / "t.db")
    repo.guardar([_r("2026-11-01 10:00:00", "a", "1.1.1.1", 5.0, Estado.OK),
                  _r("2026-11-01 10:15:00", "a", "9.9.9.9", 7.0, Estado.OK),
                  _r("2026-11-01 10:30:00", "a", "", None, Estado.SIN_IP)])
    assert len(repo.historial_nodo("a", "")) == 3          # sobrevive a cambio/ausencia de IP
    assert len(repo.historial_nodo("", "9.9.9.9")) == 1    # sin nombre: por IP


def test_escaneos_lista_y_carga(tmp_path):
    repo = Repositorio(tmp_path / "t.db")
    repo.guardar([_r("2026-11-01 10:00:00", "a", "1.1.1.1", 5.0, Estado.OK),
                  _r("2026-11-01 10:00:00", "b", "", None, Estado.SIN_IP),
                  _r("2026-11-01 10:15:00", "a", "1.1.1.1", None, Estado.SIN_RESPUESTA)])
    lista = repo.escaneos()
    assert [e[0] for e in lista] == ["2026-11-01 10:15:00", "2026-11-01 10:00:00"]  # reciente primero
    assert lista[1] == ("2026-11-01 10:00:00", 2, 1, 0, 0, 1)
    carga = repo.cargar_escaneo("2026-11-01 10:00:00")
    assert [r.nombre for r in carga] == ["a", "b"] and carga[0].ms == 5.0


def _nombres(repo, lista=""):
    return [f[0] for f in repo.matriz(lista)[1]]


def test_nodo_nuevo_se_inserta_despues_de_su_predecesor(tmp_path):
    repo = Repositorio(tmp_path / "t.db")
    repo.guardar([_r("2026-11-01 10:00:00", "camara 1-A", "1.1.1.1", 5.0, Estado.OK),
                  _r("2026-11-01 10:00:00", "camara 2-A", "1.1.1.2", 5.0, Estado.OK)])
    repo.guardar([_r("2026-11-01 10:15:00", "camara 1-A", "1.1.1.1", 5.0, Estado.OK),
                  _r("2026-11-01 10:15:00", "camara 1-B", "1.1.1.9", 5.0, Estado.OK),
                  _r("2026-11-01 10:15:00", "camara 1-C", "1.1.1.8", 5.0, Estado.OK),
                  _r("2026-11-01 10:15:00", "camara 2-A", "1.1.1.2", 5.0, Estado.OK)])
    assert _nombres(repo) == ["camara 1-A", "camara 1-B", "camara 1-C", "camara 2-A"]
    assert repo.matriz()[1][1][2] == [None, 5.0]      # 1-B solo existe en el 2do escaneo


def test_nodo_nuevo_al_inicio_y_nodo_eliminado_conserva_lugar(tmp_path):
    repo = Repositorio(tmp_path / "t.db")
    repo.guardar([_r("2026-11-01 10:00:00", n, "", None, Estado.SIN_IP) for n in ("b", "c", "d")])
    repo.guardar([_r("2026-11-01 10:15:00", n, "", None, Estado.SIN_IP) for n in ("a", "b", "d")])
    assert _nombres(repo) == ["a", "b", "c", "d"]     # 'a' al inicio, 'c' (eliminado) en su sitio
    assert repo.matriz()[1][2][2] == ["No hay IP", None]


def test_listas_separadas(tmp_path):
    repo = Repositorio(tmp_path / "t.db")
    repo.guardar([_r("2026-11-01 10:00:00", "n1", "1.1.1.1", 5.0, Estado.OK, "norte"),
                  _r("2026-11-01 10:00:00", "n2", "1.1.1.2", 5.0, Estado.OK, "norte")])
    repo.guardar([_r("2026-11-01 10:05:00", "s1", "2.2.2.1", 9.0, Estado.OK, "sur")])
    assert repo.listas() == ["sur", "norte"]                      # la mas reciente primero
    tss, filas = repo.matriz("norte")
    assert tss == ["2026-11-01 10:00:00"] and [f[0] for f in filas] == ["n1", "n2"]
    tss, filas = repo.matriz("sur")
    assert tss == ["2026-11-01 10:05:00"] and [f[0] for f in filas] == ["s1"]


def test_migracion_base_anterior_sin_columna_lista(tmp_path):
    import sqlite3
    ruta = tmp_path / "vieja.db"
    con = sqlite3.connect(ruta)
    con.execute("CREATE TABLE pings(ts TEXT NOT NULL, nombre TEXT, ip TEXT, ms REAL, perdida INTEGER, estado TEXT)")
    con.execute("INSERT INTO pings VALUES('2026-10-30 10:00:00','a','1.1.1.1',5.0,0,'OK')")
    con.commit(); con.close()
    repo = Repositorio(ruta)
    assert repo.listas() == [""] and repo.matriz("")[1][0][:2] == ("a", "1.1.1.1")
    repo.guardar([_r("2026-11-01 10:00:00", "a", "1.1.1.1", 6.0, Estado.OK, "norte")])
    assert set(repo.listas()) == {"", "norte"}


def _escaneo(repo, ts, nombres, lista=""):
    repo.guardar([_r(ts, n, "", None, Estado.SIN_IP, lista) for n in nombres])


def test_nodos_en_medio_siguen_la_posicion_del_excel(tmp_path):
    repo = Repositorio(tmp_path / "t.db")
    _escaneo(repo, "2026-11-01 10:00:00", ["c1", "c2", "c4", "c5"])
    _escaneo(repo, "2026-11-01 10:15:00", ["c1", "c2", "c3", "c4", "c9", "c5"])
    assert _nombres(repo) == ["c1", "c2", "c3", "c4", "c9", "c5"]


def test_nodo_movido_sigue_el_ultimo_excel(tmp_path):
    repo = Repositorio(tmp_path / "t.db")
    _escaneo(repo, "2026-11-01 10:00:00", ["c1", "c2", "c3", "c5"])
    _escaneo(repo, "2026-11-01 10:15:00", ["c5", "c1", "c2", "c3"])
    tss, filas = repo.matriz()
    assert [f[0] for f in filas] == ["c5", "c1", "c2", "c3"]
    assert filas[0][2] == ["No hay IP", "No hay IP"]       # su historial viaja con el


def test_eliminados_contiguos_quedan_junto_a_su_vecino(tmp_path):
    repo = Repositorio(tmp_path / "t.db")
    _escaneo(repo, "2026-11-01 10:00:00", ["a", "b", "x", "y", "c"])
    _escaneo(repo, "2026-11-01 10:15:00", ["c", "a", "b"])       # x, y eliminados; c movido
    assert _nombres(repo) == ["c", "a", "b", "x", "y"]


def test_eliminado_al_inicio_y_escaneos_identicos(tmp_path):
    repo = Repositorio(tmp_path / "t.db")
    _escaneo(repo, "2026-11-01 10:00:00", ["z", "a", "b"])
    for i in range(1, 5):
        _escaneo(repo, f"2026-11-01 10:{i:02d}:00", ["a", "b"])
    assert _nombres(repo) == ["z", "a", "b"]


def test_nombre_repetido_en_un_escaneo_no_duplica_fila(tmp_path):
    repo = Repositorio(tmp_path / "t.db")
    _escaneo(repo, "2026-11-01 10:00:00", ["a", "b", "a"])
    assert _nombres(repo) == ["a", "b"]
