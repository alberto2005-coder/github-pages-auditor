"""Novedades de la 1.5.0: doctor, secretos, Pages construyendo, límites, --fix-mode pr/--fix-extra, SEO,
reglas propias, Scorecard, alertas por gravedad, trend, issue y --diff."""
import base64
import json
import subprocess
from datetime import datetime, timezone

import pytest
import requests
from conftest import FakeResponse as R
from conftest import FakeSession
from test_e2e import github_falso

from github_pages_auditor import cache, diff, doctor, fix, github_api, history, pages_health, salidas, scorecard, secretos
from github_pages_auditor import main as cli
from github_pages_auditor.config import ErrorConfig, cargar_archivo_config, parse_args
from github_pages_auditor.github_api import API, GitHubAPIProvider
from github_pages_auditor.models import ESTADO_CONSTRUYENDO, AuditReport, PagesHealth, RepoInfo
from github_pages_auditor.rules import (MENSAJES_PROPIOS, evaluar, parsear_fail_on, registrar_propias,
                                        validar_reglas_propias)
from github_pages_auditor.score import puntuar

AHORA = datetime(2026, 11, 16, tzinfo=timezone.utc)
ENV_VERSIONADO_REAL = secretos.env_versionado  # conftest lo sustituye en cada test: guardamos el real


def correr(tmp_path, *args, fmt="json", usuario="ana"):
    salida = tmp_path / f"informe.{fmt}"
    codigo = cli.main(["-u", usuario, "-k", "t", "--no-env", "-q", "-f", fmt, "-o", str(salida), *args])
    contenido = salida.read_text(encoding="utf-8") if salida.exists() else None
    return codigo, (json.loads(contenido) if contenido and fmt == "json" else contenido)


# ============================================================ H3 secretos
def test_limpiar_oculta_tokens_y_webhooks():
    pat = "github_pat_" + "A1b2" * 10
    clasico = "ghp_" + "x" * 36
    hook = "https://discord.com/api/webhooks/123/abcDEF_-xyz"
    texto = secretos.limpiar(f"fallo con {pat}, {clasico} y {hook} y propio-secreto-123", "propio-secreto-123")
    assert pat not in texto and clasico not in texto and "webhooks" not in texto and "propio-secreto-123" not in texto
    assert texto.count("***") == 4


def test_enmascarar_y_tipo():
    assert secretos.enmascarar("github_pat_" + "z" * 30 + "ab12") == "github_pat_…ab12"
    assert secretos.enmascarar("ghp_" + "z" * 30 + "ab12") == "ghp_…ab12"
    assert secretos.enmascarar(None) == ""
    assert secretos.tipo_token("github_pat_x") == "fine-grained" and secretos.tipo_token("ghp_x") == "classic"
    assert secretos.tipo_token(None) == "none" and secretos.tipo_token("zzz") == "unknown"


@pytest.mark.skipif(subprocess.run(["git", "--version"], capture_output=True, check=False).returncode != 0,
                    reason="git no disponible")
def test_env_versionado_detecta_el_env_subido(tmp_path):
    assert ENV_VERSIONADO_REAL(str(tmp_path)) is None  # sin .env
    (tmp_path / ".env").write_text("GITHUB_TOKEN=x\n")
    assert ENV_VERSIONADO_REAL(str(tmp_path)) is None  # .env pero sin repositorio git
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    assert ENV_VERSIONADO_REAL(str(tmp_path)) is False
    subprocess.run(["git", "add", ".env"], cwd=tmp_path, check=True)
    assert ENV_VERSIONADO_REAL(str(tmp_path)) is True


def test_aviso_si_el_token_va_en_la_linea_de_comandos(instalar, tmp_path, capsys):
    instalar(github_falso())
    correr(tmp_path)  # -k t
    assert "línea de comandos" in capsys.readouterr().err
    assert parse_args(["-u", "ana", "-k", "t"]).token_en_cli is True
    assert parse_args(["-u", "ana"]).token_en_cli is False


def test_aviso_si_env_esta_en_el_repo(instalar, tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(secretos, "env_versionado", lambda *a, **k: True)
    instalar(github_falso())
    correr(tmp_path)
    assert "git rm --cached" in capsys.readouterr().err.replace("\n", " ")


def test_un_error_de_red_con_token_no_lo_filtra(instalar, tmp_path):
    token = "github_pat_" + "Q" * 30

    def fallo(url):
        if "/contents/" in url:
            raise requests.ConnectionError(f"fallo con {token}")
    instalar(github_falso(fallo=fallo))
    codigo = cli.main(["-u", "ana", "-k", token, "--no-env", "-q", "-f", "json", "-o", str(tmp_path / "i.json")])
    texto = (tmp_path / "i.json").read_text(encoding="utf-8")
    assert token not in texto and "***" in texto and codigo == 0


# ============================================================ H2 Pages construyendo
def test_pages_en_construccion_no_es_pages_rota(instalar, tmp_path):
    instalar(github_falso(pages_extra={"roto": {"status": "building"}}))
    codigo, d = correr(tmp_path, "--fail-on", "broken-pages")
    roto = next(r for r in d["repos"] if r["name"] == "roto")
    assert codigo == 0 and roto["pages"]["status"] == "construyendo"
    assert "build-en-curso" in roto["pages"]["warnings"] and d["summary"]["pages_broken"] == 0
    assert d["findings"]["broken-pages"] == []


def test_pages_construyendo_cuenta_como_activa():
    r = RepoInfo("x", tiene_pages=True, url_pages="https://u.dev/x/",
                 pages_salud=PagesHealth(estado=ESTADO_CONSTRUYENDO, url="https://u.dev/x/", problemas=["404"]))
    assert r.pages_viva and not r.pages_rota


def test_pages_con_build_fallido_sigue_siendo_rota(instalar, tmp_path):
    instalar(github_falso(pages_extra={"web": {"status": "errored"}}))
    _, d = correr(tmp_path)
    assert next(r for r in d["repos"] if r["name"] == "web")["pages"]["status"] == "roto"


# ============================================================ H4 caché y límites
def test_cache_auto_usa_la_carpeta_del_usuario(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert cache.resolver_carpeta("auto") == str(tmp_path / "github-pages-auditor" / "cache")
    assert cache.resolver_carpeta("AUTO").endswith("cache")
    assert cache.resolver_carpeta("mi/carpeta") == "mi/carpeta"


def _proveedor(handler):
    return GitHubAPIProvider("ana", "https://ana.github.io", FakeSession(handler), token="t")


def test_limite_inminente_espera_y_reintenta(monkeypatch):
    esperas, llamadas = [], []
    monkeypatch.setattr(github_api.time, "sleep", esperas.append)

    def h(m, url, kw):
        llamadas.append(url)
        if len(llamadas) == 1:
            return R(403, headers={"X-RateLimit-Remaining": "0", "Retry-After": "3"})
        return R(200, json_data=[])
    res = _proveedor(h)._get("/users/ana/repos")
    assert res.status_code == 200 and len(llamadas) == 2 and esperas == [4.0]


def test_limite_lejano_falla_con_la_hora(monkeypatch):
    from github_pages_auditor.errors import LimiteDeTasa
    monkeypatch.setattr(github_api.time, "sleep", lambda s: pytest.fail("no debe esperar tanto"))
    reinicio = int(datetime(2026, 11, 16, 12, 34, tzinfo=timezone.utc).timestamp())
    monkeypatch.setattr(github_api.time, "time", lambda: reinicio - 3600)

    def h(m, url, kw):
        return R(403, headers={"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": str(reinicio)})
    with pytest.raises(LimiteDeTasa, match="12:34 UTC"):
        _proveedor(h)._get("/x")


def test_segundos_hasta_reinicio():
    assert github_api.segundos_hasta_reinicio({"Retry-After": "7"}) == 7
    assert github_api.segundos_hasta_reinicio({"X-RateLimit-Reset": "110"}, ahora=100) == 10
    assert github_api.segundos_hasta_reinicio({}) is None and github_api.segundos_hasta_reinicio({"Retry-After": "x"}) is None


# ============================================================ H1 doctor
def handler_doctor(user_status=200, cabeceras=None, permisos_ok=True):
    def h(m, url, kw):
        ruta = url[len(API):] if url.startswith(API) else url
        if ruta == "/user":
            return R(user_status, json_data={"login": "ana"}, headers=cabeceras or {})
        if ruta == "/rate_limit":
            return R(200, json_data={"resources": {"core": {"remaining": 4000, "limit": 5000}}})
        if ruta.startswith("/users/ana/repos") or ruta.startswith("/user/repos"):
            return R(200, json_data=[{"name": "viejo", "archived": True}, {"name": "web", "has_pages": True,
                                                                           "owner": {"login": "ana"}}])
        if ruta == "/repos/ana/web":
            return R(200, json_data={"default_branch": "main"})
        if not permisos_ok:
            return R(403)
        if ruta.endswith("/vulnerability-alerts"):
            return R(204)
        if ruta.endswith("/protection"):
            return R(404, json_data={"message": "Branch not protected"})
        return R(200, json_data=[])
    return h


def test_doctor_token_clasico_con_todo_disponible():
    filas = doctor.Doctor(FakeSession(handler_doctor(cabeceras={"X-OAuth-Scopes": "repo, read:org"})),
                          "ghp_" + "a" * 36, "ana").ejecutar()
    estados = {f["check"]: f["status"] for f in filas}
    assert estados["token"] == "ok" and estados["write"] == "ok" and estados["rate"] == "ok"
    assert estados["contents"] == estados["pages"] == estados["alerts"] == estados["protection"] == "ok"
    assert next(f for f in filas if f["check"] == "sample")["detail"] == "ana/web"  # elige uno con Pages, no el archivado
    assert not doctor.hay_fallos(filas)


def test_doctor_fine_grained_no_puede_probar_la_escritura_y_avisa_de_caducidad():
    cab = {"github-authentication-token-expiration": "2020-01-02 03:04:05 UTC"}
    filas = doctor.Doctor(FakeSession(handler_doctor(cabeceras=cab)), "github_pat_" + "a" * 30, "ana").ejecutar()
    estados = {f["check"]: f for f in filas}
    assert estados["write"]["status"] == "unknown"
    assert estados["expiry"]["status"] == "warn" and "2020-01-02" in estados["expiry"]["detail"]


def test_doctor_sin_permisos_lo_marca():
    filas = doctor.Doctor(FakeSession(handler_doctor(permisos_ok=False)), "github_pat_" + "a" * 30, "ana").ejecutar()
    estados = {f["check"]: f["status"] for f in filas}
    assert estados["contents"] == "fail" and estados["pages"] == "warn" and estados["alerts"] == "warn"
    assert doctor.hay_fallos(filas)


def test_doctor_token_invalido_y_sin_token():
    assert doctor.Doctor(FakeSession(handler_doctor(user_status=401)), "ghp_" + "a" * 36).ejecutar()[-1]["status"] == "fail"
    filas = doctor.Doctor(FakeSession(handler_doctor()), None).ejecutar()
    assert [f["status"] for f in filas] == ["fail"]


def test_doctor_en_la_cli_y_codigos_de_salida(instalar, capsys, monkeypatch):
    instalar(handler_doctor(cabeceras={"X-OAuth-Scopes": "repo"}))
    assert cli.main(["--doctor", "-k", "ghp_" + "a" * 36, "--no-env", "-u", "ana", "--no-color"]) == 0
    salida = capsys.readouterr().out
    assert "Diagnóstico del token" in salida and "ghp_…" in salida and ("a" * 36) not in salida
    instalar(handler_doctor(user_status=401))
    assert cli.main(["--doctor", "-k", "ghp_" + "a" * 36, "--no-env", "--no-color"]) == 2
    assert cli.main(["--doctor", "--no-env", "--no-color"]) == 2  # sin token


def test_doctor_no_exige_usuario():
    assert parse_args(["--doctor"]).doctor is True


# ============================================================ H5/H6 --fix-extra y --fix-mode pr
LISTA = [{"name": "app", "has_pages": False, "license": None, "description": "App", "fork": False, "archived": False,
          "language": "Python", "default_branch": "main"}]


def handler_fix150(escrituras, vacio=("LICENSE", ".gitignore", ".github/dependabot.yml", ".github/workflows/ci.yml")):
    """Repo ``app`` sin LICENSE/.gitignore/CI/dependabot y con las ramas necesarias para la PR."""
    base = github_falso(repos=LISTA)

    def h(m, url, kw):
        if "api.github.com" not in url:
            return base(m, url, kw)
        ruta = url.split("api.github.com")[-1]
        if m in ("PUT", "POST", "PATCH"):
            escrituras.append((m, ruta, kw.get("json")))
            if ruta.endswith("/git/refs"):
                return R(201, json_data={})
            if ruta.endswith("/pulls"):
                return R(201, json_data={"html_url": "https://github.com/ana/app/pull/1"})
            return R(201 if "/contents/" in ruta else 200, json_data={})
        if ruta.endswith("/git/ref/heads/main"):
            return R(200, json_data={"object": {"sha": "abc123"}})
        if ruta == "/repos/ana/app/contents/":
            return R(200, json_data=[{"name": "README.md"}, {"name": ".github"}])
        if ruta == "/repos/ana/app/contents/.github":
            return R(200, json_data=[{"name": "workflows"}])
        if ruta == "/repos/ana/app/contents/.github/workflows":
            return R(200, json_data=[])
        if "/contents/" in ruta and any(ruta.endswith(v) for v in vacio):
            return R(404)
        if "/contents/" in ruta and not any(ruta.endswith(v) for v in vacio):
            return R(200, json_data={"name": "x"})
        if ruta.endswith("/vulnerability-alerts"):
            return R(404)
        return base(m, url, kw)
    return h


def test_fix_extra_planea_los_archivos_segun_el_lenguaje(instalar, tmp_path):
    escrituras = []
    instalar(handler_fix150(escrituras))
    codigo, d = correr(tmp_path, "--fix-extra")
    objetivos = {a["target"] for a in d["fixes"]}
    assert {"LICENSE", ".github/dependabot.yml", ".github/workflows/ci.yml"} <= objetivos
    assert all(a["status"] == "planned" for a in d["fixes"]) and escrituras == []  # sin --yes no escribe


def test_fix_extra_activa_deep_y_fix():
    c = parse_args(["-u", "ana", "--fix-extra"])
    assert c.deep and c.fix and c.fix_extra and c.licencia == "mit" and c.fix_mode == "direct"


def test_fix_directo_escribe_contenido_de_las_plantillas(instalar, tmp_path):
    escrituras = []
    instalar(handler_fix150(escrituras))
    _, d = correr(tmp_path, "--fix-extra", "--license", "isc", "--yes")
    contenidos = {r.split("/contents/")[-1]: base64.b64decode(c["content"]).decode() for m, r, c in escrituras
                  if "/contents/" in r}
    assert contenidos["LICENSE"].startswith("ISC License") and str(datetime.now().year) in contenidos["LICENSE"]
    assert "ana" in contenidos["LICENSE"] and "{year}" not in contenidos["LICENSE"]
    assert "__pycache__/" in contenidos[".gitignore"] if ".gitignore" in contenidos else True
    assert "github-actions" in contenidos[".github/dependabot.yml"] and '"pip"' in contenidos[".github/dependabot.yml"]
    assert 'branches: ["main"]' in contenidos[".github/workflows/ci.yml"]
    extra = {a["target"]: a["status"] for a in d["fixes"] if a["target"] in ("LICENSE", ".github/dependabot.yml", ".github/workflows/ci.yml")}
    assert set(extra.values()) == {"applied"} and len(extra) == 3


def test_fix_mode_pr_crea_rama_sube_archivos_y_abre_la_pr(instalar, tmp_path):
    escrituras = []
    instalar(handler_fix150(escrituras))
    _, d = correr(tmp_path, "--fix-extra", "--fix-mode", "pr", "--yes")
    pasos = [(m, r.split("/repos/ana/app")[-1]) for m, r, _ in escrituras]
    assert pasos[0] == ("POST", "/git/refs") and pasos[-1] == ("POST", "/pulls")
    rama = escrituras[0][2]["ref"]
    assert rama.startswith("refs/heads/github-pages-auditor/fix-") and escrituras[0][2]["sha"] == "abc123"
    assert all(c["branch"] == rama[len("refs/heads/"):] for m, r, c in escrituras if m == "PUT")
    assert escrituras[-1][2]["base"] == "main"
    acciones = {(a["action"], a["target"]): a["status"] for a in d["fixes"]}
    assert acciones[("open-pr", "https://github.com/ana/app/pull/1")] == "applied"
    assert acciones[("create-file", "LICENSE")] == "applied"
    assert all(a.get("via") == "pr" for a in d["fixes"] if a["action"] == "create-file")


def test_fix_mode_pr_sin_yes_solo_planea(instalar, tmp_path):
    escrituras = []
    instalar(handler_fix150(escrituras))
    _, d = correr(tmp_path, "--fix-extra", "--fix-mode", "pr")
    assert escrituras == [] and all(a["status"] == "planned" and a["via"] == "pr" for a in d["fixes"])


def test_fix_mode_pr_si_no_hay_rama_no_se_escribe_nada(instalar, tmp_path):
    escrituras = []
    base = handler_fix150(escrituras)

    def h(m, url, kw):
        if url.endswith("/git/ref/heads/main"):
            return R(404)
        return base(m, url, kw)
    instalar(h)
    _, d = correr(tmp_path, "--fix-extra", "--fix-mode", "pr", "--yes")
    assert escrituras == []
    assert {a["status"] for a in d["fixes"] if a["target"] == "LICENSE"} == {"failed"}


def test_fix_mode_pr_no_pisa_lo_que_existe(instalar, tmp_path):
    escrituras = []
    instalar(handler_fix150(escrituras, vacio=(".github/dependabot.yml",)))
    _, d = correr(tmp_path, "--fix-extra", "--fix-mode", "pr", "--yes")
    estados = {a["target"]: a["status"] for a in d["fixes"] if a["action"] == "create-file"}
    assert estados.get(".github/dependabot.yml") == "applied" and "LICENSE" not in estados or estados["LICENSE"] == "skipped"


def test_plantillas_y_generadores():
    py = RepoInfo("a", lenguaje="Python", rama_defecto="trunk")
    sin_lenguaje = RepoInfo("b")
    assert "pip" in fix.dependabot_yml("Python") and "pip" not in fix.dependabot_yml(None)
    assert fix.contenido_de(sin_lenguaje, ".github/workflows/ci.yml", "ana") is None  # sin plantilla de CI
    assert 'branches: ["trunk"]' in fix.contenido_de(py, ".github/workflows/ci.yml", "ana")
    assert "node_modules/" in fix.contenido_de(RepoInfo("c", lenguaje="TypeScript"), ".gitignore", "ana")
    assert ".DS_Store" in fix.contenido_de(sin_lenguaje, ".gitignore", "ana")  # genérica
    for lic in ("mit", "bsd-3-clause", "isc", "unlicense"):
        texto = fix.contenido_de(py, "LICENSE", "Ana Pérez", lic, ahora=AHORA)
        assert "{year}" not in texto and "{holder}" not in texto
        if lic != "unlicense":
            assert "2026" in texto and "Ana Pérez" in texto


def test_las_plantillas_de_ci_y_dependabot_son_yaml_valido():
    yaml = pytest.importorskip("yaml")
    for tipo in ("python", "node", "go", "rust"):
        datos = yaml.safe_load(fix.leer_plantilla(f"ci-{tipo}.yml").replace("{rama}", "main"))
        assert datos["name"] == "CI" and "test" in datos["jobs"]
    datos = yaml.safe_load(fix.dependabot_yml("Python"))
    assert datos["version"] == 2 and len(datos["updates"]) == 2


# ============================================================ H7 SEO
def sirve(html):
    return FakeSession(lambda m, url, kw: R(200, html))


def test_seo_avisos_de_una_pagina_minima():
    s = pages_health.inspeccionar(sirve("<!doctype html><html lang='es'><head><title></title></head><body>x</body></html>"),
                                  "https://ana.github.io/web/", esperada=True)
    for aviso in ("sin-title", "sin-viewport", "sin-og-title", "sin-canonical"):
        assert aviso in s.avisos


def test_seo_pagina_completa_sin_avisos_nuevos():
    s = pages_health.inspeccionar(FakeSession(lambda m, u, k: R(200)), "https://ana.github.io/web/", esperada=True)
    assert not set(s.avisos) & pages_health.AVISOS_SIN_PUNTOS


def test_seo_contenido_mixto_solo_en_https_y_en_recursos():
    html = ("<!doctype html><html lang='es'><head><title>x</title><meta name='viewport' content='a'></head>"
            "<body><img src='http://cdn.x/i.png'><a href='http://otro.es'>enlace</a></body></html>")
    assert "contenido-mixto" in pages_health.inspeccionar(sirve(html), "https://ana.github.io/w/", esperada=True).avisos
    assert "contenido-mixto" not in pages_health.inspeccionar(sirve(html), "http://ana.github.io/w/", esperada=True).avisos
    solo_enlace = "<!doctype html><html lang='es'><head><title>x</title></head><body><a href='http://x'>a</a></body></html>"
    assert "contenido-mixto" not in pages_health.inspeccionar(sirve(solo_enlace), "https://a.github.io/w/", esperada=True).avisos


def test_los_avisos_seo_no_bajan_la_nota():
    base = dict(tiene_readme=True, tiene_licencia=True, tiene_gitignore=True, tiene_descripcion=True, tiene_pages=True,
                url_pages="https://x/")
    limpia = RepoInfo("a", pages_salud=PagesHealth(estado="ok", url="https://x/"), **base)
    seo = RepoInfo("a", pages_salud=PagesHealth(estado="ok", url="https://x/", avisos=["sin-title", "sin-canonical",
                                                                                          "contenido-mixto"]), **base)
    con_aviso = RepoInfo("a", pages_salud=PagesHealth(estado="ok", url="https://x/", avisos=["sin-sitemap"]), **base)
    assert puntuar(limpia, ahora=AHORA) == puntuar(seo, ahora=AHORA) > puntuar(con_aviso, ahora=AHORA)


# ============================================================ H8 reglas propias
def test_validar_reglas_propias():
    reglas = validar_reglas_propias([{"id": "custom-docs", "path": "docs"},
                                     {"id": "custom-sin-env", "path": ".env", "type": "file-forbidden", "message": "No .env"}])
    assert reglas[0]["type"] == "file-required" and "docs" in reglas[0]["message"] and reglas[1]["message"] == "No .env"
    for malo in ([{"id": "docs", "path": "docs"}], [{"id": "custom-a", "path": "../x"}], [{"id": "custom-a"}],
                 [{"id": "custom-a", "path": "x", "type": "otro"}], [{"id": "custom-a", "path": "x", "raro": 1}],
                 [{"id": "custom-a", "path": "x"}, {"id": "custom-a", "path": "y"}], [{"id": "missing-readme", "path": "x"}],
                 "texto"):
        with pytest.raises(ValueError):
            validar_reglas_propias(malo)


def test_fail_on_acepta_reglas_propias_y_los_grupos_las_incluyen():
    assert parsear_fail_on("custom-docs", ("custom-docs",)) == ("custom-docs",)
    with pytest.raises(ValueError):
        parsear_fail_on("custom-docs")
    assert "custom-docs" in parsear_fail_on("community", ("custom-docs",))
    assert "custom-docs" in parsear_fail_on("all", ("custom-docs",))
    assert "custom-docs" not in parsear_fail_on("any", ("custom-docs",))


def test_toml_con_reglas_propias(tmp_path):
    ruta = tmp_path / "c.toml"
    ruta.write_text('fail_on = ["custom-docs"]\nscorecard = true\n[[custom_rules]]\nid = "custom-docs"\npath = "docs"\n',
                    encoding="utf-8")
    datos = cargar_archivo_config(str(ruta))
    assert datos["reglas_propias"][0]["id"] == "custom-docs" and datos["fail_on"] == ("custom-docs",)
    assert datos["scorecard"] is True
    ruta.write_text('[[custom_rules]]\nid = "mal"\npath = "docs"\n', encoding="utf-8")
    with pytest.raises(ErrorConfig, match="custom-"):
        cargar_archivo_config(str(ruta))


def test_reglas_propias_de_punta_a_punta(instalar, tmp_path):
    toml = tmp_path / "c.toml"
    toml.write_text('[[custom_rules]]\nid = "custom-docs"\npath = "docs"\nmessage = "Falta docs/"\n'
                    '[[custom_rules]]\nid = "custom-sin-env"\npath = ".env"\ntype = "file-forbidden"\n', encoding="utf-8")
    base = github_falso()

    def h(m, url, kw):
        if url.endswith("/web/contents/docs"):
            return R(200, json_data=[])
        if url.endswith("/lib/contents/.env"):
            return R(200, json_data={})
        if url.endswith("/contents/docs") or url.endswith("/contents/.env"):
            return R(404)
        return base(m, url, kw)
    instalar(h)
    codigo, d = correr(tmp_path, "--config", str(toml), "--fail-on", "custom-docs")
    assert codigo == 1 and "web" not in d["findings"]["custom-docs"] and "lib" in d["findings"]["custom-docs"]
    assert d["findings"]["custom-sin-env"] == ["lib"]
    assert next(r for r in d["repos"] if r["name"] == "web")["custom"] == {"custom-docs": True, "custom-sin-env": False}
    assert not {"bifurcado", "viejo"} & set(d["findings"]["custom-docs"])  # ni forks ni archivados
    assert MENSAJES_PROPIOS["custom-docs"] == "Falta docs/"


def test_reglas_propias_sin_dato_no_dan_hallazgos():
    reglas = validar_reglas_propias([{"id": "custom-docs", "path": "docs"}])
    repo = RepoInfo("a", es_fork=False, esta_archivado=False)  # modo web: custom = None
    assert evaluar([repo], propias=reglas)["custom-docs"] == []
    repo.custom = {"custom-docs": False}
    assert evaluar([repo], propias=reglas)["custom-docs"] == ["a"]


def test_reglas_propias_se_muestran_con_su_mensaje(instalar, tmp_path):
    registrar_propias(validar_reglas_propias([{"id": "custom-docs", "path": "docs", "message": "Falta la carpeta docs"}]))
    from github_pages_auditor.i18n import t
    assert t("rule.custom-docs") == "Falta la carpeta docs"
    registrar_propias(())


# ============================================================ H9 Scorecard y H10 alertas
def test_scorecard_obtener():
    ok = FakeSession(lambda m, u, k: R(200, json_data={"score": 6.34}))
    assert scorecard.obtener(ok, "ana", RepoInfo("a", es_fork=False)) == 6.3
    assert scorecard.obtener(ok, "ana", RepoInfo("a", privado=True)) is None
    assert scorecard.obtener(ok, "ana", RepoInfo("a", es_fork=True)) is None
    assert scorecard.obtener(FakeSession(lambda m, u, k: R(404)), "ana", RepoInfo("a")) is None
    assert scorecard.obtener(FakeSession(lambda m, u, k: R(200, json_data={"score": -1})), "ana", RepoInfo("a")) is None

    def cae(m, u, k):
        raise requests.ConnectionError("x")
    assert scorecard.obtener(FakeSession(cae), "ana", RepoInfo("a")) is None


def test_scorecard_en_la_cli_y_regla_low_scorecard(instalar, tmp_path):
    base = github_falso()

    def h(m, url, kw):
        if "securityscorecards.dev" in url:
            return R(200, json_data={"score": 2.5 if "/lib" in url else 8.0})
        return base(m, url, kw)
    instalar(h)
    codigo, d = correr(tmp_path, "--scorecard", "--fail-on", "low-scorecard")
    notas = {r["name"]: r["scorecard"] for r in d["repos"]}
    assert notas["lib"] == 2.5 and notas["web"] == 8.0 and notas["bifurcado"] is None
    assert codigo == 1 and d["findings"]["low-scorecard"] == ["lib"]


def test_sin_scorecard_no_se_consulta_el_servicio(instalar, tmp_path):
    sesion = instalar(github_falso())
    correr(tmp_path)
    assert not any("securityscorecards" in u for _, u, _ in sesion.llamadas)


def test_alertas_de_dependabot_por_gravedad(instalar, tmp_path):
    base = github_falso()

    def h(m, url, kw):
        if url.endswith("/web/vulnerability-alerts"):
            return R(204)
        if url.endswith("/web/dependabot/alerts"):
            return R(200, json_data=[{"security_advisory": {"severity": "critical"}},
                                     {"security_advisory": {"severity": "high"}},
                                     {"security_advisory": {"severity": "high"}},
                                     {"security_advisory": {"severity": "low"}}])
        return base(m, url, kw)
    instalar(h)
    codigo, d = correr(tmp_path, "--deep", "--fail-on", "critical-vulnerabilities")
    web = next(r for r in d["repos"] if r["name"] == "web")
    assert web["deep"]["critical_alerts"] == 1 and web["deep"]["high_alerts"] == 2
    assert codigo == 1 and d["findings"]["critical-vulnerabilities"] == ["web"]


def test_alertas_sin_permiso_no_dan_hallazgo(instalar, tmp_path):
    base = github_falso()
    instalar(lambda m, u, k: R(204) if u.endswith("/vulnerability-alerts") else
             (R(403) if u.endswith("/dependabot/alerts") else base(m, u, k)))
    _, d = correr(tmp_path, "--deep")
    assert d["findings"]["critical-vulnerabilities"] == []
    assert next(r for r in d["repos"] if r["name"] == "web")["deep"]["critical_alerts"] is None


def test_la_nota_baja_con_vulnerabilidades_graves():
    limpio = RepoInfo("a", alertas_dependabot=True, alertas_criticas=0, alertas_altas=0)
    grave = RepoInfo("a", alertas_dependabot=True, alertas_criticas=1, alertas_altas=0)
    assert puntuar(limpio, ahora=AHORA) > puntuar(grave, ahora=AHORA)


# ============================================================ H11 trend, issue y H12 diff
def informe_json(puntos, fecha, repos=None, hallazgos=None):
    return {"generated_at": fecha, "summary": {"score": puntos}, "findings": hallazgos or {},
            "repos": repos if repos is not None else [{"name": "a", "score": puntos}]}


def test_trend_dibuja_la_evolucion(tmp_path):
    previos = [("ana-1.json", informe_json(50, "2026-10-01T00:00:00Z")), ("ana-2.json", informe_json(60, "2026-11-01T00:00:00Z"))]
    rep = AuditReport("ana", "https://ana.github.io", "API", [RepoInfo("a", puntuacion=80)], "api", puntuacion=80)
    html = salidas.a_trend(rep, previos, "es", ahora=AHORA)
    assert "<polyline" in html and "2026-10-01" in html and "2026-11-16" in html and "Nota actual: 80/100" in html
    assert "http://" not in html.replace("http://www.w3.org", "") or "https://github.com" in html
    assert "▲ a (+30)" in html  # de 50 a 80 desde el primer informe


def test_trend_sin_historial_suficiente_explica_por_que():
    rep = AuditReport("ana", "https://ana.github.io", "API", [], "api", puntuacion=70)
    assert "Todavía no hay suficientes informes" in salidas.a_trend(rep, [], "es", ahora=AHORA)


def test_trend_en_la_cli_necesita_history(tmp_path, capsys):
    with pytest.raises(SystemExit):
        parse_args(["-u", "ana", "-f", "trend"])
    assert "--history" in capsys.readouterr().err
    with pytest.raises(SystemExit):
        parse_args(["-u", "ana", "-f", "trend", "--history", "h", "-o", "-"])


def test_trend_de_punta_a_punta(instalar, tmp_path):
    instalar(github_falso())
    carpeta = tmp_path / "hist"
    correr(tmp_path, "--history", str(carpeta))
    correr(tmp_path, "--history", str(carpeta))
    salida = tmp_path / "evolucion.html"
    assert cli.main(["-u", "ana", "-k", "t", "--no-env", "-q", "--history", str(carpeta), "-f", "trend",
                     "-o", str(salida)]) == 0
    assert "<svg" in salida.read_text(encoding="utf-8")
    assert parse_args(["-u", "ana", "-f", "trend", "--history", "h"]).archivo_salida == "paginas_github.html"


def test_issue_resumen_markdown():
    repos = [RepoInfo("a", puntuacion=90), RepoInfo("b", puntuacion=40)]
    rep = AuditReport("ana", "https://ana.github.io", "API", repos, "api", puntuacion=65)
    md = salidas.a_issue(rep, {"missing-license": ["b"], "missing-readme": []},
                         {"previous_file": "x.json", "delta": 5})
    assert "nota 65/100 (C)" in md and "| **missing-license**" in md and "`b`" in md and "missing-readme" not in md
    assert "+5" in md and "Mejores" in md or "Best" in md
    assert "Sin hallazgos" in salidas.a_issue(rep, {"missing-readme": []})


def test_issue_en_la_cli(instalar, tmp_path):
    instalar(github_falso())
    codigo, md = correr(tmp_path, fmt="issue")
    assert codigo == 0 and md.startswith("## Auditoría de ana") and "missing-" in md
    assert parse_args(["-u", "ana", "-f", "issue"]).archivo_salida == "paginas_github.md"


def test_diff_compara_dos_informes(tmp_path, capsys):
    antes = informe_json(50, "2026-10-01T00:00:00Z",
                         repos=[{"name": "a", "score": 40}, {"name": "b", "score": 60}, {"name": "viejo", "score": 10}],
                         hallazgos={"missing-license": ["a", "b"]})
    despues = informe_json(60, "2026-11-01T00:00:00Z",
                           repos=[{"name": "a", "score": 70}, {"name": "b", "score": 50}, {"name": "nuevo", "score": 5}],
                           hallazgos={"missing-license": ["b"], "missing-readme": ["nuevo"]})
    r1, r2 = tmp_path / "antes.json", tmp_path / "despues.json"
    r1.write_text(json.dumps(antes)), r2.write_text(json.dumps(despues))
    datos = diff.comparar_informes(antes, despues, str(r1), str(r2))
    assert datos["delta"] == 10 and datos["improved"] == [{"name": "a", "before": 40, "after": 70}]
    assert datos["worsened"] == [{"name": "b", "before": 60, "after": 50}]
    assert datos["new_repos"] == ["nuevo"] and datos["removed_repos"] == ["viejo"]
    assert datos["new_findings"] == {"missing-readme": ["nuevo"]} and datos["resolved_findings"] == {"missing-license": ["a"]}
    assert cli.main(["--diff", str(r1), str(r2), "--no-color"]) == 0
    salida = capsys.readouterr().out
    assert "50 → 60" in salida and "Mejoran" in salida and "nuevo" in salida
    json_salida = tmp_path / "diff.json"
    assert cli.main(["--diff", str(r1), str(r2), "-f", "json", "-o", str(json_salida), "-q"]) == 0
    assert json.loads(json_salida.read_text())["delta"] == 10


def test_diff_con_archivos_malos_da_error(tmp_path, capsys):
    malo = tmp_path / "malo.json"
    malo.write_text("no es json")
    assert cli.main(["--diff", str(malo), str(malo)]) == 2
    assert cli.main(["--diff", str(tmp_path / "no-existe.json"), str(malo)]) == 2
    ajeno = tmp_path / "ajeno.json"
    ajeno.write_text("{}")
    assert cli.main(["--diff", str(ajeno), str(ajeno)]) == 2
    assert "repos" in capsys.readouterr().err


def test_diff_sin_cambios(tmp_path, capsys):
    f = tmp_path / "a.json"
    f.write_text(json.dumps(informe_json(50, "2026-10-01T00:00:00Z")))
    assert cli.main(["--diff", str(f), str(f), "--no-color"]) == 0
    assert "Sin diferencias" in capsys.readouterr().out


def test_history_todos_y_cargar(tmp_path):
    history.guardar(str(tmp_path), "ana", informe_json(10, "x"), ahora=datetime(2026, 1, 1, tzinfo=timezone.utc))
    history.guardar(str(tmp_path), "ana", informe_json(20, "y"), ahora=datetime(2026, 2, 1, tzinfo=timezone.utc))
    (tmp_path / "ana-roto.json").write_text("no json")
    assert [d["summary"]["score"] for _, d in history.todos(str(tmp_path), "ana")] == [10, 20]
    assert history.todos(str(tmp_path / "no-existe"), "ana") == []


# ============================================================ Action y documentación
def test_la_action_tiene_el_paso_de_la_issue():
    from pathlib import Path
    texto = (Path(__file__).resolve().parents[1] / "action.yml").read_text(encoding="utf-8")
    assert "issue:" in texto and "issue-label:" in texto and "-f issue" in texto and "gh issue" in texto
    yaml = pytest.importorskip("yaml")
    datos = yaml.safe_load(texto)
    assert datos["runs"]["steps"][-1]["if"].startswith("${{ always()")


def test_la_salida_json_incluye_los_campos_nuevos(instalar, tmp_path):
    instalar(github_falso())
    _, d = correr(tmp_path)
    repo = d["repos"][0]
    assert {"scorecard", "custom"} <= set(repo) and {"critical_alerts", "high_alerts"} <= set(repo["deep"])
    assert d["schema_version"] == 1


# ---------------------------------------------------------------- heredados de <usuario>/.github
def _con_dotgithub(base, raiz_dotgithub):
    def h(metodo, url, kw):
        if url.endswith("/repos/ana/.github/contents/"):
            return R(200, json_data=[{"name": n} for n in raiz_dotgithub])
        return base(metodo, url, kw)
    return h


def test_heredados_cuentan_como_presentes(instalar, tmp_path):
    from test_e2e import github_falso, ejecutar
    instalar(_con_dotgithub(github_falso(), ["SECURITY.md", "CODE_OF_CONDUCT.md", "CONTRIBUTING.md", "README.md"]))
    _, d = ejecutar(tmp_path, "--only", "lib")
    repo = d["repos"][0]
    assert set(repo["inherited_files"]) == {"security", "code_of_conduct", "contributing"}
    assert "lib" not in str(d["findings"].get("missing-security-policy", []))



def test_sin_defaults_repo_no_hereda(instalar, tmp_path):
    from test_e2e import github_falso, ejecutar
    instalar(_con_dotgithub(github_falso(), ["SECURITY.md"]))
    _, d = ejecutar(tmp_path, "--only", "lib", "--no-defaults-repo")
    assert d["repos"][0]["inherited_files"] is None
    assert "lib" in str(d["findings"].get("missing-security-policy", []))


def test_sin_repo_dotgithub_no_hereda(instalar, tmp_path):
    from test_e2e import github_falso, ejecutar
    instalar(github_falso())
    _, d = ejecutar(tmp_path, "--only", "lib")
    assert d["repos"][0]["inherited_files"] is None
