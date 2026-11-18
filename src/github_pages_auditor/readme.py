"""``--readme-quality``: ¿el README explica cómo instalar y usar el proyecto? (heurística simple, sin red)."""
import re
from typing import List

MIN_CARACTERES = 300
_ENCABEZADO = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$", re.MULTILINE)
_INSTALACION = re.compile(r"instal|install|getting started|primeros pasos|quick ?start|setup|requisitos|requirements", re.I)
_USO = re.compile(r"\buso\b|usage|ejemplo|example|c[oó]mo usar|how to use|quick ?start|uso b[aá]sico", re.I)


def analizar(texto: str) -> List[str]:
    """Problemas del README: ``readme-corto``, ``sin-instalacion`` y ``sin-uso`` (lista vacía = está bien)."""
    problemas = []
    if len((texto or "").strip()) < MIN_CARACTERES:
        problemas.append("readme-corto")
    titulos = _ENCABEZADO.findall(texto or "")
    if not any(_INSTALACION.search(t) for t in titulos):
        problemas.append("sin-instalacion")
    if not any(_USO.search(t) for t in titulos):
        problemas.append("sin-uso")
    return problemas
