from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from . import __version__, creditos
from .i18n import t
from .models import AuditReport
from .rules import COMUNIDAD, REGLAS
from .score import nota, ranking


def _linea_nota(report: AuditReport) -> str:
    return t("score_line", score=report.puntuacion, grade=nota(report.puntuacion))


def renderizar_consola(report: AuditReport, sin_color: bool = False, console: Optional[Console] = None,
                       hallazgos=None, detalles: bool = False, historial=None):
    console = console or Console(no_color=sin_color)

    console.print(Panel.fit(
        f"[bold cyan]GitHub Profile & Pages Auditor[/bold cyan] [dim]v{__version__}[/dim]\n"
        f"[dim]{t('user')}: [bold white]{report.usuario}[/bold white] | "
        f"{t('domain')}: [bold yellow]{report.dominio_base}[/bold yellow] | "
        f"{t('provider')}: [bold green]{report.proveedor}[/bold green][/dim]",
        border_style="cyan",
    ))

    t_pages = Table(title=t("pages_title"), style="cyan", header_style="bold magenta")
    t_pages.add_column(t("col_repo"), style="bold white", width=30)
    t_pages.add_column(t("col_link"), style="blue underline")
    for r in report.con_pages:
        t_pages.add_row(r.nombre, r.url_pages or "")
    console.print(t_pages)

    if detalles:
        t_det = Table(title=t("details_title"), style="cyan", header_style="bold magenta")
        for col in (t("col_repo"), "★", t("col_lang"), t("col_license"), t("col_push"), t("col_release"), t("col_score")):
            t_det.add_column(col, justify="right" if col in ("★", t("col_score")) else "left")
        for r in report.repos:
            t_det.add_row(r.nombre, "" if r.estrellas is None else str(r.estrellas), r.lenguaje or "",
                          r.licencia_spdx or "", (r.ultimo_push or "")[:10], r.ultima_release or "",
                          "" if r.puntuacion is None else str(r.puntuacion))
        console.print(t_det)

    tabla = Table(title=t("summary_title"), style="green", header_style="bold yellow")
    tabla.add_column(t("col_metric"), style="bold white")
    tabla.add_column(t("col_count"), justify="right", style="bold cyan")
    tabla.add_column(t("col_status"), style="bold")

    def badge(lista, msg=None):
        msg = msg or t("st_missing")
        return f"[bold red]⚠️ {len(lista)} {msg}[/bold red]" if lista else f"[bold green]{t('st_ok')}[/bold green]"

    tabla.add_row(t("row_total"), str(report.total_repos), f"[bold blue]{t('st_analyzed')}[/bold blue]")
    if report.puntuacion is not None:
        tabla.add_row(t("row_score"), f"{report.puntuacion}/100", f"[bold green]{nota(report.puntuacion)}[/bold green]")
    tabla.add_row(t("row_pages"), str(len(report.con_pages)), f"[bold green]{t('st_active')}[/bold green]")
    tabla.add_row(t("row_releases"), str(len(report.con_releases)), f"[bold green]{t('st_downloads')}[/bold green]")
    tabla.add_row(t("row_nothing"), str(len(report.sin_nada)), badge(report.sin_nada, t("st_inactive")))
    tabla.add_row(t("row_readme"), str(len(report.sin_readme)), badge(report.sin_readme))
    tabla.add_row(t("row_license"), str(len(report.sin_licencia)), badge(report.sin_licencia))
    tabla.add_row(t("row_gitignore"), str(len(report.sin_gitignore)), badge(report.sin_gitignore))
    tabla.add_row(t("row_description"), str(len(report.sin_descripcion)), badge(report.sin_descripcion))
    if report.pages_rotas:
        tabla.add_row(t("row_broken"), str(len(report.pages_rotas)), badge(report.pages_rotas, t("st_broken")))
    if report.pages_con_avisos:
        tabla.add_row(t("row_warnings"), str(len(report.pages_con_avisos)),
                      badge(report.pages_con_avisos, t("st_warnings")))
    for regla in _reglas_extra(hallazgos):
        repos = hallazgos[regla]
        tabla.add_row(t(f"rule.{regla}"), str(len(repos)), f"[bold red]⚠️ {len(repos)} {t('st_repos')}[/bold red]")
    tabla.add_row(t("row_forks"), str(len(report.forks)), f"[dim]{t('st_external')}[/dim]")
    tabla.add_row(t("row_archived"), str(len(report.archivados)), f"[dim]{t('st_readonly')}[/dim]")
    if report.con_error:
        tabla.add_row(t("row_errors"), str(len(report.con_error)), badge(report.con_error, t("st_errors")))
    console.print(tabla)

    if report.puntuacion is not None:
        mejores, peores = ranking(report)
        console.print(f"[bold]{_linea_nota(report)}[/bold]")
        if mejores:
            console.print(f"{t('best')}: " + ", ".join(f"{r.nombre} ({r.puntuacion})" for r in mejores))
        if peores:
            console.print(f"{t('worst')}: " + ", ".join(f"{r.nombre} ({r.puntuacion})" for r in peores))
    for linea in lineas_historial(historial):
        console.print(linea, highlight=False)


def _reglas_extra(hallazgos):
    """Reglas que no son las básicas (comunidad, --deep) y tienen hallazgos."""
    if not hallazgos:
        return []
    basicas = {"missing-readme", "missing-license", "missing-gitignore", "missing-description",
               "broken-pages", "analysis-errors"}
    return [r for r, repos in hallazgos.items() if repos and r not in basicas]


def lineas_historial(historial):
    if not historial:
        return []
    lineas = []
    if historial.get("delta") is not None:
        lineas.append(t("history", file=historial["previous_file"], delta=historial["delta"]))
    if historial.get("improved"):
        lineas.append(t("history_up", names=", ".join(f"{x['name']} ({x['before']}→{x['after']})"
                                                       for x in historial["improved"])))
    if historial.get("worsened"):
        lineas.append(t("history_down", names=", ".join(f"{x['name']} ({x['before']}→{x['after']})"
                                                         for x in historial["worsened"])))
    return lineas


def _seccion(titulo, nombres):
    return ["", f"=== {titulo} ===", *([f"- {n}" for n in nombres] or [t("none")])]


def generar_txt(report: AuditReport, hallazgos=None, detalles: bool = False, historial=None) -> str:
    lineas = [
        t("txt_links", user=report.usuario),
        t("txt_domain", domain=report.dominio_base),
        t("txt_provider", provider=report.proveedor),
        "",
    ]
    lineas += [f"- {r.nombre:<32} -> {r.url_pages}" for r in report.con_pages] or [t("txt_nopages")]
    if report.puntuacion is not None:
        mejores, peores = ranking(report)
        lineas += ["", f"=== {t('sec_ranking')} ===", _linea_nota(report)]
        lineas += [f"+ {r.nombre}: {r.puntuacion}" for r in mejores]
        lineas += [f"- {r.nombre}: {r.puntuacion}" for r in peores]
        lineas += lineas_historial(historial)
    lineas += _seccion(t("sec_releases"), [r.nombre for r in report.con_releases])
    lineas += _seccion(t("sec_nothing"), [r.nombre for r in report.sin_nada])
    lineas += _seccion(t("sec_readme"), [r.nombre for r in report.sin_readme])
    lineas += _seccion(t("sec_license"), [r.nombre for r in report.sin_licencia])
    lineas += _seccion(t("sec_gitignore"), [r.nombre for r in report.sin_gitignore])
    lineas += _seccion(t("sec_description"), [r.nombre for r in report.sin_descripcion])
    lineas += _seccion(t("sec_forks"), [r.nombre for r in report.forks])
    lineas += _seccion(t("sec_archived"), [r.nombre for r in report.archivados])
    if report.pages_rotas:
        lineas += _seccion(t("sec_broken"), [
            f"{r.nombre}: {', '.join(r.pages_salud.problemas)}" for r in report.pages_rotas if r.pages_salud])
    if report.pages_con_avisos:
        lineas += _seccion(t("sec_warnings"), [
            f"{r.nombre}: {', '.join(r.pages_salud.avisos)}" for r in report.pages_con_avisos if r.pages_salud])
    for regla in _reglas_extra(hallazgos):
        lineas += _seccion(t(f"rule.{regla}").upper(), hallazgos[regla])
    if detalles:
        lineas += _seccion(t("sec_details"), [
            f"{r.nombre}: stars={r.estrellas if r.estrellas is not None else '?'} "
            f"lang={r.lenguaje or '-'} license={r.licencia_spdx or '-'} "
            f"pushed={(r.ultimo_push or '-')[:10]} release={r.ultima_release or '-'} "
            f"score={r.puntuacion if r.puntuacion is not None else '-'}" for r in report.repos])
    if report.con_error:
        lineas += _seccion(t("sec_errors"), [f"{r.nombre}: {r.error}" for r in report.con_error])
    lineas += ["", "-" * 60, t("generated", version=__version__), creditos(sep="\n")]
    return "\n".join(lineas) + "\n"


def exportar_txt(report: AuditReport, ruta_salida: str):
    with open(ruta_salida, "w", encoding="utf-8") as f:
        f.write(generar_txt(report))


__all__ = ["renderizar_consola", "generar_txt", "exportar_txt", "lineas_historial", "COMUNIDAD", "REGLAS"]
