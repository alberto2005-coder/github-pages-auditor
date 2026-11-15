"""``--cache``: caché en disco con ETag para la API de GitHub (una respuesta 304 no gasta cuota)."""
import hashlib
import json
import os
from typing import Any, Optional

import requests

API = "https://api.github.com"


class SesionConCache:
    """Envuelve una sesión: solo cachea ``GET`` a api.github.com con respuesta 200 y ETag."""

    def __init__(self, session, carpeta: str):
        self._session = session
        self._carpeta = carpeta
        os.makedirs(carpeta, exist_ok=True)

    def __getattr__(self, nombre: str) -> Any:
        return getattr(self._session, nombre)

    def _ruta(self, url: str, kwargs: dict) -> str:
        params = json.dumps(kwargs.get("params") or {}, sort_keys=True)
        # El token distingue qué ve cada cuenta, pero nunca se guarda: solo entra en el hash de la clave.
        auth = (kwargs.get("headers") or {}).get("Authorization", "")
        clave = hashlib.sha256(f"{url}|{params}|{auth}".encode()).hexdigest()
        return os.path.join(self._carpeta, clave + ".json")

    def _leer(self, ruta: str) -> Optional[dict]:
        try:
            with open(ruta, encoding="utf-8") as f:
                datos = json.load(f)
            return datos if isinstance(datos, dict) and "etag" in datos and "text" in datos else None
        except (OSError, json.JSONDecodeError):
            return None

    def get(self, url: str, **kwargs):
        if not url.startswith(API) or kwargs.get("stream"):
            return self._session.get(url, **kwargs)
        ruta = self._ruta(url, kwargs)
        guardado = self._leer(ruta)
        if guardado:
            kwargs = {**kwargs, "headers": {**(kwargs.get("headers") or {}), "If-None-Match": guardado["etag"]}}
        res = self._session.get(url, **kwargs)
        if res.status_code == 304 and guardado:
            falsa = requests.Response()
            falsa.status_code = 200
            falsa._content = guardado["text"].encode("utf-8")
            falsa.headers.update({"ETag": guardado["etag"], "X-Cache": "hit"})
            falsa.url = url
            return falsa
        etag = (getattr(res, "headers", None) or {}).get("ETag")
        if res.status_code == 200 and etag:
            try:
                with open(ruta, "w", encoding="utf-8") as f:
                    json.dump({"etag": etag, "text": res.text}, f)
            except OSError:
                pass  # la caché es opcional: sin disco, se sigue sin ella
        return res
