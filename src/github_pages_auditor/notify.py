"""``--notify-webhook``: avisa por Discord, Slack o JSON genérico cuando hay hallazgos nuevos."""
from typing import Dict, List
from urllib.parse import urlparse

import requests

from .i18n import t


def componer(usuario: str, puntuacion, nuevos: Dict[str, List[str]]) -> str:
    total = sum(len(v) for v in nuevos.values())
    lineas = [t("notify_title", user=usuario, count=total, score="n/a" if puntuacion is None else puntuacion)]
    for regla, repos in nuevos.items():
        if repos:
            lineas.append(f"• {regla}: {', '.join(repos[:10])}{' …' if len(repos) > 10 else ''}")
    return "\n".join(lineas)[:1900]  # Discord admite 2000 caracteres


def cuerpo(url: str, texto: str, nuevos: Dict[str, List[str]]) -> dict:
    host = (urlparse(url).hostname or "").lower()
    if host.endswith(("discord.com", "discordapp.com")):
        return {"content": texto}
    if host.endswith("slack.com"):
        return {"text": texto}
    return {"text": texto, "content": texto, "findings": nuevos}


def avisar(url: str, usuario: str, puntuacion, nuevos: Dict[str, List[str]], session=None, timeout: float = 10.0) -> bool:
    """Envía el aviso si hay hallazgos nuevos. Devuelve True si se envió. Nunca lanza ni imprime la URL."""
    nuevos = {k: v for k, v in nuevos.items() if v}
    if not nuevos or not url.lower().startswith("https://"):
        return False
    try:
        res = (session or requests).post(url, json=cuerpo(url, componer(usuario, puntuacion, nuevos), nuevos),
                                         timeout=timeout)
        return 200 <= res.status_code < 300
    except requests.RequestException:
        return False
