import pytest

from ver_github_pages.config import normalizar_dominio, parse_args


def test_usuario_obligatorio():
    with pytest.raises(SystemExit) as e:
        parse_args([])
    assert e.value.code == 2


def test_solo_parametros_sin_env():
    c = parse_args(["-u", "ana", "-w", "ana.dev", "-k", "tk", "-o", "x.txt", "--workers", "4", "--timeout", "3"])
    assert (c.usuario, c.dominio_web, c.github_token, c.archivo_salida) == ("ana", "https://ana.dev", "tk", "x.txt")
    assert c.max_workers == 4 and c.timeout == 3 and c.usa_api


def test_alias_largos():
    c = parse_args(["--user", "ana", "--dominio", "https://a.dev/", "--token", "t"])
    assert c.usuario == "ana" and c.dominio_web == "https://a.dev" and c.github_token == "t"


def test_solo_entorno(monkeypatch):
    monkeypatch.setenv("USUARIO_GITHUB", "bob")
    monkeypatch.setenv("DOMINIO_WEB", "https://b.dev")
    monkeypatch.setenv("GITHUB_TOKEN", "envtk")
    monkeypatch.setenv("ARCHIVO_SALIDA", "o.txt")
    c = parse_args([])
    assert (c.usuario, c.dominio_web, c.github_token, c.archivo_salida) == ("bob", "https://b.dev", "envtk", "o.txt")


def test_parametros_ganan_al_entorno(monkeypatch):
    monkeypatch.setenv("USUARIO_GITHUB", "bob")
    monkeypatch.setenv("GITHUB_TOKEN", "env")
    c = parse_args(["-u", "ana", "-k", "cli"])
    assert c.usuario == "ana" and c.github_token == "cli"


def test_defectos():
    c = parse_args(["-u", "ana"])
    assert c.dominio_web == "https://ana.github.io"
    assert c.github_token is None and not c.usa_api
    assert c.archivo_salida == "paginas_github.txt" and c.max_workers == 15


def test_variables_vacias_equivalen_a_no_definidas(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "  ")
    monkeypatch.setenv("ARCHIVO_SALIDA", "")
    monkeypatch.setenv("DOMINIO_WEB", "")
    c = parse_args(["-u", "ana"])
    assert c.github_token is None and c.archivo_salida == "paginas_github.txt"
    assert c.dominio_web == "https://ana.github.io"


def test_no_api_fuerza_web():
    assert not parse_args(["-u", "a", "-k", "t", "--no-api"]).usa_api


def test_no_env_no_carga_dotenv(monkeypatch):
    llamadas = []
    monkeypatch.setattr("ver_github_pages.config.load_dotenv", lambda *a, **k: llamadas.append(1))
    parse_args(["-u", "a", "--no-env"])
    assert llamadas == []
    parse_args(["-u", "a"])
    assert llamadas == [1]


@pytest.mark.parametrize("flag", ["--workers", "--timeout"])
def test_valores_invalidos(flag):
    with pytest.raises(SystemExit):
        parse_args(["-u", "a", flag, "0"])


def test_normalizar_dominio():
    assert normalizar_dominio("x.dev/", "u") == "https://x.dev"
    assert normalizar_dominio("http://x.dev", "u") == "http://x.dev"
    assert normalizar_dominio("", "u") == "https://u.github.io"
    assert normalizar_dominio(None, "u") == "https://u.github.io"
