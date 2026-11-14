"""``--baseline``: comparar los hallazgos con un informe JSON anterior."""
import json
from typing import Dict, List

from .errors import ErrorSalida


def cargar(ruta: str) -> Dict[str, List[str]]:
    """Lee la sección ``findings`` de un informe JSON generado por esta herramienta."""
    try:
        with open(ruta, encoding="utf-8") as f:
            datos = json.load(f)
    except OSError as e:
        raise ErrorSalida(f"No se puede leer el baseline '{ruta}': {e}") from e
    except json.JSONDecodeError as e:
        raise ErrorSalida(f"El baseline '{ruta}' no es un JSON válido: {e}") from e
    hallazgos = datos.get("findings") if isinstance(datos, dict) else None
    if not isinstance(hallazgos, dict):
        raise ErrorSalida(f"El baseline '{ruta}' no parece un informe de github-pages-auditor (falta 'findings').")
    return {str(regla): [str(r) for r in repos] for regla, repos in hallazgos.items() if isinstance(repos, list)}


def nuevos(hallazgos: Dict[str, List[str]], previo: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """Hallazgos de ``hallazgos`` que no estaban en ``previo`` (una regla ausente del baseline cuenta como vacía)."""
    return {regla: [r for r in repos if r not in set(previo.get(regla, []))] for regla, repos in hallazgos.items()}
