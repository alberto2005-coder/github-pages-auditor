import sys
from .config import parse_args
from .audit import ejecutar_auditoria
from .report import renderizar_consola, exportar_txt

def main(args=None):
    try:
        config = parse_args(args)
        reporte = ejecutar_auditoria(config)
        renderizar_consola(reporte, sin_color=config.sin_color)
        exportar_txt(reporte, config.archivo_salida)
        print(f"\n✅ Reporte exportado a '{config.archivo_salida}'")
    except KeyboardInterrupt:
        print("\n⚠️ Operación cancelada por el usuario.")
        sys.exit(1)

if __name__ == "__main__":
    main()