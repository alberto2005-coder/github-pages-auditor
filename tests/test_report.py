import pytest
from ver_github_pages.models import AuditReport, RepoInfo
from ver_github_pages.report import exportar_txt

def test_exportar_txt(tmp_path):
    d = tmp_path / "sub"
    d.mkdir()
    file_path = d / "reporte_test.txt"

    repo = RepoInfo(nombre="repo-test", tiene_pages=True, url_pages="https://albertoortiz.is-a.dev/repo-test/")
    report = AuditReport(
        usuario="alberto2005-coder",
        dominio_base="https://albertoortiz.is-a.dev",
        proveedor="API REST de GitHub (Autenticado)",
        repos=[repo]
    )

    exportar_txt(report, str(file_path))

    assert file_path.exists()
    content = file_path.read_text(encoding="utf-8")
    assert "alberto2005-coder" in content
    assert "repo-test" in content
    assert "https://albertoortiz.is-a.dev/repo-test/" in content