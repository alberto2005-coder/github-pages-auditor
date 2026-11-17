"""Pruebas de humo contra la API REAL de GitHub (solo lectura: nunca escriben nada).

Se ejecutan a mano, con tu token, en un solo comando (PowerShell)::

    $env:GITHUB_TOKEN = "..."; $env:RUN_LIVE = "1"; uv run pytest -m live -q

o desde Actions -> *Run workflow* (job ``live``). Sin ``RUN_LIVE=1`` y ``GITHUB_TOKEN`` se saltan.
Sustituyen a repetir a mano las pruebas de los comandos de lectura en cada versión; lo único que NO cubren
es una escritura real (``--fix ... --yes``), que solo hay que probar cuando cambia el código de ``fix.py``.
"""
import json
import os

import pytest

from github_pages_auditor import main as cli

pytestmark = [pytest.mark.live,
              pytest.mark.skipif(os.getenv("RUN_LIVE") != "1" or not os.getenv("GITHUB_TOKEN"),
                                 reason="solo con RUN_LIVE=1 y GITHUB_TOKEN")]

# El conftest borra GITHUB_TOKEN del entorno en cada test: se lee aquí, al importar el módulo, antes de que lo haga.
TOKEN = os.getenv("GITHUB_TOKEN", "")
USUARIO = os.getenv("LIVE_USER", "alberto2005-coder")
REPO = os.getenv("LIVE_REPO", "github-pages-auditor")


@pytest.fixture
def token():
    return TOKEN


def auditar(token, tmp_path, *args, fmt="json", nombre="r"):
    salida = tmp_path / f"{nombre}.{fmt}"
    codigo = cli.main(["-u", USUARIO, "-k", token, "--no-env", "-q", "--only", REPO, "-f", fmt, "-o", str(salida), *args])
    texto = salida.read_text(encoding="utf-8") if salida.exists() else ""
    return codigo, (json.loads(texto) if fmt == "json" and texto else texto)


def test_auditoria_real_de_este_repositorio(token, tmp_path):
    codigo, datos = auditar(token, tmp_path)
    assert codigo == 0 and datos["mode"] == "api" and datos["repos"][0]["name"] == REPO
    assert isinstance(datos["summary"]["score"], int) and datos["repos"][0]["latest_release"]
    assert datos["schema_version"] == 1


def test_modo_web_sin_token(tmp_path, monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    salida = tmp_path / "w.json"
    codigo = cli.main(["-u", USUARIO, "--no-env", "-q", "--only", REPO, "-f", "json", "-o", str(salida)])
    datos = json.loads(salida.read_text(encoding="utf-8"))
    assert codigo == 0 and datos["mode"] == "web" and datos["repos"][0]["name"] == REPO


def test_deep_y_scorecard(token, tmp_path):
    codigo, datos = auditar(token, tmp_path, "--deep", "--scorecard")
    repo = datos["repos"][0]
    assert codigo == 0 and {"ci", "dependabot_yml", "critical_alerts", "high_alerts"} <= set(repo["deep"])
    assert repo["deep"]["ci"] is True  # este repo tiene workflows
    assert repo["scorecard"] is None or 0 <= repo["scorecard"] <= 10


def test_regla_propia_comprueba_un_archivo_real(token, tmp_path):
    toml = tmp_path / "c.toml"
    toml.write_text('[[custom_rules]]\nid = "custom-live"\npath = "pyproject.toml"\n'
                    '[[custom_rules]]\nid = "custom-live-ausente"\npath = "no-existe-xyz"\n', encoding="utf-8")
    _, datos = auditar(token, tmp_path, "--config", str(toml))
    assert datos["repos"][0]["custom"] == {"custom-live": True, "custom-live-ausente": False}
    assert datos["findings"]["custom-live-ausente"] == [REPO] and datos["findings"]["custom-live"] == []


@pytest.mark.parametrize("fmt", ["html", "csv", "sarif", "badge", "md", "txt", "issue"])
def test_todos_los_formatos(token, tmp_path, fmt):
    codigo, texto = auditar(token, tmp_path, fmt=fmt)
    assert codigo == 0 and texto.strip()
    if fmt == "sarif":
        assert json.loads(texto)["version"] == "2.1.0"
    if fmt == "badge":
        assert texto.lstrip().startswith("<svg")
    if fmt == "html":
        assert "<!doctype html>" in texto.lower()


def test_historico_tendencia_y_diff(token, tmp_path):
    hist = tmp_path / "hist"
    for _ in range(2):
        assert auditar(token, tmp_path, "--history", str(hist))[0] == 0
    codigo, html = auditar(token, tmp_path, "--history", str(hist), fmt="trend", nombre="evolucion")
    assert codigo == 0 and "<svg" in html
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    auditar(token, tmp_path, nombre="a"), auditar(token, tmp_path, nombre="b")
    assert cli.main(["--diff", str(a), str(b), "--no-color"]) == 0


def test_arreglos_solo_se_planean_sin_yes(token, tmp_path):
    """Con ``--fix-extra --fix-mode pr`` y SIN ``--yes`` solo se muestra el plan: nunca se escribe."""
    codigo, datos = auditar(token, tmp_path, "--fix", "--fix-extra", "--fix-mode", "pr", "--fix-pages", "--fix-metadata")
    assert codigo == 0
    assert all(a["status"] == "planned" for a in datos.get("fixes", []))


def test_doctor_con_token_personal(token, capsys):
    if token.startswith(("ghs_", "ghu_")):
        pytest.skip("el token de Actions no es de una persona: /user no responde")
    codigo = cli.main(["--doctor", "-k", token, "--no-env", "-u", USUARIO, "--no-color"])
    salida = capsys.readouterr().out
    assert codigo in (0, 1) and "Diagnóstico del token" in salida and token not in salida
