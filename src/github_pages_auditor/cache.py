"""``--cache``: caché en disco con ETag para la API de GitHub (una respuesta 304 no gasta cuota)."""
import hashlib
import json
import os
import re
import threading
import time
from typing import Any, Optional

import requests

API = "https://api.github.com"
NOMBRE_CARPETA = "github-pages-auditor"
DIAS_CADUCIDAD = 30  # las entradas sin tocar más tiempo se borran solas
_ENTRADA = re.compile(r"^[0-9a-f]{64}\.json$")


def resolver_carpeta(valor: str) -> str:
    """``auto`` = la carpeta de caché del usuario (LOCALAPPDATA en Windows, XDG_CACHE_HOME o ~/.cache); si no, tal cual."""
    if valor.strip().lower() != "auto":
        return valor
    base = (os.environ.get("LOCALAPPDATA") or os.environ.get("XDG_CACHE_HOME")
            or os.path.join(os.path.expanduser("~"), ".cache"))
    return os.path.join(base, NOMBRE_CARPETA, "cache")


def _entradas(carpeta: str):
    try:
        return [os.path.join(carpeta, n) for n in os.listdir(carpeta) if _ENTRADA.match(n)]
    except OSError:
        return []


def limpiar_caducadas(carpeta: str, dias: int = DIAS_CADUCIDAD) -> int:
    """Borra las entradas de caché sin usar desde hace ``dias`` días. Devuelve cuántas borró."""
    limite, borradas = time.time() - dias * 86400, 0
    for ruta in _entradas(carpeta):
        try:
            if os.path.getmtime(ruta) < limite:
                os.remove(ruta)
                borradas += 1
        except OSError:
            pass
    return borradas


def borrar(carpeta: str) -> int:
    """``--cache-clear``: borra solo los archivos de caché (``<64 hex>.json``), nada más. Devuelve cuántos."""
    borrados = 0
    for ruta in _entradas(carpeta):
        try:
            os.remove(ruta)
            borrados += 1
        except OSError:
            pass
    return borrados


class SesionConCache:
    """Envuelve una sesión: solo cachea ``GET`` a api.github.com con respuesta 200 y ETag."""

    def __init__(self, session, carpeta: str):
        self._session = session
        self._carpeta = carpeta
        os.makedirs(carpeta, exist_ok=True)
        self.aciertos = 0   # respuestas 304: no gastan cuota
        self.peticiones = 0  # GET a la API que pasaron por la caché
        self._lock = threading.Lock()
        limpiar_caducadas(carpeta)

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
        with self._lock:
            self.peticiones += 1
        ruta = self._ruta(url, kwargs)
        guardado = self._leer(ruta)
        if guardado:
            kwargs = {**kwargs, "headers": {**(kwargs.get("headers") or {}), "If-None-Match": guardado["etag"]}}
        res = self._session.get(url, **kwargs)
        if res.status_code == 304 and guardado:
            with self._lock:
                self.aciertos += 1
            falsa = requests.Response()
            falsa.status_code = 200
            falsa._content = guardado["text"].encode("utf-8")
            falsa.headers.update({"ETag": guardado["etag"], "X-Cache": "hit"})
            falsa.url = url
            try:
                os.utime(ruta)
            except OSError:
                pass
            return falsa
        etag = (getattr(res, "headers", None) or {}).get("ETag")
        if res.status_code == 200 and etag:
            try:
                with open(ruta, "w", encoding="utf-8") as f:
                    json.dump({"etag": etag, "text": res.text}, f)
            except OSError:
                pass  # la caché es opcional: sin disco, se sigue sin ella
        return res
