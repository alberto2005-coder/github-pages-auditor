# GitHub Profile & Pages Auditor

[Español](#español) | [English](#english)

> Desarrollado por / Developed by **[Alberto Ortiz](https://github.com/alberto2005-coder/)** · 🌐 [albertoortiz.is-a.dev](https://albertoortiz.is-a.dev/)

---

<a name="español"></a>
# Español

Herramienta de línea de comandos en Python para auditar los repositorios públicos de un usuario de GitHub: mapea los enlaces de **GitHub Pages** (incluido un dominio personalizado), detecta **releases** y evalúa la calidad del repositorio (README, licencia, `.gitignore` y descripción).

Se controla **solo con parámetros de consola**: no necesita archivo `.env`. El **token de la API es opcional**: con token usa la API oficial de GitHub; sin token usa un modo web público de "mejor esfuerzo".

## Índice

1. [Características](#características-es)
2. [Modos de funcionamiento: con y sin API](#modos-es)
3. [Requisitos previos](#requisitos-previos-es)
4. [Instalación](#instalación-es)
5. [Uso por línea de comandos](#uso-es)
6. [Jerarquía de configuración](#configuración-es)
7. [Códigos de salida](#salida-es)
8. [Pruebas automatizadas](#pruebas-es)
9. [Estructura del proyecto](#estructura-es)
10. [Seguridad](#seguridad-es)
11. [Autor](#autor-es)
12. [Licencia](#licencia-es)

---

<a name="características-es"></a>
## Características

- **Mapeo de GitHub Pages:** raíz (`<usuario>.github.io`) o subruta por repositorio, verificando que la URL responde de verdad.
- **Releases:** detectadas mediante el feed Atom público, sin consumir cuota de la API.
- **Auditoría de calidad:** sin README, sin licencia, sin `.gitignore` y sin descripción (About).
- **Clasificación:** forks y repositorios archivados.
- **Rendimiento:** todo el análisis se hace en paralelo (`ThreadPoolExecutor`) con reintentos y timeout.
- **Informe determinista:** los repositorios salen siempre en el mismo orden; un fallo de red en un repo no tumba el resto (se lista aparte).
- **Créditos del autor** en `--help`, `--version`, la consola y el informe.

<a name="modos-es"></a>
## Modos de funcionamiento: con y sin API

| | Con token (`-k` / `GITHUB_TOKEN`) | Sin token |
| :--- | :--- | :--- |
| Fuente de datos | API REST oficial (5.000 peticiones/hora) | Páginas públicas de GitHub (HTML, `raw`, Atom) |
| Fiabilidad | **Alta** | De mejor esfuerzo: depende del marcado público de GitHub |
| Límite | 5.000/h | Puede recibir `429` si se abusa |
| Se activa | Automáticamente si hay token | Si no hay token, o con `--no-api` |

El token **solo se envía a `api.github.com`**.

**URL de las Pages:** con API se usa la URL real que GitHub tiene configurada (incluido tu dominio personalizado). Sin API, si no indicas `-w`, se prueba `https://<usuario>.github.io/...` y, si GitHub redirige a tu dominio personalizado, se detecta y se muestra ese dominio. Con `-w` se comprueba directamente ese dominio.

<a name="requisitos-previos-es"></a>
## Requisitos previos

- **Python** 3.10 o superior.
- **Gestor de paquetes:** [`uv`](https://docs.astral.sh/uv/) (recomendado) o `pip`.

<a name="instalación-es"></a>
## Instalación

```bash
git clone https://github.com/alberto2005-coder/ver-github-pages.git
cd ver-github-pages
```

- **Con `uv` (recomendado):**
  ```bash
  uv sync
  ```
- **Con `pip`:**
  ```bash
  pip install -e .
  ```

<a name="uso-es"></a>
## Uso por línea de comandos

```text
ver-github-pages -u USUARIO [-w DOMINIO] [-k TOKEN] [-o ARCHIVO] [opciones]
```

**Ejemplos**

```bash
# 1. Básico, sin token ni .env (modo web)
uv run ver-github-pages -u alberto2005-coder

# 2. Con dominio personalizado y token (modo API)
uv run ver-github-pages -u alberto2005-coder -w https://albertoortiz.is-a.dev -k ghp_tu_token

# 3. Forzar modo web aunque haya token y cambiar el archivo de salida
uv run ver-github-pages -u alberto2005-coder -k ghp_tu_token --no-api -o mi_reporte.txt

# 4. Token por variable de entorno (más seguro: no queda en el historial del shell)
GITHUB_TOKEN=ghp_tu_token uv run ver-github-pages -u alberto2005-coder

# 5. También funciona como módulo
python -m ver_github_pages -u alberto2005-coder
```

**Opciones**

| Parámetro | Alternativas | Descripción | Obligatorio |
| :--- | :--- | :--- | :--- |
| `-u` | `--usuario`, `--user` | Usuario de GitHub | **Sí** (o `USUARIO_GITHUB`) |
| `-w` | `--web`, `--dominio` | Dominio base de las Pages | No (def. `https://<usuario>.github.io`) |
| `-k` | `--key`, `--token` | Personal Access Token (activa la API) | No |
| `-o` | `--output` | Archivo del informe | No (def. `paginas_github.txt`) |
| `--workers` | | Hilos en paralelo | No (def. `15`) |
| `--timeout` | | Timeout por petición, en segundos | No (def. `10`) |
| `--no-api` | | Fuerza el modo web aunque haya token | No |
| `--no-color` | | Consola sin colores | No |
| `--no-env` | | No leer el archivo `.env` | No |
| `-V` | `--version` | Versión y créditos | No |
| `-h` | `--help` | Ayuda y créditos | No |

<a name="configuración-es"></a>
## Jerarquía de configuración

1. **Parámetros de consola** (`-u`, `-w`, `-k`, `-o`…).
2. **Variables de entorno**, incluidas las de un archivo `.env` **opcional** en el directorio actual: `USUARIO_GITHUB`, `DOMINIO_WEB`, `GITHUB_TOKEN`, `ARCHIVO_SALIDA`. Un valor vacío se trata como no definido.
3. **Valores por defecto.**

Hay una plantilla en [`.env.example`](.env.example).

<a name="salida-es"></a>
## Códigos de salida

| Código | Significado |
| :---: | :--- |
| `0` | Auditoría correcta e informe escrito |
| `1` | El usuario no tiene repositorios públicos (no se escribe informe) |
| `2` | Error: parámetros inválidos, usuario inexistente, token rechazado, límite de tasa, red o escritura |
| `130` | Cancelado con Ctrl+C |

<a name="pruebas-es"></a>
## Pruebas automatizadas

Los tests usan una sesión HTTP falsa: no tocan la red ni consumen cuota de GitHub.

```bash
uv run pytest          # o: pip install -r requirements-dev.txt && pytest
```

Cubren configuración y prioridades, cliente HTTP, ambos proveedores (API y web), orquestación en paralelo, informe, CLI, códigos de salida y créditos. La integración continua (GitHub Actions) los ejecuta en Linux, macOS y Windows con Python 3.10 y 3.13.

<a name="estructura-es"></a>
## Estructura del proyecto

```text
ver-github-pages/
├── .github/workflows/test.yml   # Integración continua
├── .env.example                 # Plantilla opcional de variables
├── .gitignore
├── CHANGELOG.md                 # Historial de versiones
├── LICENSE
├── README.md
├── pyproject.toml
├── requirements.txt             # Dependencias para pip
├── requirements-dev.txt         # + pytest
├── uv.lock
├── src/ver_github_pages/
│   ├── __init__.py              # Versión y créditos del autor
│   ├── __main__.py              # python -m ver_github_pages
│   ├── main.py                  # Punto de entrada de la CLI
│   ├── config.py                # Argumentos y entorno
│   ├── audit.py                 # Orquestación en paralelo
│   ├── github_api.py            # Proveedor: API oficial (con token)
│   ├── github_web.py            # Proveedor: web pública (sin token)
│   ├── http.py                  # Sesión con reintentos y timeout
│   ├── pages.py                 # URLs y comprobación de GitHub Pages
│   ├── models.py                # Estructuras de datos
│   ├── errors.py                # Excepciones propias
│   └── report.py                # Consola (Rich) e informe .txt
└── tests/                       # Suite de pytest
```

<a name="seguridad-es"></a>
## Seguridad

- El token se envía **únicamente** a `api.github.com`, nunca a `github.com`, `raw.githubusercontent.com` ni a tu dominio.
- Un parámetro `-k` queda en el historial del shell: es preferible la variable `GITHUB_TOKEN`.
- No subas tu `.env` a git (ya está en `.gitignore`). Para esta herramienta basta un token sin permisos especiales (repos públicos).

<a name="autor-es"></a>
## Autor

Desarrollado por **Alberto Ortiz**.

- GitHub: <https://github.com/alberto2005-coder/>
- Web personal: <https://albertoortiz.is-a.dev/>

<a name="licencia-es"></a>
## Licencia

Distribuido bajo la Licencia MIT. Consulta [LICENSE](LICENSE).

---

<a name="english"></a>
# English

Python command-line tool that audits a GitHub user's public repositories: it maps **GitHub Pages** links (including a custom domain), detects **releases**, and checks repository quality (README, license, `.gitignore` and description).

It is driven **entirely by command-line parameters**: no `.env` file needed. The **API token is optional**: with a token it uses the official GitHub API; without one it falls back to a best-effort public web mode.

## Table of Contents

1. [Features](#features-en)
2. [Operating modes: with and without API](#modes-en)
3. [Prerequisites](#prerequisites-en)
4. [Installation](#installation-en)
5. [Command-line usage](#usage-en)
6. [Configuration precedence](#configuration-en)
7. [Exit codes](#exit-en)
8. [Automated tests](#tests-en)
9. [Project structure](#structure-en)
10. [Security](#security-en)
11. [Author](#author-en)
12. [License](#license-en)

---

<a name="features-en"></a>
## Features

- **GitHub Pages mapping:** root (`<user>.github.io`) or per-repository subpath, verifying that the URL really responds.
- **Releases:** detected through the public Atom feed, without using API quota.
- **Quality audit:** missing README, license, `.gitignore` and description (About).
- **Classification:** forks and archived repositories.
- **Performance:** all checks run in parallel (`ThreadPoolExecutor`) with retries and timeouts.
- **Deterministic report:** repositories always appear in the same order; a network failure on one repo does not abort the rest (it is listed separately).
- **Author credits** in `--help`, `--version`, the console and the report.

<a name="modes-en"></a>
## Operating modes: with and without API

| | With token (`-k` / `GITHUB_TOKEN`) | Without token |
| :--- | :--- | :--- |
| Data source | Official REST API (5,000 requests/hour) | Public GitHub pages (HTML, `raw`, Atom) |
| Reliability | **High** | Best effort: depends on GitHub's public markup |
| Limit | 5,000/h | May receive `429` if abused |
| Enabled | Automatically when a token is present | When no token is given, or with `--no-api` |

The token is **only ever sent to `api.github.com`**.

**Pages URL:** with the API, the real URL configured on GitHub is used (including your custom domain). Without the API and without `-w`, `https://<user>.github.io/...` is tried and, if GitHub redirects to your custom domain, that domain is detected and shown. With `-w`, that domain is checked directly.

<a name="prerequisites-en"></a>
## Prerequisites

- **Python** 3.10 or higher.
- **Package manager:** [`uv`](https://docs.astral.sh/uv/) (recommended) or `pip`.

<a name="installation-en"></a>
## Installation

```bash
git clone https://github.com/alberto2005-coder/ver-github-pages.git
cd ver-github-pages
```

- **Using `uv` (recommended):**
  ```bash
  uv sync
  ```
- **Using `pip`:**
  ```bash
  pip install -e .
  ```

<a name="usage-en"></a>
## Command-line usage

```text
ver-github-pages -u USER [-w DOMAIN] [-k TOKEN] [-o FILE] [options]
```

**Examples**

```bash
# 1. Basic, no token and no .env (web mode)
uv run ver-github-pages -u alberto2005-coder

# 2. Custom domain and token (API mode)
uv run ver-github-pages -u alberto2005-coder -w https://albertoortiz.is-a.dev -k ghp_your_token

# 3. Force web mode even with a token, and change the output file
uv run ver-github-pages -u alberto2005-coder -k ghp_your_token --no-api -o my_report.txt

# 4. Token from an environment variable (safer: not stored in shell history)
GITHUB_TOKEN=ghp_your_token uv run ver-github-pages -u alberto2005-coder

# 5. Also works as a module
python -m ver_github_pages -u alberto2005-coder
```

**Options**

| Flag | Aliases | Description | Required |
| :--- | :--- | :--- | :--- |
| `-u` | `--usuario`, `--user` | GitHub username | **Yes** (or `USUARIO_GITHUB`) |
| `-w` | `--web`, `--dominio` | Base domain of the Pages site | No (default `https://<user>.github.io`) |
| `-k` | `--key`, `--token` | Personal Access Token (enables the API) | No |
| `-o` | `--output` | Report file | No (default `paginas_github.txt`) |
| `--workers` | | Parallel threads | No (default `15`) |
| `--timeout` | | Per-request timeout, in seconds | No (default `10`) |
| `--no-api` | | Force web mode even with a token | No |
| `--no-color` | | Colorless console output | No |
| `--no-env` | | Do not read the `.env` file | No |
| `-V` | `--version` | Version and credits | No |
| `-h` | `--help` | Help and credits | No |

<a name="configuration-en"></a>
## Configuration precedence

1. **Command-line parameters** (`-u`, `-w`, `-k`, `-o`…).
2. **Environment variables**, including those from an **optional** `.env` file in the current directory: `USUARIO_GITHUB`, `DOMINIO_WEB`, `GITHUB_TOKEN`, `ARCHIVO_SALIDA`. An empty value counts as unset.
3. **Built-in defaults.**

A template is provided in [`.env.example`](.env.example).

<a name="exit-en"></a>
## Exit codes

| Code | Meaning |
| :---: | :--- |
| `0` | Audit succeeded and report written |
| `1` | The user has no public repositories (no report is written) |
| `2` | Error: invalid parameters, unknown user, rejected token, rate limit, network or write failure |
| `130` | Cancelled with Ctrl+C |

<a name="tests-en"></a>
## Automated tests

Tests use a fake HTTP session: they never touch the network or use GitHub quota.

```bash
uv run pytest          # or: pip install -r requirements-dev.txt && pytest
```

They cover configuration and precedence, the HTTP client, both providers (API and web), parallel orchestration, the report, the CLI, exit codes and credits. Continuous integration (GitHub Actions) runs them on Linux, macOS and Windows with Python 3.10 and 3.13.

<a name="structure-en"></a>
## Project structure

```text
ver-github-pages/
├── .github/workflows/test.yml   # Continuous integration
├── .env.example                 # Optional variables template
├── .gitignore
├── CHANGELOG.md                 # Version history
├── LICENSE
├── README.md
├── pyproject.toml
├── requirements.txt             # pip dependencies
├── requirements-dev.txt         # + pytest
├── uv.lock
├── src/ver_github_pages/
│   ├── __init__.py              # Version and author credits
│   ├── __main__.py              # python -m ver_github_pages
│   ├── main.py                  # CLI entry point
│   ├── config.py                # Arguments and environment
│   ├── audit.py                 # Parallel orchestration
│   ├── github_api.py            # Provider: official API (with token)
│   ├── github_web.py            # Provider: public web (no token)
│   ├── http.py                  # Session with retries and timeout
│   ├── pages.py                 # Pages URLs and checks
│   ├── models.py                # Data structures
│   ├── errors.py                # Custom exceptions
│   └── report.py                # Console (Rich) and .txt report
└── tests/                       # pytest suite
```

<a name="security-en"></a>
## Security

- The token is sent **only** to `api.github.com`, never to `github.com`, `raw.githubusercontent.com` or your own domain.
- A `-k` parameter is stored in your shell history: prefer the `GITHUB_TOKEN` environment variable.
- Do not commit your `.env` (it is already in `.gitignore`). A token with no special scopes (public repos) is enough for this tool.

<a name="author-en"></a>
## Author

Developed by **Alberto Ortiz**.

- GitHub: <https://github.com/alberto2005-coder/>
- Personal website: <https://albertoortiz.is-a.dev/>

<a name="license-en"></a>
## License

Distributed under the MIT License. See [LICENSE](LICENSE).
