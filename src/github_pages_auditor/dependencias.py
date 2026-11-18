"""``--dep-licenses``: dependencias con licencia copyleft fuerte (GPL/AGPL), leyendo los manifiestos del repo.

Solo lee ``pyproject.toml``, ``requirements.txt`` y ``package.json`` y consulta los registros públicos de PyPI y npm
(solo lectura, sin enviar datos del repo). Con un máximo de dependencias por repo; si algo falla, no se afirma nada.
"""
import json
import re
from typing import Callable, List, Optional, Set

import requests

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover  (Python 3.10)
    import tomli as tomllib

MAX_DEPENDENCIAS = 30
_NOMBRE = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")
_COPYLEFT = re.compile(r"\b(a?gpl)\b|gnu (affero )?general public", re.I)
_DEBIL = re.compile(r"lgpl|lesser|library general", re.I)


def es_copyleft(licencia: Optional[str]) -> bool:
    """GPL / AGPL (no LGPL, que permite enlazar desde software con otra licencia)."""
    if not licencia or _DEBIL.search(licencia):
        return False
    return bool(_COPYLEFT.search(licencia))


def _requisito(linea: str) -> Optional[str]:
    linea = linea.split("#", 1)[0].strip()
    if not linea or linea.startswith(("-", "git+", "http")):
        return None
    m = _NOMBRE.match(linea)
    return m.group(1) if m else None


def leer_manifiestos(leer: Callable[[str], Optional[str]]):
    """Devuelve ``(python, node)``: nombres de dependencias directas de cada ecosistema."""
    python: List[str] = []
    texto = leer("pyproject.toml")
    if texto:
        try:
            proyecto = tomllib.loads(texto).get("project", {})
            python += [n for n in (_requisito(str(d)) for d in proyecto.get("dependencies", [])) if n]
        except (tomllib.TOMLDecodeError, AttributeError, TypeError):
            pass
    texto = leer("requirements.txt")
    if texto:
        python += [n for n in (_requisito(linea) for linea in texto.splitlines()) if n]
    node: List[str] = []
    texto = leer("package.json")
    if texto:
        try:
            deps = json.loads(texto).get("dependencies", {})
            node = [str(n) for n in deps] if isinstance(deps, dict) else []
        except (json.JSONDecodeError, AttributeError):
            pass
    return list(dict.fromkeys(python)), list(dict.fromkeys(node))


def _licencia_pypi(session, nombre: str) -> Optional[str]:
    try:
        res = session.get(f"https://pypi.org/pypi/{nombre}/json")
        info = res.json().get("info", {}) if res.status_code == 200 else {}
    except (requests.RequestException, ValueError, AttributeError):
        return None
    clasificadores = [c for c in (info.get("classifiers") or []) if str(c).startswith("License ::")]
    return " ".join([str(info.get("license_expression") or info.get("license") or "")[:200]] + clasificadores) or None


def _licencia_npm(session, nombre: str) -> Optional[str]:
    try:
        res = session.get(f"https://registry.npmjs.org/{nombre}/latest")
        lic = res.json().get("license") if res.status_code == 200 else None
    except (requests.RequestException, ValueError, AttributeError):
        return None
    return str(lic)[:200] if isinstance(lic, (str, dict)) else None


def copyleft(session, leer: Callable[[str], Optional[str]]) -> Optional[List[str]]:
    """Dependencias con licencia GPL/AGPL como ``"nombre (licencia)"``; ``None`` si no hay manifiestos legibles."""
    python, node = leer_manifiestos(leer)
    if not python and not node:
        return None
    encontradas: List[str] = []
    vistas: Set[str] = set()
    for nombres, consulta in ((python, _licencia_pypi), (node, _licencia_npm)):
        for nombre in nombres[:MAX_DEPENDENCIAS]:
            if nombre in vistas:
                continue
            vistas.add(nombre)
            licencia = consulta(session, nombre)
            if es_copyleft(licencia):
                encontradas.append(f"{nombre} ({(licencia or '').strip()[:40]})")
    return encontradas
