"""Proveedor CON token: API REST oficial de GitHub (5.000 peticiones/hora)."""
import threading
import time
from datetime import datetime, timezone
from typing import List, Optional, Sequence
from urllib.parse import quote

import requests

from . import pages, pages_health
from .errors import ErrorAuditoria, LimiteDeTasa, TokenInvalido, UsuarioNoEncontrado
from .models import ESTADO_CONSTRUYENDO, ESTADO_ROTA, RepoInfo
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


ESPERA_MAXIMA_S = 60  # si el límite se restablece en menos de esto, se espera y se reintenta una vez


def segundos_hasta_reinicio(headers, ahora: Optional[float] = None) -> Optional[float]:
    """Segundos hasta que se restablece el límite (``Retry-After`` o ``X-RateLimit-Reset``); ``None`` si no se sabe."""
    try:
        if "Retry-After" in headers:
            return max(0.0, float(headers["Retry-After"]))
        if "X-RateLimit-Reset" in headers:
            return max(0.0, float(headers["X-RateLimit-Reset"]) - (time.time() if ahora is None else ahora))
    except (TypeError, ValueError):
        return None
    return None


def _hora_reinicio(headers) -> str:
    try:
        return datetime.fromtimestamp(float(headers["X-RateLimit-Reset"]), timezone.utc).strftime("%H:%M UTC")
    except (KeyError, TypeError, ValueError, OverflowError, OSError):
        return ""


def _mensaje(res) -> str:
    try:
        datos = res.json()
        return str(datos.get("message", "")) if isinstance(datos, dict) else ""
    except ValueError:
        return ""


def _misma_url(a: str, b: str) -> bool:
    """Compara dos URL ignorando esquema, ``www.``, mayúsculas y barra final."""
    def norm(u: str) -> str:
        u = u.strip().lower().split("://", 1)[-1]
        return u[4:] if u.startswith("www.") else u
    return norm(a).rstrip("/") == norm(b).rstrip("/")


def _secret_scanning(raw: dict) -> Optional[bool]:
    seg = raw.get("security_and_analysis")
    if not isinstance(seg, dict) or not isinstance(seg.get("secret_scanning"), dict):
        return None
    return seg["secret_scanning"].get("status") == "enabled"


class GitHubAPIProvider:
    def __init__(self, usuario: str, dominio: str, session: requests.Session, token: Optional[str] = None,
                 org: bool = False, privados: bool = False, deep: bool = False, check_links: bool = False,
                 reglas_propias: Sequence[dict] = (), repo_defaults: bool = True):
        self.usuario = usuario
        self.repo_defaults = repo_defaults
        self._defaults: Optional[dict] = None
        self._defaults_lock = threading.Lock()
        self.reglas_propias = tuple(reglas_propias)
        self.org = org
        self.privados = privados
        self.deep = deep
        self.check_links = check_links
        self.dominio = dominio
        self.session = session
        # El token solo se envía a api.github.com, nunca a otros hosts.
        self._headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
        if token:
            self._headers["Authorization"] = f"Bearer {token}"

    def _get(self, ruta: str, **kwargs):
        for intento in (1, 2):
            res = self.session.get(f"{API}{ruta}", headers=self._headers, **kwargs)
            if res.status_code == 401:
                raise TokenInvalido("GitHub rechazó el token (401). Comprueba que sea válido y no haya caducado.")
            if res.status_code in (403, 429):
                headers = getattr(res, "headers", {}) or {}
                if res.status_code == 429 or headers.get("X-RateLimit-Remaining") == "0" or "Retry-After" in headers:
                    espera = segundos_hasta_reinicio(headers)
                    if intento == 1 and espera is not None and espera <= ESPERA_MAXIMA_S:
                        time.sleep(espera + 1)  # límite secundario o reinicio inminente: un solo reintento
                        continue
                    cuando = _hora_reinicio(headers)
                    raise LimiteDeTasa("Se agotó el límite de la API de GitHub"
                                       + (f" (se restablece a las {cuando})" if cuando else "")
                                       + ". Espera a que se restablezca o usa un token.")
            return res
        return res  # pragma: no cover

    def obtener_repositorios(self, on_progress=None) -> List[RepoInfo]:
        repos: List[RepoInfo] = []
        for page in range(1, MAX_PAGINAS + 1):
            if on_progress:
                on_progress(page, len(repos))
            if self.org:
                ruta, params = f"/orgs/{self.usuario}/repos", {"per_page": POR_PAGINA, "page": page, "type": "all"}
            elif self.privados:  # los repos del usuario del token, públicos y privados
                ruta, params = "/user/repos", {"per_page": POR_PAGINA, "page": page, "affiliation": "owner",
                                               "visibility": "all"}
            else:
                ruta, params = f"/users/{self.usuario}/repos", {"per_page": POR_PAGINA, "page": page}
            res = self._get(ruta, params=params)
            if res.status_code == 404:
                raise UsuarioNoEncontrado(f"{'La organización' if self.org else 'El usuario'} '{self.usuario}' no existe.")
            if res.status_code != 200:
                raise ErrorAuditoria(f"La API de GitHub respondió {res.status_code} al listar los repositorios.")

            data = res.json()
            if not isinstance(data, list):
                break
            for raw in data:
                nombre = raw.get("name")
                if not nombre:
                    continue
                if self.privados and (raw.get("owner") or {}).get("login", "").lower() != self.usuario.lower():
                    continue  # /user/repos también devuelve repos de otros con acceso
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
                    privado=raw.get("private") if "private" in raw else None,
                    rama_defecto=raw.get("default_branch"),
                    secret_scanning=_secret_scanning(raw),
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

    def _heredables(self) -> dict:
        """Ficheros de comunidad del repo ``<usuario>/.github`` (GitHub los aplica a los repos que no tienen el suyo).

        Se consulta una sola vez y solo si hace falta. ``{}`` si el repo no existe o no se puede leer.
        """
        with self._defaults_lock:
            if self._defaults is None:
                self._defaults = {}
                raiz = self._nombres(".github")
                if raiz:
                    nombres = {"": set(raiz)}
                    for carpeta in ("docs", ".github"):
                        if carpeta in raiz:
                            nombres[carpeta] = set(self._nombres(".github", carpeta))
                    for atributo, (base, carpetas) in FICHEROS_COMUNIDAD.items():
                        for carpeta in ("",) + tuple(carpetas):
                            if any(n == base or n.startswith(base + ".") for n in nombres.get(carpeta, ())):
                                self._defaults[atributo] = True
                                break
            return self._defaults

    def _heredar(self, repo: RepoInfo) -> None:
        """Marca como presentes los ficheros que faltan en el repo pero que hereda de ``.github``."""
        if not self.repo_defaults or repo.nombre.lower() == ".github":
            return
        faltan = [a for a in FICHEROS_COMUNIDAD if getattr(repo, a) is False]
        if not faltan:
            return
        defecto = self._heredables()
        heredados = [a for a in faltan if defecto.get(a)]
        for a in heredados:
            setattr(repo, a, True)
        if heredados:
            repo.heredados = [a.replace("tiene_", "") for a in heredados]

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
        self._heredar(repo)
        if self.deep:
            self._profundo(repo, archivos)
        if self.reglas_propias:
            self._propias(repo)

        if repo.tiene_pages:
            self._comprobar_pages(repo)
        return repo

    def _propias(self, repo: RepoInfo) -> None:
        """Reglas propias del TOML: ¿existe cada ruta? (``None`` si la API no responde 200/404)."""
        repo.custom = {}
        for regla in self.reglas_propias:
            res = self._get(f"/repos/{self.usuario}/{repo.nombre}/contents/{quote(regla['path'].strip('/'))}")
            if res.status_code in (200, 404):
                repo.custom[regla["id"]] = res.status_code == 200

    def _profundo(self, repo: RepoInfo, raiz: List[str]) -> None:
        """Seguridad, CI, contribuidores y PRs (``--deep``). Sin permisos el dato queda en ``None``."""
        base = f"/repos/{self.usuario}/{repo.nombre}"
        en_github = set(self._nombres(repo.nombre, ".github")) if ".github" in raiz else set()
        flujos = self._nombres(repo.nombre, ".github/workflows") if "workflows" in en_github else []
        repo.tiene_ci = any(n.endswith((".yml", ".yaml")) for n in flujos)
        repo.tiene_dependabot_yml = bool({"dependabot.yml", "dependabot.yaml"} & en_github)

        res = self._get(f"{base}/vulnerability-alerts")
        repo.alertas_dependabot = True if res.status_code == 204 else False if res.status_code == 404 else None

        if repo.rama_defecto:
            res = self._get(f"{base}/branches/{repo.rama_defecto}/protection")
            if res.status_code == 200:
                repo.rama_protegida = True
            elif res.status_code == 404 and _mensaje(res) == "Branch not protected":
                repo.rama_protegida = False  # cualquier otro 404 = sin permisos: no se afirma nada

        if repo.alertas_dependabot:  # gravedad de las alertas abiertas (necesita permiso de lectura de alertas)
            res = self._get(f"{base}/dependabot/alerts", params={"state": "open", "per_page": POR_PAGINA})
            if res.status_code == 200 and isinstance(res.json(), list):
                gravedades = [((a.get("security_advisory") or {}).get("severity") or "").lower()
                              for a in res.json() if isinstance(a, dict)]
                repo.alertas_criticas = gravedades.count("critical")
                repo.alertas_altas = gravedades.count("high")

        res = self._get(f"{base}/contributors", params={"per_page": POR_PAGINA})
        if res.status_code in (200, 204):
            datos = res.json() if res.status_code == 200 else []
            repo.contribuidores = len(datos) if isinstance(datos, list) else None
        res = self._get(f"{base}/pulls", params={"state": "open", "per_page": POR_PAGINA})
        if res.status_code == 200 and isinstance(res.json(), list):
            repo.prs_abiertas = len(res.json())
        if repo.tiene_ci and repo.rama_defecto:
            res = self._get(f"{base}/actions/runs", params={"per_page": 1, "branch": repo.rama_defecto,
                                                            "status": "completed"})
            if res.status_code == 200 and isinstance(res.json(), dict):
                ejecuciones = res.json().get("workflow_runs") or []
                if ejecuciones:
                    repo.ci_estado = ejecuciones[0].get("conclusion")

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
            salud = pages_health.inspeccionar(self.session, url or "", esperada=True)
        if datos.get("status") == "errored":
            salud.problemas.append("build-fallido")
        elif datos.get("status") == "building":
            salud.avisos.append("build-en-curso")
        if datos.get("https_enforced") is False:
            salud.avisos.append("https-no-forzado")
        if salud.problemas:
            # Justo después de un commit GitHub reconstruye las Pages y la web falla unos segundos: no es "rota".
            salud.estado = ESTADO_CONSTRUYENDO if datos.get("status") == "building" else ESTADO_ROTA
        pages_health.profundizar(self.session, salud, comprobar_enlaces=self.check_links)
        repo.pages_salud = salud
        repo.url_pages = salud.url_final or url
        if repo.homepage and repo.url_pages and not _misma_url(repo.homepage, repo.url_pages):
            salud.avisos.append("homepage-distinta")
