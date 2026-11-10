import pytest
from unittest.mock import MagicMock
from ver_github_pages.github_api import GitHubAPIProvider

def test_github_api_obtener_repositorios():
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {
            "name": "repo1",
            "has_pages": True,
            "license": {"key": "mit"},
            "description": "Una descripción de prueba",
            "fork": False,
            "archived": False
        }
    ]
    mock_session.get.return_value = mock_response

    provider = GitHubAPIProvider("alberto2005-coder", "https://albertoortiz.is-a.dev", mock_session)
    repos = provider.obtener_repositorios()

    assert len(repos) == 1
    assert repos[0].nombre == "repo1"
    assert repos[0].tiene_pages is True
    assert repos[0].tiene_licencia is True
    assert repos[0].tiene_descripcion is True