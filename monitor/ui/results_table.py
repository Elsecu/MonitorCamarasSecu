"""Tabla de resultados con colores, filtro y ordenamiento."""
from __future__ import annotations

from tkinter import ttk
from typing import Callable, Optional

from ..config import COLOR_ESTADO
from ..models import Estado, Resultado
from ..utils import clave_ip

COLUMNAS = ("Cámara", "Dirección IP", "Latencia (ms)", "% Paquetes perdidos", "Estado")
_ATRIBUTO = {"Cámara": "nombre", "Dirección IP": "ip", "Latencia (ms)": "ms",
             "% Paquetes perdidos": "perdida", "Estado": "estado"}
_ANCHOS = (340, 120, 90, 100, 120)


class TablaResultados(ttk.Frame):
    def __init__(self, parent, al_abrir: Optional[Callable[[str, str], None]] = None):
        super().__init__(parent)
        self._al_abrir = al_abrir
        self._resultados: list[Resultado] = []
        self._orden_inverso: dict[str, bool] = {}
        self._filtro_estado = "Todos"
        self._filtro_texto = ""

        self.tree = ttk.Treeview(self, columns=COLUMNAS, show="headings")
        for col, ancho in zip(COLUMNAS, _ANCHOS):
            self.tree.heading(col, text=col, command=lambda c=col: self._ordenar(c))
            self.tree.column(col, width=ancho,
                             anchor="w" if col in ("Cámara") else "center")
        sb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)
        for estado, color in COLOR_ESTADO.items():
            self.tree.tag_configure(estado, background="#" + color)
        self.tree.bind("<Double-1>", self._doble_click)

    # ---------- API publica
    @property
    def resultados(self) -> list[Resultado]:
        return self._resultados

    def cargar(self, resultados: list[Resultado]) -> None:
        self._resultados = list(resultados)
        self._render()

    def filtrar(self, estado: str, texto: str) -> None:
        self._filtro_estado = estado
        self._filtro_texto = texto.strip().lower()
        self._render()

    def conteo(self) -> dict[str, int]:
        c = {e: 0 for e in Estado.TODOS}
        for r in self._resultados:
            c[r.estado] = c.get(r.estado, 0) + 1
        return c

    # ---------- interno
    def _render(self) -> None:
        self.tree.delete(*self.tree.get_children())
        for r in self._resultados:
            if self._filtro_estado != "Todos" and r.estado != self._filtro_estado:
                continue
            if self._filtro_texto and self._filtro_texto not in f"{r.nombre} {r.ip}".lower():
                continue
            self.tree.insert(
                "", "end",
                values=(r.nombre, r.ip,
                        "" if r.ms is None else r.ms,
                        "" if r.perdida is None else r.perdida,
                        r.estado),
                tags=(r.estado,),
            )

    def _ordenar(self, columna: str) -> None:
        attr = _ATRIBUTO[columna]
        inverso = self._orden_inverso.get(columna, False)

        def clave(r: Resultado):
            v = getattr(r, attr)
            if attr == "ip":
                return clave_ip(v)
            if attr in ("ms", "perdida"):
                return (v is None, v if v is not None else 0)
            return str(v).lower()

        self._resultados.sort(key=clave, reverse=inverso)
        self._orden_inverso[columna] = not inverso
        self._render()

    def _doble_click(self, _evt) -> None:
        sel = self.tree.selection()
        if sel and self._al_abrir:
            v = self.tree.item(sel[0], "values")
            self._al_abrir(v[0], v[1])
