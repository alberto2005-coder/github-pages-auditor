"""Novedades de la 1.3.0: datos por repo, reglas de comunidad, filtros, baseline, formato github, config, TLS."""
import json
import socket
import sys

import pytest
from test_e2e import REPOS, ejecutar, github_falso

from github_pages_auditor import baseline, formatters, releases, tls
from github_pages_auditor import main as cli
from github_pages_auditor.tls import dias_restantes as dias_restantes_real  # antes de que conftest lo parchee
from github_pages_auditor.models import AuditReport, RepoInfo
from github_pages_auditor.rules import evaluar, parsear_fail_on

RICOS = [dict(r, stargazers_count=n, forks_count=1, open_issues_count=2, language="Python", topics=["a"],
              pushed_at=f"2026-0{n}-01T00:00:00Z", created_at="2020-01-01T00:00:00Z", homepage="")
         for n, r in zip((3, 9, 1, 5, 7), REPOS)]
ATOM = ('<feed><entry><link rel="alternate" href="https://github.com/ana/web/releases/tag/v2.0"/>'
        '<updated>2026-05-01T10:00:00Z</updated></entry></feed>')


def handler(repos=RICOS, **kw):
    base = github_falso(repos, **kw)

    def h(m, url, k):
        if url.endswith("releases.atom"):
            from conftest import FakeResponse as R
            return R(200, ATOM)
        return base(m, url, k)
    return h


# ------------------------------------------------------------ A. datos
def test_atom_extrae_tag_y_fecha():
    assert releases.parsear_ultima_release(ATOM) == ("v2.0", "2026-05-01T10:00:00Z")
    assert releases.parsear_ultima_release("<feed></feed>") == (None, None)


def test_json_incluye_datos_nuevos_y_schema_sigue_en_1(instalar, tmp_path):
    instalar(handler())
    codigo, d = ejecutar(tmp_path)
    web = next(r for r in d["repos"] if r["name"] == "web")
    assert d["schema_version"] == 1
    assert (web["stars"], web["forks"], web["open_issues"], web["language"]) == (3, 1, 2, "Python")
    assert web["latest_release"] == {"tag": "v2.0", "date": "2026-05-01T10:00:00Z"}
    assert web["community"]["security_policy"] is False
    assert "tls_days_left" in web["pages"]


@pytest.mark.parametrize("orden,primero", [("stars", "roto"), ("name", "bifurcado"), ("updated", "roto"), ("listing", "web")])
def test_sort(instalar, tmp_path, orden, primero):
    instalar(handler())
    _, d = ejecutar(tmp_path, "--sort", orden)
    assert d["repos"][0]["name"] == primero


def test_only_e_ignore(instalar, tmp_path):
    instalar(handler())
    _, d = ejecutar(tmp_path, "--only", "w*,roto,LIB", "--ignore", "roto")
    assert sorted(r["name"] for r in d["repos"]) == ["lib", "web"]


# ------------------------------------------------------------ B. reglas
def test_reglas_de_comunidad_y_grupos(instalar, tmp_path):
    instalar(handler())
    codigo, d = ejecutar(tmp_path, "--fail-on", "community")
    assert codigo == 1
    assert "web" in d["findings"]["missing-security-policy"]
    assert "bifurcado" not in d["findings"]["missing-security-policy"]  # forks fuera
    assert "viejo" not in d["findings"]["missing-security-policy"]      # archivados fuera
    assert "stale-repo" in d["findings"]


def test_any_no_incluye_comunidad(instalar, tmp_path):
    instalar(handler())
    codigo, d = ejecutar(tmp_path, "--fail-on", "missing-security-policy")
    assert codigo == 1
    assert parsear_fail_on("any") != parsear_fail_on("all")
    assert "missing-security-policy" not in parsear_fail_on("any")


def test_sin_datos_no_hay_hallazgos_de_comunidad():
    r = RepoInfo("x")  # modo web: todo desconocido
    h = evaluar([r])
    assert not any(h[k] for k in h if k.startswith("missing-") and k not in ("missing-readme", "missing-license", "missing-gitignore", "missing-description"))


def test_stale_repo_usa_meses():
    r = RepoInfo("x", ultimo_push="2025-01-01T00:00:00Z")
    from datetime import datetime, timezone
    ahora = datetime(2026, 11, 14, tzinfo=timezone.utc)
    assert "x" in evaluar([r], stale_meses=12, ahora=ahora)["stale-repo"]
    assert "x" not in evaluar([r], stale_meses=24, ahora=ahora)["stale-repo"]


# ------------------------------------------------------------ D. Pages
def test_tls_dias_hasta():
    import ssl
    ahora = ssl.cert_time_to_seconds("Jan  1 00:00:00 2026 GMT")
    assert tls.dias_hasta("Jan 11 00:00:00 2026 GMT", ahora) == 10
    assert tls.dias_hasta("Dec 31 12:00:00 2025 GMT", ahora) == -1


def test_tls_falla_sin_red_devuelve_none(monkeypatch):
    def boom(*a, **k):
        raise OSError("sin red")
    monkeypatch.setattr(socket, "create_connection", boom)
    assert dias_restantes_real.__wrapped__("ejemplo.invalid") is None


def test_aviso_tls_y_404(instalar, tmp_path, monkeypatch):
    monkeypatch.setattr("github_pages_auditor.tls.dias_restantes", lambda *a, **k: 5)
    from conftest import FakeResponse as R
    instalar(handler(web=lambda u: R(404) if u.endswith("/404.html") else R(200)))
    _, d = ejecutar(tmp_path)
    web = next(r for r in d["repos"] if r["name"] == "web")
    assert web["pages"]["tls_days_left"] == 5
    assert "tls-caduca-pronto" in web["pages"]["warnings"]
    assert "sin-404-personalizada" in web["pages"]["warnings"]


def test_homepage_distinta(instalar, tmp_path):
    repos = [dict(RICOS[0], homepage="https://otro.example/")]
    instalar(handler(repos))
    _, d = ejecutar(tmp_path)
    assert "homepage-distinta" in d["repos"][0]["pages"]["warnings"]


# ------------------------------------------------------------ F. baseline / github / config
def test_baseline_sin_nuevos_no_falla(instalar, tmp_path):
    instalar(handler())
    _, previo = ejecutar(tmp_path, "--fail-on", "community")
    ruta = tmp_path / "base.json"
    ruta.write_text(json.dumps(previo), encoding="utf-8")
    codigo, d = ejecutar(tmp_path, "--fail-on", "community", "--baseline", str(ruta))
    assert codigo == 0 and d["baseline"]["new_findings"] == {}


def test_baseline_invalido_sale_con_2(instalar, tmp_path):
    instalar(handler())
    ruta = tmp_path / "mal.json"
    ruta.write_text("[1]", encoding="utf-8")
    assert ejecutar(tmp_path, "--baseline", str(ruta))[0] == 2
    assert ejecutar(tmp_path, "--baseline", str(tmp_path / "no.json"))[0] == 2


def test_baseline_nuevos_funcion():
    assert baseline.nuevos({"a": ["x", "y"], "b": ["z"]}, {"a": ["x"]}) == {"a": ["y"], "b": ["z"]}


def test_formato_github(instalar, tmp_path):
    instalar(handler())
    codigo, txt = ejecutar(tmp_path, "--fail-on", "missing-security-policy", fmt="github")
    assert "::error title=missing-security-policy::web:" in txt
    assert "::warning title=" in txt


def test_github_escapa():
    r = RepoInfo("a", error="x\ny%")
    rep = AuditReport("u", "d", "API", [r], "api")
    out = formatters.a_github(rep, {"analysis-errors": ["a"]}, ())
    assert "%0A" in out and "%25" in out and out.count("\n") == 1


def test_config_toml(instalar, tmp_path, monkeypatch):
    pytest.importorskip("tomllib") if sys.version_info >= (3, 11) else pytest.importorskip("tomli")
    instalar(handler())
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".github-pages-auditor.toml").write_text('sort = "stars"\nignore = ["lib"]\n', encoding="utf-8")
    _, d = ejecutar(tmp_path)
    assert d["repos"][0]["name"] == "roto" and "lib" not in [r["name"] for r in d["repos"]]
    _, d = ejecutar(tmp_path, "--no-config")
    assert "lib" in [r["name"] for r in d["repos"]]
    _, d = ejecutar(tmp_path, "--sort", "name")  # CLI gana al archivo
    assert d["repos"][0]["name"] == "bifurcado"


def test_config_rechaza_token_y_claves_desconocidas(tmp_path, monkeypatch, capsys):
    pytest.importorskip("tomllib") if sys.version_info >= (3, 11) else pytest.importorskip("tomli")
    monkeypatch.chdir(tmp_path)
    for contenido in ('token = "ghp_x"\n', 'cosa = 1\n'):
        (tmp_path / ".github-pages-auditor.toml").write_text(contenido, encoding="utf-8")
        with pytest.raises(SystemExit) as e:
            cli.main(["-u", "ana", "-k", "t", "--no-env", "-q"])
        assert e.value.code == 2


# ------------------------------------------------------------ L. details / md
def test_details_en_markdown_y_txt(instalar, tmp_path):
    instalar(handler())
    _, md = ejecutar(tmp_path, "--details", fmt="md")
    assert "Estrellas" in md
    _, txt = ejecutar(tmp_path, "--details", fmt="txt")
    assert "DETALLES POR REPOSITORIO" in txt and "stars=3" in txt
