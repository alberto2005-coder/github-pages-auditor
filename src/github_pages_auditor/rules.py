"""Reglas evaluables para ``--fail-on`` (y para la sección ``findings`` del JSON)."""
from typing import Callable, Dict, List, Sequence

from .models import RepoInfo

# id estable (parte del contrato público) -> (descripción, predicado "hay hallazgo")
REGLAS: Dict[str, tuple] = {
    "missing-readme": ("Repositorio sin README", lambda r: not r.tiene_readme),
    "missing-license": ("Repositorio sin licencia", lambda r: not r.tiene_licencia),
    "missing-gitignore": ("Repositorio sin .gitignore", lambda r: not r.tiene_gitignore),
    "missing-description": ("Repositorio sin descripción (About)", lambda r: r.tiene_descripcion is False),
    "broken-pages": ("GitHub Pages activadas pero rotas", lambda r: r.pages_rota),
}
REGLA_ERRORES = "analysis-errors"  # repos que no se pudieron analizar (red)
TODAS = tuple(REGLAS) + (REGLA_ERRORES,)


def parsear_fail_on(texto: str) -> Sequence[str]:
    """'missing-license,broken-pages' | 'any' -> tupla validada de ids."""
    ids = [t.strip().lower() for t in texto.split(",") if t.strip()]
    if "any" in ids:
        return TODAS
    desconocidas = [i for i in ids if i not in TODAS]
    if desconocidas:
        raise ValueError(
            f"reglas desconocidas: {', '.join(desconocidas)}. Válidas: any, {', '.join(TODAS)}"
        )
    return tuple(dict.fromkeys(ids))


def evaluar(repos: List[RepoInfo]) -> Dict[str, List[str]]:
    """Devuelve {regla: [repos con hallazgo]} para TODAS las reglas (listas vacías incluidas)."""
    analizados = [r for r in repos if not r.error]
    resultado = {rid: [r.nombre for r in analizados if pred(r)] for rid, (_, pred) in REGLAS.items()}
    resultado[REGLA_ERRORES] = [r.nombre for r in repos if r.error]
    return resultado


def disparadas(hallazgos: Dict[str, List[str]], fail_on: Sequence[str]) -> List[str]:
    return [rid for rid in fail_on if hallazgos.get(rid)]
