import time

import pytest
import requests
from rich.console import Console

from github_pages_auditor import audit
from github_pages_auditor.config import Config
from github_pages_auditor.errors import ErrorAuditoria, LimiteDeTasa
from github_pages_auditor.github_api import GitHubAPIProvider
from github_pages_auditor.github_web import GitHubWebProvider
from github_pages_auditor.models import RepoInfo


def cfg(**kw):
    base = dict(usuario="ana", dominio_web="https://ana.dev", github_token=None, archivo_salida="x.txt",
                max_workers=4, forzar_web=False, sin_color=True)
    base.update(kw)
    return Config(**base)


def test_proveedor_segun_token():
    assert isinstance(audit.crear_proveedor(cfg(), None)[0], GitHubWebProvider)
    assert isinstance(audit.crear_proveedor(cfg(github_token="t"), None)[0], GitHubAPIProvider)
    assert isinstance(audit.crear_proveedor(cfg(github_token="t", forzar_web=True), None)[0], GitHubWebProvider)


class Falso:
    def __init__(self, nombres, falla=(), global_error=None):
        self.nombres, self.falla, self.global_error = nombres, set(falla), global_error

    def obtener_repositorios(self, on_progress=None):
        return [RepoInfo(n) for n in self.nombres]

    def enriquecer_repo(self, repo):
        if repo.nombre in self.falla:
            raise requests.ConnectionError("sin red")
        if self.global_error and repo.nombre == self.nombres[-1]:
            raise self.global_error
        time.sleep(0.03 if repo.nombre == "a" else 0)  # el primero termina el último
        repo.tiene_readme = True
        return repo


def ejecutar(monkeypatch, falso, **kw):
    monkeypatch.setattr(audit, "crear_proveedor", lambda c, s: (falso, "Falso"))
    return audit.ejecutar_auditoria(cfg(**kw), session=object(), console=Console(quiet=True))


def test_orden_determinista_aunque_terminen_desordenados(monkeypatch):
    informe = ejecutar(monkeypatch, Falso(list("abcdef")))
    assert [r.nombre for r in informe.repos] == list("abcdef")


def test_un_fallo_de_red_no_tumba_el_resto(monkeypatch):
    informe = ejecutar(monkeypatch, Falso(["a", "b", "c"], falla={"b"}))
    assert [bool(r.error) for r in informe.repos] == [False, True, False]
    assert [r.nombre for r in informe.con_error] == ["b"]
    assert "b" not in [r.nombre for r in informe.sin_readme]  # un repo fallido no cuenta como "sin README"


def test_error_global_se_propaga(monkeypatch):
    with pytest.raises(LimiteDeTasa):
        ejecutar(monkeypatch, Falso(list("abc"), global_error=LimiteDeTasa("tope")))


def test_error_de_red_al_listar_se_convierte_en_error_de_auditoria(monkeypatch):
    class Roto:
        def obtener_repositorios(self, on_progress=None):
            raise requests.ConnectionError("dns")

    with pytest.raises(ErrorAuditoria):
        ejecutar(monkeypatch, Roto())


def test_sin_repos_devuelve_informe_vacio(monkeypatch):
    assert ejecutar(monkeypatch, Falso([])).repos == []


def test_filtros_de_forks_y_archivados_se_aplican_antes_de_analizar(monkeypatch):
    analizados = []

    class P:
        def obtener_repositorios(self, on_progress=None):
            return [RepoInfo("propio", es_fork=False, esta_archivado=False),
                    RepoInfo("fork", es_fork=True), RepoInfo("viejo", esta_archivado=True)]

        def enriquecer_repo(self, repo):
            analizados.append(repo.nombre)
            return repo

    monkeypatch.setattr(audit, "crear_proveedor", lambda c, s: (P(), "P"))
    informe = audit.ejecutar_auditoria(cfg(excluir_forks=True, excluir_archivados=True), session=object(),
                                       console=Console(quiet=True))
    assert analizados == ["propio"] and [r.nombre for r in informe.repos] == ["propio"]


def test_el_modo_queda_registrado(monkeypatch):
    monkeypatch.setattr(audit, "crear_proveedor", lambda c, s: (Falso(["a"]), "F"))
    assert audit.ejecutar_auditoria(cfg(github_token="t"), session=object(), console=Console(quiet=True)).modo == "api"
    assert audit.ejecutar_auditoria(cfg(), session=object(), console=Console(quiet=True)).modo == "web"
