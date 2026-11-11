import re
from pathlib import Path

import pytest

from ver_github_pages import AUTOR, URL_GITHUB, URL_WEB, __version__, creditos
from ver_github_pages import main as cli
from ver_github_pages.errors import UsuarioNoEncontrado
from ver_github_pages.models import AuditReport, RepoInfo


def informe(*repos):
    return AuditReport("ana", "https://ana.dev", "Falso", list(repos))


def test_creditos_con_autor_y_enlaces():
    c = creditos()
    assert AUTOR in c and URL_GITHUB == "https://github.com/alberto2005-coder/" and URL_WEB == "https://albertoortiz.is-a.dev/"
    assert URL_GITHUB in c and URL_WEB in c


def test_help_incluye_creditos(capsys):
    with pytest.raises(SystemExit) as e:
        cli.main(["--help"])
    out = capsys.readouterr().out
    assert e.value.code == 0
    assert "Desarrollado por Alberto Ortiz" in out
    assert URL_GITHUB in out and URL_WEB in out
    for flag in ("--usuario", "--token", "--no-api", "--no-env", "--timeout", "--version"):
        assert flag in out


def test_version_incluye_creditos(capsys):
    with pytest.raises(SystemExit) as e:
        cli.main(["--version"])
    out = capsys.readouterr().out
    assert e.value.code == 0
    assert __version__ in out and URL_GITHUB in out and URL_WEB in out


def test_version_del_paquete_coincide_con_pyproject():
    toml = (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(encoding="utf-8")
    assert re.search(r'^version = "([^"]+)"', toml, re.M).group(1) == __version__


def test_ejecucion_correcta_escribe_informe_y_muestra_creditos(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(cli, "ejecutar_auditoria", lambda c, console=None: informe(
        RepoInfo("juego", tiene_pages=True, url_pages="https://ana.dev/juego/")))
    salida = tmp_path / "out.txt"
    assert cli.main(["-u", "ana", "-o", str(salida), "--no-color"]) == 0
    txt = salida.read_text(encoding="utf-8")
    assert "https://ana.dev/juego/" in txt and URL_WEB in txt
    out = capsys.readouterr().out
    assert "Desarrollado por Alberto Ortiz" in out and URL_GITHUB in out and URL_WEB in out


def test_sin_usuario_sale_con_2():
    with pytest.raises(SystemExit) as e:
        cli.main([])
    assert e.value.code == 2


def test_error_de_auditoria_da_2_y_no_escribe(monkeypatch, tmp_path, capsys):
    def falla(c, console=None):
        raise UsuarioNoEncontrado("no existe")

    monkeypatch.setattr(cli, "ejecutar_auditoria", falla)
    salida = tmp_path / "out.txt"
    assert cli.main(["-u", "x", "-o", str(salida)]) == 2
    assert not salida.exists()
    assert "no existe" in capsys.readouterr().err


def test_sin_repos_da_1_y_no_escribe(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "ejecutar_auditoria", lambda c, console=None: informe())
    salida = tmp_path / "out.txt"
    assert cli.main(["-u", "x", "-o", str(salida)]) == 1
    assert not salida.exists()


def test_ruta_de_salida_invalida_da_2(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "ejecutar_auditoria", lambda c, console=None: informe(RepoInfo("a")))
    assert cli.main(["-u", "x", "-o", str(tmp_path / "no_existe" / "o.txt")]) == 2


def test_ctrl_c_da_130(monkeypatch):
    def interrumpe(c, console=None):
        raise KeyboardInterrupt

    monkeypatch.setattr(cli, "ejecutar_auditoria", interrumpe)
    assert cli.main(["-u", "x"]) == 130


def test_carpeta_de_salida_inexistente_falla_antes_de_auditar(monkeypatch, tmp_path, capsys):
    llamadas = []
    monkeypatch.setattr(cli, "ejecutar_auditoria", lambda c, console=None: llamadas.append(1))
    assert cli.main(["-u", "x", "-o", str(tmp_path / "no_existe" / "o.txt")]) == 2
    assert llamadas == []  # no se pierde tiempo auditando
    assert "carpeta de salida" in capsys.readouterr().err
