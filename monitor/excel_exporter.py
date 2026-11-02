"""Exportaciones a Excel: corrida actual y matriz cronologica del mes."""
from __future__ import annotations

from datetime import datetime

from openpyxl import Workbook
from openpyxl.cell import WriteOnlyCell
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.styles import Alignment

from .config import COLOR_ESTADO, FMT_TS
from .models import Resultado


def _relleno(estado: str) -> PatternFill:
    return PatternFill("solid", fgColor=COLOR_ESTADO[estado])


def exportar_resultados(ruta: str, resultados: list[Resultado]) -> None:
    """Corrida actual: una fila por nodo."""
    enc = ["Fecha", "Cámara", "Dirección IP", "Latencia (ms)", "% Paquetes perdidos", "Estado"]
    wb = Workbook()
    ws = wb.active
    ws.title = "Resultado"
    ws.append(enc)
    for c in ws[1]:
        c.font = Font(bold=True)
    for r in resultados:
        ws.append(list(r.a_fila()[:6]))
        
        # Latencia: agregar ms y alinear a la izquierda
        celda = ws.cell(ws.max_row, 4)
        if isinstance(r.ms, (int, float)):
            celda.number_format = '0.## "ms"'
            celda.alignment = Alignment(horizontal="left")
        
        if r.estado in COLOR_ESTADO and r.estado != "OK":
            ws.cell(ws.max_row, 4).fill = _relleno(r.estado)
            ws.cell(ws.max_row, 6).fill = _relleno(r.estado)
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    for letra, ancho in zip("ABCDEF", (20, 28, 18, 16, 12, 16)):
        ws.column_dimensions[letra].width = ancho
    wb.save(ruta)


def exportar_matriz(
    ruta: str,
    timestamps: list[str],
    filas: list[tuple[str, str, list]],
    lento_ms: float,
) -> None:
    """Historial del mes: filas = nodos, columnas = fecha/hora de cada analisis
    (de izquierda a derecha, cronologico). Modo write_only: soporta millones de celdas.
    """
    if not timestamps:
        raise ValueError("No hay historial todavia.")

    wb = Workbook(write_only=True)
    ws = wb.create_sheet("Historial")
    ws.freeze_panes = "C2"
    ws.column_dimensions["A"].width = 28
    ws.column_dimensions["B"].width = 16
    for i in range(3, 3 + len(timestamps)):
        ws.column_dimensions[get_column_letter(i)].width = 17

    negrita = Font(bold=True)
    encabezado = []
    for texto in ("Cámara", "Dirección IP"):
        c = WriteOnlyCell(ws, value=texto)
        c.font = negrita
        encabezado.append(c)
    for ts in timestamps:
        c = WriteOnlyCell(ws, value=datetime.strptime(ts, FMT_TS))
        c.number_format = "yyyy-mm-dd hh:mm"
        c.font = negrita
        encabezado.append(c)
    ws.append(encabezado)

    for nombre, ip, valores in filas:
        celdas = [nombre, ip]

        for valor in valores:
            c = WriteOnlyCell(ws, value=valor)
            c.alignment = Alignment(horizontal="left", vertical="center")
            c.number_format = '0.## "ms"'
            celdas.append(c)

        ws.append(celdas)

    # Colores por formato condicional (no pesa por celda)
    ultima_col = get_column_letter(2 + len(timestamps))
    rango = f"C2:{ultima_col}{len(filas) + 1}"
    rojo = _relleno("Sin respuesta")
    gris = _relleno("No hay IP")
    amarillo = _relleno("Lento")
    ws.conditional_formatting.add(rango, FormulaRule(formula=['C2="Sin respuesta"'], fill=rojo))
    ws.conditional_formatting.add(
        rango, FormulaRule(formula=['OR(C2="No hay IP",C2="IP invalida")'], fill=gris)
    )
    ws.conditional_formatting.add(
        rango, FormulaRule(formula=[f"AND(ISNUMBER(C2),C2>{lento_ms})"], fill=amarillo)
    )
    ws.auto_filter.ref = f"A1:{ultima_col}{len(filas) + 1}"
    wb.save(ruta)
