import pytest
from unittest.mock import MagicMock
from ver_github_pages.github_web import GitHubWebProvider

def test_github_web_obtener_repositorios():
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = '<a href="/alberto2005-coder/repo-web" itemprop="name codeRepository">repo-web</a>'
    mock_session.get.return_value = mock_response

    provider = GitHubWebProvider("alberto2005-coder", "https://albertoortiz.is-a.dev", mock_session)
    repos = provider.obtener_repositorios()

    assert len(repos) == 1
    assert repos[0].nombre == "repo-web"