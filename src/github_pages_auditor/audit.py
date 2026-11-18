import fnmatch
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import replace
from typing import List, Optional, Sequence

import requests
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn, TimeRemainingColumn

from . import dependencias, readme, scorecard
from .cache import SesionConCache, resolver_carpeta
from .config import Config, normalizar_dominio, parsear_since
from .errors import ErrorAuditoria
from .github_api import GitHubAPIProvider
from .github_web import GitHubWebProvider
from .http import crear_sesion_http
from .i18n import t
from .models import AuditReport, RepoInfo
from .secretos import limpiar


def _reciente(repo: RepoInfo, limite) -> bool:
    """``--since``: sin fecha de push (modo web) no se puede filtrar, así que se conserva."""
    from .rules import _fecha
    ultimo = _fecha(repo.ultimo_push)
    if ultimo is None:
        return True
    return (ultimo if ultimo.tzinfo else ultimo.replace(tzinfo=limite.tzinfo)) >= limite


def _coincide(nombre: str, patrones: Sequence[str]) -> bool:
    return any(fnmatch.fnmatchcase(nombre.lower(), p.lower()) for p in patrones)


def ordenar(repos: List[RepoInfo], criterio: str) -> List[RepoInfo]:
    """``listing`` conserva el orden de GitHub; el resto es estable y desempata por nombre."""
    if criterio == "listing":
        return list(repos)
    por_nombre = sorted(repos, key=lambda r: r.nombre.lower())
    if criterio == "stars":
        return sorted(por_nombre, key=lambda r: r.estrellas if r.estrellas is not None else -1, reverse=True)
    if criterio == "updated":
        return sorted(por_nombre, key=lambda r: r.ultimo_push or "", reverse=True)
    return por_nombre


def crear_proveedor(config: Config, session):
    if config.usa_api:
        return (GitHubAPIProvider(config.usuario, config.dominio_web, session, token=config.github_token,
                                  org=bool(config.org), privados=config.incluir_privados, deep=config.deep,
                                  check_links=config.check_links, crawl=config.crawl, reglas_propias=config.reglas_propias,
                                  repo_defaults=config.repo_defaults,
                                  graphql=config.graphql),
                t("prov.api"))
    return (GitHubWebProvider(config.usuario, config.dominio_web, session, check_links=config.check_links,
                                 crawl=config.crawl),
            t("prov.web"))


def _varias_cuentas(config: Config, session, console) -> AuditReport:
    """Audita cada cuenta de ``-u a,b`` y junta los repos en un solo informe (``cuenta/repo``)."""
    session = session or crear_sesion_http(timeout=config.timeout)
    console = console or Console(no_color=config.sin_color)
    unido: Optional[AuditReport] = None
    for cuenta in config.usuarios:
        parcial = ejecutar_auditoria(replace(config, usuario=cuenta, usuarios=(), dominio_web=normalizar_dominio(None, cuenta)),
                                     session, console)
        for repo in parcial.repos:
            repo.propietario, repo.nombre = cuenta, f"{cuenta}/{repo.nombre}"
        if unido is None:
            unido = AuditReport(usuario=config.usuario, dominio_base="", proveedor=parcial.proveedor, modo=parcial.modo)
        unido.repos += parcial.repos
    assert unido is not None
    return unido


def ejecutar_auditoria(config: Config, session=None, console: Optional[Console] = None) -> AuditReport:
    """Audita todos los repos. Un fallo de red en un repo se anota en ``RepoInfo.error``
    sin tumbar el resto; los errores globales (usuario inexistente, token inválido,
    límite de tasa) se propagan como ``ErrorAuditoria``.
    """
    if len(config.usuarios) > 1:
        return _varias_cuentas(config, session, console)
    session = session or crear_sesion_http(timeout=config.timeout)
    if config.cache:
        session = SesionConCache(session, resolver_carpeta(config.cache))
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

    repos_base = [
        r for r in repos_base
        if not (config.excluir_forks and r.es_fork) and not (config.excluir_archivados and r.esta_archivado)
        and (not config.solo or _coincide(r.nombre, config.solo))
        and not _coincide(r.nombre, config.ignorar)
    ]
    if config.since:
        limite = parsear_since(config.since)
        repos_base = [r for r in repos_base if _reciente(r, limite)]
    informe = AuditReport(usuario=config.usuario, dominio_base=config.dominio_web, proveedor=nombre_proveedor,
                          modo="api" if config.usa_api else "web")
    if not repos_base:
        return informe

    if config.graphql and config.usa_api and hasattr(provider, "precargar_graphql"):
        provider.precargar_graphql([r.nombre for r in repos_base if not r.es_fork and not r.esta_archivado])

    def trabajo(repo: RepoInfo) -> RepoInfo:
        try:
            repo = provider.enriquecer_repo(repo)
            if config.usa_api and not repo.es_fork and not repo.esta_archivado:
                if config.readme_quality and repo.tiene_readme:
                    texto = provider.leer_readme(repo)
                    if texto is not None:
                        repo.readme_problemas = readme.analizar(texto)
                if config.dep_licenses:
                    repo.deps_copyleft = dependencias.copyleft(session, lambda ruta: provider.leer_archivo(repo, ruta))
            if config.scorecard:
                repo.scorecard = scorecard.obtener(session, config.usuario, repo)
            return repo
        except requests.RequestException as e:
            repo.error = limpiar(e, config.github_token)
            return repo

    resultados: List[RepoInfo] = list(repos_base)
    with Progress(SpinnerColumn(), TextColumn("[bold cyan]" + t("progress") + "[/bold cyan]"), BarColumn(bar_width=35),
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

    if isinstance(session, SesionConCache):
        informe.cache_aciertos, informe.cache_peticiones = session.aciertos, session.peticiones
    informe.repos = ordenar(resultados, config.orden)  # por defecto, el orden del listado: informe determinista
    return informe
