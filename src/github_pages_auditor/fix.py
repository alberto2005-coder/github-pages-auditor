"""``--fix``, ``--fix-extra``, ``--fix-pages`` y ``--fix-metadata``: arreglos opt-in sobre tus repos.

Por defecto solo se PLANEA (``--dry-run`` implícito); ``--yes`` aplica los cambios. Nunca toca forks, archivados
ni archivos que ya existan, y no escribe nada si la API no responde como se espera. Con ``--fix-mode pr`` los
archivos se suben a una rama nueva y se abre una Pull Request en vez de hacer commit en la rama principal.
"""
import base64
import re
from datetime import datetime, timezone
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
# --fix-extra (1.5.0): archivos según el lenguaje del repo.
RUTA_LICENCIA, RUTA_GITIGNORE = "LICENSE", ".gitignore"
RUTA_DEPENDABOT, RUTA_CI = ".github/dependabot.yml", ".github/workflows/ci.yml"
EXTRAS = {  # regla -> ruta destino
    "missing-license": RUTA_LICENCIA, "missing-gitignore": RUTA_GITIGNORE,
    "missing-dependabot": RUTA_DEPENDABOT, "missing-ci": RUTA_CI,
}
GITIGNORE_POR_LENGUAJE = {"Python": "python", "JavaScript": "node", "TypeScript": "node", "Java": "java",
                          "Kotlin": "java", "Go": "go", "Rust": "rust", "C#": "csharp"}
CI_POR_LENGUAJE = {"Python": "python", "JavaScript": "node", "TypeScript": "node", "Go": "go", "Rust": "rust"}
ECOSISTEMA_DEPENDABOT = {"Python": "pip", "JavaScript": "npm", "TypeScript": "npm", "Java": "maven", "Go": "gomod",
                         "Rust": "cargo", "PHP": "composer", "Ruby": "bundler", "C#": "nuget", "Dart": "pub"}
MAX_DESCRIPCION = 120
RAMA_PR = "github-pages-auditor/fix"


def leer_plantilla(nombre: str) -> str:
    return resources.files("github_pages_auditor").joinpath("templates").joinpath(nombre).read_text(encoding="utf-8")


def dependabot_yml(lenguaje: Optional[str]) -> str:
    """``dependabot.yml`` semanal: GitHub Actions y, si se conoce el lenguaje, su gestor de paquetes."""
    ecosistemas = ["github-actions"]
    if lenguaje in ECOSISTEMA_DEPENDABOT:
        ecosistemas.append(ECOSISTEMA_DEPENDABOT[lenguaje])
    bloques = "".join(f'  - package-ecosystem: "{e}"\n    directory: "/"\n    schedule:\n      interval: "weekly"\n'
                      for e in ecosistemas)
    return ("# Generado por github-pages-auditor: es un punto de partida, ajústalo a tu proyecto.\n"
            f"version: 2\nupdates:\n{bloques}")


def contenido_de(repo: RepoInfo, ruta: str, propietario: str, licencia: str = "mit",
                 ahora: Optional[datetime] = None) -> Optional[str]:
    """Texto del archivo ``ruta`` para ``repo``; ``None`` si no hay plantilla adecuada (p. ej. CI de un lenguaje raro)."""
    for _, (destino, plantilla) in PLANTILLAS.items():
        if destino == ruta:
            return leer_plantilla(plantilla)
    if ruta == RUTA_LICENCIA:
        año = (ahora or datetime.now(timezone.utc)).year
        return leer_plantilla(f"license-{licencia}.txt").replace("{year}", str(año)).replace("{holder}", propietario)
    if ruta == RUTA_GITIGNORE:
        return leer_plantilla(f"gitignore-{GITIGNORE_POR_LENGUAJE.get(repo.lenguaje or '', 'generic')}.txt")
    if ruta == RUTA_DEPENDABOT:
        return dependabot_yml(repo.lenguaje)
    if ruta == RUTA_CI:
        tipo = CI_POR_LENGUAJE.get(repo.lenguaje or "")
        if tipo is None:
            return None
        return leer_plantilla(f"ci-{tipo}.yml").replace("{rama}", repo.rama_defecto or "main")
    return None


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


def planear_extra(report: AuditReport, hallazgos: Dict[str, List[str]], licencia: str = "mit",
                  propietario: str = "") -> List[dict]:
    """LICENSE, .gitignore, dependabot.yml y CI (``--fix-extra``). Sin plantilla adecuada no se planea nada."""
    por_nombre = {r.nombre: r for r in report.repos}
    acciones = []
    for regla, ruta in EXTRAS.items():
        for nombre in hallazgos.get(regla, []):
            repo = por_nombre[nombre]
            if _editable(repo) and contenido_de(repo, ruta, propietario or report.usuario, licencia) is not None:
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
    def __init__(self, usuario: str, session, headers: dict, timeout: float = 15.0,
                 repos: Optional[Dict[str, RepoInfo]] = None, licencia: str = "mit", modo: str = "direct"):
        self.usuario, self.session, self.headers, self.timeout = usuario, session, headers, timeout
        self.repos, self.licencia, self.modo = repos or {}, licencia, modo

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
                texto = contenido_de(self.repos.get(repo) or RepoInfo(repo), destino, self.usuario, self.licencia)
                if texto is None:
                    return {**accion, "status": "skipped", "detail": "sin plantilla"}
                contenido = base64.b64encode(texto.encode("utf-8")).decode("ascii")
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


    def aplicar_pr(self, repo: str, acciones: List[dict]) -> List[dict]:
        """Sube los archivos de un repo a una rama nueva y abre una Pull Request (``--fix-mode pr``)."""
        base = f"/repos/{self.usuario}/{repo}"
        info = self.repos.get(repo) or RepoInfo(repo)
        rama_base = info.rama_defecto
        resultados: Dict[int, dict] = {}
        pendientes: List[int] = []
        try:
            if not rama_base:
                rama_base = (self._req("GET", base).json() or {}).get("default_branch")
            for i, a in enumerate(acciones):
                existe = self._req("GET", f"{base}/contents/{a['target']}", params={"ref": rama_base})
                if existe.status_code == 200:
                    resultados[i] = {**a, "status": "skipped", "detail": "ya existe"}
                elif contenido_de(info, a["target"], self.usuario, self.licencia) is None:
                    resultados[i] = {**a, "status": "skipped", "detail": "sin plantilla"}
                else:
                    pendientes.append(i)
            extra: List[dict] = []
            if pendientes:
                ref = self._req("GET", f"{base}/git/ref/heads/{rama_base}")
                if ref.status_code != 200:
                    raise _FalloPr(f"HTTP {ref.status_code} al leer la rama {rama_base}")
                sha = (ref.json().get("object") or {}).get("sha")
                ahora = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
                rama = f"{RAMA_PR}-{ahora}"
                nueva = self._req("POST", f"{base}/git/refs", json={"ref": f"refs/heads/{rama}", "sha": sha})
                if nueva.status_code != 201:
                    raise _FalloPr(f"HTTP {nueva.status_code} al crear la rama")
                subidos = 0
                for i in pendientes:
                    a = acciones[i]
                    texto = contenido_de(info, a["target"], self.usuario, self.licencia) or ""
                    res = self._req("PUT", f"{base}/contents/{a['target']}", json={
                        "message": f"docs: añadir {a['target']} (github-pages-auditor)", "branch": rama,
                        "content": base64.b64encode(texto.encode("utf-8")).decode("ascii")})
                    ok = res.status_code in (200, 201)
                    subidos += ok
                    resultados[i] = {**a, "status": "applied" if ok else "failed", "detail": f"rama {rama}" if ok
                                     else f"HTTP {res.status_code}"}
                if subidos:
                    pr = self._req("POST", f"{base}/pulls", json={
                        "title": "Mejoras sugeridas por github-pages-auditor", "head": rama, "base": rama_base,
                        "body": "Archivos que faltaban en el repositorio, generados con "
                                "[github-pages-auditor](https://github.com/alberto2005-coder/github-pages-auditor).\n\n"
                                "Revísalos y ajústalos antes de fusionar."})
                    url = (pr.json() or {}).get("html_url") if pr.status_code == 201 else None
                    extra.append({"repo": repo, "action": "open-pr", "target": url or rama,
                                  "status": "applied" if url else "failed",
                                  **({} if url else {"detail": f"HTTP {pr.status_code}"})})
            return [resultados[i] for i in range(len(acciones))] + extra
        except (requests.RequestException, _FalloPr, AttributeError, ValueError) as e:
            detalle = str(e) if isinstance(e, _FalloPr) else type(e).__name__
            return [resultados.get(i, {**a, "status": "failed", "detail": detalle}) for i, a in enumerate(acciones)]


class _FalloPr(Exception):
    """Un paso de la Pull Request no respondió como se esperaba."""


def ejecutar(config, report: AuditReport, session, headers: dict, hallazgos=None) -> List[dict]:
    """Planea (y con ``--yes`` sin ``--dry-run`` aplica) los arreglos pedidos. Devuelve la lista de acciones."""
    hallazgos = hallazgos if hallazgos is not None else evaluar(report.repos)
    solo = tuple(getattr(config, "fix_only", ()) or ())
    if solo:  # --fix-only: las reglas de archivos que no se eligieron quedan fuera del plan
        hallazgos = {k: ([] if k in {**PLANTILLAS, **EXTRAS} and k not in solo else v) for k, v in hallazgos.items()}
    modo = getattr(config, "fix_mode", "direct")
    arreglos = Arreglos(report.usuario, session, headers, repos={r.nombre: r for r in report.repos},
                        licencia=getattr(config, "licencia", "mit"), modo=modo)
    acciones: List[dict] = []
    if config.fix:
        acciones += planear_archivos(report, hallazgos)
    if getattr(config, "fix_extra", False):
        acciones += planear_extra(report, hallazgos, arreglos.licencia, report.usuario)
    if modo == "pr":
        for a in acciones:
            a["via"] = "pr"
    if config.fix_pages:
        acciones += planear_pages(report)
    if config.fix_metadata:
        acciones += arreglos.planear_metadatos(report)
    if config.yes and not config.dry_run:
        acciones = _aplicar_todo(arreglos, acciones, modo)
    return acciones


def _aplicar_todo(arreglos: "Arreglos", acciones: List[dict], modo: str) -> List[dict]:
    if modo != "pr":
        return [arreglos.aplicar(a) for a in acciones]
    # En modo pr los archivos de cada repo van juntos (una rama, una PR); lo demás se aplica como siempre.
    por_repo: Dict[str, List[dict]] = {}
    for a in acciones:
        if a.get("via") == "pr":
            por_repo.setdefault(a["repo"], []).append(a)
    hechos: Dict[str, List[dict]] = {repo: arreglos.aplicar_pr(repo, lista) for repo, lista in por_repo.items()}
    resultado: List[dict] = []
    for a in acciones:
        if a.get("via") == "pr":
            lista = hechos[a["repo"]]
            resultado.append({**lista.pop(0), "via": "pr"} if lista and lista[0]["action"] == a["action"] else a)
        else:
            resultado.append(arreglos.aplicar(a))
    for lista in hechos.values():  # lo que queda es la acción open-pr de cada repo
        resultado += [x for x in lista if x["action"] == "open-pr"]
    return resultado
