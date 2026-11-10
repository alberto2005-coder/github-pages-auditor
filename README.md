# GitHub Profile & Pages Auditor

[Español](#español) | [English](#english)

---

<a name="español"></a>
# Español

Una herramienta de línea de comandos en Python diseñada para auditar repositorios de GitHub. Permite mapear enlaces de GitHub Pages con dominio personalizado, verificar lanzamientos y evaluar la calidad de la documentación (README, Licencia, `.gitignore` y descripción) sin requerir obligatoriamente un archivo de configuración `.env` ni credenciales.

Cuenta con soporte para autenticación mediante Personal Access Token (Key) por parámetro para consultas a la API oficial de GitHub, así como un motor de respaldo por scraping público en paralelo.

## Índice

1. [Características](#características-es)
2. [Arquitectura y Solución Técnica](#arquitectura-y-solución-técnica-es)
3. [Requisitos Previos](#requisitos-previos-es)
4. [Instalación](#instalación-es)
5. [Uso por Línea de Comandos](#uso-por-línea-de-comandos-es)
6. [Jerarquía de Configuración](#jerarquía-de-configuración-es)
7. [Pruebas Automatizadas](#pruebas-automatizadas-es)
8. [Estructura del Proyecto](#estructura-del-proyecto-es)
9. [Licencia](#licencia-es)

---

<a name="características-es"></a>
## Características

- **Mapeo Real de GitHub Pages:** Identifica despliegues activos evaluando respuestas HTTP y siguiendo redirecciones para evitar falsos positivos.
- **Soporte Dual (API + Scraping):** Funciona mediante la API REST oficial de GitHub o a través de scraping público y feeds Atom sin necesidad de API Key ni archivo `.env`.
- **Auditoría de Calidad:**
  - Repositorios sin archivo `README`
  - Repositorios sin archivo de `Licencia`
  - Repositorios sin `.gitignore`
  - Repositorios sin Descripción (About)
- **Clasificación:** Identifica repositorios que son *Forks* o que están *Archivados*.
- **Rendimiento:** Ejecución multihilo optimizada mediante `ThreadPoolExecutor` para análisis de código y validación web.
- **Consola Interactiva:** Salida formateada con tablas y paneles visuales mediante `Rich`.

---

<a name="arquitectura-y-solución-técnica-es"></a>
## Arquitectura y Solución Técnica

La API pública REST de GitHub impone un límite de 60 peticiones/hora a usuarios no autenticados, lo que provoca errores `403 Rate Limit Exceeded` al auditar múltiples repositorios.

Esta herramienta resuelve esta limitación mediante dos enfoques:
1. **Modo API (Con Key):** Si se proporciona un Personal Access Token por parámetro o entorno, la herramienta realiza peticiones masivas a la API oficial, elevando la cuota a 5.000 peticiones/hora.
2. **Modo Scraping (Sin Key):** Si no hay clave disponible, analiza el HTML público del perfil de GitHub y consulta los lanzamientos a través de feeds Atom públicos (`/releases.atom`), los cuales no consumen cuota de la API REST.

---

<a name="requisitos-previos-es"></a>
## Requisitos Previos

- **Python:** Versión 3.10 o superior.
- **Gestor de paquetes:** `uv` (Recomendado) o `pip`.

---

<a name="instalación-es"></a>
## Instalación

1. Clona el repositorio:
   ```bash
   git clone https://github.com/alberto2005-coder/ver-github-pages.git
   cd ver-github-pages
   ```

2. Instala las dependencias necesarias:

   - **Usando `uv` (Recomendado):**
     ```bash
     uv sync
     ```

   - **Usando `pip`:**
     ```bash
     pip install -r requirements.txt
     ```

---

<a name="uso-por-línea-de-comandos-es"></a>
## Uso por Línea de Comandos

Los parámetros se pueden pasar directamente por la consola sin necesidad de crear ni modificar un archivo `.env`.

### Ejemplo 1: Ejecución básica (sin clave ni token)
```bash
uv run ver-github-pages -u alberto2005-coder
```

### Ejemplo 2: Especificando dominio personalizado y token de API
```bash
uv run ver-github-pages -u alberto2005-coder -w https://albertoortiz.is-a.dev -k ghp_tu_token_aqui
```

### Ejemplo 3: Forzar modo scraping y cambiar archivo de salida
```bash
uv run ver-github-pages -u alberto2005-coder --no-api -o mi_reporte.txt
```

### Opciones de la CLI

| Parámetro | Alternativa | Descripción | Obligatorio |
| :--- | :--- | :--- | :--- |
| `-u` | `--usuario` / `--user` | Nombre de usuario de GitHub | **Sí** |
| `-w` | `--web` / `--dominio` | Dominio base para GitHub Pages | No (default: `https://<usuario>.github.io`) |
| `-k` | `--key` / `--token` | GitHub Personal Access Token | No |
| `-o` | `--output` | Ruta del archivo de salida | No (default: `paginas_github.txt`) |
| `--no-api` | - | Forzar scraping público ignorando la API Key | No |
| `--no-color` | - | Desactivar salida con colores en la consola | No |

---

<a name="jerarquía-de-configuración-es"></a>
## Jerarquía de Configuración

El programa evalúa la configuración respetando el siguiente orden de prioridad:
1. **Argumentos de línea de comandos** (Ej: `-u`, `-w`, `-k`).
2. **Variables en el archivo `.env`** (si existe en la raíz del proyecto).
3. **Valores por defecto del sistema**.

---

<a name="pruebas-automatizadas-es"></a>
## Pruebas Automatizadas

El proyecto incluye una suite de tests unitarios con `pytest` que simula respuestas HTTP para validar la lógica sin consumir cuotas de GitHub:

```bash
uv run pytest
```

---

<a name="estructura-del-proyecto-es"></a>
## Estructura del Proyecto

```text
ver-github-pages/
├── .env.example          # Plantilla opcional de variables de entorno
├── .gitignore            # Archivos excluidos del control de versiones
├── LICENSE               # Licencia del proyecto
├── README.md             # Documentación unificada (Español / Inglés)
├── pyproject.toml        # Configuración del paquete y dependencias
├── requirements.txt      # Archivo de dependencias para pip
├── src/
│   └── ver_github_pages/
│       ├── __init__.py
│       ├── __main__.py
│       ├── audit.py       # Orquestador de la auditoría
│       ├── config.py      # Parser de argumentos CLI y entorno
│       ├── github_api.py  # Proveedor de datos vía API oficial
│       ├── github_web.py  # Proveedor de datos vía Scraping público
│       ├── http.py        # Cliente HTTP con soporte para reintentos
│       ├── main.py        # Punto de entrada de la CLI
│       ├── models.py      # Estructuras de datos
│       ├── pages.py       # Verificación de URLs de GitHub Pages
│       └── report.py     # Generador de consola (Rich) y archivo .txt
└── tests/                # Tests unitarios automatizados
    ├── conftest.py
    ├── test_config.py
    ├── test_github_api.py
    ├── test_github_web.py
    ├── test_pages.py
    └── test_report.py
```

---

<a name="licencia-es"></a>
## Licencia

Este proyecto se distribuye bajo la Licencia MIT. Consulta el archivo [LICENSE](LICENSE) para obtener más información.

---

<a name="english"></a>
# English

A Python CLI tool designed to audit GitHub repositories. It maps GitHub Pages URLs with custom domains, verifies published releases, and checks documentation quality (README, License, `.gitignore`, and description) — without requiring a `.env` configuration file or credentials.

Supports authentication via GitHub Personal Access Tokens (Key) passed via CLI arguments, as well as an automatic public web scraping fallback mechanism.

## Table of Contents

1. [Features](#features-en)
2. [Architecture and Technical Solution](#architecture-and-technical-solution-en)
3. [Prerequisites](#prerequisites-en)
4. [Installation](#installation-en)
5. [CLI Usage](#cli-usage-en)
6. [Configuration Precedence](#configuration-precedence-en)
7. [Automated Tests](#automated-tests-en)
8. [Project Structure](#project-structure-en)
9. [License](#license-en)

---

<a name="features-en"></a>
## Features

- **Real GitHub Pages Mapping:** Validates active deployments by evaluating HTTP status codes and following redirects to prevent false positives.
- **Dual-Mode Support (API + Scraping):** Operates through the official GitHub REST API or public web scraping via Atom feeds without requiring an API key or `.env` file.
- **Quality Audit:**
  - Repositories missing a `README` file
  - Repositories missing a `License` file
  - Repositories missing `.gitignore`
  - Repositories missing About/Description
- **Categorization:** Flags repositories that are *Forks* or *Archived*.
- **Performance:** Multi-threaded execution powered by `ThreadPoolExecutor` for code analysis and URL verification.
- **Interactive Output:** Clean console UI formatted with tables and panels built with `Rich`.

---

<a name="architecture-and-technical-solution-en"></a>
## Architecture and Technical Solution

The unauthenticated GitHub REST API enforces a rate limit of 60 requests per hour, leading to `403 Rate Limit Exceeded` errors when auditing multiple repositories.

This tool resolves API limits through two operational modes:
1. **API Mode (With Key):** Passing a Personal Access Token via CLI flag or environment variable switches to official API endpoints, increasing the limit to 5,000 requests/hour.
2. **Scraping Mode (Keyless):** Parses the public HTML profile and fetches release information via public Atom feeds (`/releases.atom`), bypassing API quota limits.

---

<a name="prerequisites-en"></a>
## Prerequisites

- **Python:** Version 3.10 or higher.
- **Package Manager:** `uv` (Recommended) or `pip`.

---

<a name="installation-en"></a>
## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/alberto2005-coder/ver-github-pages.git
   cd ver-github-pages
   ```

2. Install the required dependencies:

   - **Using `uv` (Recommended):**
     ```bash
     uv sync
     ```

   - **Using `pip`:**
     ```bash
     pip install -r requirements.txt
     ```

---

<a name="cli-usage-en"></a>
## CLI Usage

All configuration options can be supplied directly through the command line without requiring a `.env` file.

### Example 1: Basic execution (Keyless)
```bash
uv run ver-github-pages -u alberto2005-coder
```

### Example 2: Passing custom domain and API key/token
```bash
uv run ver-github-pages -u alberto2005-coder -w https://albertoortiz.is-a.dev -k ghp_your_token_here
```

### Example 3: Force web scraping mode and set custom output path
```bash
uv run ver-github-pages -u alberto2005-coder --no-api -o my_report.txt
```

### CLI Flags Reference

| Flag | Alternative | Description | Required |
| :--- | :--- | :--- | :--- |
| `-u` | `--usuario` / `--user` | GitHub username | **Yes** |
| `-w` | `--web` / `--dominio` | Base domain for GitHub Pages | No (default: `https://<user>.github.io`) |
| `-k` | `--key` / `--token` | GitHub Personal Access Token | No |
| `-o` | `--output` | Output `.txt` report file path | No (default: `paginas_github.txt`) |
| `--no-api` | - | Force web scraping mode ignoring API Key | No |
| `--no-color` | - | Disable colorized console output | No |

---

<a name="configuration-precedence-en"></a>
## Configuration Precedence

Configurations are resolved in the following priority order:
1. **Command-line flags** (e.g., `-u`, `-w`, `-k`).
2. **`.env` file variables** (if present in the root directory).
3. **Built-in default values**.

---

<a name="automated-tests-en"></a>
## Automated Tests

The repository includes a suite of unit tests powered by `pytest` that mock HTTP responses to validate logic without consuming GitHub quotas:

```bash
uv run pytest
```

---

<a name="project-structure-en"></a>
## Project Structure

```text
ver-github-pages/
├── .env.example          # Environment variables template
├── .gitignore            # Files excluded from version control
├── LICENSE               # Project license
├── README.md             # Unified documentation (Spanish / English)
├── pyproject.toml        # Package configuration and dependencies
├── requirements.txt      # Dependencies file for pip
├── src/
│   └── ver_github_pages/
│       ├── __init__.py
│       ├── __main__.py
│       ├── audit.py       # Audit orchestrator
│       ├── config.py      # CLI arguments and environment parser
│       ├── github_api.py  # Data provider via GitHub REST API
│       ├── github_web.py  # Data provider via web scraping
│       ├── http.py        # HTTP client with retry logic
│       ├── main.py        # CLI entrypoint
│       ├── models.py      # Data structures
│       ├── pages.py       # GitHub Pages URL verification
│       └── report.py     # Console (Rich) and text report renderer
└── tests/                # Automated unit tests
    ├── conftest.py
    ├── test_config.py
    ├── test_github_api.py
    ├── test_github_web.py
    ├── test_pages.py
    └── test_report.py
```

---

<a name="license-en"></a>
## License

Distributed under the MIT License. See [LICENSE](LICENSE) for more information.