from dataclasses import dataclass, field
from typing import Dict, List, Optional

ESTADO_OK = "ok"        # la web responde y parece una página real
ESTADO_ROTA = "roto"    # se esperaba una web (Pages activadas) pero falla
ESTADO_NINGUNA = "ninguna"  # no hay Pages (o no se pueden afirmar)
ESTADO_CONSTRUYENDO = "construyendo"  # GitHub está reconstruyendo las Pages: no se marca como rota


@dataclass
class PagesHealth:
    """Resultado de inspeccionar una URL de GitHub Pages."""

    estado: str
    url: str
    url_final: Optional[str] = None
    http_status: Optional[int] = None
    ms: Optional[int] = None
    titulo: Optional[str] = None
    problemas: List[str] = field(default_factory=list)  # errores: la página está rota
    avisos: List[str] = field(default_factory=list)     # avisos: funciona pero mejorable
    tls_dias: Optional[int] = None  # días hasta que caduca el certificado (None = no comprobado)
    enlaces_rotos: Optional[List[str]] = None  # solo con --check-links (None = no comprobado)
    paginas_rotas: Optional[List[str]] = None  # solo con --crawl (None = no comprobado)
    peso_bytes: Optional[int] = None  # tamaño del HTML de la portada (Content-Length)
    icono_en_html: Optional[bool] = field(default=None, repr=False)  # uso interno
    cuerpo: Optional[str] = field(default=None, repr=False)  # uso interno: se descarta en profundizar()

    @property
    def ok(self) -> bool:
        return self.estado == ESTADO_OK


@dataclass
class RepoInfo:
    """Resultado de auditar un repositorio.

    ``tiene_descripcion``, ``es_fork`` y ``esta_archivado`` valen ``None`` cuando
    no se han podido determinar (no se listan en el informe).
    """

    nombre: str
    tiene_pages: bool = False
    url_pages: Optional[str] = None
    tiene_releases: bool = False
    tiene_readme: bool = False
    tiene_licencia: bool = False
    tiene_gitignore: bool = False
    tiene_descripcion: Optional[bool] = None
    es_fork: Optional[bool] = None
    esta_archivado: Optional[bool] = None
    descripcion: Optional[str] = None
    pages_salud: Optional[PagesHealth] = None
    error: Optional[str] = None
    # Datos del repositorio (modo API; ``None`` = no disponible, p. ej. en modo web).
    estrellas: Optional[int] = None
    forks_count: Optional[int] = None
    issues_abiertas: Optional[int] = None
    lenguaje: Optional[str] = None
    topics: Optional[List[str]] = None
    licencia_spdx: Optional[str] = None
    creado: Optional[str] = None
    ultimo_push: Optional[str] = None
    homepage: Optional[str] = None  # "" = vacío; None = desconocido
    # Última release (feed Atom: funciona con y sin token).
    ultima_release: Optional[str] = None
    fecha_release: Optional[str] = None
    # Ficheros de comunidad (modo API; ``None`` = no se pudo comprobar).
    tiene_security: Optional[bool] = None
    tiene_contributing: Optional[bool] = None
    tiene_code_of_conduct: Optional[bool] = None
    tiene_issue_template: Optional[bool] = None
    # Datos de --deep (modo API; ``None`` = no disponible o sin permisos).
    privado: Optional[bool] = None
    rama_defecto: Optional[str] = None
    tiene_ci: Optional[bool] = None            # hay workflows en .github/workflows
    tiene_dependabot_yml: Optional[bool] = None
    alertas_dependabot: Optional[bool] = None  # alertas de vulnerabilidades activadas
    secret_scanning: Optional[bool] = None
    rama_protegida: Optional[bool] = None
    contribuidores: Optional[int] = None
    prs_abiertas: Optional[int] = None
    ci_estado: Optional[str] = None            # success | failure | otro
    puntuacion: Optional[int] = None           # 0-100 (ver score.py)
    # 1.5.0
    alertas_criticas: Optional[int] = None     # alertas abiertas de Dependabot de gravedad crítica
    alertas_altas: Optional[int] = None        # ... y de gravedad alta
    scorecard: Optional[float] = None          # OpenSSF Scorecard 0-10 (--scorecard)
    readme_problemas: Optional[List[str]] = None  # --readme-quality: readme-corto, sin-instalacion, sin-uso
    deps_copyleft: Optional[List[str]] = None     # --dep-licenses: dependencias GPL/AGPL (None = no comprobado)
    propietario: Optional[str] = None  # solo con varias cuentas: de quién es el repo (nombre = "cuenta/repo")
    heredados: Optional[List[str]] = None      # ficheros de comunidad heredados de <usuario>/.github
    custom: Optional[Dict[str, bool]] = None   # reglas propias: id -> el archivo existe (None = no comprobado)

    @property
    def pages_rota(self) -> bool:
        return self.pages_salud is not None and self.pages_salud.estado == ESTADO_ROTA

    @property
    def pages_viva(self) -> bool:
        if not self.tiene_pages or not self.url_pages:
            return False
        return self.pages_salud is None or self.pages_salud.ok or self.pages_salud.estado == ESTADO_CONSTRUYENDO


def ruta_github(repo: "RepoInfo", usuario: str) -> str:
    """``cuenta/repo`` para construir enlaces (con varias cuentas el nombre ya la incluye)."""
    return repo.nombre if repo.propietario else f"{usuario}/{repo.nombre}"


@dataclass
class AuditReport:
    usuario: str
    dominio_base: str
    proveedor: str
    repos: List[RepoInfo] = field(default_factory=list)
    modo: str = "web"  # "api" | "web" (identificador estable para el JSON)
    cache_aciertos: Optional[int] = None    # --cache: peticiones respondidas con 304 (no gastan cuota)
    cache_peticiones: Optional[int] = None  # --cache: peticiones a la API que pasaron por la caché
    puntuacion: Optional[int] = None  # nota global 0-100 (ver score.py)

    @property
    def total_repos(self) -> int:
        return len(self.repos)

    @property
    def _analizados(self) -> List[RepoInfo]:
        """Repos sin error: de un repo que falló no se puede afirmar nada."""
        return [r for r in self.repos if not r.error]

    @property
    def con_error(self) -> List[RepoInfo]:
        return [r for r in self.repos if r.error]

    @property
    def con_pages(self) -> List[RepoInfo]:
        return [r for r in self._analizados if r.pages_viva]

    @property
    def pages_con_avisos(self) -> List[RepoInfo]:
        return [r for r in self._analizados if r.pages_viva and r.pages_salud and r.pages_salud.avisos]

    @property
    def pages_rotas(self) -> List[RepoInfo]:
        return [r for r in self._analizados if r.pages_rota]

    @property
    def con_releases(self) -> List[RepoInfo]:
        return [r for r in self._analizados if r.tiene_releases]

    @property
    def sin_nada(self) -> List[RepoInfo]:
        return [r for r in self._analizados if not r.tiene_pages and not r.tiene_releases]

    @property
    def sin_readme(self) -> List[RepoInfo]:
        return [r for r in self._analizados if not r.tiene_readme]

    @property
    def sin_licencia(self) -> List[RepoInfo]:
        return [r for r in self._analizados if not r.tiene_licencia]

    @property
    def sin_gitignore(self) -> List[RepoInfo]:
        return [r for r in self._analizados if not r.tiene_gitignore]

    @property
    def sin_descripcion(self) -> List[RepoInfo]:
        return [r for r in self._analizados if r.tiene_descripcion is False]

    @property
    def forks(self) -> List[RepoInfo]:
        return [r for r in self._analizados if r.es_fork]

    @property
    def archivados(self) -> List[RepoInfo]:
        return [r for r in self._analizados if r.esta_archivado]
