"""Protección de secretos: ocultar tokens en cualquier mensaje y avisar de malas prácticas.

Los tokens y webhooks nunca deben aparecer en pantalla, en el JSON ni en los logs de CI.
"""
import os
import re
import subprocess  # nosec: solo se llama a ``git ls-files`` con argumentos fijos
from typing import Optional

OCULTO = "***"
_PATRON = re.compile(
    r"github_pat_[A-Za-z0-9_]{20,}|gh[pousr]_[A-Za-z0-9]{20,}"
    r"|https://(?:discord(?:app)?\.com/api/webhooks|hooks\.slack\.com/services)/[^\s\"'<>]+"
)


def limpiar(texto: object, *secretos: Optional[str]) -> str:
    """Sustituye por ``***`` los tokens conocidos (por su forma) y los secretos concretos que se pasen."""
    resultado = _PATRON.sub(OCULTO, str(texto))
    for s in secretos:
        if s and len(s) >= 8:
            resultado = resultado.replace(s, OCULTO)
    return resultado


def enmascarar(token: Optional[str]) -> str:
    """``github_pat_…a1b2``: el tipo y los 4 últimos caracteres bastan para reconocer el token."""
    if not token:
        return ""
    prefijo = "github_pat_" if token.startswith("github_pat_") else (token[:4] if token.startswith("gh") else "")
    return f"{prefijo}…{token[-4:]}"


def tipo_token(token: Optional[str]) -> str:
    if not token:
        return "none"
    if token.startswith("github_pat_"):
        return "fine-grained"
    if token.startswith("ghp_"):
        return "classic"
    if token.startswith(("ghs_", "ghu_", "gho_", "ghr_")):
        return "app"
    return "unknown"


def env_versionado(carpeta: Optional[str] = None) -> Optional[bool]:
    """¿Está ``.env`` dentro del repositorio git? ``None`` si no hay ``.env``, no es un repo o no hay git."""
    carpeta = carpeta or os.getcwd()
    if not os.path.isfile(os.path.join(carpeta, ".env")):
        return None
    try:
        res = subprocess.run(["git", "ls-files", "--error-unmatch", ".env"], cwd=carpeta, capture_output=True,
                             timeout=5, check=False)  # noqa: S603,S607
    except (OSError, subprocess.SubprocessError):
        return None
    if res.returncode == 0:
        return True
    return False if b"did not match" in res.stderr or b"pathspec" in res.stderr else None
