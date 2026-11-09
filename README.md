# GitHub Profile & Pages Auditor

[Español](#español) | [English](#english)

---

<a name="español"></a>
# Español

Una herramienta de línea de comandos en Python diseñada para auditar repositorios de GitHub. Permite mapear enlaces de GitHub Pages con dominio personalizado, verificar lanzamientos y evaluar la calidad de la documentación (README, Licencia, `.gitignore` y descripción) sin sufrir restricciones de tasa de peticiones en la API (Error 403 HTTP) gracias a procesamiento en paralelo y feeds públicos.

## Índice

1. [Características](#características-es)
2. [Arquitectura y Solución Técnica](#arquitectura-y-solución-técnica-es)
3. [Requisitos Previos](#requisitos-previos-es)
4. [Instalación](#instalación-es)
5. [Configuración](#configuración-es)
6. [Uso](#uso-es)
7. [Estructura del Proyecto](#estructura-del-proyecto-es)
8. [Estructura del Reporte](#estructura-del-reporte-es)
9. [Licencia](#licencia-es)

---

<a name="características-es"></a>
## Características

- **Mapeo de GitHub Pages:** Asigna automáticamente el dominio raíz o la subruta correspondiente según el repositorio.
- **Detección de Releases:** Identifica lanzamientos publicados sin consumir cuota de la API REST.
- **Auditoría de Calidad:**
  - Repositorios sin archivo `README`
  - Repositorios sin archivo de `Licencia`
  - Repositorios sin `.gitignore`
  - Repositorios sin Descripción (About)
- **Clasificación:** Identifica repositorios que son *Forks* o que están *Archivados*.
- **Rendimiento:** Ejecución multihilo optimizada mediante `ThreadPoolExecutor`.
- **Portabilidad:** Gestión de variables de entorno con archivo `.env`.

---

<a name="arquitectura-y-solución-técnica-es"></a>
## Arquitectura y Solución Técnica

La API pública REST de GitHub impone un límite estricto de 60 peticiones/hora para usuarios no autenticados. Al auditar múltiples repositorios, este límite provoca errores `403 Rate Limit Exceeded`.

Esta herramienta soluciona dicha limitación mediante las siguientes técnicas:
- **Navegación Web Directa:** Obtiene la lista completa de repositorios consultando el perfil público HTML de GitHub.
- **Atom Feeds:** Consulta la presencia de versiones o lanzamientos a través de feeds Atom públicos (`/releases.atom`), los cuales no consumen la cuota de la API REST.
- **Verificación Multihilo:** Utiliza `concurrent.futures.ThreadPoolExecutor` para procesar el análisis de repositorios en paralelo, reduciendo el tiempo de ejecución a pocos segundos.

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

<a name="configuración-es"></a>
## Configuración

Crea un archivo llamado `.env` en la raíz del proyecto. Puedes guiarte del siguiente modelo:

```env
USUARIO_GITHUB=alberto2005-coder
DOMINIO_WEB=https://albertoortiz.is-a.dev
ARCHIVO_SALIDA=paginas_github.txt
```

### Parámetros de configuración

| Variable | Descripción | Ejemplo |
| :--- | :--- | :--- |
| `USUARIO_GITHUB` | Nombre de usuario exacto en GitHub | `alberto2005-coder` |
| `DOMINIO_WEB` | Dominio personalizado o base de despliegue | `https://albertoortiz.is-a.dev` |
| `ARCHIVO_SALIDA` | Nombre del archivo `.txt` donde se guardará el informe | `paginas_github.txt` |

---

<a name="uso-es"></a>
## Uso

Para ejecutar el análisis, corre el script principal según el gestor que utilices:

- **Con `uv`:**
  ```bash
  uv run main.py
  ```

- **Con `python`:**
  ```bash
  python main.py
  ```

---

<a name="estructura-del-proyecto-es"></a>
## Estructura del Proyecto

```text
ver-github-pages/
├── .env                  # Variables de entorno local
├── .env.example          # Plantilla de variables de entorno
├── .gitignore            # Archivos excluidos del control de versiones
├── LICENSE               # Licencia del proyecto
├── README.md             # Documentación unificada (Español / Inglés)
├── main.py               # Script principal de ejecución
└── requirements.txt      # Archivo de dependencias
```

---

<a name="estructura-del-reporte-es"></a>
## Estructura del Reporte

Al finalizar el análisis, la herramienta genera un archivo `.txt` detallado:

```text
=== ENLACES DE GITHUB PAGES PARA: usuario ===
Dominio base: https://dominio.dev

- repositorio-demo               -> https://dominio.dev/repositorio-demo/

=== REPOSITORIOS CON RELEASES ===
- repositorio-demo

=== REPOSITORIOS SIN RELEASES NI GITHUB PAGES ===
- otro-proyecto

=== REPOSITORIOS SIN README ===
- proyecto-sin-readme

=== REPOSITORIOS SIN LICENCIA ===
- proyecto-sin-licencia

=== REPOSITORIOS SIN .GITIGNORE ===
- proyecto-sin-gitignore

=== REPOSITORIOS SIN DESCRIPCIÓN (ABOUT) ===
- proyecto-sin-descripcion
```

---

<a name="licencia-es"></a>
## Licencia

Este proyecto se distribuye bajo la Licencia MIT. Consulta el archivo [LICENSE](LICENSE) para obtener más información.

---

<a name="english"></a>
# English

A Python CLI tool designed to audit GitHub repositories. It maps GitHub Pages URLs with custom domains, verifies published releases, and checks documentation quality (README, License, `.gitignore`, and description) — without hitting API rate limits (Error 403 HTTP) by leveraging parallel processing and public feeds.

## Table of Contents

1. [Features](#features-en)
2. [Architecture and Technical Solution](#architecture-and-technical-solution-en)
3. [Prerequisites](#prerequisites-en)
4. [Installation](#installation-en)
5. [Configuration](#configuration-en)
6. [Usage](#usage-en)
7. [Project Structure](#project-structure-en)
8. [Report Structure](#report-structure-en)
9. [License](#license-en)

---

<a name="features-en"></a>
## Features

- **GitHub Pages Mapping:** Automatically assigns root domains or project subpaths based on repository naming.
- **Release Tracking:** Detects published releases without consuming REST API quotas.
- **Quality Audit:**
  - Repositories missing a `README` file
  - Repositories missing a `License` file
  - Repositories missing `.gitignore`
  - Repositories missing About/Description
- **Categorization:** Flags repositories that are *Forks* or *Archived*.
- **Performance:** Optimized multi-threaded execution using `ThreadPoolExecutor`.
- **Portability:** Environment variable management via `.env` file.

---

<a name="architecture-and-technical-solution-en"></a>
## Architecture and Technical Solution

The GitHub REST API enforces a strict rate limit of 60 requests per hour for unauthenticated users. When auditing multiple repositories, this constraint leads to `403 Rate Limit Exceeded` errors.

This tool bypasses API restrictions through the following techniques:
- **Direct Web Navigation:** Fetches the repository list from the user's public GitHub profile HTML.
- **Atom Feeds:** Checks for published releases using public Atom feeds (`/releases.atom`), which do not affect REST API quotas.
- **Multi-threaded Verification:** Employs `concurrent.futures.ThreadPoolExecutor` to process repository checks in parallel, completing execution in seconds.

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

2. Install dependencies:

   - **Using `uv` (Recommended):**
     ```bash
     uv sync
     ```

   - **Using `pip`:**
     ```bash
     pip install -r requirements.txt
     ```

---

<a name="configuration-en"></a>
## Configuration

Create a file named `.env` in the root directory:

```env
USUARIO_GITHUB=alberto2005-coder
DOMINIO_WEB=https://albertoortiz.is-a.dev
ARCHIVO_SALIDA=paginas_github.txt
```

### Configuration Parameters

| Variable | Description | Example |
| :--- | :--- | :--- |
| `USUARIO_GITHUB` | Exact GitHub username | `alberto2005-coder` |
| `DOMINIO_WEB` | Custom domain or base deployment URL | `https://albertoortiz.is-a.dev` |
| `ARCHIVO_SALIDA` | Output `.txt` filename for the report | `paginas_github.txt` |

---

<a name="usage-en"></a>
## Usage

Run the main script using your preferred tool:

- **Using `uv`:**
  ```bash
  uv run main.py
  ```

- **Using `python`:**
  ```bash
  python main.py
  ```

---

<a name="project-structure-en"></a>
## Project Structure

```text
ver-github-pages/
├── .env                  # Local environment variables
├── .env.example          # Environment variables template
├── .gitignore            # Files excluded from version control
├── LICENSE               # Project license
├── README.md             # Unified documentation (Spanish / English)
├── main.py               # Main execution script
└── requirements.txt      # Dependencies file
```

---

<a name="report-structure-en"></a>
## Report Structure

After completion, the tool outputs a formatted `.txt` report:

```text
=== ENLACES DE GITHUB PAGES PARA: username ===
Dominio base: https://domain.dev

- demo-repository               -> https://domain.dev/demo-repository/

=== REPOSITORIOS CON RELEASES ===
- demo-repository

=== REPOSITORIOS SIN RELEASES NI GITHUB PAGES ===
- other-project

=== REPOSITORIOS SIN README ===
- project-without-readme

=== REPOSITORIOS SIN LICENCIA ===
- project-without-license

=== REPOSITORIOS SIN .GITIGNORE ===
- project-without-gitignore

=== REPOSITORIOS SIN DESCRIPCIÓN (ABOUT) ===
- project-without-description
```

---

<a name="license-en"></a>
## License

Distributed under the MIT License. See [LICENSE](LICENSE) for more information.