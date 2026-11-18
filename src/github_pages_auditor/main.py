import json
import os
import sys

from rich.console import Console

from . import audit as auditoria
from . import baseline as base
from . import cache, creditos, diff, doctor, fix, history, init, notify, salidas, secretos
from .audit import ejecutar_auditoria
from .config import Config, parse_args
from .errors import ErrorAuditoria
from .formatters import a_dict, a_github, a_json, bloque_markdown, inyectar
from .i18n import set_idioma, t
from .report import generar_txt, renderizar_consola
from .rules import disparadas, evaluar, registrar_propias
from .score import puntuar_informe

EXIT_OK, EXIT_HALLAZGOS, EXIT_ERROR, EXIT_SIN_REPOS, EXIT_CTRL_C = 0, 1, 2, 3, 130
REGLA_MIN_SCORE = "min-score"


def _contenido(config: Config, reporte, hallazgos, activadas, info_baseline=None, historial=None,
               arreglos=None) -> str:
    if config.formato == "github":
        return a_github(reporte, hallazgos, config.fail_on)
    if config.formato == "json":
        # En stdout, JSON solo ASCII: sobrevive a cualquier codificación de consola (p. ej. cp1252 en Windows).
        return a_json(reporte, hallazgos, config.fail_on, activadas, solo_ascii=config.salida_estandar,
                      baseline=info_baseline, historial=historial, arreglos=arreglos)
    if config.formato == "md":
        return bloque_markdown(reporte, detalles=config.details)
    if config.formato == "html":
        return salidas.a_html(reporte, hallazgos, config.lang, historial)
    if config.formato == "csv":
        return salidas.a_csv(reporte, hallazgos, bom=not config.salida_estandar)
    if config.formato == "sarif":
        return salidas.a_sarif(reporte, hallazgos, config.fail_on)
    if config.formato == "badge":
        return salidas.a_badge(reporte.puntuacion)
    if config.formato == "trend":
        return salidas.a_trend(reporte, history.todos(config.history or "", reporte.usuario), config.lang)
    if config.formato == "issue":
        return salidas.a_issue(reporte, hallazgos, historial)
    return generar_txt(reporte, hallazgos, config.details, historial)


def _escribir_stdout(texto: str) -> None:
    """Escribe en UTF-8 aunque la consola use otra codificación (cp1252, etc.)."""
    buffer = getattr(sys.stdout, "buffer", None)
    if buffer is not None:
        buffer.write(texto.encode("utf-8"))
        buffer.flush()
    else:  # stdout sustituido (tests)
        sys.stdout.write(texto)
        sys.stdout.flush()


def _carpeta_ok(ruta: str) -> bool:
    return os.path.isdir(os.path.dirname(os.path.abspath(ruta)))


def _necesita_token(config: Config) -> list:
    pedidas = {"--org": config.org, "--include-private": config.incluir_privados, "--deep": config.deep,
               "--fix": config.fix, "--fix-extra": config.fix_extra, "--fix-pages": config.fix_pages,
               "--fix-metadata": config.fix_metadata}
    return [opcion for opcion, activa in pedidas.items() if activa] if not config.usa_api else []


def _seguro(e: object, config: Config) -> str:
    """Texto de un error sin tokens ni webhooks."""
    return secretos.limpiar(e, config.github_token, config.webhook)


def _ejecutar_doctor(config: Config, console: Console) -> int:
    from rich.table import Table
    sesion = auditoria.crear_sesion_http(timeout=config.timeout)
    filas = doctor.Doctor(sesion, config.github_token, config.usuario, org=bool(config.org),
                          privados=config.incluir_privados).ejecutar()
    tabla = Table(title=t("doctor.title"), title_style="bold cyan", header_style="bold magenta")
    for columna in ("doctor.col_check", "doctor.col_status", "doctor.col_detail"):
        tabla.add_column(t(columna))
    for f in filas:
        detalle = secretos.limpiar(f["detail"], config.github_token)
        tabla.add_row(t(f"doctor.check.{f['check']}"), t(f"doctor.st.{f['status']}"), detalle)
    console.print(tabla)
    basicos = {f["check"]: f["status"] for f in filas}
    if basicos.get("token") == doctor.FALLO or basicos.get("api") == doctor.FALLO:
        console.print(f"[bold red]{t('doctor.summary_fail')}[/bold red]")
        return EXIT_ERROR
    if doctor.hay_fallos(filas):
        console.print(f"[bold red]{t('doctor.summary_fail')}[/bold red]")
        return EXIT_HALLAZGOS
    if any(f["status"] in (doctor.AVISO, doctor.DESCONOCIDO) for f in filas):
        console.print(f"[bold yellow]{t('doctor.summary_warn')}[/bold yellow]")
    else:
        console.print(f"[bold green]{t('doctor.summary_ok')}[/bold green]")
    return EXIT_OK


def _ejecutar_diff(config: Config, console: Console, err: Console) -> int:
    antes_ruta, despues_ruta = config.diff
    try:
        datos = diff.comparar_informes(history.cargar(antes_ruta), history.cargar(despues_ruta), antes_ruta, despues_ruta)
        if config.formato == "json" and config.archivo_salida:
            texto = json.dumps(datos, indent=2, ensure_ascii=config.salida_estandar) + "\n"
            if config.salida_estandar:
                _escribir_stdout(texto)
            else:
                with open(config.archivo_salida, "w", encoding="utf-8", newline="") as f:
                    f.write(texto)
    except (ErrorAuditoria, OSError) as e:
        err.print(f"[bold red]❌ {_seguro(e, config)}[/bold red]")
        return EXIT_ERROR
    diff.mostrar(datos, console)
    return EXIT_OK


def main(args=None) -> int:
    """Devuelve 0 (ok), 1 (--fail-on o --min-score disparado), 2 (error), 3 (sin repositorios) o 130 (Ctrl+C)."""
    config = parse_args(args)  # --help, --version y errores de uso salen aquí
    set_idioma(config.lang)
    # Con '-o -' el informe va a stdout y TODA la interfaz pasa a stderr (stdout queda limpio para pipes).
    console = Console(no_color=config.sin_color, stderr=config.salida_estandar, quiet=config.quiet)
    err = Console(stderr=True, no_color=config.sin_color)
    registrar_propias(config.reglas_propias)

    if config.token_en_cli:
        err.print(f"[yellow]{t('warn.token_cli')}[/yellow]")
    if config.github_token and secretos.env_versionado():
        err.print(f"[yellow]{t('warn.env_tracked')}[/yellow]")
    if config.diff:
        return _ejecutar_diff(config, console, err)
    if config.cache_clear:
        carpeta = cache.resolver_carpeta(config.cache or "auto")
        console.print(t("cache_cleared", count=cache.borrar(carpeta), path=carpeta), highlight=False, markup=False)
        return EXIT_OK
    if config.notify_test:
        if config.webhook and notify.probar(config.webhook):
            console.print(f"[bold green]{t('notify_test_ok')}[/bold green]")
            return EXIT_OK
        err.print(f"[bold red]{t('notify_test_fail')}[/bold red]")
        return EXIT_ERROR
    if config.init:
        try:
            ruta = init.crear(usuario=config.usuario or None, sobrescribir=config.yes)
        except (FileExistsError, OSError) as e:
            err.print(f"[bold red]{t('init.exists', path=getattr(e, 'filename', None) or e)}[/bold red]")
            return EXIT_ERROR
        console.print(f"[bold green]{t('init.created', path=ruta)}[/bold green]", highlight=False)
        return EXIT_OK
    if config.doctor:
        return _ejecutar_doctor(config, Console(no_color=config.sin_color))

    if config.archivo_salida and not config.salida_estandar and not _carpeta_ok(config.archivo_salida):
        carpeta = os.path.dirname(os.path.abspath(config.archivo_salida))
        err.print(f"[bold red]❌ La carpeta de salida no existe: '{carpeta}'[/bold red]")
        return EXIT_ERROR
    if config.inject and not os.path.isfile(config.inject):
        err.print(f"[bold red]❌ No existe el archivo para --inject: '{config.inject}'[/bold red]")
        return EXIT_ERROR
    sin_token = _necesita_token(config)
    if sin_token:
        err.print(f"[bold red]❌ {', '.join(sin_token)} necesita un token de GitHub (modo API): "
                  "define GITHUB_TOKEN y no uses --no-api.[/bold red]")
        return EXIT_ERROR
    if config.webhook and not config.webhook.lower().startswith("https://"):
        err.print("[bold red]❌ --notify-webhook debe ser una URL https://[/bold red]")
        return EXIT_ERROR

    previo = None
    try:
        if config.baseline:  # se valida antes de auditar, como --inject
            previo = base.cargar(config.baseline)
        if config.history:
            history.preparar(config.history)
    except ErrorAuditoria as e:
        err.print(f"[bold red]❌ {_seguro(e, config)}[/bold red]")
        return EXIT_ERROR

    try:
        reporte = ejecutar_auditoria(config, console=console)
    except ErrorAuditoria as e:
        err.print(f"[bold red]❌ {_seguro(e, config)}[/bold red]")
        return EXIT_ERROR
    except KeyboardInterrupt:
        err.print("\n[bold yellow]⚠️ Operación cancelada por el usuario.[/bold yellow]")
        return EXIT_CTRL_C

    if not reporte.repos:
        err.print("[bold red]❌ No hay repositorios que analizar (usuario sin repos públicos o todos filtrados).[/bold red]")
        return EXIT_SIN_REPOS

    hallazgos = evaluar(reporte.repos, stale_meses=config.stale_meses, propias=config.reglas_propias)
    puntuar_informe(reporte, stale_meses=config.stale_meses)

    info_baseline = None
    comparables = hallazgos
    if previo is not None:
        nuevos = base.nuevos(hallazgos, previo)
        info_baseline = {"file": config.baseline, "new_findings": {k: v for k, v in nuevos.items() if v}}
        comparables = nuevos
    activadas = disparadas(comparables, config.fail_on)
    if config.min_score is not None and reporte.puntuacion is not None and reporte.puntuacion < config.min_score:
        activadas.append(REGLA_MIN_SCORE)

    # Histórico: comparar con el último informe guardado ANTES de guardar el actual.
    historial, nuevos_para_aviso = None, comparables
    ultimo = history.ultimo(config.history, reporte.usuario) if config.history else None
    if config.history:
        actual = a_dict(reporte, hallazgos, config.fail_on, activadas)
        if ultimo:
            historial = history.comparar(actual, ultimo[1], ultimo[0])
            if previo is None:
                nuevos_para_aviso = base.nuevos(hallazgos, {k: v for k, v in (ultimo[1].get("findings") or {}).items()
                                                              if isinstance(v, list)})

    # Arreglos opt-in (--fix*): por defecto solo se planean.
    arreglos = None
    if config.fix or config.fix_pages or config.fix_metadata:
        cabeceras = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28",
                     "Authorization": f"Bearer {config.github_token}"}
        try:
            arreglos = fix.ejecutar(config, reporte, auditoria.crear_sesion_http(timeout=config.timeout),
                                    cabeceras, hallazgos)
        except ErrorAuditoria as e:
            err.print(f"[bold red]❌ {_seguro(e, config)}[/bold red]")
            return EXIT_ERROR

    if arreglos is not None and config.fix_log:
        try:
            with open(config.fix_log, "w", encoding="utf-8", newline="\n") as f:
                json.dump({"user": config.usuario, "applied": bool(config.yes and not config.dry_run),
                           "actions": arreglos}, f, ensure_ascii=False, indent=2)
        except OSError as e:
            err.print(f"[bold red]❌ --fix-log: {_seguro(e, config)}[/bold red]")
    renderizar_consola(reporte, console=console, hallazgos=hallazgos, detalles=config.details, historial=historial)
    if arreglos is not None:
        aplicados = config.yes and not config.dry_run
        console.print(f"\n[bold]{t('fix_applied') if aplicados else t('fix_plan')}[/bold]" if arreglos
                      else f"\n{t('fix_none')}")
        if arreglos and config.fix_mode == "pr":
            console.print(t("fix_pr"), highlight=False)
        for a in arreglos:
            console.print(f"  [{a['status']}] {a['repo']}: {a['action']} {a['target']}"
                          + (f" ({_seguro(a['detail'], config)})" if a.get("detail") else ""), highlight=False, markup=False)
        if any(a.get("detail") == "HTTP 403" for a in arreglos):
            console.print(t("fix.403"), highlight=False, markup=False)
    try:
        if config.archivo_salida:
            contenido = _contenido(config, reporte, hallazgos, activadas, info_baseline, historial, arreglos)
            if config.salida_estandar:
                _escribir_stdout(contenido)
            else:
                with open(config.archivo_salida, "w", encoding="utf-8", newline="") as f:
                    f.write(contenido)
                console.print(f"\n[bold green]✅ Reporte exportado a '[white]{config.archivo_salida}[/white]'[/bold green]")
        if config.inject:
            with open(config.inject, encoding="utf-8") as f:
                original = f.read()
            nuevo = inyectar(original, bloque_markdown(reporte, incluir_forks=False, detalles=config.details))
            with open(config.inject, "w", encoding="utf-8") as f:
                f.write(nuevo)
            console.print(f"[bold green]✅ Tabla de demos actualizada en '[white]{config.inject}[/white]'[/bold green]")
        if config.history:
            ruta = history.guardar(config.history, reporte.usuario,
                                   a_dict(reporte, hallazgos, config.fail_on, activadas, baseline=info_baseline,
                                          historial=historial, arreglos=arreglos))
            console.print(f"[dim]📈 Histórico: {ruta}[/dim]", highlight=False, markup=True)
    except ErrorAuditoria as e:
        err.print(f"[bold red]❌ {_seguro(e, config)}[/bold red]")
        return EXIT_ERROR
    except OSError as e:
        err.print(f"[bold red]❌ No se pudo escribir la salida: {e}[/bold red]")
        return EXIT_ERROR

    if config.webhook and notify.avisar(config.webhook, reporte.usuario, reporte.puntuacion, nuevos_para_aviso,
                                        siempre=config.notify_on == "always"):
        console.print("[dim]🔔 Aviso enviado al webhook[/dim]")

    if reporte.cache_peticiones:
        console.print(f"[dim]{t('cache_stats', hits=reporte.cache_aciertos, total=reporte.cache_peticiones)}[/dim]",
                      highlight=False)
    console.print(f"[dim]{creditos()}[/dim]", highlight=False, soft_wrap=True)
    if activadas:
        err.print(f"[bold red]❌ --fail-on disparado por: {', '.join(activadas)}[/bold red]")
        return EXIT_HALLAZGOS
    if config.tui:
        from . import tui
        try:
            tui.lanzar(reporte, hallazgos)
        except ErrorAuditoria as e:
            err.print(f"[bold red]❌ {_seguro(e, config)}[/bold red]")
            return EXIT_ERROR
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
