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

## `summary`

`total`, `analyzed`, `pages_live`, `pages_broken`, `releases`, `no_pages_no_releases`, `missing_readme`,
`missing_license`, `missing_gitignore`, `missing_description`, `forks`, `archived`, `errors`.

## `findings`

Claves = reglas de `--fail-on` / keys = `--fail-on` rules: `missing-readme`, `missing-license`, `missing-gitignore`,
`missing-description`, `broken-pages`, `analysis-errors`. Cada valor es una lista de nombres de repositorio.
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
| `error` | string \| null | Motivo si el repo no se pudo analizar / why the repo could not be analyzed |

### `repos[].pages`

| Campo / Field | Descripción / Description |
| --- | --- |
| `status` | `ok`, `roto` (Pages activadas pero fallan / enabled but failing) o `ninguna` (no hay web / no site) |
| `url` | URL final / final URL |
| `http_status` | Código HTTP o `null` / HTTP status or `null` |
| `response_ms` | Tiempo de respuesta en ms / response time in ms |
| `title` | `<title>` de la página / page `<title>` |
| `problems` | Lista de problemas (hacen que `status` sea `roto`) / problems (make `status` = `roto`): `404`, `http-<código>`, `tls-error`, `timeout`, `sin-conexion`, `redireccion-externa`, `demasiadas-redirecciones`, `cuerpo-vacio`, `build-fallido` |
| `warnings` | Avisos que no rompen la web / non-breaking warnings: `lenta`, `sin-html`, `https-no-forzado`, `build-en-curso` |

## Ejemplo / Example

```bash
github-pages-auditor -u alberto2005-coder -f json -o - -q | jq '.summary'
github-pages-auditor -u alberto2005-coder -f json -o - -q | jq -r '.repos[] | select(.pages.status=="roto") | .name'
```
