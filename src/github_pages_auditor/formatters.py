"""Serializadores de salida: JSON (contrato versionado) y Markdown (índice de demos)."""
import json
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Sequence

from . import NOMBRE_PROGRAMA, URL_GITHUB, __version__
from .errors import ErrorSalida
from .i18n import t
from .models import AuditReport, RepoInfo, ruta_github
from .rules import REGLA_ERRORES
from .score import nota, ranking

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
            "tls_days_left": s.tls_dias,
            "broken_links": s.enlaces_rotos,
            "broken_pages": s.paginas_rotas,
            "size_bytes": s.peso_bytes,
        },
        "pages_url": r.url_pages,
        "has_releases": r.tiene_releases,
        "has_readme": r.tiene_readme,
        "has_license": r.tiene_licencia,
        "has_gitignore": r.tiene_gitignore,
        "has_description": r.tiene_descripcion,
        "stars": r.estrellas,
        "forks": r.forks_count,
        "open_issues": r.issues_abiertas,
        "language": r.lenguaje,
        "topics": r.topics,
        "license": r.licencia_spdx,
        "created_at": r.creado,
        "pushed_at": r.ultimo_push,
        "homepage": r.homepage,
        "latest_release": ({"tag": r.ultima_release, "date": r.fecha_release}
                           if r.ultima_release or r.fecha_release else None),
        "community": {
            "security_policy": r.tiene_security,
            "contributing": r.tiene_contributing,
            "code_of_conduct": r.tiene_code_of_conduct,
            "issue_template": r.tiene_issue_template,
        },
        "score": r.puntuacion,
        "grade": nota(r.puntuacion),
        "private": r.privado,
        "default_branch": r.rama_defecto,
        "deep": {
            "ci": r.tiene_ci,
            "ci_status": r.ci_estado,
            "dependabot_yml": r.tiene_dependabot_yml,
            "dependabot_alerts": r.alertas_dependabot,
            "secret_scanning": r.secret_scanning,
            "branch_protected": r.rama_protegida,
            "contributors": r.contribuidores,
            "open_prs": r.prs_abiertas,
            "critical_alerts": r.alertas_criticas,
            "high_alerts": r.alertas_altas,
        },
        "scorecard": r.scorecard,
        "readme_issues": r.readme_problemas,
        "copyleft_dependencies": r.deps_copyleft,
        "inherited_files": r.heredados,
        "custom": r.custom,
        "error": r.error,
    }


def _punt(r: RepoInfo) -> dict:
    return {"name": r.nombre, "score": r.puntuacion}


def a_dict(report: AuditReport, hallazgos: Dict[str, List[str]], fail_on: Sequence[str],
           disparadas: Sequence[str], ahora: Optional[datetime] = None,
           baseline: Optional[dict] = None, historial: Optional[dict] = None,
           arreglos: Optional[list] = None) -> dict:
    ahora = ahora or datetime.now(timezone.utc)
    mejores, peores = ranking(report)
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
            "score": report.puntuacion,
            "grade": nota(report.puntuacion),
        },
        "ranking": {"best": [_punt(r) for r in mejores], "worst": [_punt(r) for r in peores]},
        "findings": hallazgos,
        "fail_on": {"rules": list(fail_on), "triggered": list(disparadas)},
        "baseline": baseline,
        "history": historial,
        "fixes": arreglos,
        "repos": [_repo_a_dict(r) for r in report.repos],
    }


def a_json(report: AuditReport, hallazgos, fail_on, disparadas, ahora=None, solo_ascii=False,
           baseline=None, historial=None, arreglos=None) -> str:
    return json.dumps(a_dict(report, hallazgos, fail_on, disparadas, ahora, baseline, historial, arreglos),
                      indent=2, ensure_ascii=solo_ascii) + "\n"


# ------------------------------------------------------------- Markdown
def _celda(texto: Optional[str]) -> str:
    return " ".join((texto or "").replace("|", "\\|").split())


def bloque_markdown(report: AuditReport, incluir_forks: bool = False, detalles: bool = False) -> str:
    """Tabla de demos en vivo, entre marcadores, lista para un README de perfil."""
    vivas = sorted(
        (r for r in report.con_pages if incluir_forks or not r.es_fork),
        key=lambda r: r.nombre.lower(),
    )
    lineas = [MARCA_INICIO, f"## {t('md_title')}", ""]
    if vivas:
        if detalles:
            lineas += [f"| {t('md_project')} | {t('md_demo')} | {t('md_stars')} | {t('md_updated')} | {t('md_desc')} |",
                       "| --- | --- | ---: | --- | --- |"]
        else:
            lineas += [f"| {t('md_project')} | {t('md_demo')} | {t('md_desc')} |", "| --- | --- | --- |"]
        for r in vivas:
            desc = r.descripcion or (r.pages_salud.titulo if r.pages_salud else "")
            fila = (f"| [{_celda(r.nombre)}](https://github.com/{ruta_github(r, report.usuario)}) "
                    f"| [{t('md_open')}]({r.url_pages}) |")
            if detalles:
                fila += f" {'' if r.estrellas is None else r.estrellas} | {(r.ultimo_push or '')[:10]} |"
            lineas.append(f"{fila} {_celda(desc)} |")
    else:
        lineas.append(t('md_empty'))
    lineas += ["", f"<sub>{t('md_generated')} [{NOMBRE_PROGRAMA}]({URL_GITHUB}) v{__version__}</sub>", MARCA_FIN]
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


# --------------------------------------------------------------- GitHub Actions
def _esc_dato(texto: str) -> str:
    return texto.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def _esc_prop(texto: str) -> str:
    return _esc_dato(texto).replace(":", "%3A").replace(",", "%2C")


def a_github(report: AuditReport, hallazgos: Dict[str, List[str]], fail_on: Sequence[str]) -> str:
    """Anotaciones de flujo de trabajo (``::error::``/``::warning::``) para el log y el resumen de Actions."""
    por_nombre = {r.nombre: r for r in report.repos}
    lineas: List[str] = []
    for regla, repos in hallazgos.items():
        nivel = "error" if regla in fail_on else "warning"
        for nombre in repos:
            repo = por_nombre.get(nombre)
            if regla == REGLA_ERRORES:
                detalle = t("gh_error", error=repo.error if repo else "")
            elif regla == "broken-pages" and repo and repo.pages_salud:
                detalle = f"{t('rule.broken-pages')} ({', '.join(repo.pages_salud.problemas)})"
            else:
                detalle = t(f"rule.{regla}")
            lineas.append(f"::{nivel} title={_esc_prop(regla)}::{_esc_dato(f'{nombre}: {detalle}')}")
    for r in report.pages_con_avisos:
        avisos = r.pages_salud.avisos if r.pages_salud else []
        lineas.append(f"::notice title=pages-warning::{_esc_dato(f'{r.nombre}: ' + ', '.join(avisos))}")
    if not lineas:
        lineas.append(f"::notice title={NOMBRE_PROGRAMA}::"
                      + _esc_dato(t("gh_none", total=report.total_repos, user=report.usuario)))
    return "\n".join(lineas) + "\n"
