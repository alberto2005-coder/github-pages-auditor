import pytest

from ver_github_pages.errors import ErrorAuditoria, LimiteDeTasa, UsuarioNoEncontrado
from ver_github_pages.github_web import GitHubWebProvider, parsear_listado
from ver_github_pages.models import RepoInfo


def li(nombre, descripcion=False, fork=False, archivado=False):
    return (
        '<li itemprop="owns" itemscope class="col-12">'
        f'<h3><a href="/ana/{nombre}" itemprop="name codeRepository">{nombre}</a>'
        + ('<span class="Label">Archived</span>' if archivado else "") + "</h3>"
        + ("<span>Forked from <a>x/y</a></span>" if fork else "")
        + ('<p itemprop="description">algo</p>' if descripcion else "") + "</li>"
    )


def test_parsear_listado_extrae_metadatos():
    uno, dos = parsear_listado(li("uno", descripcion=True) + li("dos", fork=True, archivado=True), "ana")
    assert uno == {"nombre": "uno", "descripcion": True, "fork": False, "archivado": False}
    assert dos == {"nombre": "dos", "descripcion": False, "fork": True, "archivado": True}


def test_parsear_listado_fallback_deja_metadatos_desconocidos():
    html = '<a href="/ana/solo" itemprop="name codeRepository">solo</a>'
    assert parsear_listado(html, "ana") == [{"nombre": "solo", "descripcion": None, "fork": None, "archivado": None}]


def test_obtener_repositorios_pagina_hasta_que_no_hay_nuevos(sesion, Resp):
    paginas = {1: li("a", descripcion=True) + li("b"), 2: li("c"), 3: li("c")}
    prov = GitHubWebProvider("ana", "https://ana.dev", sesion(lambda m, u, k: Resp(200, paginas.get(k["params"]["page"], ""))))
    progreso = []
    repos = prov.obtener_repositorios(on_progress=lambda p, n: progreso.append((p, n)))
    assert [r.nombre for r in repos] == ["a", "b", "c"]
    assert repos[0].tiene_descripcion is True and repos[1].tiene_descripcion is False
    assert progreso[0] == (1, 0)


def test_usuario_inexistente(sesion, Resp):
    with pytest.raises(UsuarioNoEncontrado):
        GitHubWebProvider("ana", "https://a.dev", sesion(lambda m, u, k: Resp(404))).obtener_repositorios()


def test_429_lanza_limite_de_tasa(sesion, Resp):
    with pytest.raises(LimiteDeTasa):
        GitHubWebProvider("ana", "https://a.dev", sesion(lambda m, u, k: Resp(429))).obtener_repositorios()


def test_error_de_servidor_en_primera_pagina(sesion, Resp):
    with pytest.raises(ErrorAuditoria):
        GitHubWebProvider("ana", "https://a.dev", sesion(lambda m, u, k: Resp(503))).obtener_repositorios()


def handler_repo(existentes, atom="", pages_ok=True):
    def h(m, u, k):
        from conftest import FakeResponse as R
        if u.endswith("releases.atom"):
            return R(200, atom)
        if u.startswith("https://raw.githubusercontent.com"):
            return R(200 if u.rsplit("/", 1)[-1] in existentes else 404)
        return R(200 if pages_ok else 404)
    return h


def test_enriquecer_repo_completo(sesion):
    s = sesion(handler_repo({"README.md", "LICENSE", ".gitignore"}, atom="<feed><entry></entry></feed>"))
    r = GitHubWebProvider("ana", "https://ana.dev", s).enriquecer_repo(RepoInfo("juego"))
    assert r.tiene_readme and r.tiene_licencia and r.tiene_gitignore and r.tiene_releases
    assert r.tiene_pages and r.url_pages == "https://ana.dev/juego/"


def test_enriquecer_repo_vacio(sesion):
    r = GitHubWebProvider("ana", "https://ana.dev", sesion(handler_repo(set(), pages_ok=False))).enriquecer_repo(RepoInfo("v"))
    assert not (r.tiene_readme or r.tiene_licencia or r.tiene_gitignore or r.tiene_releases or r.tiene_pages)
    assert r.url_pages is None


def test_readme_con_otra_extension_cuenta(sesion):
    r = GitHubWebProvider("ana", "https://a.dev", sesion(handler_repo({"README.rst"}))).enriquecer_repo(RepoInfo("x"))
    assert r.tiene_readme


def test_atom_sin_entradas_no_es_release(sesion):
    r = GitHubWebProvider("ana", "https://a.dev", sesion(handler_repo(set(), atom="<feed></feed>"))).enriquecer_repo(RepoInfo("x"))
    assert not r.tiene_releases


def test_el_modo_web_no_envia_ninguna_credencial(sesion):
    s = sesion(handler_repo({"README.md"}))
    GitHubWebProvider("ana", "https://a.dev", s).enriquecer_repo(RepoInfo("x"))
    assert all("Authorization" not in (k.get("headers") or {}) for _, _, k in s.llamadas)


def test_sin_dominio_se_descubre_el_dominio_personalizado(sesion):
    """Con el dominio por defecto (github.io), una redirección al dominio propio cuenta como Pages."""
    from conftest import FakeResponse as R

    def h(m, u, k):
        if u.startswith("https://ana.github.io"):
            return R(200, url="https://ana.dev/juego/")
        return R(404)

    r = GitHubWebProvider("ana", "https://ana.github.io", sesion(h)).enriquecer_repo(RepoInfo("juego"))
    assert r.tiene_pages and r.url_pages == "https://ana.dev/juego/"
