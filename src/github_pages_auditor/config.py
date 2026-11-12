"""Configuración: parámetros de consola > variables de entorno (.env opcional) > defecto."""
import argparse
import os
from dataclasses import dataclass
from typing import Optional, Tuple

from dotenv import find_dotenv, load_dotenv

from . import NOMBRE_PROGRAMA, __version__, creditos
from .rules import TODAS, parsear_fail_on

SALIDA_BASE = "paginas_github"
WORKERS_DEFECTO = 15
TIMEOUT_DEFECTO = 10.0
FORMATOS = ("txt", "json", "md")


@dataclass
class Config:
    usuario: str
    dominio_web: str
    github_token: Optional[str]
    archivo_salida: Optional[str]  # None = no escribir informe; "-" = stdout
    max_workers: int
    forzar_web: bool
    sin_color: bool
    timeout: float = TIMEOUT_DEFECTO
    formato: str = "txt"
    fail_on: Tuple[str, ...] = ()
    excluir_forks: bool = False
    excluir_archivados: bool = False
    inject: Optional[str] = None
    quiet: bool = False

    @property
    def usa_api(self) -> bool:
        return bool(self.github_token) and not self.forzar_web

    @property
    def salida_estandar(self) -> bool:
        return self.archivo_salida == "-"


def normalizar_dominio(dominio: Optional[str], usuario: str) -> str:
    dominio = (dominio or "").strip()
    if not dominio:
        return f"https://{usuario}.github.io"
    if not dominio.lower().startswith(("http://", "https://")):
        dominio = f"https://{dominio}"
    return dominio.rstrip("/")


def _fail_on(texto: str):
    try:
        return parsear_fail_on(texto)
    except ValueError as e:
        raise argparse.ArgumentTypeError(str(e))


def crear_parser() -> argparse.ArgumentParser:
    env = lambda k, d=None: (os.getenv(k) or "").strip() or d  # noqa: E731  (vacío == no definido)

    parser = argparse.ArgumentParser(
        prog=NOMBRE_PROGRAMA,
        description="Auditor CLI para repositorios, GitHub Pages y releases de un usuario de GitHub.\n"
                    "Funciona solo con parámetros: el archivo .env y el token de la API son opcionales.",
        epilog=(
            "Prioridad de configuración: parámetros > variables de entorno/.env > valores por defecto.\n"
            "Variables de entorno: USUARIO_GITHUB, DOMINIO_WEB, GITHUB_TOKEN, ARCHIVO_SALIDA.\n"
            "Códigos de salida: 0 ok, 1 --fail-on disparado, 2 error, 3 sin repositorios, 130 Ctrl+C.\n\n"
            + creditos(sep="\n")
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-u", "--usuario", "--user", dest="usuario", default=env("USUARIO_GITHUB"),
                        help="Nombre de usuario de GitHub (obligatorio).")
    parser.add_argument("-w", "--web", "--dominio", dest="dominio_web", default=env("DOMINIO_WEB"),
                        help="Dominio base de tu sitio web o GitHub Pages (por defecto https://<usuario>.github.io).")
    parser.add_argument("-k", "--key", "--token", dest="github_token", default=env("GITHUB_TOKEN"),
                        help="GitHub Personal Access Token (opcional). Con token se usa la API; sin él, el modo web. "
                             "Más seguro: variable GITHUB_TOKEN (un parámetro queda en el historial del shell).")
    parser.add_argument("-o", "--output", dest="archivo_salida", default=env("ARCHIVO_SALIDA"),
                        help=f"Archivo del informe (por defecto {SALIDA_BASE}.<formato>). Usa '-' para escribirlo "
                             "en la salida estándar (la interfaz pasa a stderr).")
    parser.add_argument("-f", "--format", dest="formato", choices=FORMATOS, default="txt",
                        help="Formato del informe: txt (por defecto), json (contrato versionado) o md "
                             "(tabla de demos en vivo para tu README).")
    parser.add_argument("--fail-on", dest="fail_on", type=_fail_on, default=(), metavar="REGLAS",
                        help="Sale con código 1 si hay hallazgos en estas reglas (separadas por comas): "
                             f"{', '.join(TODAS)}, o 'any'.")
    parser.add_argument("--exclude-forks", dest="excluir_forks", action="store_true",
                        help="Ignora los repositorios que son forks.")
    parser.add_argument("--exclude-archived", dest="excluir_archivados", action="store_true",
                        help="Ignora los repositorios archivados.")
    parser.add_argument("--inject", dest="inject", metavar="ARCHIVO",
                        help="Actualiza la tabla de demos dentro de ARCHIVO (p. ej. README.md), entre los marcadores "
                             "<!-- github-pages-auditor:start --> y <!-- github-pages-auditor:end -->.")
    parser.add_argument("-q", "--quiet", dest="quiet", action="store_true",
                        help="No muestra tablas ni progreso (solo errores).")
    parser.add_argument("--workers", dest="max_workers", type=int, default=WORKERS_DEFECTO,
                        help=f"Número máximo de hilos concurrentes (por defecto {WORKERS_DEFECTO}).")
    parser.add_argument("--timeout", dest="timeout", type=float, default=TIMEOUT_DEFECTO,
                        help=f"Timeout por petición en segundos (por defecto {TIMEOUT_DEFECTO:g}).")
    parser.add_argument("--no-api", dest="forzar_web", action="store_true",
                        help="Forzar scraping web omitiendo la API aunque haya token.")
    parser.add_argument("--no-color", dest="sin_color", action="store_true",
                        help="Desactivar colores en la consola.")
    parser.add_argument("--no-env", dest="no_env", action="store_true",
                        help="No leer el archivo .env.")
    parser.add_argument("-V", "--version", action="version",
                        version=f"%(prog)s {__version__}\n" + creditos(sep="\n"))
    return parser


def parse_args(args=None) -> Config:
    # El .env se carga ANTES de construir los valores por defecto del parser.
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--no-env", action="store_true")
    if not pre.parse_known_args(args)[0].no_env:
        load_dotenv(find_dotenv(usecwd=True))  # busca el .env en el directorio actual

    parser = crear_parser()
    parsed = parser.parse_args(args)

    usuario = (parsed.usuario or "").strip()
    if not usuario:
        parser.error("El usuario de GitHub es obligatorio. Usa -u <usuario> o define USUARIO_GITHUB.")
    if parsed.max_workers < 1:
        parser.error("--workers debe ser >= 1.")
    if parsed.timeout <= 0:
        parser.error("--timeout debe ser > 0.")

    salida = (parsed.archivo_salida or "").strip() or None
    if salida is None and not parsed.inject:
        salida = f"{SALIDA_BASE}.{parsed.formato}"  # con --inject solo se escribe informe si se pide con -o

    return Config(
        usuario=usuario,
        dominio_web=normalizar_dominio(parsed.dominio_web, usuario),
        github_token=(parsed.github_token or "").strip() or None,
        archivo_salida=salida,
        max_workers=parsed.max_workers,
        forzar_web=parsed.forzar_web,
        sin_color=parsed.sin_color,
        timeout=parsed.timeout,
        formato=parsed.formato,
        fail_on=tuple(parsed.fail_on),
        excluir_forks=parsed.excluir_forks,
        excluir_archivados=parsed.excluir_archivados,
        inject=parsed.inject,
        quiet=parsed.quiet,
    )
