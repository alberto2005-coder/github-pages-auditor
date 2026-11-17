"""Formatos de salida adicionales: insignia SVG, CSV, SARIF 2.1.0 y página HTML autocontenida."""
import csv
import html
import io
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

from . import NOMBRE_PROGRAMA, URL_GITHUB, __version__
from .i18n import t
from .models import AuditReport
from .rules import REGLA_ERRORES
from .score import nota, ranking

COLORES = {"A": "#2da44e", "B": "#4c9f38", "C": "#dfb317", "D": "#fe7d37", "E": "#e05d44", "-": "#9f9f9f"}


def _hallazgos_por_repo(hallazgos: Dict[str, List[str]]) -> Dict[str, List[str]]:
    por_repo: Dict[str, List[str]] = {}
    for regla, repos in hallazgos.items():
        for nombre in repos:
            por_repo.setdefault(nombre, []).append(regla)
    return por_repo


# ------------------------------------------------------------------ badge
def a_badge(puntuacion: Optional[int], etiqueta: str = "health") -> str:
    """Insignia SVG estilo shields.io con la nota global."""
    valor = "n/a" if puntuacion is None else f"{puntuacion} {nota(puntuacion)}"
    color = COLORES[nota(puntuacion) or "-"]
    ancho_e, ancho_v = 6 * len(etiqueta) + 14, 7 * len(valor) + 14
    total = ancho_e + ancho_v
    et, va = html.escape(etiqueta), html.escape(valor)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{total}" height="20" role="img" aria-label="{et}: {va}">'
        f'<title>{et}: {va}</title>'
        f'<rect width="{ancho_e}" height="20" fill="#555"/>'
        f'<rect x="{ancho_e}" width="{ancho_v}" height="20" fill="{color}"/>'
        f'<g fill="#fff" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="11" text-anchor="middle">'
        f'<text x="{ancho_e / 2:g}" y="14">{et}</text>'
        f'<text x="{ancho_e + ancho_v / 2:g}" y="14">{va}</text></g></svg>\n'
    )


# -------------------------------------------------------------------- CSV
COLUMNAS_CSV = ("name", "score", "grade", "fork", "archived", "has_pages", "pages_status", "pages_url",
                "has_releases", "latest_release", "has_readme", "has_license", "has_gitignore", "has_description",
                "stars", "forks", "open_issues", "language", "license", "pushed_at", "findings")


def _celda_csv(valor) -> str:
    """Evita la inyección de fórmulas al abrir el CSV en Excel/Calc."""
    texto = "" if valor is None else ("true" if valor is True else "false" if valor is False else str(valor))
    return "'" + texto if texto[:1] in ("=", "+", "-", "@", "\t", "\r") else texto


def a_csv(report: AuditReport, hallazgos: Dict[str, List[str]], bom: bool = False) -> str:
    por_repo = _hallazgos_por_repo(hallazgos)
    salida = io.StringIO()
    escritor = csv.writer(salida, lineterminator="\n")
    escritor.writerow(COLUMNAS_CSV)
    for r in report.repos:
        s = r.pages_salud
        escritor.writerow([_celda_csv(v) for v in (
            r.nombre, r.puntuacion, nota(r.puntuacion), r.es_fork, r.esta_archivado, r.tiene_pages,
            s.estado if s else None, r.url_pages, r.tiene_releases, r.ultima_release, r.tiene_readme,
            r.tiene_licencia, r.tiene_gitignore, r.tiene_descripcion, r.estrellas, r.forks_count,
            r.issues_abiertas, r.lenguaje, r.licencia_spdx, r.ultimo_push, ";".join(por_repo.get(r.nombre, [])))])
    return ("﻿" if bom else "") + salida.getvalue()


# ------------------------------------------------------------------ SARIF
def a_sarif(report: AuditReport, hallazgos: Dict[str, List[str]], fail_on: Sequence[str]) -> str:
    """SARIF 2.1.0: un resultado por (regla, repo). Los repos se identifican por ubicación lógica."""
    reglas, resultados = [], []
    for regla, repos in hallazgos.items():
        if not repos:
            continue
        reglas.append({"id": regla, "shortDescription": {"text": t(f"rule.{regla}")},
                       "helpUri": f"{URL_GITHUB}github-pages-auditor#readme"})
        por_nombre = {r.nombre: r for r in report.repos}
        for nombre in repos:
            repo = por_nombre.get(nombre)
            texto = f"{nombre}: {t(f'rule.{regla}')}"
            if regla == REGLA_ERRORES and repo:
                texto += f" ({repo.error})"
            resultados.append({
                "ruleId": regla,
                "level": "error" if regla in fail_on else "warning",
                "message": {"text": texto},
                "locations": [{"logicalLocations": [{
                    "name": nombre, "kind": "module", "fullyQualifiedName": f"{report.usuario}/{nombre}"}]}],
                "properties": {"repository": f"{report.usuario}/{nombre}"},
            })
    return json.dumps({
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [{"tool": {"driver": {"name": NOMBRE_PROGRAMA, "version": __version__,
                                      "informationUri": URL_GITHUB + NOMBRE_PROGRAMA, "rules": reglas}},
                  "results": resultados}],
    }, indent=2, ensure_ascii=True) + "\n"


# ------------------------------------------------------------------- HTML
CSS = """
:root{--bg:#fff;--fg:#1f2328;--mut:#656d76;--bd:#d0d7de;--card:#f6f8fa;--ok:#2da44e;--warn:#bf8700;--bad:#cf222e}
@media (prefers-color-scheme:dark){:root{--bg:#0d1117;--fg:#e6edf3;--mut:#8d96a0;--bd:#30363d;--card:#161b22}}
*{box-sizing:border-box}body{margin:0;padding:24px 16px;background:var(--bg);color:var(--fg);
font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}main{max-width:1100px;margin:0 auto}
h1{font-size:22px;margin:0 0 4px}.sub{color:var(--mut);margin:0 0 20px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:20px}
.card{background:var(--card);border:1px solid var(--bd);border-radius:8px;padding:12px}
.card b{display:block;font-size:24px}.card span{color:var(--mut);font-size:13px}
input{width:100%;padding:8px 10px;border:1px solid var(--bd);border-radius:6px;background:var(--bg);color:var(--fg);margin-bottom:12px}
.wrap{overflow-x:auto}table{border-collapse:collapse;width:100%}
th,td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--bd);white-space:nowrap}
th{cursor:pointer;color:var(--mut);font-weight:600;user-select:none}td.n,th.n{text-align:right}
.g{display:inline-block;min-width:22px;text-align:center;border-radius:4px;color:#fff;font-weight:700;padding:0 6px}
.A{background:#2da44e}.B{background:#4c9f38}.C{background:#dfb317}.D{background:#fe7d37}.E{background:#e05d44}
.tag{display:inline-block;font-size:12px;border:1px solid var(--bd);border-radius:10px;padding:0 8px;margin:0 4px 2px 0;
white-space:normal}a{color:#0969da}footer{margin-top:24px;color:var(--mut);font-size:13px}
"""

JS = """
(function(){var t=document.getElementById('t'),b=t.tBodies[0],f=document.getElementById('f');
f.addEventListener('input',function(){var q=f.value.toLowerCase();
for(var i=0;i<b.rows.length;i++){b.rows[i].style.display=b.rows[i].textContent.toLowerCase().indexOf(q)<0?'none':'';}});
var h=t.tHead.rows[0].cells;for(let c=0;c<h.length;c++){h[c].addEventListener('click',function(){
var d=this.getAttribute('data-d')==='1'?-1:1;this.setAttribute('data-d',d===1?'1':'0');
var r=Array.prototype.slice.call(b.rows);r.sort(function(x,y){var a=x.cells[c].getAttribute('data-v'),z=y.cells[c].getAttribute('data-v');
var na=parseFloat(a),nz=parseFloat(z);if(!isNaN(na)&&!isNaN(nz))return(na-nz)*d;return a.localeCompare(z)*d;});
r.forEach(function(x){b.appendChild(x);});});}})();
"""


def _e(valor) -> str:
    return html.escape("" if valor is None else str(valor), quote=True)


def a_html(report: AuditReport, hallazgos: Dict[str, List[str]], lang: str = "es", historial: Optional[dict] = None) -> str:
    """Página única sin recursos externos ni peticiones de red; todo dato de GitHub se escapa."""
    por_repo = _hallazgos_por_repo(hallazgos)
    mejores, peores = ranking(report)
    tarjetas = [
        (f"{report.puntuacion if report.puntuacion is not None else '–'}", t("row_score")),
        (str(report.total_repos), t("row_total")),
        (str(len(report.con_pages)), t("row_pages")),
        (str(len(report.pages_rotas)), t("row_broken")),
        (str(sum(len(v) for k, v in hallazgos.items() if k != REGLA_ERRORES)), t("html_findings")),
    ]
    cabecera = [t("col_repo"), t("col_score"), t("html_status"), t("col_release"), t("html_stars"), t("col_lang"),
                t("col_push"), t("html_findings")]
    filas = []
    for r in report.repos:
        s = r.pages_salud
        letra = nota(r.puntuacion)
        etiquetas = "".join(f'<span class="tag">{_e(x)}</span>' for x in por_repo.get(r.nombre, []))
        enlace = f'<a href="https://github.com/{_e(report.usuario)}/{_e(r.nombre)}" rel="noopener">{_e(r.nombre)}</a>'
        pagina = (f'<a href="{_e(r.url_pages)}" rel="noopener">{_e(s.estado if s else "ok")}</a>'
                  if r.url_pages and r.url_pages.startswith(("http://", "https://")) else _e(s.estado if s else ""))
        filas.append(
            f'<tr><td data-v="{_e(r.nombre.lower())}">{enlace}</td>'
            f'<td class="n" data-v="{_e(r.puntuacion if r.puntuacion is not None else -1)}">'
            f'{f"""<span class="g {letra}">{_e(r.puntuacion)}</span>""" if letra else ""}</td>'
            f'<td data-v="{_e(s.estado if s else "")}">{pagina}</td>'
            f'<td data-v="{_e(r.ultima_release or "")}">{_e(r.ultima_release)}</td>'
            f'<td class="n" data-v="{_e(r.estrellas if r.estrellas is not None else -1)}">{_e(r.estrellas)}</td>'
            f'<td data-v="{_e(r.lenguaje or "")}">{_e(r.lenguaje)}</td>'
            f'<td data-v="{_e((r.ultimo_push or "")[:10])}">{_e((r.ultimo_push or "")[:10])}</td>'
            f'<td data-v="{len(por_repo.get(r.nombre, []))}">{etiquetas}</td></tr>')
    extra = ""
    if mejores or peores:
        extra = ("<p>" + _e(t("best")) + ": " + ", ".join(f"{_e(r.nombre)} ({r.puntuacion})" for r in mejores)
                 + "<br>" + _e(t("worst")) + ": " + ", ".join(f"{_e(r.nombre)} ({r.puntuacion})" for r in peores) + "</p>")
    if historial and historial.get("delta") is not None:
        extra += f"<p>{_e(t('history', file=historial['previous_file'], delta=historial['delta']))}</p>"
    return (
        f'<!doctype html><html lang="{_e(lang)}"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{_e(t('html_title'))} · {_e(report.usuario)}</title><style>{CSS}</style></head><body><main>"
        f"<h1>{_e(t('html_title'))} · {_e(report.usuario)}</h1>"
        f'<p class="sub">{_e(report.proveedor)} · {_e(report.dominio_base)}</p>'
        '<div class="cards">' + "".join(f'<div class="card"><b>{_e(v)}</b><span>{_e(k)}</span></div>' for v, k in tarjetas)
        + f"</div>{extra}"
        f'<input id="f" type="search" placeholder="{_e(t("html_filter"))}" aria-label="{_e(t("html_filter"))}">'
        '<div class="wrap"><table id="t"><thead><tr>'
        + "".join(f'<th class="{"n" if i in (1, 4) else ""}">{_e(c)}</th>' for i, c in enumerate(cabecera))
        + "</tr></thead><tbody>" + "".join(filas) + "</tbody></table></div>"
        f'<footer>{_e(t("generated", version=__version__))} · <a href="{_e(URL_GITHUB)}" rel="noopener">{_e(URL_GITHUB)}</a>'
        f"</footer></main><script>{JS}</script></body></html>\n")


# ------------------------------------------------------------------ trend
def _fecha_de(nombre: str, datos: Dict[str, Any]) -> str:
    return str(datos.get("generated_at") or nombre)[:10]


def a_trend(report: AuditReport, previos: Sequence[Tuple[str, Dict[str, Any]]], lang: str = "es",
            ahora: Optional[datetime] = None) -> str:
    """Página HTML (SVG en línea, sin recursos externos) con la evolución de la nota global.

    ``previos`` son los informes guardados con ``--history`` (de más antiguo a más reciente); el actual va al final.
    """
    ahora = ahora or datetime.now(timezone.utc)
    puntos: List[Tuple[str, Optional[int]]] = [(_fecha_de(n, d), (d.get("summary") or {}).get("score")) for n, d in previos]
    puntos.append((ahora.strftime("%Y-%m-%d"), report.puntuacion))
    validos = [(f, p) for f, p in puntos if isinstance(p, int)]
    ancho, alto, margen = 720, 260, 36
    if len(validos) >= 2:
        pasos = len(validos) - 1
        coords = [(margen + i * (ancho - 2 * margen) / pasos, alto - margen - p / 100 * (alto - 2 * margen))
                  for i, (_, p) in enumerate(validos)]
        linea = " ".join(f"{x:.1f},{y:.1f}" for x, y in coords)
        marcas = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="#0969da"><title>{_e(f)}: {p}</title></circle>'
                         for (x, y), (f, p) in zip(coords, validos))
        guias = "".join(f'<line x1="{margen}" x2="{ancho - margen}" y1="{alto - margen - v / 100 * (alto - 2 * margen):.1f}" '
                        f'y2="{alto - margen - v / 100 * (alto - 2 * margen):.1f}" stroke="currentColor" opacity=".15"/>'
                        f'<text x="4" y="{alto - margen - v / 100 * (alto - 2 * margen) + 4:.1f}" font-size="11" '
                        f'fill="currentColor" opacity=".6">{v}</text>' for v in (0, 25, 50, 75, 100))
        grafica = (f'<svg viewBox="0 0 {ancho} {alto}" role="img" aria-label="{_e(t("trend.title"))}" width="100%">{guias}'
                   f'<polyline fill="none" stroke="#0969da" stroke-width="2" points="{linea}"/>{marcas}</svg>')
    else:
        grafica = f"<p>{_e(t('trend.empty'))}</p>"
    filas = "".join(f"<tr><td>{_e(f)}</td><td class=\"n\">{_e('–' if p is None else p)}</td></tr>"
                    for f, p in reversed(puntos[-30:]))
    cambios = ""
    if previos:
        primero, ultimo = previos[0][1], report.repos
        antes = {str(r.get("name")): r.get("score") for r in primero.get("repos", []) if isinstance(r, dict)}
        dif = []
        for r in ultimo:
            previo = antes.get(r.nombre)
            if r.puntuacion is not None and isinstance(previo, int):
                dif.append((r.puntuacion - previo, r.nombre))
        dif.sort(key=lambda x: (-x[0], x[1].lower()))
        sube = [f"{_e(n)} (+{d})" for d, n in dif if d > 0][:5]
        baja = [f"{_e(n)} ({d})" for d, n in reversed(dif) if d < 0][:5]
        if sube or baja:
            cambios = (f"<p>{_e(t('trend.since', date=_fecha_de(previos[0][0], primero)))}<br>"
                       + (f"▲ {', '.join(sube)}<br>" if sube else "") + (f"▼ {', '.join(baja)}" if baja else "") + "</p>")
    return (
        f'<!doctype html><html lang="{_e(lang)}"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{_e(t('trend.title'))} · {_e(report.usuario)}</title><style>{CSS}</style></head><body><main>"
        f"<h1>{_e(t('trend.title'))} · {_e(report.usuario)}</h1>"
        f'<p class="sub">{_e(t("trend.current", score=report.puntuacion if report.puntuacion is not None else "–"))}</p>'
        f'<div class="card">{grafica}</div>{cambios}'
        f'<div class="wrap"><table><thead><tr><th>{_e(t("trend.date"))}</th><th class="n">{_e(t("trend.score"))}</th></tr></thead>'
        f"<tbody>{filas}</tbody></table></div>"
        f'<footer>{_e(t("generated", version=__version__))} · <a href="{_e(URL_GITHUB)}" rel="noopener">{_e(URL_GITHUB)}</a>'
        "</footer></main></body></html>\n")


# ------------------------------------------------------------------ issue
def a_issue(report: AuditReport, hallazgos: Dict[str, List[str]], historial: Optional[dict] = None) -> str:
    """Resumen en Markdown pensado para el cuerpo de una issue (lo usa la Action con ``issue: true``)."""
    letra = nota(report.puntuacion) or "–"
    lineas = [f"## {t('issue.title', user=report.usuario, score=report.puntuacion if report.puntuacion is not None else '–', grade=letra)}", ""]
    if historial and historial.get("delta") is not None:
        lineas += [f"{t('history', file=historial['previous_file'], delta=historial['delta'])}", ""]
    activos = {r: v for r, v in hallazgos.items() if v}
    if not activos:
        lineas.append(t("issue.none"))
    else:
        lineas += [f"### {t('issue.findings')}", "", f"| {t('issue.rule')} | {t('issue.repos')} |", "| --- | --- |"]
        for regla, repos in sorted(activos.items()):
            nombres = ", ".join(f"`{n}`" for n in repos[:15]) + (f" … (+{len(repos) - 15})" if len(repos) > 15 else "")
            lineas.append(f"| **{regla}**: {t(f'rule.{regla}').replace('|', ' ')} | {nombres} |")
    mejores, peores = ranking(report)
    if mejores or peores:
        lineas += ["", f"**{t('best')}:** " + ", ".join(f"{r.nombre} ({r.puntuacion})" for r in mejores),
                   f"**{t('worst')}:** " + ", ".join(f"{r.nombre} ({r.puntuacion})" for r in peores)]
    lineas += ["", f"<sub>{t('md_generated')} [{NOMBRE_PROGRAMA}]({URL_GITHUB}) v{__version__}</sub>"]
    return "\n".join(lineas) + "\n"
