"""Extremo a extremo: CLI -> auditoría -> proveedor API contra un GitHub simulado (sin red).

Automatizan las pruebas manuales 3.5, 3.6, 5.5-5.7, 6.1-6.5, 8.x y 10.x de pruebas.md.
"""
import json
import time

import pytest
import requests
from conftest import FakeResponse as R
from conftest import FakeSession

from github_pages_auditor import audit
from github_pages_auditor import main as cli
from github_pages_auditor.github_api import API

REPOS = [
    {"name": "web", "has_pages": True, "license": {"key": "mit"}, "description": "Sitio", "fork": False, "archived": False},
    {"name": "roto", "has_pages": True, "license": {"key": "mit"}, "description": "Pages sin index", "fork": False, "archived": False},
    {"name": "bifurcado", "has_pages": False, "license": None, "description": "Fork", "fork": True, "archived": False},
    {"name": "viejo", "has_pages": False, "license": {"key": "mit"}, "description": "Archivado", "fork": False, "archived": True},
    {"name": "lib", "has_pages": False, "license": {"key": "mit"}, "description": "Librería", "fork": False, "archived": False},
]
ARCHIVOS = [{"name": "README.md"}, {"name": "LICENSE"}, {"name": ".gitignore"}]


def github_falso(repos=REPOS, web=None, pages_extra=None, fallo=None, retardo=None, lista=None):
    """Handler de una sesión falsa. ``web(url)`` decide la respuesta de las webs; ``fallo(url)`` puede lanzar."""
    pages_extra = pages_extra or {}

    def h(metodo, url, kw):
        if fallo:
            fallo(url)
        if retardo and "/contents/" in url:
            time.sleep(retardo(url))
        if url.startswith(API):
            ruta = url[len(API):]
            if ruta == "/users/ana/repos":
                if lista:
                    return lista()
                return R(200, json_data=repos if kw["params"]["page"] == 1 else [])
            partes = ruta.strip("/").split("/")  # repos/ana/<repo>/(contents|pages)
            if ruta.endswith("/contents/"):
                return R(200, json_data=ARCHIVOS)
            if ruta.endswith("/pages"):
                datos = {"html_url": f"https://ana.github.io/{partes[2]}/", "status": "built", "https_enforced": True}
                datos.update(pages_extra.get(partes[2], {}))
                return R(200, json_data=datos)
            return R(404)
        if url.endswith("releases.atom"):
            return R(200, "<entry>")
        if web:
            return web(url)
        return R(404) if "/roto/" in url else R(200)

    return h


@pytest.fixture
def instalar(monkeypatch):
    """instalar(handler) -> FakeSession usada por la auditoría."""
    def _instalar(handler):
        sesion = FakeSession(handler)
        monkeypatch.setattr(audit, "crear_sesion_http", lambda **kw: sesion)
        return sesion
    return _instalar


def ejecutar(tmp_path, *args, fmt="json"):
    salida = tmp_path / f"informe.{fmt}"
    codigo = cli.main(["-u", "ana", "-k", "t", "--no-env", "-q", "-f", fmt, "-o", str(salida), *args])
    contenido = salida.read_text(encoding="utf-8") if salida.exists() else None
    return codigo, (json.loads(contenido) if contenido and fmt == "json" else contenido)


# ---------------------------------------------------------------- 6. Salud de Pages
def test_6_1_pages_sana_trae_estado_tiempo_y_titulo(instalar, tmp_path):
    instalar(github_falso())
    codigo, datos = ejecutar(tmp_path)
    web = next(r for r in datos["repos"] if r["name"] == "web")
    assert codigo == 0 and web["pages"]["status"] == "ok"
    assert web["pages"]["title"] == "Demo" and isinstance(web["pages"]["response_ms"], int)
    assert datos["summary"]["pages_live"] == 1


def test_6_2_pages_rota_con_token_da_exit_1_y_aparece_en_el_informe(instalar, tmp_path):
    instalar(github_falso())
    codigo, datos = ejecutar(tmp_path, "--fail-on", "broken-pages")
    assert codigo == 1
    assert datos["summary"]["pages_broken"] == 1 and datos["findings"]["broken-pages"] == ["roto"]
    roto = next(r for r in datos["repos"] if r["name"] == "roto")
    assert roto["pages"]["status"] == "roto" and roto["pages"]["problems"] == ["404"]
    assert datos["fail_on"]["triggered"] == ["broken-pages"]
    codigo, txt = ejecutar(tmp_path, fmt="txt")
    assert codigo == 0 and "GITHUB PAGES ROTAS" in txt and "roto: 404" in txt


def test_6_3_sin_pages_activadas_no_hay_pages_rotas(instalar, tmp_path):
    repos = [dict(r, has_pages=False) for r in REPOS]
    instalar(github_falso(repos=repos))
    codigo, datos = ejecutar(tmp_path, "--fail-on", "broken-pages")
    assert codigo == 0 and datos["summary"]["pages_broken"] == 0 and datos["summary"]["pages_live"] == 0


def test_6_4_avisos_de_https_no_forzado_y_build(instalar, tmp_path):
    instalar(github_falso(pages_extra={"web": {"https_enforced": False, "status": "building"}}))
    _, datos = ejecutar(tmp_path)
    web = next(r for r in datos["repos"] if r["name"] == "web")
    assert web["pages"]["status"] == "ok" and web["pages"]["warnings"] == ["build-en-curso", "https-no-forzado"]
    _, txt = ejecutar(tmp_path, fmt="txt")
    assert "GITHUB PAGES CON AVISOS" in txt and "web: build-en-curso, https-no-forzado" in txt


@pytest.mark.parametrize("error,problema", [
    (requests.exceptions.SSLError("x"), "tls-error"),
    (requests.exceptions.ConnectionError("x"), "sin-conexion"),
    (requests.exceptions.Timeout("x"), "timeout"),
])
def test_6_5_dominio_caido_o_mal_configurado_es_pages_rota(instalar, tmp_path, error, problema):
    def fallo(url):
        if url.startswith("https://ana.github.io/web/"):
            raise error
    instalar(github_falso(fallo=fallo))
    codigo, datos = ejecutar(tmp_path, "--fail-on", "broken-pages")
    web = next(r for r in datos["repos"] if r["name"] == "web")
    assert codigo == 1 and web["pages"]["status"] == "roto" and problema in web["pages"]["problems"]


# ---------------------------------------------------------------- 8. Filtros
def test_8_1_exclude_forks(instalar, tmp_path):
    instalar(github_falso())
    _, datos = ejecutar(tmp_path, "--exclude-forks")
    assert datos["summary"]["total"] == 4 and datos["summary"]["forks"] == 0
    assert "bifurcado" not in [r["name"] for r in datos["repos"]]


def test_8_2_exclude_archived_ni_siquiera_se_analizan(instalar, tmp_path):
    sesion = instalar(github_falso())
    _, datos = ejecutar(tmp_path, "--exclude-archived")
    assert datos["summary"]["total"] == 4 and datos["summary"]["archived"] == 0
    assert not any("/viejo" in url for _, url, _ in sesion.llamadas)


def test_5_6_sin_repos_tras_filtrar_da_3_y_no_escribe(instalar, tmp_path):
    instalar(github_falso(repos=[REPOS[2]]))
    codigo, datos = ejecutar(tmp_path, "--exclude-forks")
    assert codigo == 3 and datos is None


# ---------------------------------------------------------------- 10. Robustez
def test_10_1_sin_conexion_da_2_sin_traceback(instalar, tmp_path, capsys):
    def fallo(url):
        raise requests.exceptions.ConnectionError("sin red")
    instalar(github_falso(fallo=fallo))
    codigo, datos = ejecutar(tmp_path)
    assert codigo == 2 and datos is None and "Error de red" in capsys.readouterr().err


def test_10_2_timeout_en_un_repo_no_tumba_el_resto(instalar, tmp_path):
    def fallo(url):
        if url.endswith("/repos/ana/lib/contents/"):
            raise requests.exceptions.Timeout("lento")
    instalar(github_falso(fallo=fallo))
    codigo, datos = ejecutar(tmp_path)
    assert codigo == 0 and datos["summary"]["errors"] == 1 and datos["summary"]["analyzed"] == 4
    lib = next(r for r in datos["repos"] if r["name"] == "lib")
    assert lib["error"]
    codigo, _ = ejecutar(tmp_path, "--fail-on", "analysis-errors")
    assert codigo == 1


def _sin_fecha(datos):
    datos = dict(datos)
    datos.pop("generated_at")
    return datos


def test_10_3_y_10_4_mismo_resultado_con_1_o_40_hilos_y_orden_estable(instalar, tmp_path):
    instalar(github_falso(retardo=lambda url: 0.05 if "/web/" in url else 0))
    resultados = []
    for workers in ("1", "40", "40"):
        codigo, datos = ejecutar(tmp_path, "--workers", workers)
        assert codigo == 0
        resultados.append(_sin_fecha(datos))
    assert resultados[0] == resultados[1] == resultados[2]
    assert [r["name"] for r in resultados[0]["repos"]] == [r["name"] for r in REPOS]


def test_10_5_limite_de_tasa_da_2_con_mensaje(instalar, tmp_path, capsys):
    instalar(github_falso(lista=lambda: R(429)))
    codigo, _ = ejecutar(tmp_path)
    assert codigo == 2 and "límite" in capsys.readouterr().err


# ---------------------------------------------------------------- 3 y 5. Errores de la API
def test_3_5_token_falso_da_2_sin_traceback(instalar, tmp_path, capsys):
    instalar(github_falso(lista=lambda: R(401)))
    codigo, _ = ejecutar(tmp_path)
    assert codigo == 2 and "rechazó el token" in capsys.readouterr().err


def test_5_5_usuario_inexistente_da_2(instalar, tmp_path, capsys):
    instalar(github_falso(lista=lambda: R(404)))
    codigo, _ = ejecutar(tmp_path)
    assert codigo == 2 and "no existe" in capsys.readouterr().err


def test_3_6_el_token_solo_viaja_a_la_api(instalar, tmp_path):
    sesion = instalar(github_falso())
    ejecutar(tmp_path)
    con_token = [(u, k) for _, u, k in sesion.llamadas if "Authorization" in (k.get("headers") or {})]
    assert con_token and all(u.startswith(API) for u, _ in con_token)
    assert any(not u.startswith(API) for _, u, _ in sesion.llamadas)  # sí hubo peticiones a webs/atom, sin token
