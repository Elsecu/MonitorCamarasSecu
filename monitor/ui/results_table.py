"""Tabla de resultados con colores, filtro y ordenamiento."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

from ..config import COLOR_ESTADO
from ..models import Estado, Resultado
from ..utils import clave_ip, normalizar_ip

COLUMNAS = ("Cámara", "Dirección IP", "Latencia (ms)", "% Paquetes perdidos", "Estado")
_ATRIBUTO = {"Cámara": "nombre", "Dirección IP": "ip", "Latencia (ms)": "ms",
             "% Paquetes perdidos": "perdida", "Estado": "estado"}
_ANCHOS = (340, 120, 90, 100, 120)


class TablaResultados(ttk.Frame):
    def __init__(self, parent, al_abrir: Optional[Callable[[str, str], None]] = None,
                 al_tracert: Optional[Callable[[str, str], None]] = None,
                 al_seleccionar: Optional[Callable[[], None]] = None):
        super().__init__(parent)
        self._al_abrir = al_abrir
        self._al_tracert = al_tracert
        self._al_seleccionar = al_seleccionar
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
        self.tree.bind("<<TreeviewSelect>>", lambda e: self._notificar_seleccion())
        self._menu = tk.Menu(self.tree, tearoff=0)
        self._menu.add_command(label="Tracert a esta cámara", command=self._tracert_seleccionado)
        self._menu.add_command(label="Ver historial de la cámara", command=self._historial_seleccionado)
        self.tree.bind("<Button-3>", self._menu_contextual)

    # ---------- API publica
    @property
    def resultados(self) -> list[Resultado]:
        return self._resultados

    def seleccionado(self) -> Optional[tuple[str, str]]:
        """(nombre, ip) de la fila seleccionada, o None."""
        sel = self.tree.selection()
        if not sel:
            return None
        v = self.tree.item(sel[0], "values")
        return str(v[0]), str(v[1])

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
        self._notificar_seleccion()

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

    def _notificar_seleccion(self) -> None:
        if self._al_seleccionar:
            self._al_seleccionar()

    def _menu_contextual(self, evt) -> None:
        iid = self.tree.identify_row(evt.y)
        if not iid:
            return
        self.tree.selection_set(iid)
        sel = self.seleccionado()
        valido = bool(sel and normalizar_ip(sel[1]))
        self._menu.entryconfig(0, state="normal" if valido else "disabled")
        try:
            self._menu.tk_popup(evt.x_root, evt.y_root)
        finally:
            self._menu.grab_release()

    def _tracert_seleccionado(self) -> None:
        sel = self.seleccionado()
        if sel and self._al_tracert:
            self._al_tracert(*sel)

    def _historial_seleccionado(self) -> None:
        sel = self.seleccionado()
        if sel and self._al_abrir:
            self._al_abrir(*sel)
