"""Configuración: parámetros de consola > variables de entorno (.env opcional) > defecto."""
import argparse
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from dotenv import find_dotenv, load_dotenv

try:  # Python 3.11+ trae tomllib; en 3.10 se usa el paquete tomli (dependencia condicional)
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib

from . import NOMBRE_PROGRAMA, __version__, creditos
from .rules import COMUNIDAD, STALE_MESES_DEFECTO, TODAS, parsear_fail_on

SALIDA_BASE = "paginas_github"
WORKERS_DEFECTO = 15
TIMEOUT_DEFECTO = 10.0
FORMATOS = ("txt", "json", "md", "github")
ORDENES = ("listing", "name", "stars", "updated")
ARCHIVO_CONFIG = ".github-pages-auditor.toml"


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
    details: bool = False
    orden: str = "listing"
    ignorar: Tuple[str, ...] = ()
    solo: Tuple[str, ...] = ()
    stale_meses: int = STALE_MESES_DEFECTO
    baseline: Optional[str] = None

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


def _lista(texto: str) -> Tuple[str, ...]:
    """'a, b,c' -> ('a', 'b', 'c')."""
    return tuple(dict.fromkeys(t.strip() for t in texto.split(",") if t.strip()))


class ErrorConfig(ValueError):
    """El archivo de configuración no es válido."""


# clave del archivo .toml -> (destino en el parser, tipo esperado)
CLAVES_ARCHIVO = {
    "user": ("usuario", str), "web": ("dominio_web", str), "output": ("archivo_salida", str),
    "format": ("formato", str), "fail_on": ("fail_on", "lista"), "exclude_forks": ("excluir_forks", bool),
    "exclude_archived": ("excluir_archivados", bool), "ignore": ("ignorar", "lista"), "only": ("solo", "lista"),
    "stale_months": ("stale_meses", int), "workers": ("max_workers", int), "timeout": ("timeout", float),
    "details": ("details", bool), "sort": ("orden", str), "no_api": ("forzar_web", bool),
    "quiet": ("quiet", bool), "no_color": ("sin_color", bool), "baseline": ("baseline", str),
}


def cargar_archivo_config(ruta: str) -> Dict[str, Any]:
    """Lee y valida un ``.toml``. Devuelve {destino_del_parser: valor}. Lanza ``ErrorConfig``."""
    try:
        with open(ruta, "rb") as f:
            datos = tomllib.load(f)
    except OSError as e:
        raise ErrorConfig(f"no se puede leer: {e}") from e
    except tomllib.TOMLDecodeError as e:
        raise ErrorConfig(f"TOML no válido: {e}") from e

    for prohibida in ("token", "github_token", "key"):
        if prohibida in datos:
            raise ErrorConfig("no pongas el token en el archivo de configuración; "
                              "usa la variable de entorno GITHUB_TOKEN")
    desconocidas = [k for k in datos if k not in CLAVES_ARCHIVO]
    if desconocidas:
        raise ErrorConfig(f"claves desconocidas: {', '.join(desconocidas)}. Válidas: {', '.join(CLAVES_ARCHIVO)}")

    valores: Dict[str, Any] = {}
    for clave, valor in datos.items():
        destino, tipo = CLAVES_ARCHIVO[clave]
        if tipo == "lista":
            if isinstance(valor, str):
                valor = [valor]
            if not isinstance(valor, list) or not all(isinstance(x, str) for x in valor):
                raise ErrorConfig(f"'{clave}' debe ser una lista de textos")
            if clave == "fail_on":
                try:
                    valores[destino] = tuple(parsear_fail_on(",".join(valor)))
                except ValueError as e:
                    raise ErrorConfig(f"'fail_on': {e}") from e
            else:
                valores[destino] = tuple(x.strip() for x in valor if x.strip())
            continue
        correcto = (isinstance(valor, (int, float)) and not isinstance(valor, bool)) if tipo is float \
            else isinstance(valor, tipo) and (tipo is bool or not isinstance(valor, bool))
        if not correcto:
            raise ErrorConfig(f"'{clave}' debe ser de tipo {tipo.__name__}")
        valores[destino] = float(valor) if tipo is float else valor
    if valores.get("formato", "txt") not in FORMATOS:
        raise ErrorConfig(f"'format' debe ser uno de: {', '.join(FORMATOS)}")
    if valores.get("orden", "listing") not in ORDENES:
        raise ErrorConfig(f"'sort' debe ser uno de: {', '.join(ORDENES)}")
    return valores


def crear_parser(archivo: Optional[Dict[str, Any]] = None) -> argparse.ArgumentParser:
    archivo = archivo or {}
    env = lambda k, d=None: (os.getenv(k) or "").strip() or d  # noqa: E731  (vacío == no definido)

    parser = argparse.ArgumentParser(
        prog=NOMBRE_PROGRAMA,
        description="Auditor CLI para repositorios, GitHub Pages y releases de un usuario de GitHub.\n"
                    "Funciona solo con parámetros: el archivo .env y el token de la API son opcionales.",
        epilog=(
            "Prioridad de configuración: parámetros > variables de entorno/.env > archivo "
            f"{ARCHIVO_CONFIG} > valores por defecto.\n"
            "Variables de entorno: USUARIO_GITHUB, DOMINIO_WEB, GITHUB_TOKEN, ARCHIVO_SALIDA.\n"
            "Códigos de salida: 0 ok, 1 --fail-on disparado, 2 error, 3 sin repositorios, 130 Ctrl+C.\n\n"
            + creditos(sep="\n")
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-u", "--usuario", "--user", dest="usuario", default=env("USUARIO_GITHUB", archivo.get("usuario")),
                        help="Nombre de usuario de GitHub (obligatorio).")
    parser.add_argument("-w", "--web", "--dominio", dest="dominio_web", default=env("DOMINIO_WEB", archivo.get("dominio_web")),
                        help="Dominio base de tu sitio web o GitHub Pages (por defecto https://<usuario>.github.io).")
    parser.add_argument("-k", "--key", "--token", dest="github_token", default=env("GITHUB_TOKEN"),
                        help="GitHub Personal Access Token (opcional). Con token se usa la API; sin él, el modo web. "
                             "Más seguro: variable GITHUB_TOKEN (un parámetro queda en el historial del shell).")
    parser.add_argument("-o", "--output", dest="archivo_salida", default=env("ARCHIVO_SALIDA", archivo.get("archivo_salida")),
                        help=f"Archivo del informe (por defecto {SALIDA_BASE}.<formato>). Usa '-' para escribirlo "
                             "en la salida estándar (la interfaz pasa a stderr).")
    parser.add_argument("-f", "--format", dest="formato", choices=FORMATOS, default="txt",
                        help="Formato del informe: txt (por defecto), json (contrato versionado), md "
                             "(tabla de demos en vivo para tu README) o github (anotaciones ::warning:: "
                             "para GitHub Actions; sale por stdout).")
    parser.add_argument("--fail-on", dest="fail_on", type=_fail_on, default=(), metavar="REGLAS",
                        help="Sale con código 1 si hay hallazgos en estas reglas (separadas por comas): "
                             f"{', '.join(TODAS)}. Grupos: 'any' (las reglas básicas de siempre), "
                             f"'community' ({len(COMUNIDAD)} reglas de comunidad y actividad) y 'all' (todas).")
    parser.add_argument("--exclude-forks", dest="excluir_forks", action="store_true",
                        help="Ignora los repositorios que son forks.")
    parser.add_argument("--exclude-archived", dest="excluir_archivados", action="store_true",
                        help="Ignora los repositorios archivados.")
    parser.add_argument("--inject", dest="inject", metavar="ARCHIVO",
                        help="Actualiza la tabla de demos dentro de ARCHIVO (p. ej. README.md), entre los marcadores "
                             "<!-- github-pages-auditor:start --> y <!-- github-pages-auditor:end -->.")
    parser.add_argument("--ignore", dest="ignorar", type=_lista, default=(), metavar="REPOS",
                        help="Repos a ignorar (nombres o patrones con * y ?, separados por comas).")
    parser.add_argument("--only", dest="solo", type=_lista, default=(), metavar="REPOS",
                        help="Audita solo estos repos (nombres o patrones con * y ?, separados por comas).")
    parser.add_argument("--details", dest="details", action="store_true",
                        help="Añade al informe el detalle por repo: estrellas, lenguaje, licencia, último push "
                             "y última release (con token; sin él algunos datos no están disponibles).")
    parser.add_argument("--sort", dest="orden", choices=ORDENES, default="listing",
                        help="Orden de los repos: listing (el de GitHub, por defecto), name, stars o updated.")
    parser.add_argument("--stale-months", dest="stale_meses", type=int, default=STALE_MESES_DEFECTO, metavar="N",
                        help=f"Meses sin push para la regla stale-repo (por defecto {STALE_MESES_DEFECTO}).")
    parser.add_argument("--baseline", dest="baseline", metavar="INFORME.json",
                        help="Informe JSON anterior: --fail-on solo se dispara por hallazgos NUEVOS respecto a él.")
    parser.add_argument("--config", dest="config", metavar="ARCHIVO",
                        help=f"Archivo de configuración TOML (por defecto ./{ARCHIVO_CONFIG} si existe).")
    parser.add_argument("--no-config", dest="no_config", action="store_true",
                        help=f"No leer {ARCHIVO_CONFIG}.")
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
    # Valores del archivo de configuración (los parámetros y las variables de entorno les ganan).
    por_defecto = {k: v for k, v in archivo.items() if k not in ("usuario", "dominio_web", "archivo_salida")}
    parser.set_defaults(**por_defecto)
    return parser


def parse_args(args=None) -> Config:
    # El .env se carga ANTES de construir los valores por defecto del parser.
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--no-env", action="store_true")
    pre.add_argument("--no-config", action="store_true")
    pre.add_argument("--config")
    previo = pre.parse_known_args(args)[0]
    if not previo.no_env:
        load_dotenv(find_dotenv(usecwd=True))  # busca el .env en el directorio actual

    archivo: Dict[str, Any] = {}
    ruta_config = previo.config or (ARCHIVO_CONFIG if os.path.isfile(ARCHIVO_CONFIG) else None)
    if ruta_config and not previo.no_config:
        try:
            archivo = cargar_archivo_config(ruta_config)
        except ErrorConfig as e:
            crear_parser().error(f"{ruta_config}: {e}")

    parser = crear_parser(archivo)
    parsed = parser.parse_args(args)

    usuario = (parsed.usuario or "").strip()
    if not usuario:
        parser.error("El usuario de GitHub es obligatorio. Usa -u <usuario> o define USUARIO_GITHUB.")
    if parsed.max_workers < 1:
        parser.error("--workers debe ser >= 1.")
    if parsed.timeout <= 0:
        parser.error("--timeout debe ser > 0.")
    if parsed.stale_meses < 1:
        parser.error("--stale-months debe ser >= 1.")

    salida = (parsed.archivo_salida or "").strip() or None
    if salida is None and not parsed.inject:
        # con --inject solo se escribe informe si se pide con -o; el formato github va a stdout
        salida = "-" if parsed.formato == "github" else f"{SALIDA_BASE}.{parsed.formato}"

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
        details=parsed.details,
        orden=parsed.orden,
        ignorar=tuple(parsed.ignorar),
        solo=tuple(parsed.solo),
        stale_meses=parsed.stale_meses,
        baseline=parsed.baseline,
    )
