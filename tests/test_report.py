from rich.console import Console

from github_pages_auditor import URL_GITHUB, URL_WEB, __version__
from github_pages_auditor.models import AuditReport, RepoInfo
from github_pages_auditor.report import exportar_txt, generar_txt, renderizar_consola

COMPLETO = RepoInfo("bueno", True, "https://a.dev/bueno/", True, True, True, True, True, False, False)
POBRE = RepoInfo("pobre", tiene_descripcion=False, es_fork=True, esta_archivado=True)
DESCONOCIDO = RepoInfo("raro", tiene_readme=True, tiene_licencia=True, tiene_gitignore=True)  # metadatos None
FALLO = RepoInfo("roto", error="timeout")


def informe(*repos):
    return AuditReport("ana", "https://a.dev", "API", list(repos))


def test_clasificacion():
    r = informe(COMPLETO, POBRE, DESCONOCIDO, FALLO)
    assert [x.nombre for x in r.con_pages] == ["bueno"]
    assert [x.nombre for x in r.sin_nada] == ["pobre", "raro"]
    assert [x.nombre for x in r.sin_descripcion] == ["pobre"]  # None = desconocido, no cuenta
    assert [x.nombre for x in r.forks] == ["pobre"] and [x.nombre for x in r.archivados] == ["pobre"]
    assert [x.nombre for x in r.con_error] == ["roto"]


def test_txt_contenido_y_creditos():
    t = generar_txt(informe(COMPLETO, POBRE, FALLO))
    assert "=== ENLACES DE GITHUB PAGES PARA: ana ===" in t
    assert "https://a.dev/bueno/" in t
    assert "=== REPOSITORIOS SIN README ===\n- pobre" in t
    assert "roto: timeout" in t
    assert f"v{__version__}" in t and URL_GITHUB in t and URL_WEB in t


def test_txt_sin_errores_no_tiene_esa_seccion():
    assert "NO ANALIZADOS" not in generar_txt(informe(COMPLETO))


def test_exportar_txt(tmp_path):
    ruta = tmp_path / "sub" / "r.txt"
    ruta.parent.mkdir()
    exportar_txt(informe(COMPLETO), str(ruta))
    assert "bueno" in ruta.read_text(encoding="utf-8")


def test_consola_muestra_tablas():
    c = Console(record=True, width=120, no_color=True)
    renderizar_consola(informe(COMPLETO, POBRE, FALLO), console=c)
    salida = c.export_text()
    assert "GitHub Pages Activas" in salida and "Resumen de Auditoría" in salida and "No analizados" in salida


def test_seccion_pages_con_avisos_en_txt():
    from github_pages_auditor.models import AuditReport, PagesHealth, RepoInfo
    from github_pages_auditor.report import generar_txt
    r = RepoInfo("a", tiene_pages=True, url_pages="https://u.dev/a/", pages_salud=PagesHealth(estado="ok", url="https://u.dev/a/", avisos=["https-no-forzado"]))
    rep = AuditReport("u", "https://u.github.io", "API", [r], "api")
    assert "GITHUB PAGES CON AVISOS" in generar_txt(rep) and "a: https-no-forzado" in generar_txt(rep)
