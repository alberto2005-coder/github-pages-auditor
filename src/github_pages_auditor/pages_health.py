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

from . import dns, linkcheck, tls
from .models import ESTADO_NINGUNA, ESTADO_OK, ESTADO_ROTA, PagesHealth

LIMITE_BYTES = 65536
MAX_REDIRECCIONES = 5
UMBRAL_LENTA_MS = 3000
UMBRAL_TLS_DIAS = 14

_TITULO = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_HTML = re.compile(r"<(!doctype\s+html|html|head|body)\b", re.IGNORECASE)
_META_DESCRIPCION = re.compile(r"<meta\b[^>]*\bname\s*=\s*[\"']description[\"']", re.IGNORECASE)
_LANG = re.compile(r"<html\b[^>]*\blang\s*=", re.IGNORECASE)
_ICONO = re.compile(r"<link\b[^>]*\brel\s*=\s*[\"'][^\"']*icon", re.IGNORECASE)
_IMG = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
_ALT = re.compile(r"\balt\s*=", re.IGNORECASE)
UMBRAL_PESO_BYTES = 1_000_000
_OG_IMAGE = re.compile(r"<meta\b[^>]*\bproperty\s*=\s*[\"']og:image[\"']", re.IGNORECASE)
_OG_TITLE = re.compile(r"<meta\b[^>]*\bproperty\s*=\s*[\"']og:title[\"']", re.IGNORECASE)
_VIEWPORT = re.compile(r"<meta\b[^>]*\bname\s*=\s*[\"']viewport[\"']", re.IGNORECASE)
_CANONICAL = re.compile(r"<link\b[^>]*\brel\s*=\s*[\"']canonical[\"']", re.IGNORECASE)
_MIXTO = re.compile(r"<(?:img|script|iframe|source|video|audio|link)\b[^>]*\b(?:src|href)\s*=\s*[\"']http://", re.IGNORECASE)
# Avisos de SEO y buenas prácticas añadidos en la 1.5.0: informan, pero no bajan la nota (así el histórico es comparable).
AVISOS_SIN_PUNTOS = frozenset({"sin-title", "sin-viewport", "sin-og-title", "sin-canonical", "contenido-mixto"})


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
    cuerpo = ""
    icono_en_html = None
    peso = None
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
            else:  # primera impresión al compartir el enlace
                if not _META_DESCRIPCION.search(cuerpo):
                    avisos.append("sin-meta-description")
                if not _OG_IMAGE.search(cuerpo):
                    avisos.append("sin-og-image")
                if not _LANG.search(cuerpo):
                    avisos.append("sin-lang")
                if _titulo(cuerpo) is None:
                    avisos.append("sin-title")
                if not _VIEWPORT.search(cuerpo):
                    avisos.append("sin-viewport")
                if not _OG_TITLE.search(cuerpo):
                    avisos.append("sin-og-title")
                if not _CANONICAL.search(cuerpo):
                    avisos.append("sin-canonical")
                if url.startswith("https://") and _MIXTO.search(cuerpo):
                    avisos.append("contenido-mixto")
                if any(not _ALT.search(img) for img in _IMG.findall(cuerpo)):
                    avisos.append("imagenes-sin-alt")
                icono_en_html = _ICONO.search(cuerpo) is not None
            try:
                peso = int((getattr(response, "headers", None) or {}).get("Content-Length", ""))
            except (TypeError, ValueError):
                peso = None
            if peso is not None and peso > UMBRAL_PESO_BYTES:
                avisos.append("pagina-pesada")
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
        peso_bytes=peso, icono_en_html=icono_en_html, cuerpo=cuerpo or None,
    )


def _existe(session, url: str) -> Optional[bool]:
    """True/False según responda 200; ``None`` si no se pudo comprobar."""
    try:
        respuesta = session.get(url, allow_redirects=True, stream=True)
        existe = respuesta.status_code == 200
        respuesta.close()
        return existe
    except requests.RequestException:
        return None


def profundizar(session, salud: PagesHealth, comprobar_enlaces: bool = False) -> None:
    """Comprobaciones extra de una web que ya responde bien.

    TLS, ``404.html``, ``sitemap.xml``, ``robots.txt``, favicon, DNS del dominio propio y, si se pide,
    enlaces rotos. Solo añade avisos (nunca marca la web como rota) y nunca lanza excepciones de red.
    """
    cuerpo, salud.cuerpo = salud.cuerpo, None  # no conservar el HTML en memoria
    if not salud.ok:
        return
    base = salud.url_final or salud.url
    partes = urlparse(base)
    if partes.scheme == "https" and partes.hostname:
        salud.tls_dias = tls.dias_restantes(partes.hostname)
        if salud.tls_dias is not None and salud.tls_dias < UMBRAL_TLS_DIAS:
            salud.avisos.append("tls-caduca-pronto")
    if partes.hostname and not partes.hostname.endswith(".github.io") and dns.apunta_a_github(partes.hostname) is False:
        salud.avisos.append("dns-no-apunta-a-github")
    raiz = base if base.endswith("/") else base + "/"
    for archivo, aviso in (("404.html", "sin-404-personalizada"), ("sitemap.xml", "sin-sitemap"),
                           ("robots.txt", "sin-robots")):
        if _existe(session, raiz + archivo) is False:
            salud.avisos.append(aviso)
    if salud.icono_en_html is False and _existe(session, raiz + "favicon.ico") is False:
        salud.avisos.append("sin-favicon")
    if comprobar_enlaces and cuerpo:
        salud.enlaces_rotos = linkcheck.enlaces_rotos(session, cuerpo, raiz)
        if salud.enlaces_rotos:
            salud.avisos.append("enlaces-rotos")
