"""Ventana con el historial de 30 dias de un nodo."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ..config import COLOR_ESTADO, DIAS_RETENCION
from ..database import Repositorio
from ..models import Estado


class VentanaHistorial(tk.Toplevel):
    def __init__(self, parent, repo: Repositorio, nombre: str, ip: str):
        super().__init__(parent)
        detalle = f"{nombre} ({ip})" if nombre and ip else (nombre or ip)
        self.title(f"Historial {DIAS_RETENCION} dias - {detalle}")
        self.geometry("620x520")
        datos = repo.historial_nodo(nombre, ip)

        ttk.Label(self, text=self._resumen(datos)).pack(anchor="w", padx=8, pady=6)

        cols = ("Fecha", "Latencia (ms)", "% Paquetes perdidos", "Estado")
        tree = ttk.Treeview(self, columns=cols, show="headings")
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=140, anchor="center")
        sb = ttk.Scrollbar(self, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        tree.pack(fill="both", expand=True, padx=(8, 0), pady=(0, 8))
        for estado, color in COLOR_ESTADO.items():
            tree.tag_configure(estado, background="#" + color)
        for ts, ms, perdida, estado in datos:
            tree.insert("", "end",
                        values=(ts, "" if ms is None else ms,
                                "" if perdida is None else perdida, estado),
                        tags=(estado,))

    @staticmethod
    def _resumen(datos: list[tuple]) -> str:
        if not datos:
            return "Sin datos en el historial."
        total = len(datos)
        caidos = sum(1 for d in datos if d[3] == Estado.SIN_RESPUESTA)
        ms = [d[1] for d in datos if d[1] is not None]
        base = f"Muestras: {total} | Disponibilidad: {100 * (total - caidos) / total:.1f}% | "
        if not ms:
            return base + "Sin respuestas"
        return base + f"Prom: {sum(ms) / len(ms):.1f} ms | Min: {min(ms):.1f} | Max: {max(ms):.1f}"
