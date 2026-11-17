"""``--doctor``: qué puede hacer tu token. Diagnostica sin escribir nada en GitHub."""
from datetime import datetime, timezone
from typing import Dict, List, Optional

import requests

from .i18n import t
from .secretos import enmascarar, tipo_token

API = "https://api.github.com"
OK, AVISO, FALLO, DESCONOCIDO = "ok", "warn", "fail", "unknown"


def _fila(clave: str, estado: str, detalle: str = "") -> Dict[str, str]:
    return {"check": clave, "status": estado, "detail": detalle}


class Doctor:
    def __init__(self, session, token: Optional[str], usuario: str = "", org: bool = False, privados: bool = False):
        self.session = session
        self.usuario, self.org, self.privados = usuario, org, privados
        self.token = token
        self.cabeceras = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
        if token:
            self.cabeceras["Authorization"] = f"Bearer {token}"

    def _get(self, ruta: str, **kw):
        return self.session.get(f"{API}{ruta}", headers=self.cabeceras, **kw)

    def ejecutar(self) -> List[Dict[str, str]]:
        filas: List[Dict[str, str]] = []
        tipo = tipo_token(self.token)
        if not self.token:
            filas.append(_fila("token", FALLO, t("doctor.no_token")))
            return filas
        filas.append(_fila("token", OK, f"{enmascarar(self.token)} ({t('doctor.type.' + tipo)})"))
        try:
            res = self._get("/user")
        except requests.RequestException as e:
            filas.append(_fila("api", FALLO, type(e).__name__))
            return filas
        if res.status_code == 401:
            filas.append(_fila("api", FALLO, t("doctor.invalid")))
            return filas
        if res.status_code != 200:
            filas.append(_fila("api", FALLO, f"HTTP {res.status_code}"))
            return filas
        datos = res.json() if isinstance(res.json(), dict) else {}
        login = str(datos.get("login") or "")
        filas.append(_fila("api", OK, t("doctor.logged", login=login)))
        filas += self._caducidad(res)
        filas += self._alcance(res, tipo)
        filas += self._limite()
        if self.usuario and login and login.lower() != self.usuario.lower():
            filas.append(_fila("owner", AVISO if self.privados else OK, t("doctor.other_user", login=login, user=self.usuario)))
        repo = self._repo_de_muestra(login)
        if repo is None:
            filas.append(_fila("sample", DESCONOCIDO, t("doctor.no_repo")))
            return filas
        filas.append(_fila("sample", OK, repo))
        filas += self._permisos(repo)
        return filas

    def _caducidad(self, res) -> List[Dict[str, str]]:
        texto = (getattr(res, "headers", {}) or {}).get("github-authentication-token-expiration")
        if not texto:
            return [_fila("expiry", OK, t("doctor.no_expiry"))]
        try:
            fecha = datetime.strptime(texto.replace(" UTC", ""), "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            dias = (fecha - datetime.now(timezone.utc)).days
        except ValueError:
            return [_fila("expiry", DESCONOCIDO, texto)]
        return [_fila("expiry", AVISO if dias < 7 else OK, t("doctor.expires", date=texto[:10], days=dias))]

    def _alcance(self, res, tipo: str) -> List[Dict[str, str]]:
        alcances = (getattr(res, "headers", {}) or {}).get("X-OAuth-Scopes")
        if tipo == "classic" and alcances is not None:
            lista = [a.strip() for a in alcances.split(",") if a.strip()]
            escribe = "repo" in lista or "public_repo" in lista
            return [_fila("write", OK if escribe else AVISO, t("doctor.scopes", scopes=", ".join(lista) or "-"))]
        return [_fila("write", DESCONOCIDO, t("doctor.write_unknown"))]

    def _limite(self) -> List[Dict[str, str]]:
        try:
            res = self._get("/rate_limit")
            core = ((res.json() or {}).get("resources") or {}).get("core") or {}
            if res.status_code == 200 and "remaining" in core:
                restante, total = core["remaining"], core.get("limit")
                return [_fila("rate", AVISO if restante < 100 else OK, t("doctor.rate", left=restante, total=total))]
        except (requests.RequestException, ValueError, AttributeError):
            pass
        return [_fila("rate", DESCONOCIDO, "")]

    def _repo_de_muestra(self, login: str) -> Optional[str]:
        if self.org:
            ruta = f"/orgs/{self.usuario}/repos"
        elif self.privados or not self.usuario:
            ruta = "/user/repos"
        else:
            ruta = f"/users/{self.usuario}/repos"
        try:
            res = self._get(ruta, params={"per_page": 30})
            datos = res.json() if res.status_code == 200 else []
        except (requests.RequestException, ValueError):
            return None
        repos = [r for r in datos if isinstance(r, dict) and not r.get("fork") and not r.get("archived")]
        repos.sort(key=lambda r: not r.get("has_pages"))  # mejor uno con Pages: permite probar ese permiso
        if not repos:
            return None
        dueno = (repos[0].get("owner") or {}).get("login") or self.usuario or login
        return f"{dueno}/{repos[0].get('name')}"

    def _permisos(self, repo: str) -> List[Dict[str, str]]:
        base = f"/repos/{repo}"
        filas: List[Dict[str, str]] = []

        def sondear(clave: str, ruta: str, validos, explicacion: str, grave: bool = False, **kw) -> None:
            try:
                res = self._get(ruta, **kw)
            except requests.RequestException as e:
                filas.append(_fila(clave, DESCONOCIDO, type(e).__name__))
                return
            if res.status_code in validos:
                filas.append(_fila(clave, OK, t("doctor.can")))
            elif res.status_code in (401, 403, 404):  # falta un permiso: solo es grave si sin él no se puede auditar
                filas.append(_fila(clave, FALLO if grave else AVISO, f"HTTP {res.status_code}: {explicacion}"))
            else:
                filas.append(_fila(clave, DESCONOCIDO, f"HTTP {res.status_code}"))

        sondear("contents", f"{base}/contents/", (200, 404), t("doctor.need.contents"), grave=True)
        sondear("pages", f"{base}/pages", (200, 404), t("doctor.need.pages"))
        sondear("actions", f"{base}/actions/runs", (200,), t("doctor.need.actions"), params={"per_page": 1})
        sondear("alerts", f"{base}/vulnerability-alerts", (204, 404), t("doctor.need.alerts"))
        # Rama protegida: 404 "Branch not protected" también es una respuesta válida (hay permiso).
        try:
            repo_json = self._get(base).json()
            rama = repo_json.get("default_branch") if isinstance(repo_json, dict) else None
            if rama:
                res = self._get(f"{base}/branches/{rama}/protection")
                mensaje = str(res.json().get("message", "")) if res.status_code == 404 else ""
                ok = res.status_code == 200 or (res.status_code == 404 and mensaje == "Branch not protected")
                filas.append(_fila("protection", OK if ok else AVISO,
                                   t("doctor.can") if ok else f"HTTP {res.status_code}: {t('doctor.need.admin')}"))
        except (requests.RequestException, ValueError, AttributeError):
            filas.append(_fila("protection", DESCONOCIDO, ""))
        return filas


def hay_fallos(filas: List[Dict[str, str]]) -> bool:
    return any(f["status"] == FALLO for f in filas)
