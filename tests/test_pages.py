from ver_github_pages.pages import construir_url_pages

def test_construir_url_pages_principal():
    url = construir_url_pages("alberto2005-coder", "alberto2005-coder.github.io", "https://albertoortiz.is-a.dev")
    assert url == "https://albertoortiz.is-a.dev"

def test_construir_url_pages_subruta():
    url = construir_url_pages("alberto2005-coder", "3-en-raya", "https://albertoortiz.is-a.dev")
    assert url == "https://albertoortiz.is-a.dev/3-en-raya/"