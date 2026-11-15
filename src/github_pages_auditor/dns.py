"""Comprobación de DNS de dominios propios: ¿apuntan a GitHub Pages?"""
import socket
from functools import lru_cache
from typing import Optional, Tuple

IPS_GITHUB_PAGES = frozenset({"185.199.108.153", "185.199.109.153", "185.199.110.153", "185.199.111.153"})


@lru_cache(maxsize=128)
def resolver_ipv4(host: str) -> Optional[Tuple[str, ...]]:
    """Direcciones IPv4 de ``host`` (sigue los CNAME); ``None`` si no se puede resolver."""
    try:
        return tuple(sorted({str(i[4][0]) for i in socket.getaddrinfo(host, None, socket.AF_INET)}))
    except (OSError, UnicodeError):
        return None


def apunta_a_github(host: str) -> Optional[bool]:
    """True/False según las IP de GitHub Pages; ``None`` si no se pudo comprobar.

    Con un proxy delante (p. ej. Cloudflare) la IP no es la de GitHub aunque todo funcione: es solo un aviso.
    """
    ips = resolver_ipv4(host)
    if ips is None:
        return None
    return bool(IPS_GITHUB_PAGES.intersection(ips))
