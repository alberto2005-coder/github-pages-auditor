"""Sesión HTTP con reintentos y timeout por defecto.

IMPORTANTE: la sesión NO lleva credenciales. El token de GitHub se añade
únicamente en las peticiones a api.github.com (ver github_api.py), de modo que
nunca viaja a github.com, raw.githubusercontent.com ni a tu dominio.
"""
from __future__ import annotations

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from . import __version__

USER_AGENT = f"Mozilla/5.0 (compatible; ver-github-pages/{__version__}; +https://github.com/alberto2005-coder/ver-github-pages)"


class SesionHttp(requests.Session):
    """requests.Session que aplica un timeout por defecto a todas las peticiones."""

    def __init__(self, timeout: float = 10.0) -> None:
        super().__init__()
        self.request_timeout = timeout

    def request(self, method, url, **kwargs):
        kwargs.setdefault("timeout", self.request_timeout)
        return super().request(method, url, **kwargs)


def crear_sesion_http(timeout: float = 10.0, pool: int = 50) -> SesionHttp:
    session = SesionHttp(timeout=timeout)
    retries = Retry(
        total=3,
        backoff_factor=1.0,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "HEAD"],
        respect_retry_after_header=True,
        raise_on_status=False,  # devolver la última respuesta en vez de lanzar RetryError
    )
    adapter = HTTPAdapter(max_retries=retries, pool_connections=pool, pool_maxsize=pool)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers["User-Agent"] = USER_AGENT
    return session
