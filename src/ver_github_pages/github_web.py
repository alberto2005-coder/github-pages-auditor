"""Proveedor SIN token: páginas públicas de GitHub (HTML, raw y feeds Atom).

Es un modo de "mejor esfuerzo": depende del marcado público de GitHub, que puede
cambiar. Para resultados más fiables usa la API con token.
"""
import re
from typing import Any, Dict, List

import requests

from . import pages
from .errors import ErrorAuditoria, LimiteDeTasa, UsuarioNoEncontrado
from .models import RepoInfo

URL = "https://github.com"
RAW = "https://raw.githubusercontent.com"
MAX_PAGINAS = 100
CANDIDATOS_README = ("README.md", "README", "README.rst", "README.txt", "readme.md")
CANDIDATOS_LICENCIA = ("LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING")


def parsear_listado(html: str, usuario: str) -> List[Dict[str, Any]]:
    """Extrae los repos de una página del perfil con descripción/fork/archivado.

    Si no se reconoce el marcado por repositorio, devuelve solo los nombres con
    los metadatos a ``None`` (desconocidos).
    """
    patron = re.compile(
        r'href="/' + re.escape(usuario) + r'/([^"/?#]+)"[^>]*itemprop="name codeRepository"',
        re.IGNORECASE,
    )
    repos: List[Dict[str, Any]] = []
    for bloque in re.split(r'<li\b[^>]*itemprop="owns"', html)[1:]:
        m = patron.search(bloque)
        if m:
            repos.append({
                "nombre": m.group(1),
                "descripcion": 'itemprop="description"' in bloque,
                "fork": "Forked from" in bloque,
                "archivado": re.search(r">\s*Archived\s*<", bloque) is not None,
            })
    if repos:
        return repos
    return [
        {"nombre": n, "descripcion": None, "fork": None, "archivado": None}
        for n in dict.fromkeys(patron.findall(html))
    ]


class GitHubWebProvider:
    def __init__(self, usuario: str, dominio: str, session: requests.Session):
        self.usuario = usuario
        self.dominio = dominio
        self.session = session

    def obtener_repositorios(self, on_progress=None) -> List[RepoInfo]:
        vistos: Dict[str, Dict[str, Any]] = {}
        for page in range(1, MAX_PAGINAS + 1):
            if on_progress:
                on_progress(page, len(vistos))
            res = self.session.get(f"{URL}/{self.usuario}", params={"page": page, "tab": "repositories"})
            if res.status_code == 404 and page == 1:
                raise UsuarioNoEncontrado(f"El usuario '{self.usuario}' no existe.")
            if res.status_code == 429:
                raise LimiteDeTasa("GitHub limitó las peticiones (429). Prueba más tarde o usa un token (-k).")
            if res.status_code != 200:
                if page == 1:
                    raise ErrorAuditoria(f"GitHub respondió {res.status_code} al listar los repositorios.")
                break
            nuevos = [x for x in parsear_listado(res.text, self.usuario) if x["nombre"] not in vistos]
            if not nuevos:
                break
            for x in nuevos:
                vistos[x["nombre"]] = x

        return [
            RepoInfo(
                nombre=x["nombre"],
                tiene_descripcion=x["descripcion"],
                es_fork=x["fork"],
                esta_archivado=x["archivado"],
            )
            for x in vistos.values()
        ]

    def _existe(self, url: str) -> bool:
        return self.session.head(url, allow_redirects=True).status_code == 200

    def enriquecer_repo(self, repo: RepoInfo) -> RepoInfo:
        atom = self.session.get(f"{URL}/{self.usuario}/{repo.nombre}/releases.atom")
        repo.tiene_releases = atom.status_code == 200 and "<entry>" in atom.text

        raw = f"{RAW}/{self.usuario}/{repo.nombre}/HEAD/"
        repo.tiene_readme = any(self._existe(raw + f) for f in CANDIDATOS_README)
        repo.tiene_licencia = any(self._existe(raw + f) for f in CANDIDATOS_LICENCIA)
        repo.tiene_gitignore = self._existe(raw + ".gitignore")

        # La comprobación de Pages se hace aquí (en paralelo), no al listar.
        url = pages.construir_url_pages(self.usuario, repo.nombre, self.dominio)
        repo.url_pages = pages.resolver_pages(self.session, url)
        repo.tiene_pages = repo.url_pages is not None
        return repo
