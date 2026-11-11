from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn, TimeRemainingColumn

from .config import Config
from .errors import ErrorAuditoria
from .github_api import GitHubAPIProvider
from .github_web import GitHubWebProvider
from .http import crear_sesion_http
from .models import AuditReport, RepoInfo


def crear_proveedor(config: Config, session):
    if config.usa_api:
        return (GitHubAPIProvider(config.usuario, config.dominio_web, session, token=config.github_token),
                "API REST de GitHub (Autenticado)")
    return (GitHubWebProvider(config.usuario, config.dominio_web, session),
            "Scraping Web Público (Sin API)")


def ejecutar_auditoria(config: Config, session=None, console: Console = None) -> AuditReport:
    """Audita todos los repos. Un fallo de red en un repo se anota en ``RepoInfo.error``
    sin tumbar el resto; los errores globales (usuario inexistente, token inválido,
    límite de tasa) se propagan como ``ErrorAuditoria``.
    """
    session = session or crear_sesion_http(timeout=config.timeout)
    console = console or Console(no_color=config.sin_color)
    provider, nombre_proveedor = crear_proveedor(config, session)

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
                  transient=True, console=console) as progress:
        task_list = progress.add_task(
            description=f"🔍 Escaneando repositorios de [bold yellow]{config.usuario}[/bold yellow]...", total=None)

        def actualizar_progreso(pagina: int, encontrados: int):
            progress.update(task_list, description=(
                f"🔍 Escaneando página [bold cyan]{pagina}[/bold cyan]... "
                f"([bold green]{encontrados}[/bold green] repositorios encontrados)"))

        try:
            repos_base = provider.obtener_repositorios(on_progress=actualizar_progreso)
        except requests.RequestException as e:
            raise ErrorAuditoria(f"Error de red al listar los repositorios: {e}") from e

    informe = AuditReport(usuario=config.usuario, dominio_base=config.dominio_web, proveedor=nombre_proveedor)
    if not repos_base:
        return informe

    def trabajo(repo: RepoInfo) -> RepoInfo:
        try:
            return provider.enriquecer_repo(repo)
        except requests.RequestException as e:
            repo.error = str(e)
            return repo

    resultados = [None] * len(repos_base)
    with Progress(SpinnerColumn(), TextColumn("[bold cyan]Auditando código:[/bold cyan]"), BarColumn(bar_width=35),
                  TaskProgressColumn(), TextColumn("[yellow]({task.completed}/{task.total})[/yellow]"),
                  TimeRemainingColumn(), console=console) as progress:
        task_audit = progress.add_task("audit", total=len(repos_base))
        with ThreadPoolExecutor(max_workers=config.max_workers) as executor:
            futuros = {executor.submit(trabajo, repo): i for i, repo in enumerate(repos_base)}
            try:
                for futuro in as_completed(futuros):
                    resultados[futuros[futuro]] = futuro.result()
                    progress.advance(task_audit)
            except BaseException:
                executor.shutdown(wait=False, cancel_futures=True)
                raise

    informe.repos = resultados  # mismo orden que el listado: informe determinista
    return informe
