"""Lectura de la lista de nodos desde Excel."""
from __future__ import annotations

from openpyxl import load_workbook

from .models import Nodo


def leer_nodos(ruta: str) -> list[Nodo]:
    """Columna A = nombre, B = IP, fila 1 = encabezado."""
    wb = load_workbook(ruta, read_only=True, data_only=True)
    try:
        ws = wb.active
        nodos: list[Nodo] = []
        for fila in ws.iter_rows(min_row=2, max_col=2, values_only=True):
            a, b = (tuple(fila) + (None, None))[:2]
            nombre = str(a).strip() if a is not None else ""
            ip = str(b).strip() if b is not None else ""
            if nombre or ip:
                nodos.append(Nodo(nombre, ip))
        return nodos
    finally:
        wb.close()
