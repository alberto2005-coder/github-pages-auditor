"""Serializadores de salida: JSON (contrato versionado) y Markdown (índice de demos)."""
import json
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Sequence

from . import NOMBRE_PROGRAMA, URL_GITHUB, __version__
from .errors import ErrorSalida
from .models import AuditReport, RepoInfo

SCHEMA_VERSION = 1
MARCA_INICIO = "<!-- github-pages-auditor:start -->"
MARCA_FIN = "<!-- github-pages-auditor:end -->"


# ----------------------------------------------------------------- JSON
def _repo_a_dict(r: RepoInfo) -> dict:
    s = r.pages_salud
    return {
        "name": r.nombre,
        "description": r.descripcion,
        "fork": r.es_fork,
        "archived": r.esta_archivado,
        "has_pages": r.tiene_pages,
        "pages": None if s is None else {
            "status": s.estado,
            "url": r.url_pages,
            "http_status": s.http_status,
            "response_ms": s.ms,
            "title": s.titulo,
            "problems": s.problemas,
            "warnings": s.avisos,
        },
        "pages_url": r.url_pages,
        "has_releases": r.tiene_releases,
        "has_readme": r.tiene_readme,
        "has_license": r.tiene_licencia,
        "has_gitignore": r.tiene_gitignore,
        "has_description": r.tiene_descripcion,
        "error": r.error,
    }


def a_dict(report: AuditReport, hallazgos: Dict[str, List[str]], fail_on: Sequence[str],
           disparadas: Sequence[str], ahora: Optional[datetime] = None) -> dict:
    ahora = ahora or datetime.now(timezone.utc)
    return {
        "schema_version": SCHEMA_VERSION,
        "tool": {"name": NOMBRE_PROGRAMA, "version": __version__, "url": URL_GITHUB},
        "generated_at": ahora.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "user": report.usuario,
        "mode": report.modo,
        "domain": report.dominio_base,
        "summary": {
            "total": report.total_repos,
            "analyzed": report.total_repos - len(report.con_error),
            "pages_live": len(report.con_pages),
            "pages_broken": len(report.pages_rotas),
            "releases": len(report.con_releases),
            "no_pages_no_releases": len(report.sin_nada),
            "missing_readme": len(report.sin_readme),
            "missing_license": len(report.sin_licencia),
            "missing_gitignore": len(report.sin_gitignore),
            "missing_description": len(report.sin_descripcion),
            "forks": len(report.forks),
            "archived": len(report.archivados),
            "errors": len(report.con_error),
        },
        "findings": hallazgos,
        "fail_on": {"rules": list(fail_on), "triggered": list(disparadas)},
        "repos": [_repo_a_dict(r) for r in report.repos],
    }


def a_json(report: AuditReport, hallazgos, fail_on, disparadas, ahora=None, solo_ascii=False) -> str:
    return json.dumps(a_dict(report, hallazgos, fail_on, disparadas, ahora),
                      indent=2, ensure_ascii=solo_ascii) + "\n"


# ------------------------------------------------------------- Markdown
def _celda(texto: Optional[str]) -> str:
    return " ".join((texto or "").replace("|", "\\|").split())


def bloque_markdown(report: AuditReport, incluir_forks: bool = False) -> str:
    """Tabla de demos en vivo, entre marcadores, lista para un README de perfil."""
    vivas = sorted(
        (r for r in report.con_pages if incluir_forks or not r.es_fork),
        key=lambda r: r.nombre.lower(),
    )
    lineas = [MARCA_INICIO, "## Demos en vivo", ""]
    if vivas:
        lineas += ["| Proyecto | Demo | Descripción |", "| --- | --- | --- |"]
        for r in vivas:
            desc = r.descripcion or (r.pages_salud.titulo if r.pages_salud else "")
            lineas.append(f"| [{_celda(r.nombre)}](https://github.com/{report.usuario}/{r.nombre}) "
                          f"| [Abrir]({r.url_pages}) | {_celda(desc)} |")
    else:
        lineas.append("_Todavía no hay demos publicadas._")
    lineas += ["", f"<sub>Generado con [{NOMBRE_PROGRAMA}]({URL_GITHUB}) v{__version__}</sub>", MARCA_FIN]
    return "\n".join(lineas) + "\n"


def inyectar(texto: str, bloque: str) -> str:
    """Sustituye lo que haya entre los marcadores; falla si no existen (no adivina dónde escribir)."""
    patron = re.compile(re.escape(MARCA_INICIO) + r".*?" + re.escape(MARCA_FIN) + r"\n?", re.DOTALL)
    if not patron.search(texto):
        raise ErrorSalida(
            f"El archivo no contiene los marcadores {MARCA_INICIO} ... {MARCA_FIN}. "
            "Añádelos donde quieras la tabla y vuelve a ejecutar."
        )
    return patron.sub(lambda _m: bloque, texto, count=1)
