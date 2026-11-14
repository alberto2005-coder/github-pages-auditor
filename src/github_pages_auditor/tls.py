"""Caducidad del certificado TLS de una web (solo lectura, sin enviar datos)."""
import socket
import ssl
import time
from functools import lru_cache
from typing import Optional


def dias_hasta(not_after: str, ahora: Optional[float] = None) -> int:
    """Días (enteros, hacia abajo) que faltan para ``notAfter`` (formato del módulo ``ssl``)."""
    expira = ssl.cert_time_to_seconds(not_after)
    return int((expira - (time.time() if ahora is None else ahora)) // 86400)


@lru_cache(maxsize=128)
def dias_restantes(host: str, puerto: int = 443, timeout: float = 5.0) -> Optional[int]:
    """Días hasta que caduca el certificado de ``host``; ``None`` si no se puede comprobar."""
    try:
        contexto = ssl.create_default_context()
        with socket.create_connection((host, puerto), timeout=timeout) as sock:
            with contexto.wrap_socket(sock, server_hostname=host) as seguro:
                certificado = seguro.getpeercert()
        return dias_hasta(certificado["notAfter"])
    except (OSError, KeyError, ValueError, TypeError):
        return None
