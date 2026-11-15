"""``--history``: guarda cada informe JSON y lo compara con el anterior."""
import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from .errors import ErrorSalida


def _seguro(texto: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", texto)


def preparar(carpeta: str) -> None:
    try:
        os.makedirs(carpeta, exist_ok=True)
    except OSError as e:
        raise ErrorSalida(f"No se puede usar la carpeta de histórico '{carpeta}': {e}") from e


def ultimo(carpeta: str, usuario: str) -> Optional[Tuple[str, dict]]:
    """(ruta, informe) del informe guardado más reciente de ``usuario``; ``None`` si no hay o no se puede leer."""
    prefijo = _seguro(usuario) + "-"
    try:
        nombres = sorted(n for n in os.listdir(carpeta) if n.startswith(prefijo) and n.endswith(".json"))
    except OSError:
        return None
    for nombre in reversed(nombres):  # el más reciente que sea legible
        ruta = os.path.join(carpeta, nombre)
        try:
            with open(ruta, encoding="utf-8") as f:
                datos = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(datos, dict) and isinstance(datos.get("repos"), list):
            return ruta, datos
    return None


def guardar(carpeta: str, usuario: str, datos: Dict[str, Any], ahora: Optional[datetime] = None) -> str:
    ahora = ahora or datetime.now(timezone.utc)
    ruta = os.path.join(carpeta, f"{_seguro(usuario)}-{ahora.strftime('%Y%m%dT%H%M%SZ')}.json")
    try:
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=True, indent=2)
    except OSError as e:
        raise ErrorSalida(f"No se pudo guardar el histórico en '{ruta}': {e}") from e
    return ruta


def comparar(actual: Dict[str, Any], previo: Dict[str, Any], ruta_previa: str) -> Dict[str, Any]:
    """Diferencias de nota entre dos informes (``actual`` y ``previo`` con el formato de ``formatters.a_dict``)."""
    def notas(d: dict) -> Dict[str, Optional[int]]:
        return {str(r.get("name")): r.get("score") for r in d.get("repos", []) if isinstance(r, dict)}

    antes, ahora = notas(previo), notas(actual)
    mejoran: List[Dict[str, Any]] = []
    empeoran: List[Dict[str, Any]] = []
    for nombre in sorted(ahora, key=str.lower):
        a, b = antes.get(nombre), ahora[nombre]
        if a is None or b is None or a == b:
            continue
        (mejoran if b > a else empeoran).append({"name": nombre, "before": a, "after": b})
    antes_global = (previo.get("summary") or {}).get("score")
    ahora_global = (actual.get("summary") or {}).get("score")
    return {
        "previous_file": os.path.basename(ruta_previa),
        "previous_generated_at": previo.get("generated_at"),
        "score_before": antes_global,
        "score_after": ahora_global,
        "delta": None if antes_global is None or ahora_global is None else ahora_global - antes_global,
        "improved": mejoran,
        "worsened": empeoran,
        "new_repos": sorted((n for n in ahora if n not in antes), key=str.lower),
        "removed_repos": sorted((n for n in antes if n not in ahora), key=str.lower),
    }
