"""Proveedor CON token: API REST oficial de GitHub (5.000 peticiones/hora)."""
from typing import List, Optional

import requests

from . import pages, pages_health
from .errors import ErrorAuditoria, LimiteDeTasa, TokenInvalido, UsuarioNoEncontrado
from .models import ESTADO_ROTA, RepoInfo
from .releases import parsear_ultima_release

API = "https://api.github.com"
POR_PAGINA = 100
MAX_PAGINAS = 100
PREFIJOS_LICENCIA = ("license", "licence", "copying")
# atributo de RepoInfo -> (nombre base del fichero, carpetas donde GitHub también lo reconoce)
FICHEROS_COMUNIDAD = {
    "tiene_security": ("security", (".github", "docs")),
    "tiene_contributing": ("contributing", (".github", "docs")),
    "tiene_code_of_conduct": ("code_of_conduct", (".github", "docs")),
    "tiene_issue_template": ("issue_template", (".github",)),
}


def _misma_url(a: str, b: str) -> bool:
    """Compara dos URL ignorando esquema, ``www.``, mayúsculas y barra final."""
    def norm(u: str) -> str:
        u = u.strip().lower().split("://", 1)[-1]
        return u[4:] if u.startswith("www.") else u
    return norm(a).rstrip("/") == norm(b).rstrip("/")


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
                licencia = raw.get("license")
                repos.append(RepoInfo(
                    nombre=nombre,
                    tiene_pages=tiene_pages,
                    url_pages=pages.construir_url_pages(self.usuario, nombre, self.dominio) if tiene_pages else None,
                    tiene_licencia=raw.get("license") is not None,
                    tiene_descripcion=bool((raw.get("description") or "").strip()),
                    descripcion=(raw.get("description") or "").strip() or None,
                    es_fork=bool(raw.get("fork", False)),
                    esta_archivado=bool(raw.get("archived", False)),
                    estrellas=raw.get("stargazers_count"),
                    forks_count=raw.get("forks_count"),
                    issues_abiertas=raw.get("open_issues_count"),
                    lenguaje=raw.get("language"),
                    topics=list(raw.get("topics") or []) if "topics" in raw else None,
                    licencia_spdx=licencia.get("spdx_id") if isinstance(licencia, dict) else None,
                    creado=raw.get("created_at"),
                    ultimo_push=raw.get("pushed_at"),
                    homepage=(raw.get("homepage") or "").strip() if "homepage" in raw else None,
                ))
            if len(data) < POR_PAGINA:
                break
        return repos

    def _nombres(self, nombre: str, carpeta: str = "") -> List[str]:
        res = self._get(f"/repos/{self.usuario}/{nombre}/contents/{carpeta}")
        if res.status_code != 200:  # 404 = repositorio vacío o carpeta inexistente
            return []
        datos = res.json()
        return [f.get("name", "").lower() for f in datos] if isinstance(datos, list) else []

    def _archivos_raiz(self, nombre: str) -> List[str]:
        return self._nombres(nombre)

    def _comunidad(self, repo: RepoInfo, raiz: List[str]) -> None:
        """SECURITY, CONTRIBUTING, CODE_OF_CONDUCT e issue templates: raíz, ``.github/`` o ``docs/``.

        Solo se pide el contenido de ``.github``/``docs`` si existe y aún falta algún fichero.
        """
        contenidos = {"": set(raiz)}

        def en(carpeta: str) -> set:
            if carpeta not in contenidos:
                contenidos[carpeta] = set(self._nombres(repo.nombre, carpeta)) if carpeta in raiz else set()
            return contenidos[carpeta]

        def coincide(nombres: set, base: str) -> bool:
            return any(n == base or n.startswith(base + ".") for n in nombres)

        for atributo, (base, carpetas) in FICHEROS_COMUNIDAD.items():
            encontrado = coincide(contenidos[""], base)
            for carpeta in carpetas:
                if encontrado:
                    break
                encontrado = coincide(en(carpeta), base)
            setattr(repo, atributo, encontrado)

    def enriquecer_repo(self, repo: RepoInfo) -> RepoInfo:
        # Releases vía feed Atom: no consume cuota de la API.
        atom = self.session.get(f"https://github.com/{self.usuario}/{repo.nombre}/releases.atom")
        repo.tiene_releases = atom.status_code == 200 and "<entry>" in atom.text
        if repo.tiene_releases:
            repo.ultima_release, repo.fecha_release = parsear_ultima_release(atom.text)

        # README, LICENSE y .gitignore con una sola llamada al contenido raíz.
        archivos = self._archivos_raiz(repo.nombre)
        repo.tiene_readme = any(n.startswith("readme") for n in archivos)
        repo.tiene_gitignore = ".gitignore" in archivos
        repo.tiene_licencia = repo.tiene_licencia or any(n.startswith(PREFIJOS_LICENCIA) for n in archivos)
        self._comunidad(repo, archivos)

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
        pages_health.profundizar(self.session, salud)
        repo.pages_salud = salud
        repo.url_pages = salud.url_final or url
        if repo.homepage and repo.url_pages and not _misma_url(repo.homepage, repo.url_pages):
            salud.avisos.append("homepage-distinta")
