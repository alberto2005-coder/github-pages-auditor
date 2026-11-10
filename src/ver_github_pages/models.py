from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class RepoInfo:
    nombre: str
    tiene_pages: bool = False
    url_pages: Optional[str] = None
    tiene_releases: bool = False
    tiene_readme: bool = False
    tiene_licencia: bool = False
    tiene_gitignore: bool = False
    tiene_descripcion: bool = False
    es_fork: bool = False
    esta_archivado: bool = False

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
    def con_pages(self) -> List[RepoInfo]:
        return [r for r in self.repos if r.tiene_pages]

    @property
    def con_releases(self) -> List[RepoInfo]:
        return [r for r in self.repos if r.tiene_releases]

    @property
    def sin_nada(self) -> List[RepoInfo]:
        return [r for r in self.repos if not r.tiene_pages and not r.tiene_releases]

    @property
    def sin_readme(self) -> List[RepoInfo]:
        return [r for r in self.repos if not r.tiene_readme]

    @property
    def sin_licencia(self) -> List[RepoInfo]:
        return [r for r in self.repos if not r.tiene_licencia]

    @property
    def sin_gitignore(self) -> List[RepoInfo]:
        return [r for r in self.repos if not r.tiene_gitignore]

    @property
    def sin_descripcion(self) -> List[RepoInfo]:
        return [r for r in self.repos if not r.tiene_descripcion]

    @property
    def forks(self) -> List[RepoInfo]:
        return [r for r in self.repos if r.es_fork]

    @property
    def archivados(self) -> List[RepoInfo]:
        return [r for r in self.repos if r.esta_archivado]