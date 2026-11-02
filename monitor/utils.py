"""Utilidades pequenas y sin estado."""
from __future__ import annotations

import ctypes
import ipaddress


def es_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())  # type: ignore[attr-defined]
    except Exception:
        return False


def normalizar_ip(txt: str) -> str | None:
    """Devuelve la IP normalizada o None si no es una IP valida."""
    try:
        return str(ipaddress.ip_address(txt.strip()))
    except ValueError:
        return None


def clave_ip(txt: str) -> tuple:
    """Clave para ordenar IPs numericamente (v4 antes que v6, invalidas al final)."""
    try:
        ip = ipaddress.ip_address(txt)
        return (ip.version, int(ip))
    except ValueError:
        return (9, 0)
