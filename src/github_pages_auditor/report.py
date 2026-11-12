from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from . import __version__, creditos
from .models import AuditReport


def renderizar_consola(report: AuditReport, sin_color: bool = False, console: Console = None):
    console = console or Console(no_color=sin_color)

    console.print(Panel.fit(
        f"[bold cyan]GitHub Profile & Pages Auditor[/bold cyan] [dim]v{__version__}[/dim]\n"
        f"[dim]Usuario: [bold white]{report.usuario}[/bold white] | "
        f"Dominio: [bold yellow]{report.dominio_base}[/bold yellow] | "
        f"Proveedor: [bold green]{report.proveedor}[/bold green][/dim]",
        border_style="cyan",
    ))

    t_pages = Table(title="🌐 GitHub Pages Activas", style="cyan", header_style="bold magenta")
    t_pages.add_column("Repositorio", style="bold white", width=30)
    t_pages.add_column("Enlace Desplegado", style="blue underline")
    for r in report.con_pages:
        t_pages.add_row(r.nombre, r.url_pages or "")
    console.print(t_pages)

    t = Table(title="🛡️ Resumen de Auditoría", style="green", header_style="bold yellow")
    t.add_column("Métrica / Categoría", style="bold white")
    t.add_column("Cantidad", justify="right", style="bold cyan")
    t.add_column("Estado", style="bold")

    def badge(lista, msg="faltantes"):
        return f"[bold red]⚠️ {len(lista)} {msg}[/bold red]" if lista else "[bold green]✅ OK[/bold green]"

    t.add_row("Total Repositorios", str(report.total_repos), "[bold blue]Analizados[/bold blue]")
    t.add_row("GitHub Pages", str(len(report.con_pages)), "[bold green]Activas[/bold green]")
    t.add_row("Releases Publicadas", str(len(report.con_releases)), "[bold green]Con Descargas[/bold green]")
    t.add_row("Sin Web ni Releases", str(len(report.sin_nada)), badge(report.sin_nada, "inactivos"))
    t.add_row("Sin README", str(len(report.sin_readme)), badge(report.sin_readme))
    t.add_row("Sin Licencia", str(len(report.sin_licencia)), badge(report.sin_licencia))
    t.add_row("Sin .gitignore", str(len(report.sin_gitignore)), badge(report.sin_gitignore))
    t.add_row("Sin Descripción", str(len(report.sin_descripcion)), badge(report.sin_descripcion))
    if report.pages_rotas:
        t.add_row("Pages rotas", str(len(report.pages_rotas)), badge(report.pages_rotas, "rotas"))
    if report.pages_con_avisos:
        t.add_row("Pages con avisos", str(len(report.pages_con_avisos)), badge(report.pages_con_avisos, "avisos"))
    t.add_row("Forks", str(len(report.forks)), "[dim]Externos[/dim]")
    t.add_row("Archivados", str(len(report.archivados)), "[dim]Solo lectura[/dim]")
    if report.con_error:
        t.add_row("No analizados", str(len(report.con_error)), badge(report.con_error, "con error"))
    console.print(t)


def _seccion(titulo, nombres):
    return ["", f"=== {titulo} ===", *([f"- {n}" for n in nombres] or ["Ninguno"])]


def generar_txt(report: AuditReport) -> str:
    lineas = [
        f"=== ENLACES DE GITHUB PAGES PARA: {report.usuario} ===",
        f"Dominio base: {report.dominio_base}",
        f"Proveedor de datos: {report.proveedor}",
        "",
    ]
    lineas += [f"- {r.nombre:<32} -> {r.url_pages}" for r in report.con_pages] or [
        "No se encontraron repositorios con GitHub Pages."]
    lineas += _seccion("REPOSITORIOS CON RELEASES", [r.nombre for r in report.con_releases])
    lineas += _seccion("REPOSITORIOS SIN RELEASES NI GITHUB PAGES", [r.nombre for r in report.sin_nada])
    lineas += _seccion("REPOSITORIOS SIN README", [r.nombre for r in report.sin_readme])
    lineas += _seccion("REPOSITORIOS SIN LICENCIA", [r.nombre for r in report.sin_licencia])
    lineas += _seccion("REPOSITORIOS SIN .GITIGNORE", [r.nombre for r in report.sin_gitignore])
    lineas += _seccion("REPOSITORIOS SIN DESCRIPCIÓN (ABOUT)", [r.nombre for r in report.sin_descripcion])
    lineas += _seccion("REPOSITORIOS QUE SON FORKS", [r.nombre for r in report.forks])
    lineas += _seccion("REPOSITORIOS ARCHIVADOS", [r.nombre for r in report.archivados])
    if report.pages_rotas:
        lineas += _seccion("GITHUB PAGES ROTAS", [
            f"{r.nombre}: {', '.join(r.pages_salud.problemas)}" for r in report.pages_rotas])
    if report.pages_con_avisos:
        lineas += _seccion("GITHUB PAGES CON AVISOS", [
            f"{r.nombre}: {', '.join(r.pages_salud.avisos)}" for r in report.pages_con_avisos])
    if report.con_error:
        lineas += _seccion("REPOSITORIOS NO ANALIZADOS (ERROR DE RED)", [f"{r.nombre}: {r.error}" for r in report.con_error])
    lineas += ["", "-" * 60, f"Generado con github-pages-auditor v{__version__}", creditos(sep="\n")]
    return "\n".join(lineas) + "\n"


def exportar_txt(report: AuditReport, ruta_salida: str):
    with open(ruta_salida, "w", encoding="utf-8") as f:
        f.write(generar_txt(report))
