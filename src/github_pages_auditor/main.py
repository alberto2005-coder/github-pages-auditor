import os
import sys

from rich.console import Console

from . import creditos
from .audit import ejecutar_auditoria
from .config import Config, parse_args
from .errors import ErrorAuditoria
from .formatters import a_json, bloque_markdown, inyectar
from .report import generar_txt, renderizar_consola
from .rules import disparadas, evaluar

EXIT_OK, EXIT_HALLAZGOS, EXIT_ERROR, EXIT_SIN_REPOS, EXIT_CTRL_C = 0, 1, 2, 3, 130


def _contenido(config: Config, reporte, hallazgos, activadas) -> str:
    if config.formato == "json":
        # En stdout, JSON solo ASCII: sobrevive a cualquier codificación de consola (p. ej. cp1252 en Windows).
        return a_json(reporte, hallazgos, config.fail_on, activadas, solo_ascii=config.salida_estandar)
    if config.formato == "md":
        return bloque_markdown(reporte)
    return generar_txt(reporte)


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


def main(args=None) -> int:
    """Devuelve 0 (ok), 1 (--fail-on disparado), 2 (error), 3 (sin repositorios) o 130 (Ctrl+C)."""
    config = parse_args(args)  # --help, --version y errores de uso salen aquí
    # Con '-o -' el informe va a stdout y TODA la interfaz pasa a stderr (stdout queda limpio para pipes).
    console = Console(no_color=config.sin_color, stderr=config.salida_estandar, quiet=config.quiet)
    err = Console(stderr=True, no_color=config.sin_color)

    if config.archivo_salida and not config.salida_estandar and not _carpeta_ok(config.archivo_salida):
        carpeta = os.path.dirname(os.path.abspath(config.archivo_salida))
        err.print(f"[bold red]❌ La carpeta de salida no existe: '{carpeta}'[/bold red]")
        return EXIT_ERROR
    if config.inject and not os.path.isfile(config.inject):
        err.print(f"[bold red]❌ No existe el archivo para --inject: '{config.inject}'[/bold red]")
        return EXIT_ERROR

    try:
        reporte = ejecutar_auditoria(config, console=console)
    except ErrorAuditoria as e:
        err.print(f"[bold red]❌ {e}[/bold red]")
        return EXIT_ERROR
    except KeyboardInterrupt:
        err.print("\n[bold yellow]⚠️ Operación cancelada por el usuario.[/bold yellow]")
        return EXIT_CTRL_C

    if not reporte.repos:
        err.print("[bold red]❌ No hay repositorios que analizar (usuario sin repos públicos o todos filtrados).[/bold red]")
        return EXIT_SIN_REPOS

    hallazgos = evaluar(reporte.repos)
    activadas = disparadas(hallazgos, config.fail_on)

    renderizar_consola(reporte, console=console)
    try:
        if config.archivo_salida:
            contenido = _contenido(config, reporte, hallazgos, activadas)
            if config.salida_estandar:
                _escribir_stdout(contenido)
            else:
                with open(config.archivo_salida, "w", encoding="utf-8") as f:
                    f.write(contenido)
                console.print(f"\n[bold green]✅ Reporte exportado a '[white]{config.archivo_salida}[/white]'[/bold green]")
        if config.inject:
            with open(config.inject, encoding="utf-8") as f:
                original = f.read()
            nuevo = inyectar(original, bloque_markdown(reporte, incluir_forks=False))
            with open(config.inject, "w", encoding="utf-8") as f:
                f.write(nuevo)
            console.print(f"[bold green]✅ Tabla de demos actualizada en '[white]{config.inject}[/white]'[/bold green]")
    except ErrorAuditoria as e:
        err.print(f"[bold red]❌ {e}[/bold red]")
        return EXIT_ERROR
    except OSError as e:
        err.print(f"[bold red]❌ No se pudo escribir la salida: {e}[/bold red]")
        return EXIT_ERROR

    console.print(f"[dim]{creditos()}[/dim]", highlight=False, soft_wrap=True)
    if activadas:
        err.print(f"[bold red]❌ --fail-on disparado por: {', '.join(activadas)}[/bold red]")
        return EXIT_HALLAZGOS
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
