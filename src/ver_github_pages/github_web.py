import re
import requests
from typing import List
from .models import RepoInfo
from . import pages

class GitHubWebProvider:
    def __init__(self, usuario: str, dominio: str, session: requests.Session):
        self.usuario = usuario
        self.dominio = dominio
        self.session = session

    def obtener_repositorios(self) -> List[RepoInfo]:
        nombres = []
        page = 1
        headers = {"Accept": "text/html"}

        while True:
            url = f"https://github.com/{self.usuario}?page={page}&tab=repositories"
            res = self.session.get(url, headers=headers)
            
            if res.status_code != 200:
                break

            bloques = re.findall(
                r'href="/' + re.escape(self.usuario) + r'/([^"/]+)"\s+itemprop="name codeRepository"',
                res.text
            )
            if not bloques:
                break

            for nombre in bloques:
                if nombre not in nombres:
                    nombres.append(nombre)
            page += 1

        repos = []
        for nombre in nombres:
            url_pages = pages.construir_url_pages(self.usuario, nombre, self.dominio)
            tiene_pages = pages.comprobar_pages(self.session, url_pages)
            repos.append(RepoInfo(
                nombre=nombre,
                tiene_pages=tiene_pages,
                url_pages=url_pages if tiene_pages else None
            ))
        return repos

    def enriquecer_repo(self, repo: RepoInfo) -> RepoInfo:
        # Releases
        atom_url = f"https://github.com/{self.usuario}/{repo.nombre}/releases.atom"
        try:
            res_atom = self.session.get(atom_url, timeout=5)
            repo.tiene_releases = (res_atom.status_code == 200) and ("<entry>" in res_atom.text)
        except Exception:
            repo.tiene_releases = False

        # HTML Inspect
        repo_url = f"https://github.com/{self.usuario}/{repo.nombre}"
        try:
            res_repo = self.session.get(repo_url, timeout=5)
            if res_repo.status_code == 200:
                html = res_repo.text
                repo.tiene_readme = ('id="readme"' in html or 'README.md' in html)
                repo.tiene_licencia = ('LICENSE' in html or 'License' in html)
                repo.tiene_gitignore = ('.gitignore' in html)
                repo.tiene_descripcion = ('No description, website, or topics provided.' not in html)
                repo.es_fork = ('forked from' in html)
                repo.esta_archivado = ('This repository has been archived' in html)
        except Exception:
            pass

        return repo