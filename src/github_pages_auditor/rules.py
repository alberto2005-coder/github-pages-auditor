"""Reglas evaluables para ``--fail-on`` (y para la sección ``findings`` del JSON)."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Sequence

from .models import RepoInfo

STALE_MESES_DEFECTO = 12


@dataclass(frozen=True)
class Contexto:
    stale_meses: int = STALE_MESES_DEFECTO
    ahora: Optional[datetime] = None


def _fecha(texto: Optional[str]) -> Optional[datetime]:
    if not texto:
        return None
    try:
        return datetime.fromisoformat(texto.replace("Z", "+00:00"))
    except ValueError:
        return None


def _propio(r: RepoInfo) -> bool:
    """Las reglas de comunidad solo aplican a repos propios y vivos (ni forks ni archivados)."""
    return not r.es_fork and not r.esta_archivado


def _obsoleto(r: RepoInfo, ctx: Contexto) -> bool:
    ultimo = _fecha(r.ultimo_push)
    if ultimo is None or not _propio(r):
        return False
    ahora = ctx.ahora or datetime.now(timezone.utc)
    if ultimo.tzinfo is None:
        ultimo = ultimo.replace(tzinfo=timezone.utc)
    return ahora - ultimo > timedelta(days=30.44 * ctx.stale_meses)


# id estable (parte del contrato público) -> (descripción, predicado "hay hallazgo")
REGLAS_BASICAS: Dict[str, tuple] = {
    "missing-readme": ("Repositorio sin README", lambda r, c: not r.tiene_readme),
    "missing-license": ("Repositorio sin licencia", lambda r, c: not r.tiene_licencia),
    "missing-gitignore": ("Repositorio sin .gitignore", lambda r, c: not r.tiene_gitignore),
    "missing-description": ("Repositorio sin descripción (About)", lambda r, c: r.tiene_descripcion is False),
    "broken-pages": ("GitHub Pages activadas pero rotas", lambda r, c: r.pages_rota),
}
# Reglas de comunidad y actividad (1.3.0). Solo se evalúan cuando el dato es conocido (modo API).
REGLAS_COMUNIDAD: Dict[str, tuple] = {
    "missing-security-policy": ("Sin política de seguridad (SECURITY.md)",
                                lambda r, c: _propio(r) and r.tiene_security is False),
    "missing-contributing": ("Sin guía de contribución (CONTRIBUTING.md)",
                             lambda r, c: _propio(r) and r.tiene_contributing is False),
    "missing-code-of-conduct": ("Sin código de conducta (CODE_OF_CONDUCT.md)",
                                lambda r, c: _propio(r) and r.tiene_code_of_conduct is False),
    "missing-issue-template": ("Sin plantillas de issues",
                               lambda r, c: _propio(r) and r.tiene_issue_template is False),
    "missing-topics": ("Sin topics", lambda r, c: _propio(r) and r.topics is not None and not r.topics),
    "missing-homepage": ("Con Pages pero sin URL de la demo en el campo Website",
                         lambda r, c: _propio(r) and r.tiene_pages and r.homepage is not None and not r.homepage.strip()),
    "stale-repo": ("Sin actividad reciente", _obsoleto),
}
# Reglas de ``--deep`` (1.4.0): solo con el dato conocido (modo API con permisos suficientes).
REGLAS_PROFUNDAS: Dict[str, tuple] = {
    "missing-ci": ("Sin CI (GitHub Actions)", lambda r, c: _propio(r) and r.tiene_ci is False),
    "missing-dependabot": ("Sin Dependabot configurado",
                           lambda r, c: _propio(r) and r.tiene_dependabot_yml is False and r.alertas_dependabot is False),
    "failing-ci": ("El último workflow falla", lambda r, c: _propio(r) and r.ci_estado == "failure"),
    "stale-prs": ("Muchas PRs abiertas sin atender", lambda r, c: _propio(r) and (r.prs_abiertas or 0) > 3),
    "no-branch-protection": ("Rama principal sin protección", lambda r, c: _propio(r) and r.rama_protegida is False),
}
REGLAS: Dict[str, tuple] = {**REGLAS_BASICAS, **REGLAS_COMUNIDAD, **REGLAS_PROFUNDAS}
REGLA_ERRORES = "analysis-errors"  # repos que no se pudieron analizar (red)
BASICAS = tuple(REGLAS_BASICAS) + (REGLA_ERRORES,)  # lo que significa 'any' (como en 1.2)
COMUNIDAD = tuple(REGLAS_COMUNIDAD) + tuple(REGLAS_PROFUNDAS)
TODAS = BASICAS + COMUNIDAD  # 'all'


def parsear_fail_on(texto: str) -> Sequence[str]:
    """'missing-license,broken-pages' | 'any' | 'community' | 'all' -> tupla validada de ids."""
    ids = [t.strip().lower() for t in texto.split(",") if t.strip()]
    if "all" in ids:
        return TODAS
    resultado: List[str] = []
    desconocidas = []
    for i in ids:
        if i == "any":
            resultado += BASICAS
        elif i == "community":
            resultado += COMUNIDAD
        elif i in TODAS:
            resultado.append(i)
        else:
            desconocidas.append(i)
    if desconocidas:
        raise ValueError(
            f"reglas desconocidas: {', '.join(desconocidas)}. "
            f"Válidas: any, community, all, {', '.join(TODAS)}"
        )
    return tuple(dict.fromkeys(resultado))


def evaluar(repos: List[RepoInfo], stale_meses: int = STALE_MESES_DEFECTO,
            ahora: Optional[datetime] = None) -> Dict[str, List[str]]:
    """Devuelve {regla: [repos con hallazgo]} para TODAS las reglas (listas vacías incluidas)."""
    ctx = Contexto(stale_meses, ahora)
    analizados = [r for r in repos if not r.error]
    resultado = {rid: [r.nombre for r in analizados if pred(r, ctx)] for rid, (_, pred) in REGLAS.items()}
    resultado[REGLA_ERRORES] = [r.nombre for r in repos if r.error]
    return resultado


def disparadas(hallazgos: Dict[str, List[str]], fail_on: Sequence[str]) -> List[str]:
    return [rid for rid in fail_on if hallazgos.get(rid)]
