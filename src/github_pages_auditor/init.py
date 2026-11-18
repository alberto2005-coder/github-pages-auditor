"""``--init``: crea un ``.github-pages-auditor.toml`` de partida (sin secretos) en la carpeta actual."""
import os
from typing import Optional

from .config import ARCHIVO_CONFIG

PLANTILLA = """\
# Configuración de github-pages-auditor. Prioridad: línea de comandos > variables de entorno/.env > este archivo.
# NUNCA pongas aquí el token ni el webhook: usa las variables GITHUB_TOKEN y NOTIFY_WEBHOOK.
{usuario}
format = "html"            # txt, json, md, github, html, csv, sarif, badge, trend, issue
lang = "es"                # es | en
exclude_forks = true
exclude_archived = false

# --- Opcional (quita el # para activarlo) ---
# web = "tu-dominio.dev"   # dominio propio para las URL de Pages
# fail_on = ["broken-pages", "missing-license"]   # reglas que hacen fallar el programa (exit 1)
# min_score = 70
# stale_months = 12
# history = "historial"    # guarda cada informe y permite -f trend
# cache = "auto"           # caché con ETag: menos cuota de la API
# deep = true              # CI, Dependabot, protección de ramas (necesita token)
# scorecard = true         # nota de OpenSSF Scorecard
# crawl = true             # rastrea páginas internas y valida el sitemap
# check_links = true       # enlaces rotos de la portada
# readme_quality = true    # regla weak-readme
# dep_licenses = true      # regla copyleft-dependency
# defaults_repo = true     # contar los archivos heredados de tu repo .github

# Reglas propias (id siempre con prefijo custom-; solo modo API):
# [[custom_rules]]
# id = "custom-tiene-docs"
# path = "docs"
# message = "El repo no tiene carpeta docs"
#
# [[custom_rules]]
# id = "custom-readme-instala"
# path = "README.md"
# type = "content-required"   # file-required | file-forbidden | content-required | content-forbidden
# contains = "pip install"    # o regex = "..."
"""


def plantilla(usuario: Optional[str] = None) -> str:
    linea = f'user = "{usuario}"' if usuario and usuario.replace("-", "").isalnum() else '# user = "tu-usuario"'
    return PLANTILLA.format(usuario=linea)


def crear(ruta: Optional[str] = None, usuario: Optional[str] = None, sobrescribir: bool = False) -> str:
    """Escribe el archivo y devuelve su ruta. Lanza ``FileExistsError`` si ya existe y no se pide sobrescribir."""
    destino = ruta or os.path.join(os.getcwd(), ARCHIVO_CONFIG)
    if os.path.exists(destino) and not sobrescribir:
        raise FileExistsError(destino)
    with open(destino, "w", encoding="utf-8", newline="\n") as f:
        f.write(plantilla(usuario))
    return destino
