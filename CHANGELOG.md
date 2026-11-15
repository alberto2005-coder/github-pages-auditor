# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/). / Format based on Keep a Changelog.

## [1.4.0] - 2026-11-15

### Añadido / Added
- **Nota de salud 0-100** por repo y global (`score`, `grade`; básicos 30, release 10, comunidad 30, actividad 20, seguridad 10; sin datos no cuenta), `--min-score N` y resumen de mejores y peores repos. / Health score, `--min-score`, best/worst ranking.
- **Histórico:** `--history CARPETA` guarda cada informe y lo compara con el anterior (mejoras y empeoramientos). / History and comparison.
- **Salidas nuevas:** `-f html` (página autocontenida, ordenable y filtrable), `-f csv`, `-f sarif` (2.1.0), `-f badge` (insignia SVG) y `--notify-webhook` (Discord, Slack o JSON; solo si hay hallazgos nuevos). / New formats and webhook.
- **`--lang en`** (consola, txt, html, md, anotaciones). / English output.
- **`--deep`** (API): Dependabot, secret scanning, rama protegida, CI y su último estado, contribuidores y PRs abiertas; reglas `missing-ci`, `missing-dependabot`, `failing-ci`, `stale-prs`, `no-branch-protection`. `--org` y `--include-private`. / Deep data and rules; orgs and private repos.
- **Pages a fondo:** `sitemap.xml`, `robots.txt`, favicon, `lang`, imágenes sin `alt`, página pesada, DNS del dominio propio y `--check-links` (enlaces rotos, máx. 50 por web). / Deeper Pages checks.
- **Arreglos opt-in:** `--fix` (SECURITY, CONTRIBUTING, CODE_OF_CONDUCT y plantilla de issues desde plantillas del paquete), `--fix-pages` (Enforce HTTPS), `--fix-metadata` (descripción y topics), `--dry-run` y `--yes`. Por defecto solo se planea. / Opt-in fixes.
- `--tui` (extra `[tui]`), `--cache CARPETA` (ETag), `--since 30d|FECHA`. / TUI, ETag cache, `--since`.
- CI: `mypy`, cobertura mínima del 85 %, job `live` manual contra la API real y atestaciones de PyPI. Plantilla de fórmula de Homebrew y guía de `pipx`. / CI and packaging.

### Cambiado / Changed
- La publicación en PyPI usa `pypa/gh-action-pypi-publish` con atestaciones. / PyPI publishing with attestations.
- `schema_version` sigue en 1: solo se añaden campos. / `schema_version` is still 1: additive only.

## [1.3.0] - 2026-11-14

### Añadido / Added
- **Datos por repo** (modo API; la release también en modo web): estrellas, forks, issues abiertas, lenguaje, topics, licencia SPDX, fechas, Website y última release. Nuevos campos del JSON (`schema_version` sigue en 1; solo se añaden campos). `--details` los muestra en consola, `txt` y `md`; `--sort listing|name|stars|updated`. / Per-repo data, additive JSON fields, `--details`, `--sort`.
- **Reglas de comunidad** para `--fail-on`: `missing-security-policy`, `missing-contributing`, `missing-code-of-conduct`, `missing-issue-template`, `missing-topics`, `missing-homepage`, `stale-repo` (`--stale-months`, def. 12). Grupos `community` y `all`; `any` mantiene su significado anterior. / Community rules and groups.
- **Pages en profundidad:** aviso si el certificado TLS caduca en menos de 14 días (`pages.tls_days_left`), sin `404.html`, sin meta description, sin `og:image` y Website distinto de la demo. Solo avisos: no rompen el informe. / Deeper Pages checks (warnings only).
- **Configuración:** archivo `.github-pages-auditor.toml` (`--config`, `--no-config`; nunca admite el token), `--ignore`, `--only` (patrones `*`/`?`), `--baseline INFORME.json` (`--fail-on` solo por hallazgos nuevos) y `-f github` (anotaciones de GitHub Actions). / Config file, filters, baseline, Actions annotations.
- `action.yml`: Action reutilizable. `ruff` en CI y job que audita el propio repositorio. SECURITY, CONTRIBUTING, CODE_OF_CONDUCT y plantillas de issues. / Reusable Action, ruff, self-audit, community files.
- Dependencia `tomli` solo en Python 3.10. / `tomli` only on Python 3.10.

## [1.2.1] - 2026-11-13

### Añadido / Added
- Soporte y pruebas en CI para Python 3.14. / Python 3.14 support and CI.
- Documentación: contrato del JSON (`docs/json-schema.md`) y recetas de CI (`docs/ci.md`: fallar el job, resumen en `$GITHUB_STEP_SUMMARY`, refresco semanal del README). / JSON contract and CI recipes.
- Badges (PyPI, Python, tests, licencia) en el README. / README badges.
- Tests de extremo a extremo (CLI -> auditoría -> API simulada) que automatizan las pruebas manuales de filtros, Pages rotas, robustez y `.env`, y tests de higiene de release (versión, CHANGELOG, `uv.lock`, metadatos). / End-to-end and release-hygiene tests.

### Cambiado / Changed
- Los ejemplos del README pasan el token por variable de entorno y usan tokens `github_pat_…` (fine-grained). / README examples pass the token via environment variable.
- Los metadatos del paquete ya no incluyen el correo del autor. / The author email is no longer in the package metadata.

## [1.2.0] - 2026-11-12

### Añadido / Added
- `-f/--format json|md|txt`: JSON con contrato versionado (`schema_version: 1`) y tabla Markdown de demos en vivo. / Versioned JSON and Markdown demos table.
- `-o -` escribe el informe en stdout y la interfaz en stderr (apto para `| jq`). / Report to stdout, UI to stderr.
- `--fail-on <reglas|any>` para CI: `missing-readme`, `missing-license`, `missing-gitignore`, `missing-description`, `broken-pages`, `analysis-errors`. / CI gating.
- `--inject ARCHIVO`: actualiza la tabla de demos dentro de tu README entre marcadores. / In-place README update.
- Salud de Pages: 404/sin index, TLS, timeouts, redirecciones externas o en bucle, página vacía/sin HTML y lentitud; con token, también build fallido y HTTPS no forzado. / Pages health checks.
- `--exclude-forks`, `--exclude-archived`, `-q/--quiet`.
- Con token, si la API devuelve una URL `http://` (HTTPS no forzado) se prefiere la `https://` cuando responde bien; nueva sección «Pages con avisos» en consola e informe. / Prefer https URLs; new warnings section.
- Workflow de publicación en PyPI con Trusted Publishing; `uvx github-pages-auditor`. / PyPI publishing.

### Cambiado / Changed
- **Renombrado:** el proyecto pasa a llamarse `github-pages-auditor` (paquete de PyPI, comando y módulo `github_pages_auditor`), igual que el repositorio. `ver-github-pages` se mantiene como alias del comando. / Project renamed to `github-pages-auditor`; the old command remains as an alias.
- **Códigos de salida:** `1` pasa a significar «`--fail-on` disparado» y «sin repositorios» pasa a `3` (`0` ok, `2` error y `130` Ctrl+C no cambian). / Exit codes changed.
- Las Pages que fallan ya no cuentan como «activas»; se listan como «rotas» cuando se sabe que estaban activadas. / Broken Pages are no longer counted as live.
- Enlaces del repositorio corregidos a `github-pages-auditor`. / Repository URLs fixed.

## [1.1.0] - 2026-11-11

### Añadido / Added
- Créditos del autor (Alberto Ortiz · https://github.com/alberto2005-coder/ · https://albertoortiz.is-a.dev/) en `--help`, `--version`, la consola y el informe `.txt`. / Author credits.
- `--version/-V`, `--timeout`, `--no-env`; `python -m github_pages_auditor`. / New flags and module entry point.
- Códigos de salida documentados (0, 1, 2, 130). / Documented exit codes.
- Sección de informe «Repositorios no analizados» para fallos de red por repo. / Per-repo failure section.
- Suite de tests ampliada (73 tests) y CI en Linux/macOS/Windows con Python 3.10 y 3.13. / Larger test suite and CI matrix.
- `CHANGELOG.md` y `requirements-dev.txt`.

### Corregido / Fixed
- **Seguridad:** el token ya no se envía a `github.com`, `raw.githubusercontent.com` ni al dominio del usuario; solo a `api.github.com`. / Token no longer leaks to non-API hosts.
- Timeout real en todas las peticiones (antes el listado podía colgarse). / Real default timeout.
- Errores explícitos en lugar de «sin repositorios»: usuario inexistente, token inválido (401), límite de tasa (403/429), errores de red. / Explicit errors instead of an empty result.
- Los reintentos agotados ya no producen un traceback (`raise_on_status=False`). / No traceback on exhausted retries.
- Informe determinista: se conserva el orden del listado. / Deterministic ordering.
- La comprobación de Pages se hace en paralelo y verifica que no haya redirección a otro dominio. / Parallel, redirect-aware Pages check.
- Un repo llamado igual que el usuario ya no se trata como sitio raíz de Pages (solo `<usuario>.github.io`). / Profile-README repo is not a Pages root.
- Detección de README, licencia y `.gitignore` más fiable (API: contenido raíz; web: archivos `raw` con varias variantes). / More reliable file detection.
- Descripción, fork y archivado en modo web se leen del listado; si no se pueden determinar no se listan como faltantes. / Unknown ≠ missing.
- `.env` opcional ahora se busca en el directorio actual también con el paquete instalado; las variables vacías se ignoran. / `.env` discovery and empty values.
- `.env.example` con valores vacíos (los marcadores de posición provocaban fallos silenciosos). / Blank template.
- `pytest` movido de dependencias de ejecución al grupo `dev`. / pytest is a dev-only dependency.
- No se escribe informe cuando no hay repositorios. / No report for empty results.
- Sin `-w`, las Pages con dominio personalizado se detectaban como inexistentes (GitHub redirige desde `github.io`); ahora se sigue la redirección y se muestra el dominio real. Con API se usa la `html_url` real. / Custom-domain Pages are detected without `-w`.
- La carpeta de salida se valida antes de auditar (antes fallaba al final, tras todo el análisis). / Output folder validated up front.
- Aviso de `uv` por el classifier de licencia obsoleto: ahora `license = "MIT"` (SPDX). / SPDX license expression.

## [1.0.0]
- Primera versión estable: CLI con parámetros, API opcional, scraping de respaldo, tests y README bilingüe. / First stable release.
