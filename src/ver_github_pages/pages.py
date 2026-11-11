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


def comprobar_pages(session: requests.Session, url: str) -> bool:
    """True si la URL responde 200 sin acabar redirigida a otro dominio."""
    try:
        response = session.get(url, allow_redirects=True, stream=True)
    except requests.RequestException:
        return False
    try:
        final = getattr(response, "url", None) or url
        mismo_host = urlparse(final).netloc.lower() == urlparse(url).netloc.lower()
        return response.status_code == 200 and mismo_host
    finally:
        response.close()
