from concurrent.futures import ThreadPoolExecutor, as_completed
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn
from rich.console import Console

from .config import Config
from .http import crear_sesion_http
from .models import AuditReport
from .github_api import GitHubAPIProvider
from .github_web import GitHubWebProvider

def ejecutar_auditoria(config: Config) -> AuditReport:
    session = crear_sesion_http(token=config.github_token)
    console = Console(no_color=config.sin_color)

    if config.github_token and not config.forzar_web:
        provider = GitHubAPIProvider(config.usuario, config.dominio_web, session)
        nombre_proveedor = "API REST de GitHub (Autenticado)"
    else:
        provider = GitHubWebProvider(config.usuario, config.dominio_web, session)
        nombre_proveedor = "Scraping Web Público (Sin API)"

    # Fase 1: Obtener la lista con contador vivo
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
        console=console
    ) as progress:
        task_list = progress.add_task(description=f"🔍 Escaneando páginas públicas de [bold yellow]{config.usuario}[/bold yellow]...", total=None)

        def actualizar_progreso(pagina: int, encontrados: int):
            progress.update(
                task_list,
                description=f"🔍 Escaneando página [bold cyan]{pagina}[/bold cyan]... ([bold green]{encontrados}[/bold green] repositorios encontrados)"
            )

        repos_base = provider.obtener_repositorios(on_progress=actualizar_progreso)

    if not repos_base:
        return AuditReport(usuario=config.usuario, dominio_base=config.dominio_web, proveedor=nombre_proveedor)

    total_repos = len(repos_base)
    repos_enriquecidos = []

    # Fase 2: Auditoría multihilo con PORCENTAJE (Aquí sí conocemos el Total)
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]Auditando código:[/bold cyan]"),
        BarColumn(bar_width=35),
        TaskProgressColumn(),
        TextColumn("[yellow]({task.completed}/{task.total})[/yellow]"),
        TimeRemainingColumn(),
        console=console
    ) as progress:
        
        task_audit = progress.add_task("audit", total=total_repos)

        with ThreadPoolExecutor(max_workers=config.max_workers) as executor:
            futures = [executor.submit(provider.enriquecer_repo, repo) for repo in repos_base]
            for future in as_completed(futures):
                repo_procesado = future.result()
                repos_enriquecidos.append(repo_procesado)
                progress.advance(task_audit)

    return AuditReport(
        usuario=config.usuario,
        dominio_base=config.dominio_web,
        proveedor=nombre_proveedor,
        repos=repos_enriquecidos
    )