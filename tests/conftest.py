"""Utilidades de test: una sesión HTTP falsa que nunca toca la red."""
import threading

import pytest


class FakeResponse:
    PAGINA = "<!doctype html><html><head><title>Demo</title></head><body>hola</body></html>"

    def __init__(self, status_code=200, text=None, json_data=None, headers=None, url="", history=None):
        self.status_code = status_code
        self.text = text if text is not None else (self.PAGINA if status_code == 200 else "")
        self.history = history or []
        self._json = json_data
        self.headers = headers or {}
        self.url = url

    def json(self):
        return self._json

    def iter_content(self, n):
        yield self.text.encode("utf-8")

    def close(self):
        pass


class FakeSession:
    """``handler(metodo, url, kwargs) -> FakeResponse`` (o lanza una excepción)."""

    def __init__(self, handler):
        self.handler = handler
        self.llamadas = []
        self._lock = threading.Lock()

    def _llamar(self, metodo, url, kwargs):
        with self._lock:
            self.llamadas.append((metodo, url, kwargs))
        r = self.handler(metodo, url, kwargs)
        if not r.url:
            r.url = url
        return r

    def get(self, url, **kwargs):
        return self._llamar("GET", url, kwargs)

    def head(self, url, **kwargs):
        return self._llamar("HEAD", url, kwargs)


@pytest.fixture
def Resp():
    return FakeResponse


@pytest.fixture
def sesion():
    return lambda handler: FakeSession(handler)


@pytest.fixture(autouse=True)
def entorno_limpio(monkeypatch):
    """Los tests no deben depender del entorno ni de un .env real."""
    for v in ("USUARIO_GITHUB", "DOMINIO_WEB", "GITHUB_TOKEN", "ARCHIVO_SALIDA"):
        monkeypatch.delenv(v, raising=False)
    monkeypatch.setattr("github_pages_auditor.config.load_dotenv", lambda *a, **k: False)
