"""Lista de escaneos guardados; al elegir uno se carga en el panel principal."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable

from ..config import DIAS_RETENCION
from ..database import Repositorio

_COLUMNAS = ("Fecha y hora", "Total", "OK", "Lento", "Sin respuesta", "Sin IP")


class VentanaEscaneos(tk.Toplevel):
    def __init__(self, parent, repo: Repositorio, al_elegir: Callable[[str], None]):
        super().__init__(parent)
        self.title(f"Historial de escaneos ({DIAS_RETENCION} dias)")
        self.geometry("660x480")
        self._repo = repo
        self._al_elegir = al_elegir

        ttk.Label(self, text="Doble clic o pulsa el botón de abajo para ver el escaneo"
                  ).pack(anchor="w", padx=8, pady=6)

        marco = ttk.Frame(self)
        marco.pack(fill="both", expand=True, padx=8)
        self.tree = ttk.Treeview(marco, columns=_COLUMNAS, show="headings", selectmode="browse")
        for c in _COLUMNAS:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=170 if c == "Fecha y hora" else 90, anchor="center")
        sb = ttk.Scrollbar(marco, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)

        ttk.Button(self, text="Ver este escaneo", command=self._elegir).pack(pady=8)
        self.tree.bind("<Double-1>", self._elegir)
        self.recargar()

    def recargar(self) -> None:
        """Vuelve a leer los escaneos (conserva la seleccion si sigue existiendo)."""
        sel = self.tree.selection()
        self.tree.delete(*self.tree.get_children())
        for ts, total, ok, lento, sin_resp, sin_ip in self._repo.escaneos():
            self.tree.insert("", "end", iid=ts, values=(ts, total, ok, lento, sin_resp, sin_ip))
        hijos = self.tree.get_children()
        if sel and self.tree.exists(sel[0]):
            self.tree.selection_set(sel[0])
        elif hijos:
            self.tree.selection_set(hijos[0])

    def _elegir(self, _evt=None) -> None:
        sel = self.tree.selection()
        if sel:
            self._al_elegir(sel[0])
