import pytest

from github_pages_auditor.models import PagesHealth, RepoInfo
from github_pages_auditor.rules import TODAS, disparadas, evaluar, parsear_fail_on

BUENO = RepoInfo("bueno", tiene_readme=True, tiene_licencia=True, tiene_gitignore=True, tiene_descripcion=True)
POBRE = RepoInfo("pobre", tiene_descripcion=False)
ROTO = RepoInfo("roto", tiene_readme=True, tiene_licencia=True, tiene_gitignore=True, tiene_descripcion=True,
                tiene_pages=True, url_pages="https://a.dev/roto/",
                pages_salud=PagesHealth("roto", "https://a.dev/roto/", problemas=["404"]))
FALLO = RepoInfo("fallo", error="timeout")


def test_parsear_fail_on():
    assert parsear_fail_on("missing-license, BROKEN-PAGES") == ("missing-license", "broken-pages")
    assert parsear_fail_on("any") == TODAS
    assert parsear_fail_on("missing-readme,missing-readme") == ("missing-readme",)
    assert parsear_fail_on("") == ()


def test_regla_desconocida():
    with pytest.raises(ValueError, match="desconocidas: nope"):
        parsear_fail_on("missing-license,nope")


def test_evaluar_incluye_todas_las_reglas():
    h = evaluar([BUENO, POBRE, ROTO, FALLO])
    assert set(h) == set(TODAS)
    assert h["missing-readme"] == ["pobre"] and h["missing-description"] == ["pobre"]
    assert h["broken-pages"] == ["roto"] and h["analysis-errors"] == ["fallo"]


def test_un_repo_fallido_no_cuenta_como_sin_readme():
    assert "fallo" not in evaluar([FALLO])["missing-readme"]


def test_disparadas_solo_las_pedidas_con_hallazgos():
    h = evaluar([BUENO, POBRE])
    assert disparadas(h, ["missing-license", "broken-pages"]) == ["missing-license"]
    assert disparadas(h, []) == []
    assert disparadas(evaluar([BUENO]), TODAS) == []
