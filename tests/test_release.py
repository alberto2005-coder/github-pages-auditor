"""Higiene de release: si algo de esto falla, la publicación en PyPI fallaría o saldría mal."""
import re
import pytest
from pathlib import Path

tomllib = pytest.importorskip("tomllib")  # Python 3.10 no la trae; el resto del CI sí la ejecuta

from github_pages_auditor import __version__
from github_pages_auditor import formatters
from github_pages_auditor.models import AuditReport, PagesHealth, RepoInfo
from github_pages_auditor.rules import evaluar

RAIZ = Path(__file__).resolve().parents[1]
leer = lambda p: (RAIZ / p).read_text(encoding="utf-8")  # noqa: E731


def test_changelog_tiene_la_version_actual():
    assert re.search(rf"^## \[{re.escape(__version__)}\] - \d{{4}}-\d{{2}}-\d{{2}}", leer("CHANGELOG.md"), re.M)


def test_uv_lock_coincide_con_la_version():
    lock = tomllib.loads(leer("uv.lock"))
    paquete = next(p for p in lock["package"] if p["name"] == "github-pages-auditor")
    assert paquete["version"] == __version__  # el workflow usa --frozen: un lock viejo rompe la publicación


def test_metadatos_publicos():
    proyecto = tomllib.loads(leer("pyproject.toml"))["project"]
    assert proyecto["name"] == "github-pages-auditor" and proyecto["version"] == __version__
    assert all("email" not in a for a in proyecto["authors"] + proyecto.get("maintainers", []))
    assert set(proyecto["scripts"]) == {"github-pages-auditor", "ver-github-pages"}
    assert all(u.startswith("https://") for u in proyecto["urls"].values())


def test_classifiers_cubren_las_versiones_del_ci():
    ci = re.search(r"python: \[(.*?)\]", leer(".github/workflows/test.yml")).group(1)
    versiones = re.findall(r'"(3\.\d+)"', ci)
    clasificadores = tomllib.loads(leer("pyproject.toml"))["project"]["classifiers"]
    for v in versiones:
        assert f"Programming Language :: Python :: {v}" in clasificadores
    assert "3.14" in versiones


def test_workflow_de_publicacion_valida_tag_y_usa_trusted_publishing():
    wf = leer(".github/workflows/publish.yml")
    assert "release:" in wf and "id-token: write" in wf and "environment: pypi" in wf
    assert "uv publish --trusted-publishing always" in wf and "does not match" in wf


def test_readme_enlaces_absolutos_a_docs_y_sin_tokens_ghp():
    readme = leer("README.md")
    assert "ghp_" not in readme
    base = "https://github.com/alberto2005-coder/github-pages-auditor/blob/master/docs/"
    assert f"({base}json-schema.md)" in readme and f"({base}ci.md)" in readme
    assert (RAIZ / "docs/json-schema.md").exists() and (RAIZ / "docs/ci.md").exists()


def test_el_nombre_antiguo_solo_aparece_como_alias():
    for ruta in ("README.md", "pyproject.toml", "CHANGELOG.md"):
        for linea in leer(ruta).splitlines():
            if "ver-github-pages" in linea:
                assert any(p in linea.lower() for p in ("alias", "antiguo", "old", "compat", "renombrado", "renamed", "ver-github-pages =")), linea


def test_la_documentacion_del_json_cubre_todos_los_campos():
    repo = RepoInfo("a", tiene_pages=True, url_pages="https://u.dev/a/",
                    pages_salud=PagesHealth(estado="ok", url="https://u.dev/a/"))
    rep = AuditReport("u", "https://u.github.io", "API", [repo], "api")
    datos = formatters.a_dict(rep, evaluar(rep.repos), (), ())
    doc = leer("docs/json-schema.md")
    claves = set(datos) | set(datos["tool"]) | set(datos["summary"]) | set(datos["fail_on"]) | set(datos["findings"])
    claves |= set(datos["repos"][0]) | set(datos["repos"][0]["pages"])
    faltan = [k for k in claves if f"`{k}`" not in doc]
    assert not faltan, f"docs/json-schema.md no documenta: {faltan}"
    assert f"`schema_version: {datos['schema_version']}`" in doc
