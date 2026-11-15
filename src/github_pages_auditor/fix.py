"""``--fix``, ``--fix-pages`` y ``--fix-metadata``: arreglos opt-in sobre tus repos.

Por defecto solo se PLANEA (``--dry-run`` implícito); ``--yes`` aplica los cambios. Nunca toca forks, archivados
ni archivos que ya existan, y no escribe nada si la API no responde como se espera.
"""
import base64
import re
from importlib import resources
from typing import Dict, List, Optional

import requests

from .models import AuditReport, RepoInfo
from .rules import evaluar

API = "https://api.github.com"
# regla -> (ruta destino en el repo, plantilla del paquete)
PLANTILLAS = {
    "missing-security-policy": ("SECURITY.md", "SECURITY.md"),
    "missing-contributing": ("CONTRIBUTING.md", "CONTRIBUTING.md"),
    "missing-code-of-conduct": ("CODE_OF_CONDUCT.md", "CODE_OF_CONDUCT.md"),
    "missing-issue-template": (".github/ISSUE_TEMPLATE/bug_report.md", "bug_report.md"),
}
MAX_DESCRIPCION = 120


def leer_plantilla(nombre: str) -> str:
    return resources.files("github_pages_auditor").joinpath("templates").joinpath(nombre).read_text(encoding="utf-8")


def _editable(r: RepoInfo) -> bool:
    return not r.es_fork and not r.esta_archivado and not r.error


def planear_archivos(report: AuditReport, hallazgos: Dict[str, List[str]]) -> List[dict]:
    por_nombre = {r.nombre: r for r in report.repos}
    acciones = []
    for regla, (ruta, _) in PLANTILLAS.items():
        for nombre in hallazgos.get(regla, []):
            if _editable(por_nombre[nombre]):
                acciones.append({"repo": nombre, "action": "create-file", "target": ruta, "status": "planned"})
    return acciones


def planear_pages(report: AuditReport) -> List[dict]:
    return [{"repo": r.nombre, "action": "enforce-https", "target": "pages", "status": "planned"}
            for r in report.repos
            if _editable(r) and r.pages_salud is not None and "https-no-forzado" in r.pages_salud.avisos]


def descripcion_desde_readme(texto: str) -> Optional[str]:
    """Primer párrafo de texto del README (sin títulos, insignias, HTML ni enlaces de imagen), recortado."""
    for bloque in re.split(r"\n\s*\n", texto or ""):
        linea = " ".join(bloque.split())
        linea = re.sub(r"!\[[^\]]*\]\([^)]*\)|<[^>]+>", "", linea)
        linea = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", linea).strip(" #>*-_`")
        if len(linea) >= 20 and not linea.startswith(("#", "[![", "|", "```")):
            return linea[:MAX_DESCRIPCION].rstrip(" ,;:.") if len(linea) > MAX_DESCRIPCION else linea
    return None


def topics_sugeridos(r: RepoInfo) -> List[str]:
    topics = []
    if r.lenguaje:
        topics.append(re.sub(r"[^a-z0-9-]+", "-", r.lenguaje.lower()).strip("-"))
    if r.tiene_pages:
        topics.append("github-pages")
    return [t for t in dict.fromkeys(topics) if t]


class Arreglos:
    def __init__(self, usuario: str, session, headers: dict, timeout: float = 15.0):
        self.usuario, self.session, self.headers, self.timeout = usuario, session, headers, timeout

    def _req(self, metodo: str, ruta: str, **kw):
        return self.session.request(metodo, f"{API}{ruta}", headers=self.headers, timeout=self.timeout, **kw)

    def readme(self, repo: str) -> Optional[str]:
        res = self._req("GET", f"/repos/{self.usuario}/{repo}/readme")
        if res.status_code != 200:
            return None
        try:
            return base64.b64decode(res.json().get("content", "")).decode("utf-8", "replace")
        except (ValueError, AttributeError):
            return None

    def planear_metadatos(self, report: AuditReport) -> List[dict]:
        acciones = []
        for r in report.repos:
            if not _editable(r):
                continue
            if r.tiene_descripcion is False and r.tiene_readme:
                desc = descripcion_desde_readme(self.readme(r.nombre) or "")
                if desc:
                    acciones.append({"repo": r.nombre, "action": "set-description", "target": desc, "status": "planned"})
            if r.topics is not None and not r.topics and topics_sugeridos(r):
                acciones.append({"repo": r.nombre, "action": "set-topics", "target": ",".join(topics_sugeridos(r)),
                                 "status": "planned"})
        return acciones

    def aplicar(self, accion: dict) -> dict:
        """Ejecuta una acción planeada. Devuelve la acción con ``status`` = applied | skipped | failed."""
        repo, tipo, destino = accion["repo"], accion["action"], accion["target"]
        base = f"/repos/{self.usuario}/{repo}"
        try:
            if tipo == "create-file":
                existe = self._req("GET", f"{base}/contents/{destino}")
                if existe.status_code == 200:
                    return {**accion, "status": "skipped", "detail": "ya existe"}
                plantilla = next(p for _, (ruta, p) in PLANTILLAS.items() if ruta == destino)
                contenido = base64.b64encode(leer_plantilla(plantilla).encode("utf-8")).decode("ascii")
                res = self._req("PUT", f"{base}/contents/{destino}",
                                json={"message": f"docs: añadir {destino} (github-pages-auditor)", "content": contenido})
                ok = res.status_code in (200, 201)
            elif tipo == "enforce-https":
                res = self._req("PUT", f"{base}/pages", json={"https_enforced": True})
                ok = res.status_code in (200, 204)
            elif tipo == "set-description":
                res = self._req("PATCH", base, json={"description": destino})
                ok = res.status_code == 200
            elif tipo == "set-topics":
                res = self._req("PUT", f"{base}/topics", json={"names": destino.split(",")})
                ok = res.status_code == 200
            else:
                return {**accion, "status": "skipped", "detail": "acción desconocida"}
        except requests.RequestException as e:
            return {**accion, "status": "failed", "detail": type(e).__name__}
        return {**accion, "status": "applied"} if ok else {**accion, "status": "failed",
                                                          "detail": f"HTTP {res.status_code}"}


def ejecutar(config, report: AuditReport, session, headers: dict, hallazgos=None) -> List[dict]:
    """Planea (y con ``--yes`` sin ``--dry-run`` aplica) los arreglos pedidos. Devuelve la lista de acciones."""
    hallazgos = hallazgos if hallazgos is not None else evaluar(report.repos)
    arreglos = Arreglos(report.usuario, session, headers)
    acciones: List[dict] = []
    if config.fix:
        acciones += planear_archivos(report, hallazgos)
    if config.fix_pages:
        acciones += planear_pages(report)
    if config.fix_metadata:
        acciones += arreglos.planear_metadatos(report)
    if config.yes and not config.dry_run:
        acciones = [arreglos.aplicar(a) for a in acciones]
    return acciones
