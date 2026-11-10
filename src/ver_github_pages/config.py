import argparse
import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

@dataclass
class Config:
    usuario: str
    dominio_web: str
    github_token: Optional[str]
    archivo_salida: str
    max_workers: int
    forzar_web: bool
    sin_color: bool

def parse_args(args=None) -> Config:
    load_dotenv()
    
    parser = argparse.ArgumentParser(
        prog="ver-github-pages",
        description="Auditor CLI para repositorios, GitHub Pages y releases."
    )
    
    parser.add_argument("-u", "--usuario", "--user", dest="usuario",
                        default=os.getenv("USUARIO_GITHUB"),
                        help="Nombre de usuario de GitHub (obligatorio).")
    
    parser.add_argument("-w", "--web", "--dominio", dest="dominio_web",
                        default=os.getenv("DOMINIO_WEB"),
                        help="Dominio base de tu sitio web o GitHub Pages.")
    
    parser.add_argument("-k", "--key", "--token", dest="github_token",
                        default=os.getenv("GITHUB_TOKEN"),
                        help="GitHub Personal Access Token (opcional).")
    
    parser.add_argument("-o", "--output", dest="archivo_salida",
                        default=os.getenv("ARCHIVO_SALIDA", "paginas_github.txt"),
                        help="Archivo de salida del reporte.")
    
    parser.add_argument("--workers", dest="max_workers", type=int, default=15,
                        help="Número máximo de hilos concurrentes.")
    
    parser.add_argument("--no-api", dest="forzar_web", action="store_true",
                        help="Forzar scraping web omitiendo la API.")
    
    parser.add_argument("--no-color", dest="sin_color", action="store_true",
                        help="Desactivar colores en la consola.")
    
    parsed = parser.parse_args(args)

    usuario = (parsed.usuario or "").strip()
    if not usuario:
        parser.error("El usuario de GitHub es obligatorio. Usa -u <usuario> o define USUARIO_GITHUB en .env.")

    dominio = (parsed.dominio_web or "").strip()
    if not dominio:
        dominio = f"https://{usuario}.github.io"
    if not dominio.startswith(("http://", "https://")):
        dominio = f"https://{dominio}"
    dominio = dominio.rstrip("/")

    token = (parsed.github_token or "").strip() or None

    return Config(
        usuario=usuario,
        dominio_web=dominio,
        github_token=token,
        archivo_salida=parsed.archivo_salida,
        max_workers=parsed.max_workers,
        forzar_web=parsed.forzar_web,
        sin_color=parsed.sin_color,
    )