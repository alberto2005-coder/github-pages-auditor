import sys

from rich.console import Console

from . import creditos
from .audit import ejecutar_auditoria
from .config import parse_args
from .errors import ErrorAuditoria
from .report import exportar_txt, renderizar_consola


def main(args=None) -> int:
    """Punto de entrada. Devuelve 0 (ok), 1 (sin repositorios), 2 (error) o 130 (Ctrl+C)."""
    config = parse_args(args)  # --help, --version y errores de uso salen aquí
    console = Console(no_color=config.sin_color)
    err = Console(stderr=True, no_color=config.sin_color)

    try:
        reporte = ejecutar_auditoria(config, console=console)
    except ErrorAuditoria as e:
        err.print(f"[bold red]❌ {e}[/bold red]")
        return 2
    except KeyboardInterrupt:
        err.print("\n[bold yellow]⚠️ Operación cancelada por el usuario.[/bold yellow]")
        return 130

    if not reporte.repos:
        err.print("[bold red]❌ El usuario no tiene repositorios públicos.[/bold red]")
        return 1

    renderizar_consola(reporte, console=console)
    try:
        exportar_txt(reporte, config.archivo_salida)
    except OSError as e:
        err.print(f"[bold red]❌ No se pudo escribir '{config.archivo_salida}': {e}[/bold red]")
        return 2
    console.print(f"\n[bold green]✅ Reporte exportado a '[white]{config.archivo_salida}[/white]'[/bold green]")
    console.print(f"[dim]{creditos()}[/dim]", highlight=False, soft_wrap=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
