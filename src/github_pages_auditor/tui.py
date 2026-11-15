"""``--tui``: explorador interactivo de resultados (extra opcional: ``pip install 'github-pages-auditor[tui]'``)."""
from typing import Dict, List, Tuple

from .errors import ErrorSalida
from .models import AuditReport
from .score import nota

COLUMNAS = ("Repo", "Nota", "Pages", "Release", "★", "Lenguaje", "Hallazgos")


def filas(report: AuditReport, hallazgos: Dict[str, List[str]]) -> List[Tuple]:
    """Filas de la tabla (puro y testeable sin Textual)."""
    por_repo: Dict[str, List[str]] = {}
    for regla, repos in hallazgos.items():
        for nombre in repos:
            por_repo.setdefault(nombre, []).append(regla)
    resultado = []
    for r in report.repos:
        s = r.pages_salud
        resultado.append((
            r.nombre,
            "" if r.puntuacion is None else f"{r.puntuacion} {nota(r.puntuacion)}",
            s.estado if s else "",
            r.ultima_release or "",
            "" if r.estrellas is None else str(r.estrellas),
            r.lenguaje or "",
            ", ".join(por_repo.get(r.nombre, [])),
        ))
    return resultado


def lanzar(report: AuditReport, hallazgos: Dict[str, List[str]]) -> None:
    try:
        from textual.app import App, ComposeResult
        from textual.widgets import DataTable, Footer, Header, Input
    except ModuleNotFoundError as e:
        raise ErrorSalida("--tui necesita el extra opcional: pip install 'github-pages-auditor[tui]'") from e

    datos = filas(report, hallazgos)

    class Explorador(App):
        TITLE = f"github-pages-auditor · {report.usuario}"
        BINDINGS = [("q", "quit", "Salir")]

        def compose(self) -> ComposeResult:
            yield Header()
            yield Input(placeholder="Filtrar…", id="filtro")
            yield DataTable(id="tabla", cursor_type="row")
            yield Footer()

        def on_mount(self) -> None:
            self._rellenar("")

        def _rellenar(self, texto: str) -> None:
            tabla = self.query_one(DataTable)
            tabla.clear(columns=True)
            tabla.add_columns(*COLUMNAS)
            for fila in datos:
                if texto.lower() in " ".join(fila).lower():
                    tabla.add_row(*fila)

        def on_input_changed(self, evento) -> None:
            self._rellenar(evento.value)

    Explorador().run()
