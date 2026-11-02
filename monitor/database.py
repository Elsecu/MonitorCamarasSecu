"""Persistencia SQLite: historial, purga a 30 dias y consultas para reportes."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterator

from .config import DB_PATH, FMT_TS, MAX_COLUMNAS_EXCEL
from .models import Estado, Resultado

_TABLA = """
CREATE TABLE IF NOT EXISTS pings(
    ts TEXT NOT NULL, nombre TEXT, ip TEXT, ms REAL, perdida INTEGER, estado TEXT,
    lista TEXT DEFAULT '');
"""
_INDICES = """
CREATE INDEX IF NOT EXISTS i_ts ON pings(ts);
CREATE INDEX IF NOT EXISTS i_ip ON pings(ip, ts);
CREATE INDEX IF NOT EXISTS i_nombre ON pings(nombre, ts);
CREATE INDEX IF NOT EXISTS i_lista ON pings(lista, ts);
"""


class Repositorio:
    def __init__(self, ruta: Path | str = DB_PATH):
        self.ruta = Path(ruta)
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as con:
            con.executescript(_TABLA)
            cols = [r[1] for r in con.execute("PRAGMA table_info(pings)")]
            if "lista" not in cols:  # migracion de bases de datos anteriores
                con.execute("ALTER TABLE pings ADD COLUMN lista TEXT DEFAULT ''")
            con.executescript(_INDICES)

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        # Una conexion por operacion: seguro entre hilos.
        con = sqlite3.connect(self.ruta)
        try:
            yield con
            con.commit()
        finally:
            con.close()

    # ---------- escritura
    def guardar(self, resultados: list[Resultado]) -> None:
        with self._conn() as con:
            con.executemany(
                "INSERT INTO pings VALUES(?,?,?,?,?,?,?)",
                [r.a_fila() for r in resultados],
            )

    def purgar(self, dias: int, ahora: datetime | None = None) -> int:
        corte = ((ahora or datetime.now()) - timedelta(days=dias)).strftime(FMT_TS)
        with self._conn() as con:
            return con.execute("DELETE FROM pings WHERE ts < ?", (corte,)).rowcount

    # ---------- lectura
    def contar(self) -> int:
        with self._conn() as con:
            return con.execute("SELECT COUNT(*) FROM pings").fetchone()[0]

    def historial_nodo(self, nombre: str, ip: str = "", limite: int = 20000) -> list[tuple]:
        """(ts, ms, perdida, estado) del mas reciente al mas antiguo.
        Busca por NOMBRE (sobrevive a cambios de IP); si no hay nombre, por IP."""
        campo, valor = ("nombre", nombre) if nombre else ("ip", ip)
        with self._conn() as con:
            return con.execute(
                f"SELECT ts, ms, perdida, estado FROM pings WHERE {campo}=? "
                "ORDER BY ts DESC LIMIT ?",
                (valor, limite),
            ).fetchall()

    def escaneos(self) -> list[tuple]:
        """Lista de escaneos guardados (mas reciente primero):
        (ts, total, ok, lento, sin_respuesta, sin_ip)."""
        with self._conn() as con:
            return con.execute(
                "SELECT ts, COUNT(*), SUM(estado='OK'), SUM(estado='Lento'), "
                "SUM(estado='Sin respuesta'), SUM(estado IN ('No hay IP','IP invalida')) "
                "FROM pings GROUP BY ts ORDER BY ts DESC"
            ).fetchall()

    def cargar_escaneo(self, ts: str) -> list[Resultado]:
        """Resultados completos de un escaneo, en el orden original del Excel."""
        with self._conn() as con:
            filas = con.execute(
                "SELECT ts, nombre, ip, ms, perdida, estado FROM pings "
                "WHERE ts=? ORDER BY rowid", (ts,)
            ).fetchall()
        return [Resultado(*f) for f in filas]

    def listas(self) -> list[str]:
        """Listas (archivos Excel) con historial, la de uso mas reciente primero.
        '' = registros anteriores a que se guardara el nombre de la lista."""
        with self._conn() as con:
            return [r[0] or "" for r in con.execute(
                "SELECT lista FROM pings GROUP BY lista ORDER BY MAX(ts) DESC")]

    def matriz(
        self, lista: str = "", max_columnas: int = MAX_COLUMNAS_EXCEL
    ) -> tuple[list[str], list[tuple[str, str, list]]]:
        """Historial de UNA lista en forma de matriz.

        Devuelve (timestamps ASC, filas). Cada fila = (nombre, ip, valores) con un
        valor por timestamp: latencia (float) si respondio, o el texto del estado
        ('Sin respuesta', 'No hay IP', ...). None si el nodo no estaba en esa corrida.

        Los nodos se identifican por NOMBRE (si cambia la IP siguen en su fila; la
        columna IP muestra la mas reciente). Orden de filas: manda el Excel del
        ultimo escaneo (nodos nuevos o movidos quedan donde estan en ese Excel);
        un nodo eliminado queda justo despues del nodo que tenia arriba.
        """
        with self._conn() as con:
            tss = [r[0] for r in con.execute(
                "SELECT DISTINCT ts FROM pings WHERE lista=? ORDER BY ts", (lista,))]
            if not tss:
                return [], []
            tss = tss[-max_columnas:]
            col = {t: i for i, t in enumerate(tss)}
            orden: list[str] = []
            info: dict[str, list[str]] = {}
            valores: dict[str, list] = {}
            ts_actual, seq, vistos, seq_previa = None, [], set(), None
            cursor = con.execute(
                "SELECT ts, nombre, ip, ms, estado FROM pings WHERE lista=? AND ts >= ? "
                "ORDER BY ts, rowid", (lista, tss[0]))
            for ts, nombre, ip, ms, estado in cursor:
                if ts != ts_actual:
                    if ts_actual is not None and seq != seq_previa:
                        orden, seq_previa = _reordenar(orden, seq), seq
                    ts_actual, seq, vistos = ts, [], set()
                clave = nombre or f"#{ip}"
                if clave not in valores:
                    valores[clave] = [None] * len(tss)
                if clave not in vistos:
                    vistos.add(clave)
                    seq.append(clave)
                info[clave] = [nombre, ip]
                valores[clave][col[ts]] = (
                    ms if estado in Estado.CON_LATENCIA and ms is not None else estado
                )
            if seq != seq_previa:
                orden = _reordenar(orden, seq)
        return tss, [(info[k][0], info[k][1], valores[k]) for k in orden]


def _reordenar(orden: list[str], seq: list[str]) -> list[str]:
    """Nuevo orden de filas tras un escaneo cuyo Excel tenia el orden `seq`.

    Los nodos de `seq` siguen ese orden. Los que estaban en `orden` pero ya no
    estan en `seq` (eliminados) se anclan despues del nodo que tenian arriba.
    """
    presentes = set(seq)
    ancla: dict[str | None, str] = {}   # nodo previo -> nodo ausente que le sigue
    previo = None
    for k in orden:
        if k not in presentes:
            ancla[previo] = k
        previo = k
    if not ancla:
        return list(seq)

    resultado: list[str] = []

    def colocar(inicio: str) -> None:
        k: str | None = inicio
        while k is not None:           # el nodo y su cadena de eliminados contiguos
            resultado.append(k)
            k = ancla.get(k)

    if None in ancla:                  # eliminado que estaba al inicio de la lista
        colocar(ancla[None])
    for k in seq:
        colocar(k)
    return resultado
