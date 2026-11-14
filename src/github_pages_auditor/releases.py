"""Lectura de la última release a partir del feed Atom público (``releases.atom``)."""
import re
from typing import Optional, Tuple
from urllib.parse import unquote

_ENTRADA = re.compile(r"<entry>(.*?)</entry>", re.DOTALL)
_TAG = re.compile(r'<link[^>]*href="[^"]*/releases/tag/([^"]+)"')
_FECHA = re.compile(r"<updated>\s*([^<\s]+)\s*</updated>")


def parsear_ultima_release(atom: str) -> Tuple[Optional[str], Optional[str]]:
    """Devuelve ``(tag, fecha ISO)`` de la primera entrada del feed, o ``(None, None)``."""
    entrada = _ENTRADA.search(atom or "")
    if not entrada:
        return None, None
    cuerpo = entrada.group(1)
    tag = _TAG.search(cuerpo)
    fecha = _FECHA.search(cuerpo)
    return (unquote(tag.group(1)) if tag else None), (fecha.group(1) if fecha else None)
