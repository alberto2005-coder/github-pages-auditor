import json
from datetime import datetime, timezone

import pytest

from github_pages_auditor import __version__
from github_pages_auditor.errors import ErrorSalida
from github_pages_auditor.formatters import MARCA_FIN, MARCA_INICIO, a_dict, a_json, bloque_markdown, inyectar
from github_pages_auditor.models import AuditReport, PagesHealth, RepoInfo
from github_pages_auditor.rules import TODAS, disparadas, evaluar

AHORA = datetime(2026, 11, 11, 12, 0, 0, tzinfo=timezone.utc)
SALUD = PagesHealth("ok", "https://a.dev/z/", "https://a.dev/z/", 200, 120, "Titulo Z")
VIVA = RepoInfo("zeta", True, "https://a.dev/z/", descripcion="Una | demo", pages_salud=SALUD,
                tiene_readme=True, tiene_licencia=True, tiene_gitignore=True, tiene_descripcion=True)
VIVA2 = RepoInfo("Alfa", True, "https://a.dev/a/", tiene_readme=True, pages_salud=PagesHealth("ok", "u", "u", titulo="Del titulo"))
FORK = RepoInfo("forked", True, "https://a.dev/f/", es_fork=True)


def informe(*repos):
    return AuditReport("ana", "https://a.dev", "API", list(repos), modo="api")


def test_json_contrato_y_determinismo():
    r = informe(VIVA, RepoInfo("sin"))
    h = evaluar(r.repos)
    a = a_json(r, h, ("missing-license",), disparadas(h, ("missing-license",)), AHORA)
    assert a == a_json(r, h, ("missing-license",), ["missing-license"], AHORA)
    d = json.loads(a)
    assert d["schema_version"] == 1 and d["tool"]["version"] == __version__
    assert d["generated_at"] == "2026-11-11T12:00:00Z" and d["mode"] == "api" and d["user"] == "ana"
    assert d["summary"]["total"] == 2 and d["summary"]["pages_live"] == 1 and d["summary"]["missing_license"] == 1
    assert set(d["findings"]) == set(TODAS)
    assert d["fail_on"] == {"rules": ["missing-license"], "triggered": ["missing-license"]}
    z = d["repos"][0]
    assert z["name"] == "zeta" and z["pages"]["status"] == "ok" and z["pages"]["title"] == "Titulo Z"
    assert d["repos"][1]["pages"] is None


def test_json_conserva_acentos_sin_escapar():
    r = informe(RepoInfo("ñandú", descripcion="canción"))
    assert "canción" in a_json(r, evaluar(r.repos), (), [], AHORA)


def test_markdown_tabla_ordenada_y_escapada():
    md = bloque_markdown(informe(VIVA, VIVA2, FORK))
    assert md.startswith(MARCA_INICIO) and md.strip().endswith(MARCA_FIN)
    assert md.index("Alfa") < md.index("zeta")           # orden alfabético, sin distinguir mayúsculas
    assert "forked" not in md                           # los forks no son tus demos
    assert "Una \\| demo" in md                         # la tubería se escapa
    assert "Del titulo" in md                           # sin descripción -> título de la página
    assert "[Abrir](https://a.dev/z/)" in md


def test_markdown_sin_demos():
    assert "Todavía no hay demos" in bloque_markdown(informe(RepoInfo("x")))


def test_inyectar_reemplaza_y_es_idempotente():
    base = f"# Yo\n\nantes\n{MARCA_INICIO}\nviejo\n{MARCA_FIN}\ndespués\n"
    bloque = bloque_markdown(informe(VIVA))
    una = inyectar(base, bloque)
    assert "viejo" not in una and una.startswith("# Yo") and una.endswith("después\n")
    assert inyectar(una, bloque) == una


def test_inyectar_sin_marcadores_falla():
    with pytest.raises(ErrorSalida):
        inyectar("# README sin marcadores", "x")
