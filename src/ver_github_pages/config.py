"""Configuración: parámetros de consola > variables de entorno (.env opcional) > defecto."""
import argparse
import os
from dataclasses import dataclass
from typing import Optional

from dotenv import find_dotenv, load_dotenv

from . import NOMBRE_PROGRAMA, __version__, creditos

SALIDA_DEFECTO = "paginas_github.txt"
WORKERS_DEFECTO = 15
TIMEOUT_DEFECTO = 10.0


@dataclass
class Config:
    usuario: str
    dominio_web: str
    github_token: Optional[str]
    archivo_salida: str
    max_workers: int
    forzar_web: bool
    sin_color: bool
    timeout: float = TIMEOUT_DEFECTO

    @property
    def usa_api(self) -> bool:
        return bool(self.github_token) and not self.forzar_web


def normalizar_dominio(dominio: Optional[str], usuario: str) -> str:
    dominio = (dominio or "").strip()
    if not dominio:
        return f"https://{usuario}.github.io"
    if not dominio.lower().startswith(("http://", "https://")):
        dominio = f"https://{dominio}"
    return dominio.rstrip("/")


def crear_parser() -> argparse.ArgumentParser:
    env = lambda k, d=None: (os.getenv(k) or "").strip() or d  # noqa: E731  (vacío == no definido)

    parser = argparse.ArgumentParser(
        prog=NOMBRE_PROGRAMA,
        description="Auditor CLI para repositorios, GitHub Pages y releases de un usuario de GitHub.\n"
                    "Funciona solo con parámetros: el archivo .env y el token de la API son opcionales.",
        epilog=(
            "Prioridad de configuración: parámetros > variables de entorno/.env > valores por defecto.\n"
            "Variables de entorno: USUARIO_GITHUB, DOMINIO_WEB, GITHUB_TOKEN, ARCHIVO_SALIDA.\n\n"
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
    parser.add_argument("-o", "--output", dest="archivo_salida", default=env("ARCHIVO_SALIDA", SALIDA_DEFECTO),
                        help=f"Archivo de salida del reporte (por defecto {SALIDA_DEFECTO}).")
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

    return Config(
        usuario=usuario,
        dominio_web=normalizar_dominio(parsed.dominio_web, usuario),
        github_token=(parsed.github_token or "").strip() or None,
        archivo_salida=parsed.archivo_salida,
        max_workers=parsed.max_workers,
        forzar_web=parsed.forzar_web,
        sin_color=parsed.sin_color,
        timeout=parsed.timeout,
    )
