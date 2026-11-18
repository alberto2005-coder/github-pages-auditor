# Contrato JSON / JSON contract

`github-pages-auditor -f json` (o `-f json -o -` para la salida estándar) escribe un objeto con `schema_version: 1`.
Los campos existentes **no cambian de nombre ni de tipo** dentro de la versión 1; se pueden añadir campos nuevos.

`github-pages-auditor -f json` (or `-f json -o -` for stdout) writes an object with `schema_version: 1`.
Existing fields are **never renamed or retyped** within version 1; new fields may be added.

Con `-o -` el JSON sale en ASCII puro (los acentos y emojis van como `\uXXXX`), así que funciona en cualquier consola.
With `-o -` the JSON is pure ASCII (accents and emojis are `\uXXXX` escapes), so it works on any console.

## Nivel superior / Top level

| Campo / Field | Tipo / Type | Descripción / Description |
| --- | --- | --- |
| `schema_version` | int | Versión del contrato / contract version (`1`) |
| `tool` | object | `name`, `version`, `url` |
| `generated_at` | string | UTC, ISO 8601 (`2026-11-13T10:00:00Z`) |
| `user` | string | Usuario auditado / audited user |
| `mode` | string | `api` o/or `web` |
| `domain` | string | Dominio base de las Pages / Pages base domain |
| `summary` | object | Contadores / counters (ver abajo / see below) |
| `findings` | object | Una lista de repos por regla (vacía si no hay hallazgos) / one repo list per rule |
| `fail_on` | object | `rules` (pedidas / requested) y `triggered` (disparadas / triggered) |
| `repos` | array | Un objeto por repositorio / one object per repository |
| `ranking` | object | `best` y `worst`: hasta 3 repos propios con `name` y `score` / best and worst repos |
| `history` | object \| null | Solo con `--history` y un informe previo: `previous_file`, `previous_generated_at`, `score_before`, `score_after`, `delta`, `improved`, `worsened`, `new_repos`, `removed_repos` |
| `fixes` | array \| null | Solo con `--fix*`: `repo`, `action`, `target`, `status` (`planned`, `applied`, `skipped`, `failed`) y `detail` |
| `baseline` | object \| null | Solo con `--baseline`: `file` y `new_findings` (hallazgos nuevos por regla) / only with `--baseline` |

## `summary`

`total`, `analyzed`, `pages_live`, `pages_broken`, `releases`, `no_pages_no_releases`, `missing_readme`,
`missing_license`, `missing_gitignore`, `missing_description`, `forks`, `archived`, `errors`, `score` (nota global 0-100 o `null`) y `grade` (`A`-`E`).

La nota pondera básicos 30, release 10, comunidad 30, actividad 20 y seguridad 10; una categoría sin datos (p. ej. comunidad en modo web) no cuenta y las demás se reescalan. La global ignora forks y archivados.
Weights: basics 30, release 10, community 30, activity 20, security 10; a category without data is dropped and the rest rescaled. The overall score ignores forks and archived repos.

## `findings`

Claves = reglas de `--fail-on` / keys = `--fail-on` rules: `missing-readme`, `missing-license`, `missing-gitignore`,
`missing-description`, `broken-pages`, `analysis-errors` y, desde 1.3.0, las reglas de comunidad `missing-security-policy`,
`missing-contributing`, `missing-code-of-conduct`, `missing-issue-template`, `missing-topics`, `missing-homepage` y `stale-repo`
(solo modo API; no aplican a forks ni archivados) y, con `--deep`, `missing-ci`, `missing-dependabot`, `failing-ci`, `stale-prs` y `no-branch-protection`. Desde 1.5.0: `critical-vulnerabilities` (con `--deep`, alertas de Dependabot críticas o altas abiertas), `weak-readme` (con `--readme-quality`) y `copyleft-dependency` (con `--dep-licenses`) desde 1.6.0, `low-scorecard` (con `--scorecard`, nota de OpenSSF Scorecard < 4) y las reglas propias `custom-*` definidas en el TOML. `--min-score` añade `min-score` a `fail_on.triggered`. Cada valor es una lista de nombres de repositorio.
Each value is a list of repository names.

## `repos[]`

| Campo / Field | Tipo / Type | Descripción / Description |
| --- | --- | --- |
| `name` | string | Nombre del repo / repo name |
| `description` | string \| null | Descripción (About) / About text |
| `fork`, `archived` | bool | |
| `has_pages` | bool | Pages activadas (modo API) o detectadas (modo web) / enabled (API) or detected (web) |
| `pages` | object \| null | Salud de la web (ver abajo); `null` si no hay Pages / site health; `null` if no Pages |
| `pages_url` | string \| null | URL final de la demo / final demo URL |
| `has_releases`, `has_readme`, `has_license`, `has_gitignore` | bool | |
| `has_description` | bool \| null | `null` si no se pudo saber / `null` if unknown |
| `stars`, `forks`, `open_issues` | int \| null | Contadores del repo (modo API) / repo counters (API mode) |
| `language`, `license` | string \| null | Lenguaje principal y licencia SPDX (`MIT`) / main language and SPDX license |
| `topics` | array \| null | Topics del repo / repo topics |
| `created_at`, `pushed_at` | string \| null | Fechas ISO 8601 / ISO 8601 dates |
| `homepage` | string \| null | Campo Website del repo / repo Website field |
| `latest_release` | object \| null | `tag` y `date` de la última release / latest release tag and date |
| `community` | object | `security_policy`, `contributing`, `code_of_conduct`, `issue_template`: bool o `null` si se desconoce / bool or `null` if unknown |
| `score` | int \| null | Nota 0-100 del repo / repo score |
| `grade` | string \| null | `A` (≥ 90), `B` (≥ 75), `C` (≥ 60), `D` (≥ 40) o `E` |
| `private` | bool \| null | Repo privado (modo API) / private repo |
| `default_branch` | string \| null | Rama principal / default branch |
| `deep` | object | Con `--deep`: `ci`, `ci_status`, `dependabot_yml`, `dependabot_alerts`, `secret_scanning`, `branch_protected`, `contributors`, `open_prs`, y desde 1.5.0 `critical_alerts` y `high_alerts` (alertas abiertas de Dependabot por gravedad) (`null` = sin dato o sin permisos) |
| `scorecard` | number \| null | Desde 1.5.0, con `--scorecard`: nota 0-10 de OpenSSF Scorecard / OpenSSF Scorecard score |
| `readme_issues` | Desde 1.6.0, con `--readme-quality`: `readme-corto`, `sin-instalacion`, `sin-uso`; `null` si no se comprobó / since 1.6.0, with `--readme-quality`; `null` if not checked |
| `copyleft_dependencies` | Desde 1.6.0, con `--dep-licenses`: dependencias GPL/AGPL como `"nombre (licencia)"`; `null` si no se comprobó / since 1.6.0, with `--dep-licenses`; `null` if not checked |
| `inherited_files` | array \| null | Desde 1.5.0: ficheros de comunidad (`security`, `contributing`, `code_of_conduct`, `issue_template`) que el repo no tiene pero hereda de `<usuario>/.github`; cuentan como presentes / community files inherited from `<user>/.github`; they count as present |
| `custom` | object \| null | Desde 1.5.0: por cada regla propia (`id`), `true` si la ruta existe en el repo, `false` si no; `null` si no se comprobó (modo web) / per custom rule, whether the path exists |
| `error` | string \| null | Motivo si el repo no se pudo analizar / why the repo could not be analyzed |

### `repos[].pages`

| Campo / Field | Descripción / Description |
| --- | --- |
| `status` | `ok`, `roto` (Pages activadas pero fallan / enabled but failing), `construyendo` (desde 1.5.0: GitHub las está reconstruyendo y la web falla un momento / being rebuilt) o `ninguna` (no hay web / no site) |
| `url` | URL final / final URL |
| `http_status` | Código HTTP o `null` / HTTP status or `null` |
| `response_ms` | Tiempo de respuesta en ms / response time in ms |
| `title` | `<title>` de la página / page `<title>` |
| `problems` | Lista de problemas (hacen que `status` sea `roto`) / problems (make `status` = `roto`): `404`, `http-<código>`, `tls-error`, `timeout`, `sin-conexion`, `redireccion-externa`, `demasiadas-redirecciones`, `cuerpo-vacio`, `build-fallido` |
| `broken_links` | Con `--check-links`: lista de `"url (código)"`; `null` si no se comprobó / broken links; `null` if not checked |
| `broken_pages` | Desde 1.6.0, con `--crawl`: páginas internas enlazadas desde la portada que no responden (`"url (código)"`); `null` si no se comprobó / since 1.6.0, with `--crawl`: broken internal pages; `null` if not checked |
| `size_bytes` | `Content-Length` de la portada o `null` / front page size or `null` |
| `tls_days_left` | Días hasta que caduca el certificado TLS o `null` / days until the TLS certificate expires or `null` |
| `warnings` | Avisos que no rompen la web / non-breaking warnings: `lenta`, `sin-html`, `https-no-forzado`, `build-en-curso`, `tls-caduca-pronto` (< 14 días), `sin-404-personalizada`, `sin-meta-description`, `sin-og-image`, `homepage-distinta`, `sin-lang`, `imagenes-sin-alt`, `pagina-pesada` (> 1 MB), `sin-sitemap`, `sin-robots`, `sin-favicon`, `dns-no-apunta-a-github` (dominio propio; con un proxy como Cloudflare puede avisar sin ser un error), `enlaces-rotos`, desde 1.6.0 (con `--crawl`, informativos) `paginas-internas-rotas`, `sitemap-invalido` y `sitemap-urls-rotas`, y desde 1.5.0 `sin-title`, `sin-viewport`, `sin-og-title`, `sin-canonical` y `contenido-mixto` (informativos: no bajan la nota / informational: they do not lower the score) |

## Ejemplo / Example

```bash
github-pages-auditor -u alberto2005-coder -f json -o - -q | jq '.summary'
github-pages-auditor -u alberto2005-coder -f json -o - -q | jq -r '.repos[] | select(.pages.status=="roto") | .name'
```

## Otros formatos y comandos de la 1.5.0 / Other 1.5.0 formats and commands

- `fixes[]` (con `--fix*`): cada acción tiene `repo`, `action` (`create-file`, `open-pr`, `enforce-https`, `set-description`, `set-topics`), `target`, `status` (`planned`, `applied`, `skipped`, `failed`), `detail` opcional y, con `--fix-mode pr`, `via: "pr"`.
- `--diff ANTES.json DESPUES.json -f json` escribe el resultado de la comparación: `previous_file`, `score_before`, `score_after`, `delta`, `improved`, `worsened`, `new_repos`, `removed_repos`, `file_before`, `file_after`, `new_findings` y `resolved_findings`.
