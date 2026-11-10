import requests
from typing import List
from .models import RepoInfo
from . import pages

class GitHubAPIProvider:
    def __init__(self, usuario: str, dominio: str, session: requests.Session):
        self.usuario = usuario
        self.dominio = dominio
        self.session = session

    def obtener_repositorios(self) -> List[RepoInfo]:
        repos: List[RepoInfo] = []
        page = 1
        
        while True:
            url = f"https://api.github.com/users/{self.usuario}/repos?per_page=100&page={page}"
            res = self.session.get(url)
            
            if res.status_code != 200:
                break
                
            data = res.json()
            if not data or not isinstance(data, list):
                break
                
            for raw in data:
                nombre = raw.get("name")
                if not nombre:
                    continue

                url_pages = pages.construir_url_pages(self.usuario, nombre, self.dominio)
                tiene_pages = raw.get("has_pages", False)

                repo = RepoInfo(
                    nombre=nombre,
                    tiene_pages=tiene_pages,
                    url_pages=url_pages if tiene_pages else None,
                    tiene_licencia=raw.get("license") is not None,
                    tiene_descripcion=bool(raw.get("description")),
                    es_fork=raw.get("fork", False),
                    esta_archivado=raw.get("archived", False)
                )
                repos.append(repo)

            if len(data) < 100:
                break
            page += 1

        return repos

    def enriquecer_repo(self, repo: RepoInfo) -> RepoInfo:
        # Check releases via Atom feed
        atom_url = f"https://github.com/{self.usuario}/{repo.nombre}/releases.atom"
        try:
            r_atom = self.session.get(atom_url, timeout=5)
            repo.tiene_releases = (r_atom.status_code == 200) and ("<entry>" in r_atom.text)
        except Exception:
            repo.tiene_releases = False

        # Check README & .gitignore via raw content
        try:
            raw_readme = f"https://raw.githubusercontent.com/{self.usuario}/{repo.nombre}/HEAD/README.md"
            r_rm = self.session.head(raw_readme, timeout=3)
            repo.tiene_readme = (r_rm.status_code == 200)
        except Exception:
            repo.tiene_readme = False

        try:
            raw_gi = f"https://raw.githubusercontent.com/{self.usuario}/{repo.nombre}/HEAD/.gitignore"
            r_gi = self.session.head(raw_gi, timeout=3)
            repo.tiene_gitignore = (r_gi.status_code == 200)
        except Exception:
            repo.tiene_gitignore = False

        return repo