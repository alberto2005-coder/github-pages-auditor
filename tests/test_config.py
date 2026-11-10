import pytest
from ver_github_pages.config import parse_args

def test_parse_args_usuario_obligatorio(monkeypatch):
    monkeypatch.delenv("USUARIO_GITHUB", raising=False)
    with pytest.raises(SystemExit):
        parse_args([])

def test_parse_args_flags_consola():
    cfg = parse_args(["-u", "alberto2005-coder", "-w", "https://mi-dominio.dev", "-k", "ghp_12345"])
    assert cfg.usuario == "alberto2005-coder"
    assert cfg.dominio_web == "https://mi-dominio.dev"
    assert cfg.github_token == "ghp_12345"