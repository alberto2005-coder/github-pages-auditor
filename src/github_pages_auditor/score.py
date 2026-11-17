"""Nota de salud 0-100 por repositorio y global.

Categorías y pesos (suman 100): básicos 30 (README, licencia, descripción, .gitignore, Pages), release 10,
comunidad 30, actividad 20, seguridad 10. Una categoría sin datos (p. ej. comunidad en modo web) no cuenta:
los pesos de las demás se reescalan, así la nota es comparable con y sin token.
"""
from datetime import datetime, timezone
from typing import Dict, List, Optional, Sequence, Tuple

from .models import AuditReport, RepoInfo
from .pages_health import AVISOS_SIN_PUNTOS
from .rules import STALE_MESES_DEFECTO, _fecha

PESOS: Dict[str, int] = {"basicos": 30, "release": 10, "comunidad": 30, "actividad": 20, "seguridad": 10}
TRAMOS: Tuple[Tuple[int, str], ...] = ((90, "A"), (75, "B"), (60, "C"), (40, "D"))


def nota(puntos: Optional[int]) -> Optional[str]:
    """Letra A-E para una puntuación (``None`` si no hay puntuación)."""
    if puntos is None:
        return None
    return next((letra for minimo, letra in TRAMOS if puntos >= minimo), "E")


def _media(valores: Sequence[Optional[float]]) -> Optional[float]:
    conocidos = [v for v in valores if v is not None]
    return sum(conocidos) / len(conocidos) if conocidos else None


def _bool(v: Optional[bool]) -> Optional[float]:
    return None if v is None else (1.0 if v else 0.0)


def _basicos(r: RepoInfo) -> Optional[float]:
    partes: List[Optional[float]] = [_bool(r.tiene_readme), _bool(r.tiene_licencia),
                                     _bool(r.tiene_descripcion), _bool(r.tiene_gitignore)]
    if r.tiene_pages and r.pages_salud is not None:
        avisos = [a for a in r.pages_salud.avisos if a not in AVISOS_SIN_PUNTOS]
        partes.append(0.0 if r.pages_rota else max(0.0, 1.0 - 0.25 * len(avisos)))
    return _media(partes)


def _comunidad(r: RepoInfo) -> Optional[float]:
    return _media([_bool(r.tiene_security), _bool(r.tiene_contributing), _bool(r.tiene_code_of_conduct),
                   _bool(r.tiene_issue_template),
                   None if r.topics is None else (1.0 if r.topics else 0.0),
                   None if r.homepage is None else (1.0 if r.homepage else 0.0)])


def _actividad(r: RepoInfo, stale_meses: int, ahora: datetime) -> Optional[float]:
    ultimo = _fecha(r.ultimo_push)
    frescura = None
    if ultimo is not None:
        if ultimo.tzinfo is None:
            ultimo = ultimo.replace(tzinfo=timezone.utc)
        dias = (ahora - ultimo).days
        frescura = 1.0 if dias <= 90 else 0.8 if dias <= 180 else 0.5 if dias <= stale_meses * 30 else 0.0
    ci = None if r.ci_estado is None else (1.0 if r.ci_estado == "success" else 0.0 if r.ci_estado == "failure" else None)
    prs = None if r.prs_abiertas is None else (1.0 if r.prs_abiertas <= 3 else 0.0)
    return _media([frescura, ci, prs])


def _seguridad(r: RepoInfo) -> Optional[float]:
    dependencias = None
    if r.tiene_dependabot_yml is not None or r.alertas_dependabot is not None:
        dependencias = 1.0 if (r.tiene_dependabot_yml or r.alertas_dependabot) else 0.0
    vulnerabilidades = None
    if r.alertas_criticas is not None or r.alertas_altas is not None:
        vulnerabilidades = 0.0 if ((r.alertas_criticas or 0) + (r.alertas_altas or 0)) else 1.0
    scorecard = None if r.scorecard is None else min(1.0, r.scorecard / 10)
    return _media([dependencias, _bool(r.rama_protegida), _bool(r.secret_scanning), vulnerabilidades, scorecard])


def puntuar(r: RepoInfo, stale_meses: int = STALE_MESES_DEFECTO, ahora: Optional[datetime] = None) -> Optional[int]:
    """Nota 0-100 de un repo; ``None`` si falló el análisis."""
    if r.error:
        return None
    ahora = ahora or datetime.now(timezone.utc)
    categorias = {
        "basicos": _basicos(r),
        "release": _bool(r.tiene_releases),
        "comunidad": _comunidad(r),
        "actividad": _actividad(r, stale_meses, ahora),
        "seguridad": _seguridad(r),
    }
    conocidas = {k: v for k, v in categorias.items() if v is not None}
    if not conocidas:
        return None
    peso = sum(PESOS[k] for k in conocidas)
    return round(sum(PESOS[k] * v for k, v in conocidas.items()) / peso * 100)


def puntuar_informe(report: AuditReport, stale_meses: int = STALE_MESES_DEFECTO,
                    ahora: Optional[datetime] = None) -> Optional[int]:
    """Rellena ``puntuacion`` en cada repo y en el informe. La global ignora forks y archivados."""
    for r in report.repos:
        r.puntuacion = puntuar(r, stale_meses, ahora)
    propios = [r.puntuacion for r in report.repos
               if r.puntuacion is not None and not r.es_fork and not r.esta_archivado]
    report.puntuacion = round(sum(propios) / len(propios)) if propios else None
    return report.puntuacion


def ranking(report: AuditReport, n: int = 3) -> Tuple[List[RepoInfo], List[RepoInfo]]:
    """(mejores, peores): repos propios puntuados; desempata por nombre. Un repo no aparece en las dos listas."""
    propios = sorted((r for r in report.repos if r.puntuacion is not None and not r.es_fork and not r.esta_archivado),
                     key=lambda r: (-(r.puntuacion or 0), r.nombre.lower()))
    n = max(1, min(n, len(propios) // 2))  # con pocos repos, mitad y mitad
    mejores = propios[:n]
    peores = [r for r in reversed(propios) if r not in mejores][:n]
    return mejores, sorted(peores, key=lambda r: (r.puntuacion or 0, r.nombre.lower()))
