import pytest
from unittest.mock import MagicMock
from ver_github_pages.github_web import GitHubWebProvider

def test_github_web_obtener_repositorios():
    mock_session = MagicMock()
    
    # Respuesta para la página 1 del listado de repositorios
    mock_response_page1 = MagicMock()
    mock_response_page1.status_code = 200
    mock_response_page1.text = '<a href="/alberto2005-coder/repo-web" itemprop="name codeRepository">repo-web</a>'

    # Respuesta para cuando se acaban las páginas de GitHub (página 2 -> 404)
    mock_response_404 = MagicMock()
    mock_response_404.status_code = 404

    # Respuesta para cuando comprueba si existe la URL de GitHub Pages
    mock_response_pages_ok = MagicMock()
    mock_response_pages_ok.status_code = 200

    # Controlamos dinámicamente qué devuelve .get() según la URL solicitada
    def side_effect_get(url, *args, **kwargs):
        if "tab=repositories" in url:
            if "page=1" in url:
                return mock_response_page1
            else:
                return mock_response_404
        # Para la comprobación de GitHub Pages u otras llamadas
        return mock_response_pages_ok

    mock_session.get.side_effect = side_effect_get

    provider = GitHubWebProvider("alberto2005-coder", "https://albertoortiz.is-a.dev", mock_session)
    repos = provider.obtener_repositorios()

    assert len(repos) == 1
    assert repos[0].nombre == "repo-web"