# GitHub Profile & Pages Auditor

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![PyPI](https://img.shields.io/pypi/v/github-pages-auditor?label=PyPI)](https://pypi.org/project/github-pages-auditor/)
[![CI](https://github.com/alberto2005-coder/github-pages-auditor/actions/workflows/test.yml/badge.svg)](https://github.com/alberto2005-coder/github-pages-auditor/actions/workflows/test.yml)
[![MIT](https://img.shields.io/badge/Licencia-MIT-green)](https://github.com/alberto2005-coder/github-pages-auditor/blob/master/LICENSE)

[Español](#español) · [English](#english)

> Desarrollado por **[Alberto Ortiz](https://github.com/alberto2005-coder/)** · [albertoortiz.is-a.dev](https://albertoortiz.is-a.dev/)

**ES:** `github-pages-auditor` es una herramienta de línea de comandos (paquete de Python) que **audita todos los repositorios de un usuario u organización de GitHub**: comprueba si sus **GitHub Pages** funcionan (web rota, HTTPS, certificado TLS, DNS, enlaces rotos), da una **nota de 0 a 100** a cada repo y detecta lo que falta (`LICENSE`, `README`, `SECURITY.md`, CI, Dependabot...). Funciona con o sin token, genera JSON, HTML, CSV y SARIF, devuelve códigos de salida para CI y puede **crear los archivos que faltan mediante Pull Requests**.

**EN:** `github-pages-auditor` is a Python command-line tool that **audits every repository of a GitHub user or organization**: it checks that their **GitHub Pages** sites work (broken site, HTTPS, TLS certificate, DNS, broken links), gives each repo a **0-100 health score** and finds what is missing (`LICENSE`, `README`, `SECURITY.md`, CI, Dependabot...). It works with or without a token, outputs JSON, HTML, CSV and SARIF, returns CI exit codes and can **create the missing files through Pull Requests**.

```bash
uvx github-pages-auditor -u YOUR_USERNAME        # no install; or: pip install github-pages-auditor
```

---

## Español

### Índice

- [Descripción](#descripción)
- [Características](#características)
- [Modos de funcionamiento: con y sin API](#modos-de-funcionamiento-con-y-sin-api)
- [Requisitos previos](#requisitos-previos)
- [Instalación](#instalación)
- [Uso por línea de comandos](#uso-por-línea-de-comandos)
- [Jerarquía de configuración](#jerarquía-de-configuración)
- [Códigos de salida](#códigos-de-salida)
- [Formatos de salida e integración en CI](#formatos-de-salida-e-integración-en-ci)
- [Pruebas automatizadas](#pruebas-automatizadas)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Seguridad](#seguridad)
- [Autor](#autor)
- [Licencia](#licencia)

### Descripción

Herramienta de línea de comandos en Python para auditar los repositorios públicos de un usuario de GitHub: mapea los enlaces de **GitHub Pages** (incluido un dominio personalizado), detecta **releases** y evalúa la calidad del repositorio (README, licencia, `.gitignore` y descripción).

Se controla **solo con parámetros de consola**: no necesita archivo `.env`. El **token de la API es opcional**: con token usa la API oficial de GitHub; sin token usa un modo web público de «mejor esfuerzo».

### Características

- **Mapeo de GitHub Pages:** raíz (`<usuario>.github.io`) o subruta por repositorio, verificando que la URL responde de verdad.
- **Releases:** detectadas mediante el feed Atom público, sin consumir cuota de la API.
- **Auditoría de calidad:** sin README, sin licencia, sin `.gitignore` y sin descripción (About).
- **Clasificación:** forks y repositorios archivados.
- **Rendimiento:** todo el análisis se hace en paralelo (`ThreadPoolExecutor`) con reintentos y timeout.
- **Informe determinista:** los repositorios salen siempre en el mismo orden; un fallo de red en un repo no tumba el resto (se lista aparte).
- **Créditos del autor** en `--help`, `--version`, la consola y el informe.

### Modos de funcionamiento: con y sin API

| | Con token (`-k` / `GITHUB_TOKEN`) | Sin token |
| :--- | :--- | :--- |
| Fuente de datos | API REST oficial (5.000 peticiones/hora) | Páginas públicas de GitHub (HTML, `raw`, Atom) |
| Fiabilidad | **Alta** | De mejor esfuerzo: depende del marcado público de GitHub |
| Límite | 5.000/h | Puede recibir `429` si se abusa |
| Se activa | Automáticamente si hay token | Si no hay token, o con `--no-api` |

El token **solo se envía a `api.github.com`**.

**URL de las Pages:** con API se usa la URL real que GitHub tiene configurada (incluido tu dominio personalizado). Sin API, si no indicas `-w`, se prueba `https://<usuario>.github.io/...` y, si GitHub redirige a tu dominio personalizado, se detecta y se muestra ese dominio. Con `-w` se comprueba directamente ese dominio.

### Requisitos previos

- **Python** 3.10 o superior.
- **Gestor de paquetes:** [`uv`](https://docs.astral.sh/uv/) (recomendado) o `pip`.

### Instalación

- **Sin instalar nada (recomendado), con [`uv`](https://docs.astral.sh/uv/):**

  ```bash
  uvx github-pages-auditor -u tu_usuario
  ```

- **Instalarlo globalmente como comando:**

  ```bash
  uv tool install github-pages-auditor
  # o mediante pip:
  pip install github-pages-auditor
  ```

El comando antiguo `ver-github-pages` sigue funcionando como alias de compatibilidad.

Para desarrollar desde el código fuente:

```bash
git clone https://github.com/alberto2005-coder/github-pages-auditor.git
cd github-pages-auditor
```

- **Con `uv` (recomendado):**

  ```bash
  uv sync
  ```

- **Con `pip`:**

  ```bash
  pip install -e .
  ```

### Uso por línea de comandos

```text
github-pages-auditor -u USUARIO [-w DOMINIO] [-k TOKEN] [-o ARCHIVO] [opciones]
```

**Ejemplos** *(si ejecutas desde el repositorio sin instalar globalmente, antepón `uv run`)*

```bash
# 1. Básico, sin token ni .env (modo web)
github-pages-auditor -u alberto2005-coder

# 2. Con dominio personalizado y token por variable de entorno (modo API; recomendado)
export GITHUB_TOKEN=github_pat_xxx        # PowerShell: $env:GITHUB_TOKEN = "github_pat_xxx"
github-pages-auditor -u alberto2005-coder -w https://albertoortiz.is-a.dev

# 3. Forzar modo web aunque haya token en el entorno y cambiar el archivo de salida
github-pages-auditor -u alberto2005-coder --no-api -o mi_reporte.txt

# 4. Token como parámetro (funciona, pero queda en el historial del shell)
github-pages-auditor -u alberto2005-coder -k github_pat_xxx

# 5. También funciona como módulo de Python (útil si Scripts no está en el PATH)
python -m github_pages_auditor -u alberto2005-coder
```

Un token *fine-grained* sin permisos (solo repositorios públicos) es suficiente.

**Opciones**

| Parámetro | Alternativas | Descripción | Obligatorio |
| :--- | :--- | :--- | :--- |
| `-u` | `--usuario`, `--user` | Usuario de GitHub | **Sí** (o `USUARIO_GITHUB`) |
| `-w` | `--web`, `--dominio` | Dominio base de las Pages | No (def. `https://<usuario>.github.io`) |
| `-k` | `--key`, `--token` | Personal Access Token (activa la API) | No |
| `-o` | `--output` | Archivo del informe; `-` = salida estándar | No (def. `paginas_github.<formato>`) |
| `-f` | `--format` | `txt`, `json`, `md`, `github` (anotaciones de Actions), `html`, `csv`, `sarif`, `badge`, `trend` (gráfica de evolución; necesita `--history`) o `issue` (resumen para una issue) | No (def. `txt`) |
| `--fail-on` | | Reglas (o grupos `any`, `community`, `all`) que provocan código de salida 1 | No |
| `--exclude-forks` | | Ignora los forks | No |
| `--exclude-archived` | | Ignora los repositorios archivados | No |
| `--inject` | | Actualiza la tabla de demos dentro de un archivo (README) | No |
| `--ignore` | | Excluye repos por nombre o patrón (`a,b*`) | No |
| `--only` | | Audita solo estos repos (nombres o patrones) | No |
| `--details` | | Estrellas, lenguaje, licencia, último push y release | No |
| `--sort` | | `listing` (def.), `name`, `stars`, `updated` | No |
| `--stale-months` | | Meses sin push para `stale-repo` | No (def. `12`) |
| `--baseline` | | Informe JSON previo: `--fail-on` solo por hallazgos nuevos | No |
| `--config` | | Archivo TOML de configuración | No (def. `.github-pages-auditor.toml`) |
| `--no-config` | | No leer el archivo de configuración | No |
| `--min-score` | | Falla (código 1) si la nota global (0-100) es menor | No |
| `--history` | | Carpeta donde guardar cada informe y comparar con el anterior | No |
| `--lang` | | `es` (def.) o `en` | No |
| `--notify-webhook` | | Avisa a un webhook (Discord, Slack, JSON) si hay hallazgos nuevos (mejor por `NOTIFY_WEBHOOK`) | No |
| `--deep` | | Con token: seguridad, CI, contribuidores y PRs | No |
| `--org` | | Audita una organización en lugar de un usuario | No |
| `--include-private` | | Con token: incluye tus repos privados | No |
| `--readme-quality` | | Revisa el README (instalación, uso, longitud): regla `weak-readme` | No |
| `--dep-licenses` | | Busca dependencias GPL/AGPL: regla `copyleft-dependency` | No |
| `-u a,b` | | Varias cuentas separadas por comas en un solo informe (repos como `cuenta/repo`; sin `--org` ni `--fix*`) | No |
| `--graphql` | | (Experimental) Lista la raíz de los repos con GraphQL en lotes: menos peticiones; si falla, usa REST | No |
| `--init` | | Crea un `.github-pages-auditor.toml` de partida (con `--yes` lo sobrescribe) | No |
| `--fix-only` | | Con `--fix`: solo las reglas indicadas (p. ej. `missing-license,missing-security-policy`) | No |
| `--fix-log` | | Con `--fix*`: guarda en un JSON lo planeado o aplicado | No |
| `--crawl` | | Rastrea hasta 10 páginas internas de cada web y valida su `sitemap.xml` | No |
| `--check-links` | | Comprueba los enlaces de la portada de cada web | No |
| `--fix` | | Crea los archivos de comunidad que falten (plantea; `--yes` aplica) | No |
| `--fix-pages` | | Activa Enforce HTTPS donde falte | No |
| `--fix-metadata` | | Propone descripción y topics | No |
| `--dry-run` | | Con `--fix*`, no escribe nada | No |
| `--yes` | | Con `--fix*`, aplica los cambios | No |
| `--tui` | | Explorador interactivo (extra `[tui]`) | No |
| `--cache` | | Caché ETag de la API en esta carpeta | No |
| `--cache-clear` | | Borra la caché ETag y sale | No |
| `--notify-on` | | Con `--notify-webhook`: `new` (por defecto) o `always` (también si no hay nada nuevo) | No |
| `--notify-test` | | Envía un mensaje de prueba al webhook y sale | No |
| `--since` | | Solo repos con push reciente: `30d`, `12w`, `6m`, `1y` o fecha | No |
| `--doctor` | | Diagnostica el token: tipo, caducidad, límite y permisos (no audita) | No |
| `--diff` | | Compara dos informes JSON: `--diff ANTES.json DESPUES.json` (no audita) | No |
| `--fix-extra` | | Implica `--fix`: crea además `LICENSE`, `.gitignore`, `dependabot.yml` y un CI básico según el lenguaje | No |
| `--fix-mode` | | `direct` (def., commit en la rama principal) o `pr` (rama y Pull Request por repo) | No |
| `--license` | | Licencia que crea `--fix-extra`: `mit` (def.), `bsd-3-clause`, `isc`, `unlicense` | No |
| `--scorecard` | | Añade la nota de OpenSSF Scorecard (0-10) y la regla `low-scorecard` | No |
| `-q` | `--quiet` | Sin tablas ni progreso | No |
| `--workers` | | Hilos en paralelo | No (def. `15`) |
| `--timeout` | | Timeout por petición, en segundos | No (def. `10`) |
| `--no-api` | | Fuerza el modo web aunque haya token | No |
| `--no-color` | | Consola sin colores | No |
| `--no-defaults-repo` | | No contar como presentes los ficheros heredados de tu repositorio `.github` | No |
| `--no-env` | | No leer el archivo `.env` | No |
| `-V` | `--version` | Versión y créditos | No |
| `-h` | `--help` | Ayuda y créditos | No |

### Jerarquía de configuración

1. **Parámetros de consola** (`-u`, `-w`, `-k`, `-o`…).
2. **Variables de entorno**, incluidas las de un archivo `.env` **opcional** en el directorio actual: `USUARIO_GITHUB`, `DOMINIO_WEB`, `GITHUB_TOKEN`, `ARCHIVO_SALIDA`. Un valor vacío se trata como no definido.
3. **Archivo `.github-pages-auditor.toml`** (opcional, en el directorio actual): claves `user`, `web`, `output`, `format`, `fail_on`, `exclude_forks`, `exclude_archived`, `ignore`, `only`, `stale_months`, `workers`, `timeout`, `details`, `sort`, `no_api`, `quiet`, `no_color`, `baseline`. **No admite el token** (es un error ponerlo ahí). `--no-config` lo ignora.
4. **Valores por defecto.**

Hay una plantilla en [`.env.example`](https://github.com/alberto2005-coder/github-pages-auditor/blob/master/.env.example).

### Códigos de salida

| Código | Significado |
| :---: | :--- |
| `0` | Auditoría correcta e informe escrito |
| `1` | Una regla de `--fail-on` encontró hallazgos (el informe sí se escribe) |
| `2` | Error: parámetros inválidos, usuario inexistente, token rechazado, límite de tasa, red o escritura |
| `3` | No hay repositorios que analizar (no se escribe informe) |
| `130` | Cancelado con Ctrl+C |

### Formatos de salida e integración en CI

`-f/--format` elige el formato del informe: `txt` (por defecto), `json` o `md`. Con `-o -` el informe va a la salida estándar y la interfaz a stderr, así que se puede encadenar con otras herramientas:

```bash
uvx github-pages-auditor -u alberto2005-coder -f json -o - -q | jq '.summary'
```

**JSON** (`schema_version: 1`): `tool`, `generated_at`, `user`, `mode` (`api`/`web`), `domain`, `summary` (contadores), `findings` (una lista por regla, vacía si no hay hallazgos), `fail_on` (reglas pedidas y disparadas) y `repos` (un objeto por repositorio, con `pages.status`, `pages.problems`, `pages.warnings`, `pages.title`, etc.).

**Markdown** (`-f md`): tabla de tus demos en vivo, ordenada y sin forks, entre los marcadores `<!-- github-pages-auditor:start -->` y `<!-- github-pages-auditor:end -->`. Con `--inject README.md` se actualiza **dentro de ese archivo**, entre esos marcadores (si no existen, falla sin tocar nada).

**Novedades de la 1.4.0.** Cada repo recibe una **nota de 0 a 100** (`A`-`E`) y el informe una nota global; `--min-score 70` hace fallar el CI si baja de ahí y `--history carpeta` compara con la ejecución anterior. `--deep` añade seguridad, CI y actividad. `--fix` crea SECURITY, CONTRIBUTING, CODE_OF_CONDUCT y la plantilla de issues que falten, `--fix-pages` activa Enforce HTTPS y `--fix-metadata` propone descripción y topics: **por defecto solo muestra el plan; `--yes` lo aplica** (con un token con permiso de escritura, nunca en forks ni archivados). Más recetas en [docs/ci.md](https://github.com/alberto2005-coder/github-pages-auditor/blob/master/docs/ci.md). Instalación alternativa: `pipx install github-pages-auditor` (TUI: `pipx install "github-pages-auditor[tui]"`).

**Novedades de la 1.5.0.**
- **`--doctor`** diagnostica tu token (tipo, caducidad, límite de peticiones y permisos) para saber qué podrá hacer: `uvx github-pages-auditor --doctor`.
- **Seguridad de los secretos:** el token y los webhooks se ocultan (`***`) en cualquier mensaje, y se avisa si lo pasas por la línea de comandos o si `.env` está dentro del repositorio git.
- **Pages en construcción:** justo después de un commit, GitHub reconstruye las Pages; ahora eso se muestra como `construyendo` y no como web rota.
- **Más fiable con la API:** si se agota el límite y se restablece en menos de un minuto, espera y reintenta; y `--cache auto` usa la carpeta de caché de tu usuario.
- **`--fix-mode pr`** abre una Pull Request por repo en lugar de escribir en la rama principal; **`--fix-extra`** crea además `LICENSE` (`--license`), `.gitignore`, `.github/dependabot.yml` y un CI básico según el lenguaje.
- **Pages (SEO y buenas prácticas):** avisos `sin-title`, `sin-viewport`, `sin-og-title`, `sin-canonical` y `contenido-mixto`; son informativos y no bajan la nota.
- **Reglas propias** en `.github-pages-auditor.toml` (el id empieza por `custom-`; `file-required`, `file-forbidden` y, desde 1.6.0, `content-required` y `content-forbidden`; solo modo API):

```toml
[[custom_rules]]
id = "custom-tiene-docs"
path = "docs"
message = "El repo no tiene carpeta docs"

[[custom_rules]]
id = "custom-sin-env"
path = ".env"
type = "file-forbidden"

# Desde 1.6.0: reglas de contenido (con `contains` o `regex`)
[[custom_rules]]
id = "custom-readme-instala"
path = "README.md"
type = "content-required"
contains = "pip install"

[[custom_rules]]
id = "custom-sin-todo"
path = "src/main.py"
type = "content-forbidden"
regex = "TODO|FIXME"
```

- **Seguridad en profundidad:** con `--deep`, la regla `critical-vulnerabilities` cuenta las alertas de Dependabot críticas y altas; con `--scorecard`, la regla `low-scorecard` salta si la nota de OpenSSF Scorecard es menor de 4.
- **Informes:** `-f trend` dibuja la evolución de la nota con tu carpeta de `--history`; `-f issue` genera el resumen en Markdown para una issue; `--diff ANTES.json DESPUES.json` compara dos informes. La Action puede abrir o actualizar una issue cada semana (ver [docs/ci.md](https://github.com/alberto2005-coder/github-pages-auditor/blob/master/docs/ci.md)).

**Reglas de `--fail-on`:** `missing-readme`, `missing-license`, `missing-gitignore`, `missing-description`, `broken-pages`, `analysis-errors` (`any` = estas), más las de comunidad (solo modo API; no aplican a forks ni archivados): `missing-security-policy`, `missing-contributing`, `missing-code-of-conduct`, `missing-issue-template`, `missing-topics`, `missing-homepage`, `stale-repo` y, con `--deep`, `missing-ci`, `missing-dependabot`, `failing-ci`, `stale-prs`, `no-branch-protection` (`community` = estas; `all` = todas). Ejemplo: `--fail-on missing-license,broken-pages`.

**`-f github`** escribe anotaciones `::error::`/`::warning::` para el log de Actions; **`--baseline informe.json`** compara con un informe anterior y `--fail-on` solo se dispara por hallazgos nuevos. **Action reutilizable:** `uses: alberto2005-coder/github-pages-auditor@v1.3.0` (ver [docs/ci.md](https://github.com/alberto2005-coder/github-pages-auditor/blob/master/docs/ci.md)).

**Salud de Pages.** Para cada sitio se comprueba, además del código 200: errores TLS, timeouts, redirecciones a otro dominio o en bucle, página vacía o sin HTML, y lentitud (aviso). Con **token** se sabe qué repos tienen Pages activadas, así que un 404, un build fallido (`errored`) o cualquier fallo cuenta como **Pages rotas**. Sin token no se puede saber si un repo *debería* tener Pages, por lo que un fallo solo significa «no hay Pages».

Contrato completo del JSON: [docs/json-schema.md](https://github.com/alberto2005-coder/github-pages-auditor/blob/master/docs/json-schema.md). Más recetas de CI (resumen del job, refresco semanal del README): [docs/ci.md](https://github.com/alberto2005-coder/github-pages-auditor/blob/master/docs/ci.md).

**Ejemplo de CI (GitHub Actions):**

```yaml
- run: uvx github-pages-auditor -u ${{ github.repository_owner }} -k ${{ secrets.GITHUB_TOKEN }} -f json -o report.json --fail-on missing-license,broken-pages
```

### Preguntas frecuentes

**¿Cómo compruebo si mis GitHub Pages están rotas?** `uvx github-pages-auditor -u TU_USUARIO --fail-on broken-pages` (con token da la URL real y el estado del build; devuelve código 1 si alguna está rota).

**¿Cómo veo qué repos no tienen licencia, `SECURITY.md` o `CONTRIBUTING.md`?** `uvx github-pages-auditor -u TU_USUARIO --details` o, para una lista exacta, `-f json -o -` y mira `findings`.

**¿Mi repo `.github` con SECURITY/CODE_OF_CONDUCT cuenta?** Sí: los ficheros de comunidad que un repo no tiene pero hereda de `<usuario>/.github` cuentan como presentes (campo JSON `inherited_files`); `--no-defaults-repo` lo desactiva.

**¿Cómo audito la seguridad de mis repos (Dependabot, ramas protegidas, OpenSSF Scorecard)?** Con token: `--deep --scorecard`; los hallazgos son `no-branch-protection`, `critical-vulnerabilities` y `low-scorecard`.

**¿Cómo creo los archivos que faltan sin tocar la rama principal?** `--fix --fix-extra --fix-mode pr --yes`: abre una Pull Request por repo con `LICENSE`, `SECURITY.md`, `.gitignore`, CI básico, etc. Sin `--yes` solo muestra el plan.

**¿Cómo lo uso en GitHub Actions?** Con la Action del repo (`uses: alberto2005-coder/github-pages-auditor@master`); recetas en [docs/ci.md](https://github.com/alberto2005-coder/github-pages-auditor/blob/master/docs/ci.md), incluida una issue semanal con el informe.

**¿Cómo sigo la evolución de la nota?** `--history carpeta` guarda cada informe y `-f trend -o evolucion.html` dibuja la gráfica.

### Pruebas automatizadas

Los tests usan una sesión HTTP falsa: no tocan la red ni consumen cuota de GitHub.

```bash
uv run pytest          # o: pip install -r requirements-dev.txt && pytest
```

Cubren configuración y prioridades, cliente HTTP, ambos proveedores (API y web), orquestación en paralelo, informe, CLI, códigos de salida y créditos. La integración continua (GitHub Actions) los ejecuta en Linux, macOS y Windows con Python 3.10, 3.13 y 3.14.

### Estructura del proyecto

```text
github-pages-auditor/
├── .github/workflows/test.yml    # Integración continua
├── .github/workflows/publish.yml # Publicación en PyPI
├── .env.example                  # Plantilla opcional de variables
├── .gitignore
├── CHANGELOG.md                  # Historial de versiones
├── LICENSE
├── README.md
├── pyproject.toml
├── requirements.txt              # Dependencias para pip
├── requirements-dev.txt          # + pytest
├── uv.lock
├── src/github_pages_auditor/
│   ├── __init__.py               # Versión y créditos del autor
│   ├── __main__.py               # python -m github_pages_auditor
│   ├── main.py                   # Punto de entrada de la CLI
│   ├── config.py                 # Argumentos y entorno
│   ├── audit.py                  # Orquestación en paralelo
│   ├── github_api.py             # Proveedor: API oficial (con token)
│   ├── github_web.py             # Proveedor: web pública (sin token)
│   ├── http.py                   # Sesión con reintentos y timeout
│   ├── pages.py                  # URLs de GitHub Pages
│   ├── pages_health.py           # Salud de Pages (404, TLS, redirecciones...)
│   ├── rules.py                  # Reglas de --fail-on
│   ├── formatters.py             # Salidas JSON y Markdown
│   ├── models.py                 # Estructuras de datos
│   ├── errors.py                 # Excepciones propias
│   └── report.py                 # Consola (Rich) e informe .txt
└── tests/                        # Suite de pytest
```

### Seguridad

- El token se envía **únicamente** a `api.github.com`, nunca a `github.com`, `raw.githubusercontent.com` ni a tu dominio.
- Un parámetro `-k` queda en el historial del shell: es preferible la variable `GITHUB_TOKEN`.
- No subas tu `.env` a git (ya está en `.gitignore`). Para esta herramienta basta un token sin permisos especiales (repos públicos).

### Autor

Desarrollado por **Alberto Ortiz**.

- GitHub: <https://github.com/alberto2005-coder/>
- Web personal: <https://albertoortiz.is-a.dev/>

### Licencia

Distribuido bajo la **Licencia MIT**. Consulta [LICENSE](https://github.com/alberto2005-coder/github-pages-auditor/blob/master/LICENSE). © 2026 Alberto Ortiz.

---

## English

### Table of contents

- [Overview](#overview)
- [Features](#features)
- [Operating modes: with and without API](#operating-modes-with-and-without-api)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Command-line usage](#command-line-usage)
- [Configuration precedence](#configuration-precedence)
- [Exit codes](#exit-codes)
- [Output formats and CI integration](#output-formats-and-ci-integration)
- [Automated tests](#automated-tests)
- [Project structure](#project-structure)
- [Security](#security)
- [Author](#author)
- [License](#license)

### Overview

A Python command-line tool that audits a GitHub user's public repositories: it maps **GitHub Pages** links (including a custom domain), detects **releases**, and checks repository quality (README, licence, `.gitignore` and description).

It is driven **entirely by command-line parameters**: no `.env` file is needed. The **API token is optional**: with a token it uses the official GitHub API; without one it falls back to a best-effort public web mode.

### Features

- **GitHub Pages mapping:** root (`<user>.github.io`) or per-repository subpath, verifying that the URL really responds.
- **Releases:** detected through the public Atom feed, without using API quota.
- **Quality audit:** missing README, licence, `.gitignore` and description (About).
- **Classification:** forks and archived repositories.
- **Performance:** all checks run in parallel (`ThreadPoolExecutor`) with retries and timeouts.
- **Deterministic report:** repositories always appear in the same order; a network failure on one repo does not abort the rest (it is listed separately).
- **Author credits** in `--help`, `--version`, the console and the report.

### Operating modes: with and without API

| | With token (`-k` / `GITHUB_TOKEN`) | Without token |
| :--- | :--- | :--- |
| Data source | Official REST API (5,000 requests/hour) | Public GitHub pages (HTML, `raw`, Atom) |
| Reliability | **High** | Best effort: depends on GitHub's public markup |
| Limit | 5,000/h | May receive `429` if abused |
| Enabled | Automatically when a token is present | When no token is given, or with `--no-api` |

The token is **only ever sent to `api.github.com`**.

**Pages URL:** with the API, the real URL configured on GitHub is used (including your custom domain). Without the API and without `-w`, `https://<user>.github.io/...` is tried and, if GitHub redirects to your custom domain, that domain is detected and shown. With `-w`, that domain is checked directly.

### Prerequisites

- **Python** 3.10 or higher.
- **Package manager:** [`uv`](https://docs.astral.sh/uv/) (recommended) or `pip`.

### Installation

- **Without installing anything (recommended), with [`uv`](https://docs.astral.sh/uv/):**

  ```bash
  uvx github-pages-auditor -u your_user
  ```

- **Install it globally as a command:**

  ```bash
  uv tool install github-pages-auditor
  # or via pip:
  pip install github-pages-auditor
  ```

The old `ver-github-pages` command keeps working as a compatibility alias.

To work from source:

```bash
git clone https://github.com/alberto2005-coder/github-pages-auditor.git
cd github-pages-auditor
```

- **Using `uv` (recommended):**

  ```bash
  uv sync
  ```

- **Using `pip`:**

  ```bash
  pip install -e .
  ```

### Command-line usage

```text
github-pages-auditor -u USER [-w DOMAIN] [-k TOKEN] [-o FILE] [options]
```

**Examples** *(if running from source without a global install, prefix with `uv run`)*

```bash
# 1. Basic, no token and no .env (web mode)
github-pages-auditor -u alberto2005-coder

# 2. Custom domain and token from an environment variable (API mode; recommended)
export GITHUB_TOKEN=github_pat_xxx        # PowerShell: $env:GITHUB_TOKEN = "github_pat_xxx"
github-pages-auditor -u alberto2005-coder -w https://albertoortiz.is-a.dev

# 3. Force web mode even with a token in the environment, and change the output file
github-pages-auditor -u alberto2005-coder --no-api -o my_report.txt

# 4. Token as a parameter (works, but it stays in your shell history)
github-pages-auditor -u alberto2005-coder -k github_pat_xxx

# 5. Also works as a Python module (useful if Scripts is not on PATH)
python -m github_pages_auditor -u alberto2005-coder
```

A fine-grained token with no permissions (public repositories only) is enough.

**Options**

| Flag | Aliases | Description | Required |
| :--- | :--- | :--- | :--- |
| `-u` | `--usuario`, `--user` | GitHub username | **Yes** (or `USUARIO_GITHUB`) |
| `-w` | `--web`, `--dominio` | Base domain of the Pages site | No (default `https://<user>.github.io`) |
| `-k` | `--key`, `--token` | Personal Access Token (enables the API) | No |
| `-o` | `--output` | Report file; `-` = standard output | No (default `paginas_github.<format>`) |
| `-f` | `--format` | `txt`, `json`, `md`, `github` (Actions annotations), `html`, `csv`, `sarif`, `badge`, `trend` (score evolution chart; needs `--history`) or `issue` (issue-ready summary) | No (default `txt`) |
| `--fail-on` | | Rules (or groups `any`, `community`, `all`) that cause exit code 1 | No |
| `--exclude-forks` | | Ignore forks | No |
| `--exclude-archived` | | Ignore archived repositories | No |
| `--inject` | | Update the demos table inside a file (README) | No |
| `--ignore` | | Exclude repos by name or pattern (`a,b*`) | No |
| `--only` | | Audit only these repos (names or patterns) | No |
| `--details` | | Stars, language, license, last push and release | No |
| `--sort` | | `listing` (default), `name`, `stars`, `updated` | No |
| `--stale-months` | | Months without a push for `stale-repo` | No (default `12`) |
| `--baseline` | | Previous JSON report: `--fail-on` only for NEW findings | No |
| `--config` | | TOML configuration file | No (default `.github-pages-auditor.toml`) |
| `--no-config` | | Do not read the configuration file | No |
| `--min-score` | | Fail (exit 1) if the overall score (0-100) is lower | No |
| `--history` | | Folder where each report is saved and compared with the previous one | No |
| `--lang` | | `es` (default) or `en` | No |
| `--notify-webhook` | | Alert a webhook (Discord, Slack, JSON) on new findings (prefer `NOTIFY_WEBHOOK`) | No |
| `--deep` | | With token: security, CI, contributors and PRs | No |
| `--org` | | Audit an organization instead of a user | No |
| `--include-private` | | With token: include your private repos | No |
| `--readme-quality` | | Check the README (install, usage, length): `weak-readme` rule | No |
| `--dep-licenses` | | Look for GPL/AGPL dependencies: `copyleft-dependency` rule | No |
| `-u a,b` | | Several accounts separated by commas in one report (repos as `account/repo`; no `--org` or `--fix*`) | No |
| `--graphql` | | (Experimental) List repo roots with GraphQL in batches: fewer requests; falls back to REST on failure | No |
| `--init` | | Create a starter `.github-pages-auditor.toml` (`--yes` overwrites it) | No |
| `--fix-only` | | With `--fix`: only the listed rules (e.g. `missing-license,missing-security-policy`) | No |
| `--fix-log` | | With `--fix*`: save what was planned or applied to a JSON file | No |
| `--crawl` | | Crawl up to 10 internal pages of each site and validate its `sitemap.xml` | No |
| `--check-links` | | Check the links on each site's front page | No |
| `--fix` | | Create missing community files (plans; `--yes` applies) | No |
| `--fix-pages` | | Turn on Enforce HTTPS where missing | No |
| `--fix-metadata` | | Suggest description and topics | No |
| `--dry-run` | | With `--fix*`, writes nothing | No |
| `--yes` | | With `--fix*`, applies the changes | No |
| `--tui` | | Interactive explorer (`[tui]` extra) | No |
| `--cache` | | ETag cache for the API in this folder | No |
| `--cache-clear` | | Delete the ETag cache and exit | No |
| `--notify-on` | | With `--notify-webhook`: `new` (default) or `always` (also when nothing is new) | No |
| `--notify-test` | | Send a test message to the webhook and exit | No |
| `--since` | | Only repos with a recent push: `30d`, `12w`, `6m`, `1y` or a date | No |
| `--doctor` | | Diagnose the token: type, expiry, rate limit and permissions (no audit) | No |
| `--diff` | | Compare two JSON reports: `--diff BEFORE.json AFTER.json` (no audit) | No |
| `--fix-extra` | | Implies `--fix`: also creates `LICENSE`, `.gitignore`, `dependabot.yml` and a basic CI by language | No |
| `--fix-mode` | | `direct` (default, commit to the default branch) or `pr` (a branch and Pull Request per repo) | No |
| `--license` | | License created by `--fix-extra`: `mit` (default), `bsd-3-clause`, `isc`, `unlicense` | No |
| `--scorecard` | | Adds the OpenSSF Scorecard score (0-10) and the `low-scorecard` rule | No |
| `-q` | `--quiet` | No tables or progress | No |
| `--workers` | | Parallel threads | No (default `15`) |
| `--timeout` | | Per-request timeout, in seconds | No (default `10`) |
| `--no-api` | | Force web mode even with a token | No |
| `--no-color` | | Colourless console output | No |
| `--no-defaults-repo` | | Do not count files inherited from your `.github` repository as present | No |
| `--no-env` | | Do not read the `.env` file | No |
| `-V` | `--version` | Version and credits | No |
| `-h` | `--help` | Help and credits | No |

### Configuration precedence

1. **Command-line parameters** (`-u`, `-w`, `-k`, `-o`…).
2. **Environment variables**, including those from an **optional** `.env` file in the current directory: `USUARIO_GITHUB`, `DOMINIO_WEB`, `GITHUB_TOKEN`, `ARCHIVO_SALIDA`. An empty value counts as unset.
3. **Built-in defaults.**

A template is provided in [`.env.example`](https://github.com/alberto2005-coder/github-pages-auditor/blob/master/.env.example).

### Exit codes

| Code | Meaning |
| :---: | :--- |
| `0` | Audit succeeded and report written |
| `1` | A `--fail-on` rule found issues (the report is still written) |
| `2` | Error: invalid parameters, unknown user, rejected token, rate limit, network or write failure |
| `3` | No repositories to analyse (no report is written) |
| `130` | Cancelled with Ctrl+C |

### Output formats and CI integration

`-f/--format` selects the report format: `txt` (default), `json` or `md`. With `-o -` the report goes to standard output and the UI to stderr, so it can be piped:

```bash
uvx github-pages-auditor -u alberto2005-coder -f json -o - -q | jq '.summary'
```

**JSON** (`schema_version: 1`): `tool`, `generated_at`, `user`, `mode` (`api`/`web`), `domain`, `summary` (counters), `findings` (one list per rule, empty when clean), `fail_on` (requested and triggered rules) and `repos` (one object per repository, with `pages.status`, `pages.problems`, `pages.warnings`, `pages.title`, etc.).

**Markdown** (`-f md`): a sorted table of your live demos, forks excluded, between the `<!-- github-pages-auditor:start -->` and `<!-- github-pages-auditor:end -->` markers. `--inject README.md` updates it **inside that file**, between those markers (if they are missing it fails without touching anything).

**What's new in 1.4.0.** Every repo gets a **0-100 score** (`A`-`E`) and the report an overall score; `--min-score 70` fails CI below it and `--history folder` compares with the previous run. `--deep` adds security, CI and activity. `--fix` creates any missing SECURITY, CONTRIBUTING, CODE_OF_CONDUCT and issue template, `--fix-pages` turns on Enforce HTTPS and `--fix-metadata` suggests a description and topics: **by default it only prints the plan; `--yes` applies it** (with a token that can write, never on forks or archived repos). More recipes in [docs/ci.md](https://github.com/alberto2005-coder/github-pages-auditor/blob/master/docs/ci.md). Alternative install: `pipx install github-pages-auditor` (TUI: `pipx install "github-pages-auditor[tui]"`).

**What's new in 1.5.0.**
- **`--doctor`** diagnoses your token (type, expiry, rate limit and permissions) so you know what it can do: `uvx github-pages-auditor --doctor`.
- **Secret protection:** the token and webhooks are masked (`***`) in every message, and you are warned if you pass it on the command line or if `.env` is inside the git repository.
- **Pages being built:** right after a commit GitHub rebuilds Pages; that now shows as `construyendo` (building) instead of a broken site.
- **More reliable with the API:** if the rate limit resets in under a minute it waits and retries once; `--cache auto` uses your user cache folder.
- **`--fix-mode pr`** opens one Pull Request per repo instead of writing to the default branch; **`--fix-extra`** also creates `LICENSE` (`--license`), `.gitignore`, `.github/dependabot.yml` and a basic CI by language.
- **Pages (SEO and best practices):** new warnings `sin-title`, `sin-viewport`, `sin-og-title`, `sin-canonical` and `contenido-mixto`; they are informational and do not lower the score.
- **Custom rules** in `.github-pages-auditor.toml` (the id starts with `custom-`; `file-required`, `file-forbidden` and, since 1.6.0, `content-required` and `content-forbidden`; API mode only), as in the example in the Spanish section above.
- **Deeper security:** with `--deep`, the `critical-vulnerabilities` rule counts open critical and high Dependabot alerts; with `--scorecard`, the `low-scorecard` rule fires when the OpenSSF Scorecard score is below 4.
- **Reports:** `-f trend` draws the score evolution from your `--history` folder; `-f issue` writes the issue-ready Markdown summary; `--diff BEFORE.json AFTER.json` compares two reports. The Action can open or update an issue every week (see [docs/ci.md](https://github.com/alberto2005-coder/github-pages-auditor/blob/master/docs/ci.md)).

**`--fail-on` rules:** `missing-readme`, `missing-license`, `missing-gitignore`, `missing-description`, `broken-pages`, `analysis-errors` (`any` = these), plus community rules (API mode only; not applied to forks or archived repos): `missing-security-policy`, `missing-contributing`, `missing-code-of-conduct`, `missing-issue-template`, `missing-topics`, `missing-homepage`, `stale-repo` and, with `--deep`, `missing-ci`, `missing-dependabot`, `failing-ci`, `stale-prs`, `no-branch-protection` (`community` = these; `all` = everything). Example: `--fail-on missing-license,broken-pages`.

**`-f github`** writes `::error::`/`::warning::` annotations for the Actions log; **`--baseline report.json`** compares with a previous report so `--fail-on` only triggers on NEW findings. **Reusable Action:** `uses: alberto2005-coder/github-pages-auditor@v1.3.0` (see [docs/ci.md](https://github.com/alberto2005-coder/github-pages-auditor/blob/master/docs/ci.md)).

**Pages health.** Besides a 200 status, each site is checked for TLS errors, timeouts, redirects to another domain or loops, empty or non-HTML pages, and slowness (warning). With a **token** the tool knows which repos have Pages enabled, so a 404, a failed build (`errored`) or any failure counts as **broken Pages**. Without a token it cannot know whether a repo *should* have Pages, so a failure just means “no Pages”.

Full JSON contract: [docs/json-schema.md](https://github.com/alberto2005-coder/github-pages-auditor/blob/master/docs/json-schema.md). More CI recipes (job summary, weekly README refresh): [docs/ci.md](https://github.com/alberto2005-coder/github-pages-auditor/blob/master/docs/ci.md).

**CI example (GitHub Actions):**

```yaml
- run: uvx github-pages-auditor -u ${{ github.repository_owner }} -k ${{ secrets.GITHUB_TOKEN }} -f json -o report.json --fail-on missing-license,broken-pages
```

### FAQ

**How do I check whether my GitHub Pages sites are broken?** `uvx github-pages-auditor -u YOUR_USERNAME --fail-on broken-pages` (with a token it uses the real URL and build status; it exits with code 1 if any site is broken).

**How do I list repos without a license, `SECURITY.md` or `CONTRIBUTING.md`?** `uvx github-pages-auditor -u YOUR_USERNAME --details`, or `-f json -o -` and read `findings` for an exact list.

**Do files from my `.github` repo count?** Yes: community files a repo lacks but inherits from `<user>/.github` count as present (JSON `inherited_files`); `--no-defaults-repo` turns this off.

**How do I audit repo security (Dependabot, branch protection, OpenSSF Scorecard)?** With a token: `--deep --scorecard`; the findings are `no-branch-protection`, `critical-vulnerabilities` and `low-scorecard`.

**How do I create missing files without touching the default branch?** `--fix --fix-extra --fix-mode pr --yes` opens one Pull Request per repo with `LICENSE`, `SECURITY.md`, `.gitignore`, a basic CI, etc. Without `--yes` it only prints the plan.

**How do I use it in GitHub Actions?** With the repo's Action (`uses: alberto2005-coder/github-pages-auditor@master`); recipes in [docs/ci.md](https://github.com/alberto2005-coder/github-pages-auditor/blob/master/docs/ci.md), including a weekly report issue.

**How do I track the score over time?** `--history folder` saves every report and `-f trend -o evolution.html` draws the chart.

### Automated tests

Tests use a fake HTTP session: they never touch the network or use GitHub quota.

```bash
uv run pytest          # or: pip install -r requirements-dev.txt && pytest
```

They cover configuration and precedence, the HTTP client, both providers (API and web), parallel orchestration, the report, the CLI, exit codes and credits. Continuous integration (GitHub Actions) runs them on Linux, macOS and Windows with Python 3.10, 3.13 and 3.14.

### Project structure

```text
github-pages-auditor/
├── .github/workflows/test.yml    # Continuous integration
├── .github/workflows/publish.yml # PyPI publishing
├── .env.example                  # Optional variables template
├── .gitignore
├── CHANGELOG.md                  # Version history
├── LICENSE
├── README.md
├── pyproject.toml
├── requirements.txt              # pip dependencies
├── requirements-dev.txt          # + pytest
├── uv.lock
├── src/github_pages_auditor/
│   ├── __init__.py               # Version and author credits
│   ├── __main__.py               # python -m github_pages_auditor
│   ├── main.py                   # CLI entry point
│   ├── config.py                 # Arguments and environment
│   ├── audit.py                  # Parallel orchestration
│   ├── github_api.py             # Provider: official API (with token)
│   ├── github_web.py             # Provider: public web (no token)
│   ├── http.py                   # Session with retries and timeout
│   ├── pages.py                  # GitHub Pages URLs
│   ├── pages_health.py           # Pages health (404, TLS, redirects...)
│   ├── rules.py                  # --fail-on rules
│   ├── formatters.py             # JSON and Markdown output
│   ├── models.py                 # Data structures
│   ├── errors.py                 # Custom exceptions
│   └── report.py                 # Console (Rich) and .txt report
└── tests/                        # pytest suite
```

### Security

- The token is sent **only** to `api.github.com`, never to `github.com`, `raw.githubusercontent.com` or your own domain.
- A `-k` parameter is stored in your shell history: prefer the `GITHUB_TOKEN` environment variable.
- Do not commit your `.env` (it is already in `.gitignore`). A token with no special scopes (public repos) is enough for this tool.

### Author

Developed by **Alberto Ortiz**.

- GitHub: <https://github.com/alberto2005-coder/>
- Personal website: <https://albertoortiz.is-a.dev/>

### License

Distributed under the **MIT License**. See [LICENSE](https://github.com/alberto2005-coder/github-pages-auditor/blob/master/LICENSE). © 2026 Alberto Ortiz.
