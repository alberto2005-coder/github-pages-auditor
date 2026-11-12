import pytest
import requests

from github_pages_auditor import pages_health
from github_pages_auditor.pages_health import inspeccionar

URL = "https://ana.dev/juego/"


def sesion_con(resp=None, error=None):
    class S:
        def get(self, url, **kw):
            if error:
                raise error
            return resp
    return S()


def test_ok_extrae_titulo(Resp):
    s = inspeccionar(sesion_con(Resp(200, "<html><head><title> Mi  Juego </title></head></html>", url=URL)), URL)
    assert s.ok and s.titulo == "Mi Juego" and s.url_final == URL and s.problemas == []


def test_404_esperada_es_rota(Resp):
    s = inspeccionar(sesion_con(Resp(404, url=URL)), URL, esperada=True)
    assert s.estado == "roto" and s.problemas == ["404"] and s.http_status == 404


def test_404_no_esperada_es_ninguna(Resp):
    s = inspeccionar(sesion_con(Resp(404, url=URL)), URL, esperada=False)
    assert s.estado == "ninguna" and s.url_final is None


@pytest.mark.parametrize("error,problema", [
    (requests.exceptions.SSLError(), "tls-error"),
    (requests.exceptions.ConnectTimeout(), "timeout"),
    (requests.exceptions.TooManyRedirects(), "bucle-de-redirecciones"),
    (requests.exceptions.ConnectionError(), "sin-conexion"),
])
def test_errores_de_red_se_clasifican(error, problema):
    s = inspeccionar(sesion_con(error=error), URL, esperada=True)
    assert s.estado == "roto" and s.problemas == [problema]
    assert inspeccionar(sesion_con(error=error), URL, esperada=False).estado == "ninguna"


def test_redireccion_de_github_io_a_dominio_propio_es_valida(Resp):
    s = inspeccionar(sesion_con(Resp(200, url="https://ana.dev/juego/")), "https://ana.github.io/juego/")
    assert s.ok and s.url_final == "https://ana.dev/juego/"


def test_redireccion_a_dominio_ajeno_es_problema(Resp):
    s = inspeccionar(sesion_con(Resp(200, url="https://parking.example/")), URL, esperada=True)
    assert s.estado == "roto" and "redireccion-externa" in s.problemas


def test_demasiadas_redirecciones(Resp):
    s = inspeccionar(sesion_con(Resp(200, url=URL, history=[object()] * 6)), URL, esperada=True)
    assert "demasiadas-redirecciones" in s.problemas


def test_cuerpo_vacio_es_problema(Resp):
    s = inspeccionar(sesion_con(Resp(200, "   ", url=URL)), URL, esperada=True)
    assert s.estado == "roto" and s.problemas == ["cuerpo-vacio"]


def test_sin_html_es_solo_aviso(Resp):
    s = inspeccionar(sesion_con(Resp(200, "solo texto plano", url=URL)), URL)
    assert s.ok and s.avisos == ["sin-html"]


def test_lenta_es_aviso(Resp, monkeypatch):
    tiempos = iter([0.0, 4.0])
    monkeypatch.setattr(pages_health.time, "monotonic", lambda: next(tiempos))
    s = inspeccionar(sesion_con(Resp(200, url=URL)), URL)
    assert s.ok and "lenta" in s.avisos and s.ms == 4000
