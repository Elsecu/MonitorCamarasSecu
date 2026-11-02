"""Dialogo modal para elegir de que lista (archivo Excel) exportar el historial."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk


def elegir_lista(parent, listas: list[str], preseleccion: str) -> str | None:
    """Devuelve el nombre de la lista elegida ('' = registros anteriores sin lista)
    o None si se cancela."""
    etiquetas = {(nombre or "(registros anteriores, sin lista)"): nombre for nombre in listas}
    elegido: dict[str, str | None] = {"valor": None}

    win = tk.Toplevel(parent)
    win.title("Exportar historial")
    win.transient(parent)
    win.resizable(False, False)
    ttk.Label(win, text="Seleccione el archivo:").pack(padx=12, pady=(12, 4), anchor="w")
    var = tk.StringVar(value=preseleccion or next(iter(etiquetas)))
    for etiqueta, nombre in etiquetas.items():
        if nombre == preseleccion:
            var.set(etiqueta)
    ttk.Combobox(win, textvariable=var, values=list(etiquetas), state="readonly",
                 width=44).pack(padx=12, pady=4)

    def aceptar() -> None:
        elegido["valor"] = etiquetas[var.get()]
        win.destroy()

    botones = ttk.Frame(win)
    botones.pack(pady=12)
    ttk.Button(botones, text="Exportar", command=aceptar).pack(side="left", padx=6)
    ttk.Button(botones, text="Cancelar", command=win.destroy).pack(side="left", padx=6)
    win.grab_set()
    parent.wait_window(win)
    return elegido["valor"]
