from ver_github_pages.pages import comprobar_pages, construir_url_pages, es_raiz


def test_principal():
    assert construir_url_pages("alberto2005-coder", "alberto2005-coder.github.io", "https://albertoortiz.is-a.dev") \
        == "https://albertoortiz.is-a.dev"


def test_subruta():
    assert construir_url_pages("alberto2005-coder", "3-en-raya", "https://albertoortiz.is-a.dev/") \
        == "https://albertoortiz.is-a.dev/3-en-raya/"


def test_repo_con_nombre_de_usuario_no_es_raiz():
    # Es el README del perfil, no un sitio de Pages.
    assert not es_raiz("ana", "ana")
    assert construir_url_pages("ana", "ana", "https://a.dev") == "https://a.dev/ana/"


def test_comprobar_pages_ok(sesion, Resp):
    assert comprobar_pages(sesion(lambda m, u, k: Resp(200)), "https://a.dev/x/")


def test_comprobar_pages_404(sesion, Resp):
    assert not comprobar_pages(sesion(lambda m, u, k: Resp(404)), "https://a.dev/x/")


def test_comprobar_pages_redireccion_a_otro_dominio(sesion, Resp):
    assert not comprobar_pages(sesion(lambda m, u, k: Resp(200, url="https://parking.example/")), "https://a.dev/x/")


def test_comprobar_pages_error_de_red(sesion):
    import requests

    def boom(m, u, k):
        raise requests.ConnectionError("sin red")

    assert not comprobar_pages(sesion(boom), "https://a.dev/x/")
