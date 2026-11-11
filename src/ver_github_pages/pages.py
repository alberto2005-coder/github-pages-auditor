from typing import Optional
from urllib.parse import urlparse

import requests


def es_raiz(usuario: str, nombre_repo: str) -> bool:
    """Solo ``<usuario>.github.io`` es el sitio raíz.

    Un repo llamado igual que el usuario es el README del perfil, no un sitio.
    """
    return nombre_repo.lower() == f"{usuario.lower()}.github.io"


def construir_url_pages(usuario: str, nombre_repo: str, dominio_base: str) -> str:
    dominio_base = dominio_base.rstrip("/")
    if es_raiz(usuario, nombre_repo):
        return dominio_base
    return f"{dominio_base}/{nombre_repo}/"


def resolver_pages(session: requests.Session, url: str) -> Optional[str]:
    """Devuelve la URL efectiva de la página si existe, o ``None``.

    - Respuesta 200 en el mismo dominio: la URL pedida.
    - Redirección desde ``*.github.io`` a otro dominio con 200: es el dominio
      personalizado que GitHub tiene configurado en esas Pages, y se devuelve
      la URL final (así se descubre el dominio real sin indicarlo con -w).
    - Cualquier otra redirección a otro dominio se descarta (p. ej. parking).
    """
    try:
        response = session.get(url, allow_redirects=True, stream=True)
    except requests.RequestException:
        return None
    try:
        if response.status_code != 200:
            return None
        final = getattr(response, "url", None) or url
        host_pedido = urlparse(url).netloc.lower()
        host_final = urlparse(final).netloc.lower()
        if host_final == host_pedido:
            return url
        if host_pedido.endswith(".github.io"):
            return final
        return None
    finally:
        response.close()


def comprobar_pages(session: requests.Session, url: str) -> bool:
    return resolver_pages(session, url) is not None
