import pytest

from ver_github_pages.errors import ErrorAuditoria, LimiteDeTasa, TokenInvalido, UsuarioNoEncontrado
from ver_github_pages.github_api import API, GitHubAPIProvider
from ver_github_pages.models import RepoInfo


def proveedor(sesion, handler, dominio="https://ana.dev"):
    s = sesion(handler)
    return GitHubAPIProvider("ana", dominio, s, token="SECRETO"), s


def test_obtener_repositorios_mapea_campos(sesion, Resp):
    datos = [
        {"name": "repo1", "has_pages": True, "license": {"key": "mit"}, "description": "hola", "fork": False, "archived": False},
        {"name": "repo2", "has_pages": False, "license": None, "description": "  ", "fork": True, "archived": True},
    ]
    p, _ = proveedor(sesion, lambda m, u, k: Resp(200, json_data=datos))
    r1, r2 = p.obtener_repositorios()
    assert r1.tiene_pages and r1.url_pages == "https://ana.dev/repo1/" and r1.tiene_licencia and r1.tiene_descripcion is True
    assert not r2.tiene_pages and r2.url_pages is None and not r2.tiene_licencia
    assert r2.tiene_descripcion is False and r2.es_fork and r2.esta_archivado


def test_pagina_de_100_en_100(sesion, Resp):
    def h(m, u, k):
        pag = k["params"]["page"]
        return Resp(200, json_data=[{"name": f"r{pag}-{i}"} for i in range(100 if pag == 1 else 3)])

    p, _ = proveedor(sesion, h)
    assert len(p.obtener_repositorios()) == 103


def test_el_token_solo_viaja_a_la_api(sesion, Resp):
    p, s = proveedor(sesion, lambda m, u, k: Resp(200, json_data=[{"name": "x"}], text=""))
    p.obtener_repositorios()
    p.enriquecer_repo(RepoInfo("x"))
    for _, url, kw in s.llamadas:
        auth = (kw.get("headers") or {}).get("Authorization")
        if url.startswith(API):
            assert auth == "Bearer SECRETO"
        else:
            assert auth is None, f"el token se filtró a {url}"


@pytest.mark.parametrize("resp,error", [
    (dict(status_code=404), UsuarioNoEncontrado),
    (dict(status_code=401), TokenInvalido),
    (dict(status_code=403, headers={"X-RateLimit-Remaining": "0"}), LimiteDeTasa),
    (dict(status_code=429), LimiteDeTasa),
    (dict(status_code=500), ErrorAuditoria),
])
def test_errores_globales_no_se_ocultan(sesion, Resp, resp, error):
    p, _ = proveedor(sesion, lambda m, u, k: Resp(**resp))
    with pytest.raises(error):
        p.obtener_repositorios()


def handler_enriquecer(archivos, atom="<entry>"):
    def h(m, u, k):
        from conftest import FakeResponse as R
        if u.endswith("releases.atom"):
            return R(200, atom)
        if u.endswith("/contents/"):
            return R(200, json_data=[{"name": n} for n in archivos]) if archivos is not None else R(404)
        raise AssertionError(u)
    return h


def test_enriquecer_detecta_readme_de_cualquier_extension(sesion):
    p, _ = proveedor(sesion, handler_enriquecer(["README.rst", "LICENSE.md", ".gitignore"]))
    r = p.enriquecer_repo(RepoInfo("x"))
    assert r.tiene_readme and r.tiene_licencia and r.tiene_gitignore and r.tiene_releases


def test_licencia_por_campo_de_la_api_se_conserva(sesion):
    p, _ = proveedor(sesion, handler_enriquecer(["main.py"], atom=""))
    r = p.enriquecer_repo(RepoInfo("x", tiene_licencia=True))
    assert r.tiene_licencia and not r.tiene_readme and not r.tiene_gitignore and not r.tiene_releases


def test_repo_vacio(sesion):
    p, _ = proveedor(sesion, handler_enriquecer(None, atom=""))
    r = p.enriquecer_repo(RepoInfo("x"))
    assert not (r.tiene_readme or r.tiene_gitignore or r.tiene_licencia)


def test_url_real_de_pages_con_dominio_personalizado(sesion):
    from conftest import FakeResponse as R

    def h(m, u, k):
        if u.endswith("/pages"):
            return R(200, json_data={"html_url": "https://ana.dev/juego/"})
        return handler_enriquecer(["README.md"])(m, u, k)

    p, _ = proveedor(sesion, h, dominio="https://ana.github.io")
    r = p.enriquecer_repo(RepoInfo("juego", tiene_pages=True, url_pages="https://ana.github.io/juego/"))
    assert r.url_pages == "https://ana.dev/juego/"


def test_si_falla_la_consulta_de_pages_se_conserva_la_url_calculada(sesion):
    from conftest import FakeResponse as R

    def h(m, u, k):
        if u.endswith("/pages"):
            return R(404)
        return handler_enriquecer([])(m, u, k)

    p, _ = proveedor(sesion, h)
    r = p.enriquecer_repo(RepoInfo("juego", tiene_pages=True, url_pages="https://ana.dev/juego/"))
    assert r.url_pages == "https://ana.dev/juego/"
