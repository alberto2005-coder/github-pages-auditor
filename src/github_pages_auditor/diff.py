"""``--diff ANTES.json DESPUES.json``: qué ha cambiado entre dos informes (nota, repos y hallazgos)."""
from typing import Any, Dict, List

from rich.console import Console

from . import history
from .i18n import t


def comparar_informes(antes: Dict[str, Any], despues: Dict[str, Any], ruta_antes: str, ruta_despues: str) -> Dict[str, Any]:
    datos = history.comparar(despues, antes, ruta_antes)
    hallazgos_a = {k: set(v) for k, v in (antes.get("findings") or {}).items() if isinstance(v, list)}
    hallazgos_d = {k: set(v) for k, v in (despues.get("findings") or {}).items() if isinstance(v, list)}
    nuevos, resueltos = {}, {}
    for regla in sorted(set(hallazgos_a) | set(hallazgos_d)):
        alta = sorted(hallazgos_d.get(regla, set()) - hallazgos_a.get(regla, set()), key=str.lower)
        baja = sorted(hallazgos_a.get(regla, set()) - hallazgos_d.get(regla, set()), key=str.lower)
        if alta:
            nuevos[regla] = alta
        if baja:
            resueltos[regla] = baja
    import os
    return {**datos, "file_before": os.path.basename(ruta_antes), "file_after": os.path.basename(ruta_despues),
            "new_findings": nuevos, "resolved_findings": resueltos}


def _cambios(items: List[dict]) -> str:
    return ", ".join(f"{x['name']} ({x['before']}→{x['after']})" for x in items)


def mostrar(datos: Dict[str, Any], console: Console) -> None:
    console.print(f"[bold]{t('diff.title', before=datos['file_before'], after=datos['file_after'])}[/bold]",
                  highlight=False)
    if datos.get("delta") is not None:
        console.print(t("diff.score", before=datos["score_before"], after=datos["score_after"], delta=datos["delta"]),
                      highlight=False)
    secciones = [
        ("diff.improved", _cambios(datos["improved"])), ("diff.worsened", _cambios(datos["worsened"])),
        ("diff.new_repos", ", ".join(datos["new_repos"])), ("diff.removed_repos", ", ".join(datos["removed_repos"])),
    ]
    for clave, texto in secciones:
        if texto:
            console.print(f"{t(clave)}: {texto}", highlight=False, markup=False)
    for clave, bloque in (("diff.new_findings", datos["new_findings"]), ("diff.resolved_findings", datos["resolved_findings"])):
        if bloque:
            console.print(f"[bold]{t(clave)}[/bold]", highlight=False)
            for regla, repos in bloque.items():
                console.print(f"  {regla}: {', '.join(repos)}", highlight=False, markup=False)
    if not any(datos[k] for k in ("improved", "worsened", "new_repos", "removed_repos", "new_findings", "resolved_findings")) \
            and not datos.get("delta"):
        console.print(t("diff.none"))
