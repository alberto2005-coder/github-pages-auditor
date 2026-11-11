"""ver-github-pages: auditor CLI de repositorios, GitHub Pages y releases."""

__version__ = "1.1.0"
NOMBRE_PROGRAMA = "ver-github-pages"
AUTOR = "Alberto Ortiz"
URL_GITHUB = "https://github.com/alberto2005-coder/"
URL_WEB = "https://albertoortiz.is-a.dev/"


def creditos(sep: str = " · ") -> str:
    """Línea de créditos que se muestra en --help, --version, consola e informe."""
    return f"Desarrollado por {AUTOR}{sep}GitHub: {URL_GITHUB}{sep}Web: {URL_WEB}"
