"""Proveedor CON token: API REST oficial de GitHub (5.000 peticiones/hora)."""
from typing import List, Optional

import requests

from . import pages, pages_health
from .errors import ErrorAuditoria, LimiteDeTasa, TokenInvalido, UsuarioNoEncontrado
from .models import ESTADO_ROTA, RepoInfo

API = "https://api.github.com"
POR_PAGINA = 100
MAX_PAGINAS = 100
PREFIJOS_LICENCIA = ("license", "licence", "copying")


class GitHubAPIProvider:
    def __init__(self, usuario: str, dominio: str, session: requests.Session, token: Optional[str] = None):
        self.usuario = usuario
        self.dominio = dominio
        self.session = session
        # El token solo se envía a api.github.com, nunca a otros hosts.
        self._headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
        if token:
            self._headers["Authorization"] = f"Bearer {token}"

    def _get(self, ruta: str, **kwargs):
        res = self.session.get(f"{API}{ruta}", headers=self._headers, **kwargs)
        if res.status_code == 401:
            raise TokenInvalido("GitHub rechazó el token (401). Comprueba que sea válido y no haya caducado.")
        if res.status_code in (403, 429):
            headers = getattr(res, "headers", {}) or {}
            if res.status_code == 429 or headers.get("X-RateLimit-Remaining") == "0" or "Retry-After" in headers:
                raise LimiteDeTasa("Se agotó el límite de la API de GitHub. Espera a que se restablezca o usa un token.")
        return res

    def obtener_repositorios(self, on_progress=None) -> List[RepoInfo]:
        repos: List[RepoInfo] = []
        for page in range(1, MAX_PAGINAS + 1):
            if on_progress:
                on_progress(page, len(repos))
            res = self._get(f"/users/{self.usuario}/repos", params={"per_page": POR_PAGINA, "page": page})
            if res.status_code == 404:
                raise UsuarioNoEncontrado(f"El usuario '{self.usuario}' no existe.")
            if res.status_code != 200:
                raise ErrorAuditoria(f"La API de GitHub respondió {res.status_code} al listar los repositorios.")

            data = res.json()
            if not isinstance(data, list):
                break
            for raw in data:
                nombre = raw.get("name")
                if not nombre:
                    continue
                tiene_pages = bool(raw.get("has_pages", False))
                repos.append(RepoInfo(
                    nombre=nombre,
                    tiene_pages=tiene_pages,
                    url_pages=pages.construir_url_pages(self.usuario, nombre, self.dominio) if tiene_pages else None,
                    tiene_licencia=raw.get("license") is not None,
                    tiene_descripcion=bool((raw.get("description") or "").strip()),
                    descripcion=(raw.get("description") or "").strip() or None,
                    es_fork=bool(raw.get("fork", False)),
                    esta_archivado=bool(raw.get("archived", False)),
                ))
            if len(data) < POR_PAGINA:
                break
        return repos

    def _archivos_raiz(self, nombre: str) -> List[str]:
        res = self._get(f"/repos/{self.usuario}/{nombre}/contents/")
        if res.status_code != 200:  # 404 = repositorio vacío
            return []
        datos = res.json()
        return [f.get("name", "").lower() for f in datos] if isinstance(datos, list) else []

    def enriquecer_repo(self, repo: RepoInfo) -> RepoInfo:
        # Releases vía feed Atom: no consume cuota de la API.
        atom = self.session.get(f"https://github.com/{self.usuario}/{repo.nombre}/releases.atom")
        repo.tiene_releases = atom.status_code == 200 and "<entry>" in atom.text

        # README, LICENSE y .gitignore con una sola llamada al contenido raíz.
        archivos = self._archivos_raiz(repo.nombre)
        repo.tiene_readme = any(n.startswith("readme") for n in archivos)
        repo.tiene_gitignore = ".gitignore" in archivos
        repo.tiene_licencia = repo.tiene_licencia or any(n.startswith(PREFIJOS_LICENCIA) for n in archivos)

        if repo.tiene_pages:
            self._comprobar_pages(repo)
        return repo

    def _datos_pages(self, nombre: str) -> Optional[dict]:
        res = self._get(f"/repos/{self.usuario}/{nombre}/pages")
        if res.status_code != 200:
            return None
        datos = res.json()
        return datos if isinstance(datos, dict) else None

    def _comprobar_pages(self, repo: RepoInfo) -> None:
        """Pages activadas según la API: aquí cualquier fallo de la web es una Pages ROTA."""
        datos = self._datos_pages(repo.nombre) or {}
        url = datos.get("html_url") or repo.url_pages
        if url and pages.es_raiz(self.usuario, repo.nombre):
            url = url.rstrip("/")
        salud = None
        if url and url.startswith("http://"):
            # La API devuelve http:// si HTTPS no está forzado; preferimos https si la web responde bien.
            https = "https://" + url[len("http://"):]
            candidata = pages_health.inspeccionar(self.session, https, esperada=True)
            if not candidata.problemas:
                salud, url = candidata, https
        if salud is None:
            salud = pages_health.inspeccionar(self.session, url, esperada=True)
        if datos.get("status") == "errored":
            salud.problemas.append("build-fallido")
        elif datos.get("status") == "building":
            salud.avisos.append("build-en-curso")
        if datos.get("https_enforced") is False:
            salud.avisos.append("https-no-forzado")
        if salud.problemas:
            salud.estado = ESTADO_ROTA
        repo.pages_salud = salud
        repo.url_pages = salud.url_final or url
