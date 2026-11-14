"""Pruebas manuales 9.x: usan el python-dotenv REAL sobre un .env temporal."""
import pytest
from dotenv import load_dotenv as dotenv_real

from github_pages_auditor import config

VARIABLES = ("USUARIO_GITHUB", "DOMINIO_WEB", "GITHUB_TOKEN", "ARCHIVO_SALIDA")


@pytest.fixture
def con_dotenv(monkeypatch, tmp_path):
    for v in VARIABLES:  # setenv + delenv: al terminar, monkeypatch deja el entorno como estaba
        monkeypatch.setenv(v, "x")
        monkeypatch.delenv(v)
    monkeypatch.setattr(config, "load_dotenv", dotenv_real)
    monkeypatch.chdir(tmp_path)

    def escribir(texto):
        (tmp_path / ".env").write_text(texto, encoding="utf-8")
    return escribir


def test_9_1_solo_con_env_funciona_sin_parametros(con_dotenv):
    con_dotenv("USUARIO_GITHUB=ana\n")
    c = config.parse_args([])
    assert c.usuario == "ana" and not c.usa_api


def test_9_2_no_env_ignora_el_archivo(con_dotenv):
    con_dotenv("USUARIO_GITHUB=ana\n")
    with pytest.raises(SystemExit) as e:
        config.parse_args(["--no-env"])
    assert e.value.code == 2


def test_9_3_los_parametros_ganan_al_env(con_dotenv):
    con_dotenv("USUARIO_GITHUB=otro\n")
    assert config.parse_args(["-u", "ana"]).usuario == "ana"


def test_9_4_variables_vacias_se_ignoran(con_dotenv):
    con_dotenv("USUARIO_GITHUB=ana\nGITHUB_TOKEN=\nDOMINIO_WEB=\n")
    c = config.parse_args([])
    assert c.github_token is None and not c.usa_api and c.dominio_web == "https://ana.github.io"


def test_9_5_el_env_se_busca_en_el_directorio_actual(con_dotenv, tmp_path, monkeypatch):
    con_dotenv("USUARIO_GITHUB=desde_cwd\n")
    sub = tmp_path / "sub"
    sub.mkdir()
    monkeypatch.chdir(sub)  # find_dotenv sube por los directorios padre
    assert config.parse_args([]).usuario == "desde_cwd"
