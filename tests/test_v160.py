"""Tests de la 1.6.0."""
import json

import pytest

from conftest import FakeResponse as R, FakeSession
from test_e2e import github_falso, ejecutar
from github_pages_auditor import linkcheck


# ---------------------------------------------------------------- 1. --crawl
def test_paginas_internas_filtra_externas_y_archivos():
    html = ('<a href="/web/a.html">a</a><a href="/web/img.png">i</a><a href="https://otro.dev/x">o</a>'
            '<a href="/web/guia/">g</a><a href="/web/">home</a>')
    assert linkcheck.paginas_internas(html, "https://ana.github.io/web/") == [
        "https://ana.github.io/web/a.html", "https://ana.github.io/web/guia/"]


def test_crawl_cli_detecta_pagina_rota_y_sitemap_invalido(instalar, tmp_path):
    def web(url):
        if url.endswith("/web/"):
            return R(200, '<!doctype html><html lang="es"><head><link rel="icon" href="i"></head><body>'
                          '<a href="/web/bien.html">b</a><a href="/web/mal.html">m</a></body></html>')
        if url.endswith("/web/mal.html"):
            return R(404)
        if url.endswith("sitemap.xml"):
            return R(200, "esto no es xml")
        return R(200)
    instalar(github_falso(web=web))
    _, d = ejecutar(tmp_path, "--crawl")
    p = next(r for r in d["repos"] if r["name"] == "web")["pages"]
    assert p["broken_pages"] == ["https://ana.github.io/web/mal.html (404)"]
    assert {"paginas-internas-rotas", "sitemap-invalido"} <= set(p["warnings"])
    _, d2 = ejecutar(tmp_path)
    assert next(r for r in d2["repos"] if r["name"] == "web")["pages"]["broken_pages"] is None


def test_sitemap_con_urls_rotas():
    xml = '<urlset><url><loc>https://a.dev/x</loc></url><url><loc>https://a.dev/y</loc></url></urlset>'

    def h(m, url, kw):
        if url.endswith("sitemap.xml"):
            return R(200, xml)
        return R(404) if url.endswith("/y") else R(200)
    assert linkcheck.validar_sitemap(FakeSession(h), "https://a.dev/sitemap.xml") == ["sitemap-urls-rotas"]


# ---------------------------------------------------------------- 3. reglas propias con contenido
def test_regla_de_contenido_validacion():
    from github_pages_auditor.rules import validar_reglas_propias as v
    ok = v([{"id": "custom-a", "path": "README.md", "type": "content-required", "contains": "a.b"}])
    assert ok[0]["regex"] == r"a\.b"
    for malo in (
        {"id": "custom-a", "path": "x", "type": "content-required"},
        {"id": "custom-a", "path": "x", "type": "content-required", "contains": "a", "regex": "b"},
        {"id": "custom-a", "path": "x", "type": "content-required", "regex": "("},
        {"id": "custom-a", "path": "x", "type": "file-required", "contains": "a"},
    ):
        with pytest.raises(ValueError):
            v([malo])


def _con_contenido(base, archivos):
    def h(metodo, url, kw):
        for ruta, texto in archivos.items():
            if url.endswith("/contents/" + ruta):
                return R(200, texto) if texto is not None else R(404)
        return base(metodo, url, kw)
    return h


def test_regla_de_contenido_en_cli(instalar, tmp_path):
    toml = tmp_path / "c.toml"
    toml.write_text('fail_on = ["custom-instala", "custom-sin-todo"]\n'
                    '[[custom_rules]]\nid = "custom-instala"\npath = "README.md"\ntype = "content-required"\n'
                    'contains = "pip install"\n'
                    '[[custom_rules]]\nid = "custom-sin-todo"\npath = "main.py"\ntype = "content-forbidden"\n'
                    'regex = "TODO|FIXME"\n', encoding="utf-8")
    instalar(_con_contenido(github_falso(), {"README.md": "uso: pip install x", "main.py": "# TODO arreglar"}))
    codigo, d = ejecutar(tmp_path, "--only", "lib", "--config", str(toml))
    assert d["repos"][0]["custom"] == {"custom-instala": True, "custom-sin-todo": True}
    assert d["findings"]["custom-sin-todo"] == ["lib"] and d["findings"]["custom-instala"] == []
    assert codigo == 1


# ---------------------------------------------------------------- 4. calidad del README
def test_analizar_readme():
    from github_pages_auditor import readme
    bueno = "# Proyecto\n" + "texto " * 80 + "\n## Instalación\nx\n## Uso\ny\n"
    assert readme.analizar(bueno) == []
    assert readme.analizar("# Hola") == ["readme-corto", "sin-instalacion", "sin-uso"]
    assert readme.analizar("# P\n" + "t " * 200 + "\n## Quick start\n") == []


def test_readme_quality_cli(instalar, tmp_path):
    def base(metodo, url, kw):
        if url.endswith("/repos/ana/lib/readme"):
            return R(200, "# lib\nSolo una línea.")
        return github_falso()(metodo, url, kw)
    instalar(base)
    _, d = ejecutar(tmp_path, "--only", "lib", "--readme-quality")
    assert d["repos"][0]["readme_issues"] == ["readme-corto", "sin-instalacion", "sin-uso"]
    assert d["findings"]["weak-readme"] == ["lib"]
    _, d2 = ejecutar(tmp_path, "--only", "lib")
    assert d2["repos"][0]["readme_issues"] is None and d2["findings"]["weak-readme"] == []


# ---------------------------------------------------------------- 8. licencias de dependencias
def test_es_copyleft():
    from github_pages_auditor.dependencias import es_copyleft
    assert es_copyleft("GPL-3.0-or-later") and es_copyleft("AGPL-3.0") and es_copyleft("GNU General Public License v3")
    assert not es_copyleft("MIT") and not es_copyleft("LGPL-3.0") and not es_copyleft(None)


def test_dep_licenses_cli(instalar, tmp_path):
    pyproject = '[project]\nname="x"\ndependencies = ["libgpl>=1", "libmit"]\n'

    def base(metodo, url, kw):
        if url.endswith("/contents/pyproject.toml"):
            return R(200, pyproject)
        if url.endswith("/contents/requirements.txt") or url.endswith("/contents/package.json"):
            return R(404)
        if url == "https://pypi.org/pypi/libgpl/json":
            return R(200, json_data={"info": {"license": "GPL-3.0", "classifiers": []}})
        if url == "https://pypi.org/pypi/libmit/json":
            return R(200, json_data={"info": {"license": "MIT", "classifiers": []}})
        return github_falso()(metodo, url, kw)
    instalar(base)
    _, d = ejecutar(tmp_path, "--only", "lib", "--dep-licenses")
    assert d["repos"][0]["copyleft_dependencies"] == ["libgpl (GPL-3.0)"]
    assert d["findings"]["copyleft-dependency"] == ["lib"]
    _, d2 = ejecutar(tmp_path, "--only", "lib")
    assert d2["repos"][0]["copyleft_dependencies"] is None


# ---------------------------------------------------------------- 5. --init
def test_init_crea_y_no_pisa(tmp_path, monkeypatch, capsys):
    from github_pages_auditor import main as cli
    from github_pages_auditor.config import cargar_archivo_config
    monkeypatch.chdir(tmp_path)
    assert cli.main(["--init", "-u", "ana", "--no-env", "--no-color"]) == 0
    ruta = tmp_path / ".github-pages-auditor.toml"
    assert 'user = "ana"' in ruta.read_text(encoding="utf-8")
    assert cargar_archivo_config(str(ruta))["usuario"] == "ana"  # la plantilla es válida
    ruta.write_text("# mio\n", encoding="utf-8")
    assert cli.main(["--init", "--no-env", "--no-color"]) == 2
    assert ruta.read_text(encoding="utf-8") == "# mio\n"
    assert cli.main(["--init", "--yes", "--no-env", "--no-color"]) == 0
    assert "Configuración de github-pages-auditor" in ruta.read_text(encoding="utf-8")


def test_plantilla_init_con_todo_descomentado_es_valida(tmp_path):
    from github_pages_auditor import init
    from github_pages_auditor.config import cargar_archivo_config
    lineas = init.plantilla("ana").splitlines()
    inicio = next(i for i, linea in enumerate(lineas) if "Opcional" in linea)
    texto = "\n".join(lineas[:inicio + 1] + [linea[2:] if linea.startswith("# ") and "Reglas propias" not in linea
                                         else linea for linea in lineas[inicio + 1:]])
    ruta = tmp_path / "c.toml"
    ruta.write_text(texto, encoding="utf-8")
    assert cargar_archivo_config(str(ruta))["usuario"] == "ana"


# ---------------------------------------------------------------- 6. --fix-only / --fix-log
def test_fix_only_filtra_y_registra(instalar, tmp_path):
    instalar(github_falso())
    log = tmp_path / "log.json"
    _, d = ejecutar(tmp_path, "--fix-only", "missing-security-policy", "--only", "lib", "--fix-log", str(log))
    objetivos = {a["target"] for a in d["fixes"]}
    assert objetivos <= {"SECURITY.md"}
    datos = json.loads(log.read_text(encoding="utf-8"))
    assert datos["applied"] is False and datos["actions"] == d["fixes"]


def test_fix_only_regla_invalida(tmp_path):
    from github_pages_auditor.config import parse_args
    with pytest.raises(SystemExit):
        parse_args(["-u", "ana", "--fix-only", "missing-nada"])
    c = parse_args(["-u", "ana", "--fix-only", "missing-license"])
    assert c.fix and c.fix_extra and c.deep and c.fix_only == ("missing-license",)


# ---------------------------------------------------------------- 10. varias cuentas
def test_varias_cuentas(instalar, tmp_path):
    def h(metodo, url, kw):
        if "/users/bea/repos" in url:
            return R(200, json_data=[])
        return github_falso()(metodo, url, kw)
    instalar(h)
    codigo, d = ejecutar(tmp_path, "-u", "ana,ana")  # duplicada: cuenta como una sola
    assert all("/" not in r["name"] for r in d["repos"])


def test_varias_cuentas_junta_repos(instalar, tmp_path):
    base = github_falso()

    def h(metodo, url, kw):
        return base(metodo, url.replace("/users/bea/", "/users/ana/").replace("/repos/bea/", "/repos/ana/"), kw)
    instalar(h)
    from github_pages_auditor import main as cli
    salida = tmp_path / "r.json"
    cli.main(["-u", "ana,bea", "-k", "t", "--no-env", "-q", "-f", "json", "-o", str(salida)])
    d = json.loads(salida.read_text(encoding="utf-8"))
    nombres = [r["name"] for r in d["repos"]]
    assert d["user"] == "ana+bea"
    assert any(n.startswith("ana/") for n in nombres) and any(n.startswith("bea/") for n in nombres)
    assert len(nombres) == len(set(nombres))


def test_varias_cuentas_rechaza_fix(tmp_path):
    from github_pages_auditor.config import parse_args
    with pytest.raises(SystemExit):
        parse_args(["-u", "a,b", "--fix"])
    assert parse_args(["-u", "a,b"]).usuarios == ("a", "b")
    assert parse_args(["-u", "a"]).usuarios == ()


# ---------------------------------------------------------------- 9. --graphql
def test_graphql_precarga_y_ahorra_peticiones(instalar, tmp_path):
    base = github_falso()

    def h(metodo, url, kw):
        if url.endswith("/graphql"):
            consulta = kw["json"]["query"]
            assert 'repository(owner: "ana", name: "lib")' in consulta
            datos = {f"r{j}": {"object": {"entries": [{"name": "README.md"}, {"name": "LICENSE"}]}} for j in range(20)}
            return R(200, json_data={"data": datos})
        return base(metodo, url, kw)
    sesion = instalar(h)
    _, d = ejecutar(tmp_path, "--only", "lib", "--graphql")
    assert d["repos"][0]["name"] == "lib"
    raiz = [u for m, u, _ in sesion.llamadas if m == "GET" and u.endswith("/repos/ana/lib/contents/")]
    assert raiz == []  # la raíz vino por GraphQL


def test_graphql_con_error_usa_rest(instalar, tmp_path):
    base = github_falso()

    def h(metodo, url, kw):
        if url.endswith("/graphql"):
            return R(200, json_data={"errors": [{"message": "boom"}], "data": None})
        return base(metodo, url, kw)
    sesion = instalar(h)
    _, d = ejecutar(tmp_path, "--only", "lib", "--graphql")
    assert d["repos"][0]["name"] == "lib"
    assert any(u.endswith("/repos/ana/lib/contents/") for m, u, _ in sesion.llamadas)


# ---------------------------------------------------------------- 2. ETag: estadísticas, --cache-clear, caducidad
def test_cache_cuenta_aciertos_y_borra(tmp_path):
    import os
    import time
    from github_pages_auditor import cache as c

    def h(metodo, url, kw):
        if kw.get("headers", {}).get("If-None-Match") == '"v1"':
            return R(304)
        return R(200, json_data={"a": 1}, headers={"ETag": '"v1"'})
    sesion = c.SesionConCache(FakeSession(h), str(tmp_path / "c"))
    sesion.get("https://api.github.com/x")
    sesion.get("https://api.github.com/x")
    assert (sesion.aciertos, sesion.peticiones) == (1, 2)
    # una entrada antigua se borra al abrir la caché; --cache-clear borra solo archivos de caché
    viejo = tmp_path / "c" / ("a" * 64 + ".json")
    viejo.write_text("{}", encoding="utf-8")
    antiguo = time.time() - 40 * 86400
    os.utime(viejo, (antiguo, antiguo))
    ajeno = tmp_path / "c" / "notas.txt"
    ajeno.write_text("no tocar", encoding="utf-8")
    c.SesionConCache(FakeSession(h), str(tmp_path / "c"))
    assert not viejo.exists()
    assert c.borrar(str(tmp_path / "c")) == 1 and ajeno.exists()


def test_cache_clear_cli(tmp_path, capsys):
    from github_pages_auditor import main as cli
    carpeta = tmp_path / "cc"
    carpeta.mkdir()
    (carpeta / ("b" * 64 + ".json")).write_text("{}", encoding="utf-8")
    assert cli.main(["--cache-clear", "--cache", str(carpeta), "--no-env", "--no-color"]) == 0
    assert not list(carpeta.glob("*.json"))


def test_cache_stats_en_consola(instalar, tmp_path, capsys):
    from github_pages_auditor import main as cli
    base = github_falso()

    def h(metodo, url, kw):
        r = base(metodo, url, kw)
        if url.startswith("https://api.github.com") and r.status_code == 200:
            r.headers = {**(r.headers or {}), "ETag": '"x"'}
        return r
    instalar(h)
    cli.main(["-u", "ana", "-k", "t", "--no-env", "--no-color", "--only", "lib", "--cache", str(tmp_path / "k")])
    cli.main(["-u", "ana", "-k", "t", "--no-env", "--no-color", "--only", "lib", "--cache", str(tmp_path / "k")])
    assert "peticiones sin gastar cuota" in capsys.readouterr().out


# ---------------------------------------------------------------- 7. webhook: Teams, always, reintento, --notify-test
def test_webhook_teams_y_siempre():
    from github_pages_auditor import notify
    assert notify.cuerpo("https://x.webhook.office.com/abc", "hola", {}) == {"text": "hola"}
    enviados = []

    class S:
        def post(self, url, json=None, timeout=None):
            enviados.append(json)
            return R(204)
    assert notify.avisar("https://hooks.slack.com/x", "ana", 80, {}, session=S()) is False
    assert notify.avisar("https://hooks.slack.com/x", "ana", 80, {}, session=S(), siempre=True) is True
    assert "sin hallazgos nuevos" in enviados[0]["text"]


def test_webhook_reintenta_una_vez(monkeypatch):
    from github_pages_auditor import notify
    monkeypatch.setattr(notify.time, "sleep", lambda s: None)
    codigos = [503, 204]

    class S:
        def post(self, url, json=None, timeout=None):
            return R(codigos.pop(0))
    assert notify.probar("https://hooks.slack.com/x", session=S()) is True
    codigos[:] = [500, 500]
    assert notify.probar("https://hooks.slack.com/x", session=S()) is False
    codigos[:] = [404]
    assert notify.probar("https://hooks.slack.com/x", session=S()) is False and codigos == []


def test_notify_test_cli(monkeypatch, capsys):
    from github_pages_auditor import main as cli, notify
    monkeypatch.setattr(notify, "probar", lambda url: url.endswith("/ok"))
    assert cli.main(["--notify-test", "--notify-webhook", "https://h.dev/ok", "--no-env", "--no-color"]) == 0
    assert cli.main(["--notify-test", "--notify-webhook", "https://h.dev/mal", "--no-env", "--no-color"]) == 2
    assert cli.main(["--notify-test", "--no-env", "--no-color"]) == 2
