"""``--scorecard``: puntuación de OpenSSF Scorecard (0-10) de cada repo público, desde su API pública."""
from typing import Optional

import requests

from .models import RepoInfo

URL = "https://api.securityscorecards.dev/projects/github.com/{owner}/{repo}"


def obtener(session, propietario: str, repo: RepoInfo) -> Optional[float]:
    """Nota de Scorecard o ``None`` (repo privado o fork, sin análisis todavía o servicio no disponible)."""
    if repo.privado or repo.es_fork or repo.error:
        return None
    try:
        res = session.get(URL.format(owner=propietario, repo=repo.nombre))
        if res.status_code != 200:
            return None
        datos = res.json()
    except (requests.RequestException, ValueError):
        return None
    puntos = datos.get("score") if isinstance(datos, dict) else None
    if isinstance(puntos, bool) or not isinstance(puntos, (int, float)) or not 0 <= puntos <= 10:
        return None
    return round(float(puntos), 1)
