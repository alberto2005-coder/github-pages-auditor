import re
from pathlib import Path

import pytest

from github_pages_auditor import AUTOR, URL_GITHUB, URL_WEB, __version__, creditos
from github_pages_auditor import main as cli
from github_pages_auditor.errors import UsuarioNoEncontrado
from github_pages_auditor.models import AuditReport, RepoInfo


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


def test_sin_repos_da_3_y_no_escribe(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "ejecutar_auditoria", lambda c, console=None: informe())
    salida = tmp_path / "out.txt"
    assert cli.main(["-u", "x", "-o", str(salida)]) == 3
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


import json

from github_pages_auditor.formatters import MARCA_FIN, MARCA_INICIO
from github_pages_auditor.models import PagesHealth

MALO = RepoInfo("malo", tiene_readme=True, tiene_gitignore=True, tiene_descripcion=True)  # sin licencia
VIVO = RepoInfo("juego", True, "https://ana.dev/juego/", tiene_readme=True, tiene_licencia=True,
                tiene_gitignore=True, tiene_descripcion=True, descripcion="Un juego",
                pages_salud=PagesHealth("ok", "https://ana.dev/juego/", "https://ana.dev/juego/"))


def fijo(monkeypatch, *repos):
    monkeypatch.setattr(cli, "ejecutar_auditoria", lambda c, console=None: informe(*repos))


def test_fail_on_disparado_da_1_pero_escribe_el_informe(monkeypatch, tmp_path):
    fijo(monkeypatch, MALO)
    salida = tmp_path / "o.json"
    assert cli.main(["-u", "x", "-f", "json", "-o", str(salida), "--fail-on", "missing-license", "--no-env"]) == 1
    d = json.loads(salida.read_text(encoding="utf-8"))
    assert d["fail_on"]["triggered"] == ["missing-license"]


def test_fail_on_sin_hallazgos_da_0(monkeypatch, tmp_path):
    fijo(monkeypatch, VIVO)
    assert cli.main(["-u", "x", "-o", str(tmp_path / "o.txt"), "--fail-on", "any", "--no-env"]) == 0


def test_sin_fail_on_los_hallazgos_no_cambian_el_exit_code(monkeypatch, tmp_path):
    fijo(monkeypatch, MALO)
    assert cli.main(["-u", "x", "-o", str(tmp_path / "o.txt"), "--no-env"]) == 0


def test_fail_on_con_regla_invalida_da_2():
    with pytest.raises(SystemExit) as e:
        cli.main(["-u", "x", "--fail-on", "inventada", "--no-env"])
    assert e.value.code == 2


def test_stdout_solo_contiene_el_json(monkeypatch, capsys):
    fijo(monkeypatch, VIVO)
    assert cli.main(["-u", "x", "-f", "json", "-o", "-", "--no-env", "--no-color"]) == 0
    captura = capsys.readouterr()
    assert json.loads(captura.out)["summary"]["pages_live"] == 1   # stdout = JSON puro, apto para jq
    assert "Resumen de Auditoría" in captura.err                    # la interfaz va a stderr


def test_formato_por_defecto_del_archivo(monkeypatch, tmp_path):
    fijo(monkeypatch, VIVO)
    monkeypatch.chdir(tmp_path)
    assert cli.main(["-u", "x", "-f", "md", "--no-env"]) == 0
    assert MARCA_INICIO in (tmp_path / "paginas_github.md").read_text(encoding="utf-8")


def test_inject_actualiza_readme_y_no_crea_informe(monkeypatch, tmp_path):
    fijo(monkeypatch, VIVO)
    monkeypatch.chdir(tmp_path)
    readme = tmp_path / "README.md"
    readme.write_text(f"# Hola\n{MARCA_INICIO}\nviejo\n{MARCA_FIN}\n", encoding="utf-8")
    assert cli.main(["-u", "x", "--inject", str(readme), "--no-env"]) == 0
    t = readme.read_text(encoding="utf-8")
    assert "viejo" not in t and "https://ana.dev/juego/" in t and t.startswith("# Hola")
    assert not (tmp_path / "paginas_github.txt").exists()


def test_inject_sin_marcadores_da_2_y_no_toca_el_archivo(monkeypatch, tmp_path):
    fijo(monkeypatch, VIVO)
    readme = tmp_path / "README.md"
    readme.write_text("# Sin marcas\n", encoding="utf-8")
    assert cli.main(["-u", "x", "--inject", str(readme), "--no-env"]) == 2
    assert readme.read_text(encoding="utf-8") == "# Sin marcas\n"


def test_inject_archivo_inexistente_da_2(monkeypatch, tmp_path):
    fijo(monkeypatch, VIVO)
    assert cli.main(["-u", "x", "--inject", str(tmp_path / "no.md"), "--no-env"]) == 2


def test_quiet_no_imprime_tablas(monkeypatch, tmp_path, capsys):
    fijo(monkeypatch, VIVO)
    assert cli.main(["-u", "x", "-o", str(tmp_path / "o.txt"), "-q", "--no-env"]) == 0
    assert "Resumen" not in capsys.readouterr().out


def test_comando_principal_y_alias_de_compatibilidad_apuntan_al_mismo_main():
    toml = (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(encoding="utf-8")
    assert 'github-pages-auditor = "github_pages_auditor.main:main"' in toml
    assert 'ver-github-pages = "github_pages_auditor.main:main"' in toml
    assert re.search(r'^name = "github-pages-auditor"', toml, re.M)


def test_json_por_stdout_es_ascii_y_valido(monkeypatch, capsys):
    import json
    from github_pages_auditor import formatters
    from github_pages_auditor.models import AuditReport, RepoInfo
    rep = AuditReport("u", "https://u.github.io", "API", [RepoInfo("a", descripcion="🎬 película")], "api")
    texto = formatters.a_json(rep, {}, (), (), solo_ascii=True)
    texto.encode("ascii")
    assert json.loads(texto)["repos"][0]["description"] == "🎬 película"
