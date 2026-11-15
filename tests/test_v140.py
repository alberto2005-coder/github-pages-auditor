"""Novedades de la 1.4.0: nota, histórico, salidas, --deep/--org, Pages, --fix, caché, --since, TUI."""
import base64
import json
from datetime import datetime, timedelta, timezone

import pytest
import requests
from conftest import FakeResponse as R
from conftest import FakeSession
from test_e2e import REPOS, ejecutar, github_falso

from github_pages_auditor import cache, dns, history, i18n, linkcheck, notify, pages_health, salidas, tui
from github_pages_auditor import main as cli
from github_pages_auditor.config import parsear_since
from github_pages_auditor.dns import apunta_a_github as apunta_real  # antes de que conftest lo parchee
from github_pages_auditor.errors import ErrorSalida
from github_pages_auditor.fix import descripcion_desde_readme, topics_sugeridos
from github_pages_auditor.models import AuditReport, PagesHealth, RepoInfo
from github_pages_auditor.score import nota, puntuar, puntuar_informe, ranking

AHORA = datetime(2026, 11, 15, tzinfo=timezone.utc)


def completo(nombre="a", **kw):
    datos = dict(tiene_readme=True, tiene_licencia=True, tiene_gitignore=True, tiene_descripcion=True,
                 tiene_releases=True, tiene_security=True, tiene_contributing=True, tiene_code_of_conduct=True,
                 tiene_issue_template=True, topics=["x"], homepage="https://x", ultimo_push="2026-11-01T00:00:00Z",
                 es_fork=False, esta_archivado=False)
    datos.update(kw)
    return RepoInfo(nombre, **datos)


def informe(*repos):
    return AuditReport("ana", "https://ana.github.io", "API", list(repos), "api")


# ============================================================ F1 nota / histórico
def test_repo_perfecto_100_y_repo_vacio_bajo():
    assert puntuar(completo(), ahora=AHORA) == 100
    vacio = RepoInfo("v", es_fork=False, esta_archivado=False, tiene_descripcion=False)
    assert puntuar(vacio, ahora=AHORA) < 20


def test_sin_datos_de_comunidad_los_pesos_se_reescalan():
    web = RepoInfo("w", tiene_readme=True, tiene_licencia=True, tiene_gitignore=True, tiene_descripcion=True,
                   tiene_releases=True)
    assert puntuar(web, ahora=AHORA) == 100  # solo cuentan basicos y release: ambos perfectos


def test_la_release_suma():
    con, sin = completo(tiene_releases=True), completo(tiene_releases=False)
    assert puntuar(con, ahora=AHORA) > puntuar(sin, ahora=AHORA)


def test_actividad_y_ci_afectan():
    viejo = completo(ultimo_push="2020-01-01T00:00:00Z", ci_estado="failure")
    assert puntuar(viejo, ahora=AHORA) < puntuar(completo(), ahora=AHORA)


def test_error_no_tiene_nota_y_tramos():
    assert puntuar(RepoInfo("e", error="x")) is None
    assert [nota(n) for n in (95, 80, 65, 45, 10, None)] == ["A", "B", "C", "D", "E", None]


def test_global_ignora_forks_y_archivados_y_ranking():
    r = informe(completo("a"), completo("b", tiene_releases=False), completo("f", es_fork=True, tiene_readme=False),
                completo("z", esta_archivado=True))
    global_ = puntuar_informe(r, ahora=AHORA)
    assert global_ == round((r.repos[0].puntuacion + r.repos[1].puntuacion) / 2)
    mejores, peores = ranking(r, n=1)
    assert [x.nombre for x in mejores] == ["a"] and [x.nombre for x in peores] == ["b"]


def test_ranking_con_pocos_repos_no_se_solapa():
    r = informe(completo("a"), completo("b", tiene_releases=False), completo("c", tiene_readme=False))
    puntuar_informe(r, ahora=AHORA)
    mejores, peores = ranking(r)
    assert [x.nombre for x in mejores] == ["a"] and [x.nombre for x in peores] == ["b"]  # sin release resta más que sin README
    assert ranking(informe(completo("solo")))[1] == []


def test_historial_guarda_y_compara(tmp_path):
    antes = {"generated_at": "t0", "summary": {"score": 70}, "findings": {}, "repos": [
        {"name": "a", "score": 60}, {"name": "b", "score": 80}, {"name": "viejo", "score": 50}]}
    ahora = {"summary": {"score": 75}, "repos": [
        {"name": "a", "score": 70}, {"name": "b", "score": 75}, {"name": "nuevo", "score": 90}]}
    ruta = history.guardar(str(tmp_path), "ana", antes, AHORA)
    assert history.ultimo(str(tmp_path), "ana")[0] == ruta
    assert history.ultimo(str(tmp_path), "otro") is None
    cmp = history.comparar(ahora, antes, ruta)
    assert cmp["delta"] == 5 and cmp["improved"] == [{"name": "a", "before": 60, "after": 70}]
    assert cmp["worsened"][0]["name"] == "b" and cmp["new_repos"] == ["nuevo"] and cmp["removed_repos"] == ["viejo"]


def test_historial_ignora_archivos_corruptos(tmp_path):
    (tmp_path / "ana-20260101T000000Z.json").write_text("{no es json", encoding="utf-8")
    assert history.ultimo(str(tmp_path), "ana") is None


def test_json_trae_nota_y_ranking(instalar, tmp_path):
    instalar(github_falso())
    _, d = ejecutar(tmp_path)
    assert isinstance(d["summary"]["score"], int) and d["summary"]["grade"] in "ABCDE"
    assert all("score" in r and "grade" in r for r in d["repos"])
    assert set(d["ranking"]) == {"best", "worst"} and d["history"] is None and d["fixes"] is None


def test_min_score(instalar, tmp_path):
    instalar(github_falso())
    codigo, d = ejecutar(tmp_path, "--min-score", "100")
    assert codigo == 1 and "min-score" in d["fail_on"]["triggered"]
    assert ejecutar(tmp_path, "--min-score", "0")[0] == 0


def test_history_dos_ejecuciones(instalar, tmp_path):
    instalar(github_falso())
    carpeta = tmp_path / "h"
    _, primero = ejecutar(tmp_path, "--history", str(carpeta))
    assert primero["history"] is None and len(list(carpeta.iterdir())) == 1
    nombre = next(carpeta.iterdir())
    nombre.rename(carpeta / "ana-20200101T000000Z.json")  # que el siguiente no pise el mismo segundo
    _, segundo = ejecutar(tmp_path, "--history", str(carpeta))
    assert segundo["history"]["previous_file"] == "ana-20200101T000000Z.json" and segundo["history"]["delta"] == 0


def test_badge():
    svg = salidas.a_badge(92)
    assert svg.startswith("<svg") and "92 A" in svg and "#2da44e" in svg
    assert "n/a" in salidas.a_badge(None)


def test_formato_badge_cli(instalar, tmp_path):
    instalar(github_falso())
    codigo, svg = ejecutar(tmp_path, fmt="badge")
    assert codigo == 0 and svg.startswith("<svg")


# ============================================================ F2 salidas
def test_html_escapa_y_no_carga_recursos_externos():
    r = completo("<script>alert(1)</script>", descripcion="<img src=x onerror=alert(1)>", lenguaje='"><b>')
    r.puntuacion = 50
    rep = informe(r)
    h = salidas.a_html(rep, {"missing-topics": [r.nombre]})
    assert "<script>alert(1)</script>" not in h and "&lt;script&gt;alert(1)&lt;/script&gt;" in h
    assert "src=" not in h.replace("<script>", "") and "https://cdn" not in h and "<link" not in h
    assert h.count("<script>") == 1  # solo el nuestro


def test_html_cli(instalar, tmp_path):
    instalar(github_falso())
    codigo, h = ejecutar(tmp_path, fmt="html")
    assert codigo == 0 and h.startswith("<!doctype html>") and "web" in h


def test_csv_cabecera_bom_e_inyeccion():
    r = completo("=cmd()", lenguaje="@x")
    rep = informe(r)
    c = salidas.a_csv(rep, {"missing-topics": ["=cmd()"]}, bom=True)
    assert c.startswith("﻿name,score,grade") and "'=cmd()" in c and "'@x" in c


def test_csv_cli(instalar, tmp_path):
    instalar(github_falso())
    _, c = ejecutar(tmp_path, fmt="csv")
    lineas = c.strip().splitlines()
    assert lineas[0].lstrip("﻿").startswith("name,score") and len(lineas) == 1 + len(REPOS)


def test_sarif_estructura(instalar, tmp_path):
    instalar(github_falso())
    _, s = ejecutar(tmp_path, "--fail-on", "missing-security-policy", fmt="sarif")
    d = json.loads(s)
    assert d["version"] == "2.1.0" and d["runs"][0]["tool"]["driver"]["name"] == "github-pages-auditor"
    niveles = {x["level"] for x in d["runs"][0]["results"] if x["ruleId"] == "missing-security-policy"}
    assert niveles == {"error"}
    assert all(x["locations"][0]["logicalLocations"][0]["fullyQualifiedName"].startswith("ana/")
               for x in d["runs"][0]["results"])


def test_webhook_solo_con_hallazgos_y_nunca_imprime_la_url(monkeypatch, capsys):
    enviados = []
    monkeypatch.setattr(requests, "post", lambda url, json=None, timeout=None: enviados.append((url, json)) or R(204))
    assert notify.avisar("https://discord.com/api/webhooks/secreto", "ana", 80, {"x": []}) is False
    assert notify.avisar("https://discord.com/api/webhooks/secreto", "ana", 80, {"missing-topics": ["a", "b"]}) is True
    url, cuerpo = enviados[0]
    assert list(cuerpo) == ["content"] and "missing-topics: a, b" in cuerpo["content"]
    assert "secreto" not in cuerpo["content"]
    assert list(notify.cuerpo("https://hooks.slack.com/x", "t", {})) == ["text"]
    assert set(notify.cuerpo("https://ejemplo.com/h", "t", {"a": ["b"]})) == {"text", "content", "findings"}


def test_webhook_falla_en_silencio(monkeypatch):
    def boom(*a, **k):
        raise requests.ConnectionError("x")
    monkeypatch.setattr(requests, "post", boom)
    assert notify.avisar("https://x.example/h", "ana", 1, {"r": ["a"]}) is False
    assert notify.avisar("http://x.example/h", "ana", 1, {"r": ["a"]}) is False  # solo https


def test_webhook_cli_http_da_2(instalar, tmp_path):
    instalar(github_falso())
    assert ejecutar(tmp_path, "--notify-webhook", "http://x.example/h")[0] == 2


def test_webhook_cli_envia_hallazgos_nuevos(instalar, tmp_path, monkeypatch):
    instalar(github_falso())
    enviados = []
    monkeypatch.setattr(requests, "post", lambda url, json=None, timeout=None: enviados.append(json) or R(200))
    ejecutar(tmp_path, "--notify-webhook", "https://hooks.slack.com/services/T/B/X")
    assert len(enviados) == 1 and "text" in enviados[0]


def test_idiomas_tienen_las_mismas_claves():
    assert set(i18n.ES) == set(i18n.EN)
    assert not [k for k in i18n.ES if not i18n.EN[k].strip()]


def test_lang_en_en_txt_y_consola(instalar, tmp_path, capsys):
    instalar(github_falso())
    try:
        codigo = cli.main(["-u", "ana", "-k", "t", "--no-env", "--lang", "en", "--no-color", "-f", "txt",
                           "-o", str(tmp_path / "r.txt")])
        assert codigo == 0
        assert "GITHUB PAGES LINKS FOR: ana" in (tmp_path / "r.txt").read_text(encoding="utf-8")
        assert "Audit summary" in capsys.readouterr().out
    finally:
        i18n.set_idioma("es")


def test_reglas_traducidas_en_ambos_idiomas():
    from github_pages_auditor.rules import REGLA_ERRORES, REGLAS
    for regla in list(REGLAS) + [REGLA_ERRORES, "min-score"]:
        assert f"rule.{regla}" in i18n.ES and f"rule.{regla}" in i18n.EN, regla


# ============================================================ F3 --deep / --org / privados
def handler_deep(extra=None):
    base = github_falso()
    extra = extra or {}

    def h(m, url, kw):
        ruta = url.split("api.github.com")[-1]
        if "api.github.com" in url:
            if ruta.endswith("/contents/") and "/web/" in ruta:
                return R(200, json_data=[{"name": "README.md"}, {"name": "LICENSE"}, {"name": ".gitignore"},
                                         {"name": ".github"}])
            if ruta.endswith("/contents/.github"):
                return R(200, json_data=[{"name": "workflows"}, {"name": "dependabot.yml"}])
            if ruta.endswith("/contents/.github/workflows"):
                return R(200, json_data=[{"name": "test.yml"}])
            if ruta.endswith("/vulnerability-alerts"):
                return R(204) if "/web/" in ruta else R(404)
            if "/branches/" in ruta and ruta.endswith("/protection"):
                return R(404, json_data={"message": "Branch not protected"}) if "/web/" in ruta else R(403)
            if ruta.endswith("/contributors"):
                return R(200, json_data=[{}, {}])
            if ruta.endswith("/pulls"):
                return R(200, json_data=[{}] * 5)
            if ruta.endswith("/actions/runs"):
                return R(200, json_data={"workflow_runs": [{"conclusion": "failure"}]})
            if ruta in extra:
                return extra[ruta]
        return base(m, url, kw)
    return h


def con_rama(repos=REPOS):
    return [dict(r, default_branch="main", private=False) for r in repos]


def test_deep_recoge_seguridad_ci_y_actividad(instalar, tmp_path):
    instalar(lambda m, u, k: handler_deep()(m, u, k) if "/users/ana/repos" not in u
             else R(200, json_data=con_rama() if k["params"]["page"] == 1 else []))
    _, d = ejecutar(tmp_path, "--deep")
    web = next(r for r in d["repos"] if r["name"] == "web")["deep"]
    assert web["ci"] is True and web["dependabot_yml"] is True and web["dependabot_alerts"] is True
    assert web["branch_protected"] is False and web["contributors"] == 2 and web["open_prs"] == 5
    assert web["ci_status"] == "failure"
    lib = next(r for r in d["repos"] if r["name"] == "lib")["deep"]
    assert lib["ci"] is False and lib["branch_protected"] is None  # 403 = sin permisos: no se afirma
    f = d["findings"]
    assert "web" in f["failing-ci"] and "web" in f["stale-prs"] and "web" in f["no-branch-protection"]
    assert "lib" in f["missing-ci"] and "web" not in f["missing-ci"] and "web" not in f["missing-dependabot"]


def test_sin_deep_no_hay_datos_ni_peticiones_extra(instalar, tmp_path):
    ses = instalar(handler_deep())
    _, d = ejecutar(tmp_path)
    assert all(v is None for v in d["repos"][0]["deep"].values())
    assert not [u for _, u, _ in ses.llamadas if "vulnerability-alerts" in u or "/pulls" in u]


def test_opciones_que_exigen_token(tmp_path, instalar):
    instalar(github_falso())
    for opcion in (["--deep"], ["--org", "acme"], ["--include-private"], ["--fix"], ["--fix-pages"], ["--fix-metadata"]):
        assert cli.main(["-u", "ana", "--no-env", "-q", "-o", str(tmp_path / "x.txt"), *opcion]) == 2


def test_org_usa_el_endpoint_de_organizaciones(instalar, tmp_path):
    def h(m, url, kw):
        if url.endswith("/orgs/acme/repos"):
            assert kw["params"]["type"] == "all"
            return R(200, json_data=[REPOS[0]] if kw["params"]["page"] == 1 else [])
        return github_falso()(m, url.replace("/acme/", "/ana/"), kw)
    instalar(h)
    codigo = cli.main(["--org", "acme", "-k", "t", "--no-env", "-q", "-f", "json", "-o", str(tmp_path / "o.json")])
    d = json.loads((tmp_path / "o.json").read_text(encoding="utf-8"))
    assert codigo == 0 and d["user"] == "acme" and [r["name"] for r in d["repos"]] == ["web"]


def test_include_private_filtra_por_propietario(instalar, tmp_path):
    propio = dict(REPOS[0], private=True, owner={"login": "ana"})
    ajeno = dict(REPOS[4], owner={"login": "otro"})

    def h(m, url, kw):
        if url.endswith("/user/repos"):
            assert kw["params"]["affiliation"] == "owner" and kw["params"]["visibility"] == "all"
            return R(200, json_data=[propio, ajeno] if kw["params"]["page"] == 1 else [])
        return github_falso()(m, url, kw)
    instalar(h)
    _, d = ejecutar(tmp_path, "--include-private")
    assert [r["name"] for r in d["repos"]] == ["web"] and d["repos"][0]["private"] is True


def test_include_private_con_org_es_error():
    with pytest.raises(SystemExit) as e:
        cli.main(["--org", "acme", "--include-private", "-k", "t", "--no-env"])
    assert e.value.code == 2


# ============================================================ F4 Pages a fondo
PAGINA_POBRE = "<!doctype html><html><head><title>T</title></head><body><img src='a.png'><a href='/x'>x</a></body></html>"


def sesion_pages(extra=None, pagina=PAGINA_POBRE):
    extra = extra or {}

    def h(m, url, kw):
        for sufijo, resp in extra.items():
            if url.endswith(sufijo):
                return resp
        if url.endswith(("404.html", "sitemap.xml", "robots.txt", "favicon.ico")):
            return R(404)
        return R(200, pagina, url=url)
    return FakeSession(h)


def test_avisos_html_basicos():
    s = sesion_pages()
    salud = pages_health.inspeccionar(s, "https://ana.github.io/x/", esperada=True)
    assert {"sin-lang", "imagenes-sin-alt"} <= set(salud.avisos) and salud.icono_en_html is False
    pages_health.profundizar(s, salud)
    assert {"sin-sitemap", "sin-robots", "sin-favicon", "sin-404-personalizada"} <= set(salud.avisos)
    assert salud.cuerpo is None  # no se conserva el HTML


def test_pagina_completa_sin_avisos():
    s = FakeSession(lambda m, u, k: R(200, url=u))
    salud = pages_health.inspeccionar(s, "https://ana.github.io/x/", esperada=True)
    pages_health.profundizar(s, salud)
    assert salud.avisos == []


def test_pagina_pesada_por_content_length():
    s = FakeSession(lambda m, u, k: R(200, headers={"Content-Length": "2500000"}, url=u))
    assert "pagina-pesada" in pages_health.inspeccionar(s, "https://ana.github.io/x/", esperada=True).avisos


def test_dns_de_dominio_propio(monkeypatch):
    monkeypatch.setattr(dns, "apunta_a_github", lambda host: False)
    s = FakeSession(lambda m, u, k: R(200, url=u))
    salud = pages_health.inspeccionar(s, "https://midominio.dev/", esperada=True)
    pages_health.profundizar(s, salud)
    assert "dns-no-apunta-a-github" in salud.avisos
    monkeypatch.setattr(dns, "apunta_a_github", lambda host: True)
    salud = pages_health.inspeccionar(s, "https://midominio.dev/", esperada=True)
    pages_health.profundizar(s, salud)
    assert "dns-no-apunta-a-github" not in salud.avisos


def test_dns_no_se_comprueba_en_github_io(monkeypatch):
    monkeypatch.setattr(dns, "apunta_a_github", lambda host: pytest.fail("no debería llamarse"))
    s = FakeSession(lambda m, u, k: R(200, url=u))
    pages_health.profundizar(s, pages_health.inspeccionar(s, "https://ana.github.io/x/", esperada=True))


def test_dns_resolucion_real_falla_sin_red(monkeypatch):
    import socket
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: (_ for _ in ()).throw(OSError("sin red")))
    dns.resolver_ipv4.cache_clear()
    assert dns.resolver_ipv4("x.invalid") is None
    for ips, esperado in ((("185.199.108.153", "9.9.9.9"), True), (("1.2.3.4",), False), (None, None)):
        monkeypatch.setattr(dns, "resolver_ipv4", lambda host, ips=ips: ips)
        assert apunta_real("x.dev") is esperado


def test_extraer_enlaces():
    html = ('<a href="/rel">r</a><a href="https://x.dev/a#frag">a</a><a href="mailto:a@b.c">m</a>'
            '<a href="#top">t</a><a href="javascript:void(0)">j</a><a href="https://x.dev/a">dup</a>')
    assert linkcheck.extraer_enlaces(html, "https://ana.github.io/x/") == ["https://ana.github.io/rel", "https://x.dev/a"]


def test_enlaces_rotos_y_no_concluyentes():
    estados = {"https://ok.dev/": 200, "https://roto.dev/": 404, "https://bot.dev/": 403, "https://caido.dev/": None}

    def h(m, url, kw):
        if estados[url] is None:
            raise requests.ConnectionError("x")
        return R(estados[url])
    html = "".join(f'<a href="{u}">x</a>' for u in estados)
    rotos = linkcheck.enlaces_rotos(FakeSession(h), html, "https://ana.github.io/")
    assert rotos == ["https://roto.dev/ (404)", "https://caido.dev/ (sin-respuesta)"]


def test_enlaces_limite_de_50():
    html = "".join(f'<a href="https://e.dev/{i}">x</a>' for i in range(120))
    assert len(linkcheck.extraer_enlaces(html, "https://a.dev/")) == linkcheck.MAX_ENLACES


def test_check_links_cli(instalar, tmp_path):
    def web(url):
        if url.endswith("/web/"):
            return R(200, '<!doctype html><html lang="es"><head><link rel="icon" href="i"></head><body>'
                          '<a href="https://muerto.example/">x</a></body></html>')
        return R(404) if "muerto.example" in url else R(200)
    instalar(github_falso(web=web))
    _, d = ejecutar(tmp_path, "--check-links")
    w = next(r for r in d["repos"] if r["name"] == "web")["pages"]
    assert w["broken_links"] == ["https://muerto.example/ (404)"] and "enlaces-rotos" in w["warnings"]
    _, d2 = ejecutar(tmp_path)
    assert next(r for r in d2["repos"] if r["name"] == "web")["pages"]["broken_links"] is None


# ============================================================ F5 --fix
def handler_fix(escrituras, existentes=()):
    base = github_falso()

    def h(m, url, kw):
        if m in ("PUT", "PATCH") and "api.github.com" in url:
            escrituras.append((m, url.split("api.github.com")[-1], kw.get("json")))
            return R(201 if "/contents/" in url else 200, json_data={})
        if m == "GET" and url.endswith(tuple(f"/contents/{e}" for e in existentes)):
            return R(200, json_data={"name": "x"})
        if m == "GET" and url.endswith("/contents/SECURITY.md"):
            return R(404)
        if m == "GET" and url.endswith("/readme"):
            texto = "# Web\n\n![b](x.svg)\n\nUn sitio de ejemplo para probar el auditor de repositorios.\n"
            return R(200, json_data={"content": base64.b64encode(texto.encode()).decode()})
        return base(m, url, kw)
    return h


def test_fix_sin_yes_solo_planea(instalar, tmp_path):
    escrituras = []
    instalar(handler_fix(escrituras))
    _, d = ejecutar(tmp_path, "--fix")
    assert escrituras == []
    assert d["fixes"] and all(a["status"] == "planned" for a in d["fixes"])
    objetivos = {a["target"] for a in d["fixes"]}
    assert objetivos == {"SECURITY.md", "CONTRIBUTING.md", "CODE_OF_CONDUCT.md", ".github/ISSUE_TEMPLATE/bug_report.md"}
    assert not {a["repo"] for a in d["fixes"]} & {"bifurcado", "viejo"}  # ni forks ni archivados


def test_fix_con_yes_escribe_y_no_pisa(instalar, tmp_path):
    escrituras = []
    instalar(handler_fix(escrituras, existentes=("CONTRIBUTING.md",)))
    _, d = ejecutar(tmp_path, "--fix", "--only", "web", "--yes")
    estados = {a["target"]: a["status"] for a in d["fixes"]}
    assert estados["CONTRIBUTING.md"] == "skipped" and estados["SECURITY.md"] == "applied"
    metodo, ruta, cuerpo = next(e for e in escrituras if e[1].endswith("/contents/SECURITY.md"))
    assert metodo == "PUT" and ruta == "/repos/ana/web/contents/SECURITY.md"
    assert "Security policy" in base64.b64decode(cuerpo["content"]).decode("utf-8")
    assert not any(e[1].endswith("CONTRIBUTING.md") for e in escrituras)


def test_fix_dry_run_gana_a_yes(instalar, tmp_path):
    escrituras = []
    instalar(handler_fix(escrituras))
    _, d = ejecutar(tmp_path, "--fix", "--yes", "--dry-run")
    assert escrituras == [] and all(a["status"] == "planned" for a in d["fixes"])


def test_fix_pages_activa_https(instalar, tmp_path):
    escrituras = []
    base = handler_fix(escrituras)

    def h(m, url, kw):
        if m == "GET" and url.endswith("/pages") and "/repos/ana/web/" in url:
            return R(200, json_data={"html_url": "https://ana.github.io/web/", "status": "built", "https_enforced": False})
        return base(m, url, kw)
    instalar(h)
    _, d = ejecutar(tmp_path, "--fix-pages", "--yes")
    assert [(a["repo"], a["status"]) for a in d["fixes"]] == [("web", "applied")]
    assert ("PUT", "/repos/ana/web/pages", {"https_enforced": True}) in escrituras


def test_fix_metadata_propone_descripcion_y_topics(instalar, tmp_path):
    escrituras = []
    repos = [dict(REPOS[0], description="", topics=[], language="Python")]
    instalar(handler_fix(escrituras))
    instalar(lambda m, u, k: R(200, json_data=repos if k["params"]["page"] == 1 else [])
             if u.endswith("/users/ana/repos") else handler_fix(escrituras)(m, u, k))
    _, d = ejecutar(tmp_path, "--fix-metadata")
    acciones = {a["action"]: a["target"] for a in d["fixes"]}
    assert acciones["set-description"].startswith("Un sitio de ejemplo") and acciones["set-topics"] == "python,github-pages"
    assert escrituras == []


def test_fix_fallo_de_api_se_anota(instalar, tmp_path):
    base = handler_fix([])

    def h(m, url, kw):
        if m == "PUT" and "/contents/" in url:
            return R(403)
        return base(m, url, kw)
    instalar(h)
    codigo, d = ejecutar(tmp_path, "--fix", "--only", "web", "--yes")
    assert codigo == 0 and {a["status"] for a in d["fixes"]} == {"failed"} and d["fixes"][0]["detail"] == "HTTP 403"


def test_plantillas_se_leen_del_paquete():
    from github_pages_auditor.fix import PLANTILLAS, leer_plantilla
    for _, plantilla in PLANTILLAS.values():
        assert leer_plantilla(plantilla).strip()


def test_descripcion_desde_readme():
    assert descripcion_desde_readme("# Hola\n\n[![CI](a)](b)\n\nHerramienta para auditar repositorios en un comando.") \
        == "Herramienta para auditar repositorios en un comando."
    assert descripcion_desde_readme("# Solo título") is None
    largo = descripcion_desde_readme("# T\n\n" + "palabra " * 40)
    assert len(largo) <= 120


def test_topics_sugeridos():
    assert topics_sugeridos(RepoInfo("a", lenguaje="C++", tiene_pages=True)) == ["c", "github-pages"]
    assert topics_sugeridos(RepoInfo("a")) == []


# ============================================================ F6 caché / since / TUI
def test_cache_etag_304(tmp_path):
    visto = []

    def h(m, url, kw):
        visto.append(dict(kw.get("headers") or {}))
        if (kw.get("headers") or {}).get("If-None-Match") == '"v1"':
            return R(304)
        return R(200, "[1, 2]", headers={"ETag": '"v1"'})
    s = cache.SesionConCache(FakeSession(h), str(tmp_path))
    kw = {"headers": {"Authorization": "Bearer SECRETO"}, "params": {"page": 1}}
    a = s.get("https://api.github.com/x", **kw)
    b = s.get("https://api.github.com/x", **kw)
    assert a.status_code == 200 and b.status_code == 200 and b.text == "[1, 2]"
    assert visto[1]["If-None-Match"] == '"v1"'
    assert not any("SECRETO" in f.read_text(encoding="utf-8") for f in tmp_path.iterdir())


def test_cache_no_toca_otras_urls_ni_streams(tmp_path):
    s = cache.SesionConCache(FakeSession(lambda m, u, k: R(200, "x", headers={"ETag": '"e"'})), str(tmp_path))
    s.get("https://github.com/x")
    s.get("https://api.github.com/x", stream=True)
    assert list(tmp_path.iterdir()) == []


def test_cache_en_cli(instalar, tmp_path):
    instalar(github_falso())
    carpeta = tmp_path / "c"
    assert ejecutar(tmp_path, "--cache", str(carpeta))[0] == 0 and carpeta.is_dir()


def test_parsear_since():
    assert parsear_since("30d", AHORA) == AHORA - timedelta(days=30)
    assert parsear_since("2w", AHORA) == AHORA - timedelta(days=14)
    assert parsear_since("2026-01-31", AHORA) == datetime(2026, 1, 31, tzinfo=timezone.utc)
    with pytest.raises(ValueError):
        parsear_since("ayer")


def test_since_filtra_por_push(instalar, tmp_path):
    reciente = (datetime.now(timezone.utc) - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
    repos = [dict(REPOS[0], pushed_at=reciente), dict(REPOS[4], pushed_at="2019-01-01T00:00:00Z")]
    instalar(github_falso(repos))
    _, d = ejecutar(tmp_path, "--since", "30d")
    assert [r["name"] for r in d["repos"]] == ["web"]


def test_since_invalido_da_2():
    with pytest.raises(SystemExit) as e:
        cli.main(["-u", "ana", "--no-env", "--since", "ayer"])
    assert e.value.code == 2


def test_tui_filas_y_extra_opcional():
    r = completo("a", lenguaje="Go", estrellas=3)
    r.puntuacion = 88
    assert tui.filas(informe(r), {"missing-topics": ["a"]}) == [("a", "88 B", "", "", "3", "Go", "missing-topics")]
    try:
        import textual  # noqa: F401
    except ModuleNotFoundError:
        with pytest.raises(ErrorSalida):
            tui.lanzar(informe(r), {})


def test_tui_pide_extra_desde_la_cli(instalar, tmp_path, monkeypatch):
    instalar(github_falso())
    import builtins
    real = builtins.__import__

    def sin_textual(nombre, *a, **k):
        if nombre.startswith("textual"):
            raise ModuleNotFoundError(nombre)
        return real(nombre, *a, **k)
    monkeypatch.setattr(builtins, "__import__", sin_textual)
    assert ejecutar(tmp_path, "--tui")[0] == 2


def test_toml_nuevas_claves_y_webhook_prohibido(tmp_path, monkeypatch):
    pytest.importorskip("tomllib")
    from github_pages_auditor.config import ErrorConfig, cargar_archivo_config
    p = tmp_path / "c.toml"
    p.write_text('deep = true\nmin_score = 70\nlang = "en"\nsince = "6m"\n', encoding="utf-8")
    v = cargar_archivo_config(str(p))
    assert v["deep"] is True and v["min_score"] == 70 and v["lang"] == "en" and v["since"] == "6m"
    for malo in ('notify_webhook = "https://x"\n', 'webhook = "https://x"\n', 'lang = "fr"\n'):
        p.write_text(malo, encoding="utf-8")
        with pytest.raises(ErrorConfig):
            cargar_archivo_config(str(p))


def test_pagina_health_dataclass_nuevos_campos():
    s = PagesHealth(estado="ok", url="u")
    assert s.enlaces_rotos is None and s.peso_bytes is None
