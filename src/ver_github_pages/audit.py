from concurrent.futures import ThreadPoolExecutor
from .config import Config
from .http import crear_sesion_http
from .models import AuditReport, RepoInfo
from .github_api import GitHubAPIProvider
from .github_web import GitHubWebProvider

def ejecutar_auditoria(config: Config) -> AuditReport:
    session = crear_sesion_http(token=config.github_token)

    if config.github_token and not config.forzar_web:
        provider = GitHubAPIProvider(config.usuario, config.dominio_web, session)
        nombre_proveedor = "API REST de GitHub (Autenticado)"
    else:
        provider = GitHubWebProvider(config.usuario, config.dominio_web, session)
        nombre_proveedor = "Scraping Web Público (Sin API)"

    repos_base = provider.obtener_repositorios()
    if not repos_base:
        return AuditReport(usuario=config.usuario, dominio_base=config.dominio_web, proveedor=nombre_proveedor)

    repos_enriquecidos = []
    with ThreadPoolExecutor(max_workers=config.max_workers) as executor:
        resultados = executor.map(provider.enriquecer_repo, repos_base)
        repos_enriquecidos = list(resultados)

    return AuditReport(
        usuario=config.usuario,
        dominio_base=config.dominio_web,
        proveedor=nombre_proveedor,
        repos=repos_enriquecidos
    )