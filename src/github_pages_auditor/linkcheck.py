"""``--check-links``: enlaces rotos de la portada de una web (con límite y sin lanzar excepciones)."""
import re
from typing import Dict, List, Optional
from urllib.parse import urldefrag, urljoin

import requests

MAX_ENLACES = 50
# Códigos que suelen significar «bloquea a los bots», no «roto».
NO_CONCLUYENTES = {401, 403, 405, 429, 999}
_A_HREF = re.compile(r"<a\b[^>]*?\bhref\s*=\s*[\"']([^\"'#][^\"']*)[\"']", re.IGNORECASE)
_cache: Dict[str, Optional[int]] = {}


def extraer_enlaces(cuerpo: str, base: str) -> List[str]:
    vistos: Dict[str, None] = {}
    for href in _A_HREF.findall(cuerpo or ""):
        url = urldefrag(urljoin(base, href.strip()))[0]
        if url.startswith(("http://", "https://")):
            vistos.setdefault(url)
    return list(vistos)[:MAX_ENLACES]


def _estado(session, url: str) -> Optional[int]:
    if url in _cache:
        return _cache[url]
    try:
        r = session.head(url, allow_redirects=True)
        if r.status_code in (403, 405, 501):
            r = session.get(url, allow_redirects=True, stream=True)
        codigo: Optional[int] = r.status_code
        r.close()
    except requests.RequestException:
        codigo = None
    _cache[url] = codigo
    return codigo


def enlaces_rotos(session, cuerpo: str, base: str) -> List[str]:
    """Lista ``"url (código|sin-respuesta)"`` de los enlaces que fallan de forma concluyente."""
    rotos = []
    for url in extraer_enlaces(cuerpo, base):
        codigo = _estado(session, url)
        if codigo is None:
            rotos.append(f"{url} (sin-respuesta)")
        elif codigo >= 400 and codigo not in NO_CONCLUYENTES:
            rotos.append(f"{url} ({codigo})")
    return rotos
