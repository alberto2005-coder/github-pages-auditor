# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/). / Format based on Keep a Changelog.

## [1.6.0] - 2026-11-18

### Añadido / Added
- **`--crawl`:** rastrea hasta 10 páginas internas de cada web y valida el `sitemap.xml` (avisos informativos `paginas-internas-rotas`, `sitemap-invalido`, `sitemap-urls-rotas`; campo JSON `pages.broken_pages`). / Crawls up to 10 internal pages and validates the sitemap.
- **Reglas propias con contenido:** `type = "content-required"` o `"content-forbidden"` con `contains` o `regex` en `[[custom_rules]]`. / Custom rules that check file contents.
- **`--readme-quality`:** regla `weak-readme` (README sin instalación, sin uso o demasiado corto; campo `readme_issues`). / README quality rule.
- **`--dep-licenses`:** regla `copyleft-dependency` (dependencias GPL/AGPL en `pyproject.toml`, `requirements.txt` y `package.json`, consultando PyPI y npm; campo `copyleft_dependencies`). / Copyleft dependency rule.
- **`--init`:** crea un `.github-pages-auditor.toml` de partida sin secretos (con `--yes` lo sobrescribe). / Starter config file.
- **`--fix-only REGLAS`** (solo esas reglas de archivos; implica `--fix`) y **`--fix-log ARCHIVO`** (JSON de lo planeado o aplicado). / Selective fixes and a fix log.
- **`-u a,b`:** varias cuentas en un solo informe, con los repos como `cuenta/repo` (no con `--org` ni `--fix*`). / Several accounts in one report.
- **`--graphql` (experimental):** lista la raíz de los repos con GraphQL en lotes de 20; si algo falla, usa REST como siempre. / Experimental batched root listing.
- **Caché ETag mejorada:** al terminar muestra cuántas peticiones no gastaron cuota (`💾 Caché: N de M`), `--cache-clear` la borra (solo sus archivos) y las entradas sin usar en 30 días se eliminan solas. / ETag cache stats, `--cache-clear` and automatic pruning.
- **Avisos por webhook mejorados:** formato para Microsoft Teams, `--notify-on always` (resumen también cuando no hay nada nuevo), un reintento si el servicio responde 429 o 5xx y `--notify-test` para probar el webhook sin auditar. / Teams format, `--notify-on always`, one retry and `--notify-test`.
- **Licencia en PyPI:** se añade el clasificador `License :: OSI Approved :: MIT License` junto a `license = "MIT"`, para que herramientas que no leen el campo moderno también la vean. / Added the MIT license classifier for tools that ignore the PEP 639 field.

### Cambiado / Changed
- `schema_version` sigue en 1: solo se añaden campos (`pages.broken_pages`, `readme_issues`, `copyleft_dependencies`; `user` puede ser `a+b` con varias cuentas). / `schema_version` is still 1: additive only.
- Las reglas nuevas son opcionales y no puntúan, así la nota sigue siendo comparable con la de la 1.5.x. / The new rules are opt-in and do not affect the score.

### Sin probar contra GitHub real / Not validated against the real API
- `--graphql`, `--dep-licenses` y `--readme-quality` se han probado con respuestas simuladas; si algo falla en tu cuenta, abre un issue. / Tested with simulated responses only.

## [1.5.0] - 2026-11-16

### Añadido / Added

- **Archivos heredados de `<usuario>/.github`:** SECURITY, CONTRIBUTING, CODE_OF_CONDUCT e issue templates que un repo no tiene pero hereda de tu repositorio `.github` cuentan como presentes (ya no salen `missing-*` ni los duplica `--fix`). Nuevo campo JSON `inherited_files` y opción `--no-defaults-repo`. / Community files inherited from your `.github` repo now count as present; new `inherited_files` JSON key and `--no-defaults-repo`.
- **`--doctor`:** diagnostica el token (tipo, caducidad, límite de peticiones y permisos de lectura de contenido, Pages, Actions, alertas y protección de ramas). / Token diagnosis.
- **Pages «construyendo»:** si GitHub está reconstruyendo las Pages, la web ya no se marca como rota (`status: construyendo`). / Pages being rebuilt are no longer reported as broken.
- **Protección de secretos:** tokens y webhooks se ocultan en cualquier mensaje; aviso si el token va en la línea de comandos o si `.env` está en el repo git. / Secret masking and warnings.
- **API más fiable:** espera y reintenta una vez si el límite se restablece en menos de un minuto, el error indica a qué hora se restablece, y `--cache auto` usa la carpeta de caché del usuario. / Rate-limit wait and `--cache auto`.
- **`--fix-mode pr`:** una rama y una Pull Request por repo en lugar de un commit en la rama principal. / Fixes via Pull Request.
- **`--fix-extra` y `--license`:** `LICENSE` (mit, bsd-3-clause, isc, unlicense), `.gitignore`, `.github/dependabot.yml` y CI básico según el lenguaje. / More fix templates.
- **Pages (SEO):** avisos `sin-title`, `sin-viewport`, `sin-og-title`, `sin-canonical` y `contenido-mixto`; no bajan la nota. / New informational SEO warnings.
- **Reglas propias** en el TOML (`[[custom_rules]]`, ids `custom-*`, `file-required` o `file-forbidden`). / Custom rules.
- **`--scorecard`** (OpenSSF Scorecard, regla `low-scorecard`) y regla `critical-vulnerabilities` (`--deep`: alertas de Dependabot críticas o altas). / Scorecard and vulnerability severity.
- **`-f trend`** (gráfica de la nota con `--history`), **`-f issue`** (resumen en Markdown), **`--diff ANTES.json DESPUES.json`** y la Action con `issue: true`. / Trend chart, issue summary, `--diff`, Action issue.

### Cambiado / Changed
- Descubribilidad: el README abre con una descripción clara (ES/EN) y preguntas frecuentes; PyPI con más `keywords`, clasificadores y enlaces (`Documentation`, `Changelog`, `JSON schema`, `CI recipes`). / Clearer README intro, FAQ and richer PyPI metadata.
- `schema_version` sigue en 1: solo se añaden campos (`scorecard`, `custom`, `deep.critical_alerts`, `deep.high_alerts`). / `schema_version` is still 1: additive only.
- `--fix-extra` activa `--deep` porque necesita saber qué falta (CI y Dependabot). / `--fix-extra` turns on `--deep`.
- Los avisos de SEO nuevos no puntúan, así la nota sigue siendo comparable con la de la 1.4.0. / New SEO warnings do not affect the score.

### No incluido / Not included
- GraphQL para acelerar la auditoría: no se ha podido validar contra la API real y queda para una versión posterior. / GraphQL is left for a later release.

## [1.4.0] - 2026-11-15

### Corregido / Fixed
- `--lang en` traduce también el proveedor y la barra de progreso; un 403 en `--fix` explica que falta permiso de escritura en el token. / `--lang en` fully translated; clearer 403 hint.

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
