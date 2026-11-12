import pytest

from github_pages_auditor.config import normalizar_dominio, parse_args


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
    monkeypatch.setattr("github_pages_auditor.config.load_dotenv", lambda *a, **k: llamadas.append(1))
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


def test_formato_y_nombre_de_archivo_por_defecto():
    assert parse_args(["-u", "a"]).archivo_salida == "paginas_github.txt"
    assert parse_args(["-u", "a", "-f", "json"]).archivo_salida == "paginas_github.json"
    assert parse_args(["-u", "a", "-f", "md"]).archivo_salida == "paginas_github.md"
    assert parse_args(["-u", "a", "-f", "json", "-o", "x.json"]).archivo_salida == "x.json"


def test_salida_estandar():
    c = parse_args(["-u", "a", "-o", "-"])
    assert c.salida_estandar and c.archivo_salida == "-"


def test_fail_on_filtros_e_inject():
    c = parse_args(["-u", "a", "--fail-on", "missing-license,broken-pages", "--exclude-forks",
                    "--exclude-archived", "--inject", "README.md", "-q"])
    assert c.fail_on == ("missing-license", "broken-pages")
    assert c.excluir_forks and c.excluir_archivados and c.quiet
    assert c.inject == "README.md" and c.archivo_salida is None  # con --inject no hay informe salvo con -o


def test_inject_con_o_explicito_tambien_escribe_informe():
    assert parse_args(["-u", "a", "--inject", "R.md", "-o", "r.txt"]).archivo_salida == "r.txt"
