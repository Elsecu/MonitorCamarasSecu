import pytest
from openpyxl import Workbook, load_workbook

from monitor.excel_exporter import exportar_matriz, exportar_resultados
from monitor.excel_reader import leer_nodos
from monitor.models import Estado, Nodo, Resultado


def test_leer_nodos(tmp_path):
    p = tmp_path / "n.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.append(["Nodo", "IP"])
    ws.append(["a", " 10.0.0.1 "])
    ws.append(["b", None])
    ws.append([None, None])
    ws.append(["solo nombre"])
    wb.save(p)
    assert leer_nodos(str(p)) == [Nodo("a", "10.0.0.1"), Nodo("b", ""), Nodo("solo nombre", "")]


def test_exportar_matriz_orden_y_formato(tmp_path):
    p = tmp_path / "m.xlsx"
    tss = ["2026-11-01 10:00:00", "2026-11-01 10:15:00", "2026-11-02 08:00:00"]
    filas = [("a", "1.1.1.1", [5.0, "Sin respuesta", 200.0]), ("b", "", ["No hay IP", None, None])]
    exportar_matriz(str(p), tss, filas, 150)
    ws = load_workbook(p).active
    assert [c.value for c in ws[1]][:2] == ["Cámara", "Dirección IP"]
    fechas = [c.value for c in ws[1]][2:]
    assert fechas == sorted(fechas) and len(fechas) == 3          # cronologico
    assert [c.value for c in ws[2]] == ["a", "1.1.1.1", 5.0, "Sin respuesta", 200.0]
    assert ws.freeze_panes == "C2"
    assert len(ws.conditional_formatting) == 1                      # un rango, 3 reglas


def test_exportar_matriz_sin_datos(tmp_path):
    with pytest.raises(ValueError):
        exportar_matriz(str(tmp_path / "x.xlsx"), [], [], 150)


def test_exportar_resultados(tmp_path):
    r = [Resultado("2026-11-01 10:00:00", "a", "1.1.1.1", None, 100, Estado.SIN_RESPUESTA)]
    exportar_resultados(str(tmp_path / "r.xlsx"), r)
    assert load_workbook(tmp_path / "r.xlsx").active["F2"].value == "Sin respuesta"
