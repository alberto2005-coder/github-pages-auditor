# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/). / Format based on Keep a Changelog.

## [1.1.0] - 2026-11-11

### Añadido / Added
- Créditos del autor (Alberto Ortiz · https://github.com/alberto2005-coder/ · https://albertoortiz.is-a.dev/) en `--help`, `--version`, la consola y el informe `.txt`. / Author credits.
- `--version/-V`, `--timeout`, `--no-env`; `python -m ver_github_pages`. / New flags and module entry point.
- Códigos de salida documentados (0, 1, 2, 130). / Documented exit codes.
- Sección de informe «Repositorios no analizados» para fallos de red por repo. / Per-repo failure section.
- Suite de tests ampliada (65 tests) y CI en Linux/macOS/Windows con Python 3.10 y 3.13. / Larger test suite and CI matrix.
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

## [1.0.0]
- Primera versión estable: CLI con parámetros, API opcional, scraping de respaldo, tests y README bilingüe. / First stable release.
