import json

from monitor.config import Settings


def test_cargar_defecto_si_no_existe(tmp_path):
    assert Settings.cargar(tmp_path / "no.json") == Settings()


def test_roundtrip_y_compat_con_version_anterior(tmp_path):
    p = tmp_path / "c.json"
    # la version 1.0 guardaba numeros como texto
    p.write_text(json.dumps({"excel": "x.xlsx", "count": "6", "timeout": "2.5", "auto": True,
                             "desconocido": 1}), encoding="utf-8")
    s = Settings.cargar(p)
    assert (s.excel, s.count, s.timeout, s.auto) == ("x.xlsx", 6, 2.5, True)
    s.guardar(p)
    assert Settings.cargar(p) == s


def test_json_corrupto(tmp_path):
    p = tmp_path / "c.json"
    p.write_text("{no es json", encoding="utf-8")
    assert Settings.cargar(p) == Settings()
