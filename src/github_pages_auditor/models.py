from dataclasses import dataclass, field
from typing import List, Optional

ESTADO_OK = "ok"        # la web responde y parece una página real
ESTADO_ROTA = "roto"    # se esperaba una web (Pages activadas) pero falla
ESTADO_NINGUNA = "ninguna"  # no hay Pages (o no se pueden afirmar)


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

    @property
    def pages_rota(self) -> bool:
        return self.pages_salud is not None and self.pages_salud.estado == ESTADO_ROTA

    @property
    def pages_viva(self) -> bool:
        if not self.tiene_pages or not self.url_pages:
            return False
        return self.pages_salud is None or self.pages_salud.ok


@dataclass
class AuditReport:
    usuario: str
    dominio_base: str
    proveedor: str
    repos: List[RepoInfo] = field(default_factory=list)
    modo: str = "web"  # "api" | "web" (identificador estable para el JSON)

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
