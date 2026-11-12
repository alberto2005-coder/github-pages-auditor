"""Salud de GitHub Pages: más allá de "responde 200".

Detecta 404 / sin ``index.html``, errores TLS, timeouts, redirecciones a otro
dominio o en bucle, páginas vacías o que no son HTML, y lentitud.

``esperada=True`` significa "sabemos que estas Pages deberían existir"
(modo API: ``has_pages``). Entonces cualquier fallo es ``roto``. Con
``esperada=False`` (modo web) un fallo solo significa "no hay Pages".
"""
import html as _html
import re
import time
from typing import Optional
from urllib.parse import urlparse

import requests

from .models import ESTADO_NINGUNA, ESTADO_OK, ESTADO_ROTA, PagesHealth

LIMITE_BYTES = 65536
MAX_REDIRECCIONES = 5
UMBRAL_LENTA_MS = 3000

_TITULO = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_HTML = re.compile(r"<(!doctype\s+html|html|head|body)\b", re.IGNORECASE)


def _leer_inicio(response) -> str:
    """Lee solo el primer fragmento del cuerpo (no descarga páginas enormes)."""
    try:
        trozo = next(iter(response.iter_content(LIMITE_BYTES)), b"")
    except (AttributeError, StopIteration, requests.RequestException):
        trozo = (getattr(response, "text", "") or "")[:LIMITE_BYTES]
    return trozo.decode("utf-8", "replace") if isinstance(trozo, bytes) else str(trozo)


def _titulo(cuerpo: str) -> Optional[str]:
    m = _TITULO.search(cuerpo)
    if not m:
        return None
    texto = " ".join(_html.unescape(m.group(1)).split())
    return texto[:120] or None


def _fallo(url: str, esperada: bool, problema: str) -> PagesHealth:
    return PagesHealth(
        estado=ESTADO_ROTA if esperada else ESTADO_NINGUNA, url=url, problemas=[problema]
    )


def inspeccionar(session, url: str, esperada: bool = False) -> PagesHealth:
    inicio = time.monotonic()
    try:
        response = session.get(url, allow_redirects=True, stream=True)
    except requests.exceptions.SSLError:
        return _fallo(url, esperada, "tls-error")
    except requests.exceptions.Timeout:
        return _fallo(url, esperada, "timeout")
    except requests.exceptions.TooManyRedirects:
        return _fallo(url, esperada, "bucle-de-redirecciones")
    except requests.RequestException:
        return _fallo(url, esperada, "sin-conexion")

    ms = int((time.monotonic() - inicio) * 1000)
    problemas, avisos = [], []
    titulo = None
    try:
        status = response.status_code
        final = getattr(response, "url", None) or url
        saltos = len(getattr(response, "history", None) or [])
        host_pedido = urlparse(url).netloc.lower()
        host_final = urlparse(final).netloc.lower()

        if status != 200:
            problemas.append("404" if status == 404 else f"http-{status}")
        else:
            if host_final != host_pedido and not host_pedido.endswith(".github.io"):
                problemas.append("redireccion-externa")  # dominio aparcado, etc.
            if saltos > MAX_REDIRECCIONES:
                problemas.append("demasiadas-redirecciones")
            cuerpo = _leer_inicio(response)
            if not cuerpo.strip():
                problemas.append("cuerpo-vacio")
            elif not _HTML.search(cuerpo):
                avisos.append("sin-html")
            titulo = _titulo(cuerpo)
            if ms > UMBRAL_LENTA_MS:
                avisos.append("lenta")
    finally:
        response.close()

    if not problemas:
        estado = ESTADO_OK
    else:
        estado = ESTADO_ROTA if esperada else ESTADO_NINGUNA
    # URL efectiva: la pedida, o el dominio personalizado al que GitHub redirige.
    url_final = url if host_final == host_pedido else final
    return PagesHealth(
        estado=estado, url=url, url_final=url_final if estado == ESTADO_OK or esperada else None,
        http_status=status, ms=ms, titulo=titulo, problemas=problemas, avisos=avisos,
    )
