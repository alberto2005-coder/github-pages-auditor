"""Prueba de humo contra la API REAL de GitHub. Solo corre con RUN_LIVE=1 y GITHUB_TOKEN (ver el job ``live``)."""
import json
import os

import pytest

from github_pages_auditor import main as cli

pytestmark = [pytest.mark.live,
              pytest.mark.skipif(os.getenv("RUN_LIVE") != "1" or not os.getenv("GITHUB_TOKEN"),
                                 reason="solo con RUN_LIVE=1 y GITHUB_TOKEN")]


def test_auditoria_real_de_este_repositorio(tmp_path, monkeypatch):
    # Los tests desactivan el .env y el entorno: aquí queremos el token real.
    token = os.environ["GITHUB_TOKEN"]
    salida = tmp_path / "r.json"
    codigo = cli.main(["-u", "alberto2005-coder", "-k", token, "--no-env", "-q", "--only", "github-pages-auditor",
                       "-f", "json", "-o", str(salida)])
    datos = json.loads(salida.read_text(encoding="utf-8"))
    assert codigo == 0 and datos["mode"] == "api" and datos["repos"][0]["name"] == "github-pages-auditor"
    assert isinstance(datos["summary"]["score"], int) and datos["repos"][0]["latest_release"]
