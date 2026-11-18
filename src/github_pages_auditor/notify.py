"""``--notify-webhook``: avisa por Discord, Slack o JSON genérico cuando hay hallazgos nuevos."""
import time
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
    if host.endswith(("slack.com", "office.com", "logic.azure.com", "webhook.office365.com")):  # Slack y Teams
        return {"text": texto}
    return {"text": texto, "content": texto, "findings": nuevos}


def _enviar(url: str, texto: str, nuevos: Dict[str, List[str]], session, timeout: float) -> bool:
    """POST con un solo reintento si el servicio responde 429 o 5xx. Nunca lanza."""
    for intento in (1, 2):
        try:
            res = (session or requests).post(url, json=cuerpo(url, texto, nuevos), timeout=timeout)
        except requests.RequestException:
            return False
        if 200 <= res.status_code < 300:
            return True
        if intento == 2 or not (res.status_code == 429 or res.status_code >= 500):
            return False
        time.sleep(1)
    return False


def avisar(url: str, usuario: str, puntuacion, nuevos: Dict[str, List[str]], session=None, timeout: float = 10.0,
           siempre: bool = False) -> bool:
    """Envía el aviso si hay hallazgos nuevos (o siempre, con ``siempre``). Devuelve True si se envió.

    Nunca lanza ni imprime la URL.
    """
    nuevos = {k: v for k, v in nuevos.items() if v}
    if not url.lower().startswith("https://") or not (nuevos or siempre):
        return False
    texto = componer(usuario, puntuacion, nuevos) if nuevos else t(
        "notify_ok", user=usuario, score="n/a" if puntuacion is None else puntuacion)
    return _enviar(url, texto, nuevos, session, timeout)


def probar(url: str, session=None, timeout: float = 10.0) -> bool:
    """``--notify-test``: manda un mensaje de prueba. True si el servicio lo aceptó."""
    if not url.lower().startswith("https://"):
        return False
    return _enviar(url, t("notify_test"), {}, session, timeout)
