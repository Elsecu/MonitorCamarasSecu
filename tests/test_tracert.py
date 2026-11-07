import sys
import time

import pytest

from monitor.tracert import SesionTracert, parsear_linea


def test_parsear_salto_normal_es():
    s = parsear_linea("  1    <1 ms    <1 ms    <1 ms  192.168.1.1")
    assert (s.numero, s.intentos, s.ip, s.nota) == (1, ("<1 ms", "<1 ms", "<1 ms"), "192.168.1.1", "")
    s = parsear_linea("  3     9 ms     8 ms    10 ms  10.0.0.1")
    assert s.intentos == ("9 ms", "8 ms", "10 ms") and s.ip == "10.0.0.1"


def test_parsear_timeout_es_y_en():
    s = parsear_linea("  2     *        *        *     Tiempo de espera agotado para esta solicitud.")
    assert s.intentos == ("*", "*", "*") and s.ip == "" and s.nota.startswith("Tiempo de espera")
    s = parsear_linea("  2     *        *        *     Request timed out.")
    assert s.ip == "" and s.nota == "Request timed out."


def test_parsear_timeout_parcial():
    s = parsear_linea("  5    12 ms     *       13 ms  172.16.0.1")
    assert s.intentos == ("12 ms", "*", "13 ms") and s.ip == "172.16.0.1"


def test_parsear_host_inaccesible():
    s = parsear_linea("  3  10.0.0.1  reports: Destination host unreachable.")
    assert s.intentos == ("", "", "") and s.ip == "10.0.0.1" and "unreachable" in s.nota


def test_parsear_ipv6():
    assert parsear_linea("  1    <1 ms    <1 ms    <1 ms  2001:db8::1").ip == "2001:db8::1"


@pytest.mark.parametrize("linea", [
    "", "\r\n", "Traza a 8.8.8.8 sobre un máximo de 30 saltos", "Tracing route to 8.8.8.8 over a maximum of 30 hops",
    "Traza completa.", "Trace complete.",
])
def test_lineas_que_no_son_saltos(linea):
    assert parsear_linea(linea) is None


def test_ip_invalida_no_se_ejecuta():
    with pytest.raises(ValueError):
        SesionTracert("8.8.8.8; calc.exe")


def _drenar(sesion, hasta_fin=True, timeout=10):
    eventos, fin = [], time.time() + timeout
    while time.time() < fin:
        try:
            ev = sesion.cola.get(timeout=0.2)
        except Exception:
            continue
        eventos.append(ev)
        if ev[0] in ("fin", "error"):
            break
    return eventos


def _falso(codigo):
    return [sys.executable, "-u", "-c", codigo]


def test_sesion_entrega_saltos_en_vivo():
    codigo = ("import time\n"
              "print('Traza a 10.0.0.3', flush=True)\n"
              "print('  1    <1 ms    <1 ms    <1 ms  192.168.1.1', flush=True); time.sleep(0.1)\n"
              "print('  2     *        *        *     Tiempo de espera agotado para esta solicitud.', flush=True)\n"
              "print('  3     5 ms     5 ms     5 ms  10.0.0.3', flush=True)\n"
              "print('Traza completa.')\n")
    s = SesionTracert("10.0.0.3", comando=_falso(codigo))
    s.iniciar()
    ev = _drenar(s)
    assert [e[1].numero for e in ev if e[0] == "salto"] == [1, 2, 3]
    assert ev[-1] == ("fin", "completo")


def test_sesion_detener_termina_el_proceso():
    codigo = ("import time\nprint('  1    <1 ms    <1 ms    <1 ms  192.168.1.1', flush=True)\ntime.sleep(60)\n")
    s = SesionTracert("10.0.0.3", comando=_falso(codigo))
    s.iniciar()
    assert s.cola.get(timeout=5)[0] == "salto"
    t0 = time.time()
    s.detener()
    assert _drenar(s)[-1] == ("fin", "detenido") and time.time() - t0 < 5


def test_sesion_programa_inexistente():
    s = SesionTracert("10.0.0.3", comando=["programa_que_no_existe_xyz"])
    s.iniciar()
    assert _drenar(s)[-1][0] == "error"


def test_sesion_codigo_de_salida_distinto_de_cero():
    s = SesionTracert("10.0.0.3", comando=_falso("import sys; sys.exit(3)"))
    s.iniciar()
    ev = _drenar(s)
    assert ev[-1][0] == "error" and "3" in ev[-1][1]
