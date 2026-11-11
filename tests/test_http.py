import requests

from ver_github_pages.http import SesionHttp, crear_sesion_http


def test_la_sesion_no_lleva_credenciales():
    s = crear_sesion_http()
    assert "Authorization" not in s.headers
    assert "ver-github-pages" in s.headers["User-Agent"]


def test_timeout_por_defecto_se_aplica(monkeypatch):
    vistos = {}

    def falso(self, method, url, **kw):
        vistos.update(kw)
        return "ok"

    monkeypatch.setattr(requests.Session, "request", falso)
    s = SesionHttp(timeout=7)
    s.get("https://x.test")
    assert vistos["timeout"] == 7
    s.get("https://x.test", timeout=2)  # un timeout explícito manda
    assert vistos["timeout"] == 2


def test_reintentos_no_lanzan_retryerror():
    s = crear_sesion_http()
    retry = s.get_adapter("https://x.test").max_retries
    assert retry.raise_on_status is False and 429 in retry.status_forcelist
