from dataclasses import dataclass, field
from typing import List, Optional


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
    error: Optional[str] = None


@dataclass
class AuditReport:
    usuario: str
    dominio_base: str
    proveedor: str
    repos: List[RepoInfo] = field(default_factory=list)

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
        return [r for r in self._analizados if r.tiene_pages]

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
