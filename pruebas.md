# Pruebas — github-pages-auditor v1.2.1

Marca cada prueba con `[x]` cuando pase, `[!]` si falla, y anota lo que veas en **Resultado**.
**Auto** = la cubre un test de `pytest` contra un GitHub simulado (no toca la red), así que se repite sola en cada CI. Lo que dependa de GitHub/PyPI reales sigue siendo manual.
Los comandos están pensados para **PowerShell** en la carpeta del proyecto. Los números de ejemplo
(82 repos, 12 Pages...) son los de la ejecución del 2026-11-11 y pueden cambiar si cambian tus repos.

| Dato | Valor |
| --- | --- |
| Fecha | 2026-11-12 |
| Versión probada | 1.2.1 (las marcadas «1.2.0» se hicieron a mano el 12-nov; las «auto» las ejecuta pytest) |
| Sistema / Python | Windows, Python 3.13 / 3.14 |
| Probado por | Alberto |

Para los comandos con token, define antes (no lo pegues en el historial):

```powershell
$env:GITHUB_TOKEN = "ghp_xxx"      # token sin permisos especiales (repos públicos)
```

---

## 0. Preparación

- [x] **0.1 Instalación limpia**
  ```powershell
  uv sync
  ```
  Esperado: termina sin errores.
  **Resultado:** OK (12-nov, Windows)

- [x] **0.2 Tests automáticos**
  ```powershell
  uv run pytest
  ```
  Esperado: `152 passed` (en Python 3.10: `144 passed, 1 skipped`).
  **Resultado:** OK: 121 passed

---

## 1. Ayuda, versión y errores de uso

- [x] **1.1 Ayuda**
  ```powershell
  uv run github-pages-auditor --help
  ```
  Esperado: aparecen `-f/--format`, `--fail-on`, `--inject`, `--exclude-forks`, `--exclude-archived`, `-q`, la línea de códigos de salida (0/1/2/3/130) y al final los créditos (Alberto Ortiz, GitHub, Web).
  **Resultado:** OK

- [x] **1.2 Versión**
  ```powershell
  uv run github-pages-auditor -V
  ```
  Esperado: `github-pages-auditor 1.2.1` + créditos (en la 1.2.0 salió `1.2.0`).
  **Resultado:** OK, se ven los créditos

- [x] **1.2b Alias antiguo**
  ```powershell
  uv run ver-github-pages -V
  ```
  Esperado: funciona igual que `github-pages-auditor -V` (alias de compatibilidad).
  **Resultado:** OK

- [x] **1.3 Sin usuario**
  ```powershell
  uv run github-pages-auditor --no-env; $LASTEXITCODE
  ```
  Esperado: mensaje de que el usuario es obligatorio y código `2`.
  **Resultado:** OK: código 2

- [x] **1.4 Regla inválida en `--fail-on`**
  ```powershell
  uv run github-pages-auditor -u alberto2005-coder --fail-on inventada --no-env; $LASTEXITCODE
  ```
  Esperado: error `reglas desconocidas: inventada` con la lista de válidas y código `2`. No debe lanzar ninguna petición.
  **Resultado:** OK: código 2, lista de reglas

---

## 2. Modo web (sin token)

> Asegúrate de que `GITHUB_TOKEN` no está definido: `Remove-Item Env:GITHUB_TOKEN -ErrorAction SilentlyContinue`

- [x] **2.1 Con dominio personalizado**
  ```powershell
  uv run github-pages-auditor -u alberto2005-coder -w https://albertoortiz.is-a.dev --no-env
  ```
  Esperado: proveedor "Scraping Web Público (Sin API)"; ~82 repos, ~12 Pages con URLs de `albertoortiz.is-a.dev`; se crea `paginas_github.txt` con los créditos al final.
  **Resultado:** OK: 82/12, sin duplicados

- [x] **2.2 Sin `-w` (descubre el dominio solo)**
  ```powershell
  uv run github-pages-auditor -u alberto2005-coder --no-env
  ```
  Esperado: las mismas ~12 Pages, mostrando `albertoortiz.is-a.dev` aunque no lo indiques.
  **Resultado:** OK: 82 repos, 12 Pages, 22 releases, 51 sin web ni releases, 1 sin licencia, 1 sin .gitignore, 11 forks

- [x] **2.3 Sin duplicados**
  Esperado en 2.1/2.2: `alberto2005-coder` (README de perfil) NO aparece como Pages; sí `alberto2005-coder.github.io`.
  **Resultado:** OK

- [ ] **2.4 Cifras coherentes con la realidad**
  Comprueba a mano en GitHub 2-3 repos: el de "Sin licencia", el de "Sin .gitignore" y uno con releases. Esperado: coinciden.
  **Resultado:**

---

## 3. Modo API (con token)

- [x] **3.1 Ejecución con token**
  ```powershell
  uv run github-pages-auditor -u alberto2005-coder -o api.txt
  ```
  Esperado: proveedor "API REST de GitHub (Autenticado)".
  **Resultado:** OK: proveedor API autenticado

- [x] **3.2 Coincide con el modo web**
  Compara `api.txt` con `paginas_github.txt` (82 repos, 12 Pages, 22 releases, 1 sin licencia, 1 sin `.gitignore`, 11 forks). Si hay diferencias, apúntalas: la API debería ser la correcta.
  ```powershell
  Compare-Object (Get-Content paginas_github.txt) (Get-Content api.txt)
  ```
  **Resultado:** OK: mismas cifras que el modo web

- [x] **3.3 URLs reales de Pages** (⚠️ en la v1.2.0 del 12-nov salían `http://` en proyectos; arreglado ahora → repetir y exigir `https://`)
  Esperado: las URLs salen con tu dominio personalizado (`html_url` de GitHub), también sin `-w`.
  **Resultado:** OK: ningún http:// en api.md

- [x] **3.4 Forzar modo web con token**
  ```powershell
  uv run github-pages-auditor -u alberto2005-coder --no-api
  ```
  Esperado: proveedor "Scraping Web Público".
  **Resultado:** OK: mode web con token presente

- [x] **3.5 Token falso**
  ```powershell
  uv run github-pages-auditor -u alberto2005-coder -k token_falso; $LASTEXITCODE
  ```
  Esperado: "GitHub rechazó el token (401)", sin traceback, código `2`.
  **Resultado:** OK: 401 sin traceback, código 2 · Auto (1.2.1): `tests/test_e2e.py::test_3_5_token_falso_da_2_sin_traceback`

- [x] **3.6 El token no se filtra** (opcional, avanzado)
  Ejecuta con un proxy/inspector de tráfico (p. ej. mitmproxy) y comprueba que la cabecera `Authorization` solo aparece en peticiones a `api.github.com`.
  **Resultado:** Auto (1.2.1): `tests/test_e2e.py::test_3_6_el_token_solo_viaja_a_la_api` (comprobado sobre las peticiones de la sesión, sin proxy)

---

## 4. Formatos de salida

- [x] **4.1 JSON a archivo**
  ```powershell
  uv run github-pages-auditor -u alberto2005-coder -f json
  ```
  Esperado: se crea `paginas_github.json`; es JSON válido con `schema_version: 1`, `summary`, `findings` (todas las reglas, aunque vacías), `fail_on` y `repos`.
  ```powershell
  Get-Content paginas_github.json -Raw | ConvertFrom-Json | Select-Object -Expand summary
  ```
  **Resultado:** OK: summary correcto

- [x] **4.2 JSON por stdout (apto para tuberías)** — FALLÓ en v1.2.0 con UnicodeEncodeError (cp1252); corregido, repetir
  ```powershell
  uv run github-pages-auditor -u alberto2005-coder -f json -o - -q | ConvertFrom-Json | Select-Object -Expand summary
  ```
  Esperado: se imprime el resumen sin errores de parseo (stdout es JSON puro; la interfaz va a stderr).
  **Resultado:** OK tras el arreglo: JSON puro por stdout, summary 82/12

- [x] **4.3 Markdown**
  ```powershell
  uv run github-pages-auditor -u alberto2005-coder -f md
  ```
  Esperado: `paginas_github.md` con la tabla "Demos en vivo" entre los marcadores, ordenada alfabéticamente, sin forks, con enlace al repo y "Abrir" a la demo. Los textos con `|` no rompen la tabla.
  **Resultado:** OK (en PowerShell usar Get-Content -Encoding utf8 para ver bien los acentos)

- [x] **4.4 `-q` (silencioso)**
  ```powershell
  uv run github-pages-auditor -u alberto2005-coder -q
  ```
  Esperado: no se ven tablas ni barra de progreso; el archivo se escribe igualmente.
  **Resultado:** OK: -q no imprime nada (visto en 5.1/5.3/5.4)

---

## 5. Códigos de salida y `--fail-on`

- [x] **5.1 Sin `--fail-on` → 0 aunque haya hallazgos**
  ```powershell
  uv run github-pages-auditor -u alberto2005-coder -q; $LASTEXITCODE
  ```
  Esperado: `0`.
  **Resultado:** OK: 0

- [x] **5.2 `--fail-on` con hallazgos → 1**
  ```powershell
  uv run github-pages-auditor -u alberto2005-coder -q --fail-on missing-license; $LASTEXITCODE
  ```
  Esperado: `1` (tienes 1 repo sin licencia), mensaje "--fail-on disparado por: missing-license", y el informe SÍ se escribe.
  **Resultado:** OK: código 1 con --fail-on missing-license

- [x] **5.3 `--fail-on` sin hallazgos → 0**
  ```powershell
  uv run github-pages-auditor -u alberto2005-coder -q --fail-on missing-readme,missing-description; $LASTEXITCODE
  ```
  Esperado: `0` (no tienes repos sin README ni sin descripción).
  **Resultado:** OK: 0

- [x] **5.4 `--fail-on any`**
  ```powershell
  uv run github-pages-auditor -u alberto2005-coder -q --fail-on any; $LASTEXITCODE
  ```
  Esperado: `1` si hay cualquier hallazgo.
  **Resultado:** OK: 1 (missing-license, missing-gitignore)

- [x] **5.5 Usuario inexistente → 2**
  ```powershell
  uv run github-pages-auditor -u usuario-que-no-existe-xyz123; $LASTEXITCODE
  ```
  Esperado: "no existe" y código `2`.
  **Resultado:** OK: código 2 · Auto (1.2.1): `tests/test_e2e.py::test_5_5_usuario_inexistente_da_2`

- [x] **5.6 Sin repositorios → 3**
  ```powershell
  uv run github-pages-auditor -u alberto2005-coder --exclude-forks --exclude-archived -q --fail-on any; $LASTEXITCODE
  ```
  Esperado: este NO da 3 (tienes repos propios). Para forzar el 3, usa una cuenta sin repos públicos y comprueba el código `3` y que no se crea archivo.
  **Resultado:** Auto (1.2.1): `tests/test_e2e.py::test_5_6_sin_repos_tras_filtrar_da_3_y_no_escribe`

- [x] **5.7 Ctrl+C → 130**
  Lanza una auditoría y pulsa Ctrl+C a media barra.
  Esperado: "Operación cancelada" y código `130`, sin traceback.
  **Resultado:** Auto (1.2.1): `tests/test_cli.py::test_ctrl_c_da_130` (simulado; la pulsación real de Ctrl+C sigue siendo opcional a mano)

- [x] **5.8 Carpeta de salida inexistente**
  ```powershell
  uv run github-pages-auditor -u alberto2005-coder -o C:\ruta\que\no\existe\x.txt; $LASTEXITCODE
  ```
  Esperado: falla al instante (sin barra de progreso) con "La carpeta de salida no existe" y código `2`.
  **Resultado:** OK: código 2

---

## 6. Salud de Pages

- [x] **6.1 Pages sanas**
  ```powershell
  uv run github-pages-auditor -u alberto2005-coder -k $env:GITHUB_TOKEN -f json -o - -q | ConvertFrom-Json | Select-Object -Expand repos | Where-Object { $_.pages } | Select-Object name, @{n='estado';e={$_.pages.status}}, @{n='ms';e={$_.pages.response_ms}}, @{n='titulo';e={$_.pages.title}}
  ```
  Esperado: tus ~12 Pages con estado `ok`, tiempo de respuesta y título de la página.
  **Resultado:** Auto (1.2.1): `tests/test_e2e.py::test_6_1_pages_sana_trae_estado_tiempo_y_titulo`

- [x] **6.2 Pages rota (404 / sin index)** — requiere un repo de prueba
  1. Crea un repo `pruebas-pages-roto` y activa Pages (Settings → Pages) **sin** subir `index.html`.
  2. Ejecuta con token:
  ```powershell
  uv run github-pages-auditor -u alberto2005-coder -k $env:GITHUB_TOKEN --fail-on broken-pages; $LASTEXITCODE
  ```
  Esperado: aparece la fila "Pages rotas", la sección "GITHUB PAGES ROTAS" en el `.txt` con `404`, y código `1`.
  **Resultado:** Auto (1.2.1): `tests/test_e2e.py::test_6_2_pages_rota_con_token_da_exit_1_y_aparece_en_el_informe` (con un repo de prueba real sigue siendo opcional)

- [x] **6.3 Sin token no marca "rotas"**
  Repite 6.2 con `--no-api`. Esperado: ese repo simplemente no aparece como Pages (no se puede saber que debería tenerla); no hay "Pages rotas".
  **Resultado:** Auto (1.2.1): `tests/test_e2e.py::test_6_3_sin_pages_activadas_no_hay_pages_rotas`

- [x] **6.4 Aviso de HTTPS no forzado / build** (opcional)
  En un repo de prueba desactiva "Enforce HTTPS" y comprueba que el JSON trae `warnings: ["https-no-forzado"]`.
  **Resultado:** Auto (1.2.1): `tests/test_e2e.py::test_6_4_avisos_de_https_no_forzado_y_build`

- [x] **6.5 Dominio personalizado caído/mal configurado** (opcional)
  Apunta temporalmente un CNAME a un dominio sin DNS. Esperado (con token): estado `roto` con `sin-conexion` o `tls-error`.
  **Resultado:** Auto (1.2.1): `tests/test_e2e.py::test_6_5_dominio_caido_o_mal_configurado_es_pages_rota` (tls-error, sin-conexion y timeout)

---

## 7. `--inject` en un README

- [x] **7.1 Crear el archivo de prueba**
  Crea `prueba-readme.md`:
  ```markdown
  # Mi perfil

  Texto antes.

  <!-- github-pages-auditor:start -->
  contenido viejo
  <!-- github-pages-auditor:end -->

  Texto después.
  ```
  **Resultado:** OK

- [x] **7.2 Inyectar**
  ```powershell
  uv run github-pages-auditor -u alberto2005-coder --inject prueba-readme.md
  ```
  Esperado: "Tabla de demos actualizada"; "contenido viejo" desaparece; "Texto antes/después" intacto; **no** se crea `paginas_github.txt`.
  **Resultado:** OK: sin paginas_github.txt

- [x] **7.3 Idempotente**
  Ejecuta 7.2 otra vez y compara: `git diff prueba-readme.md` no debe mostrar cambios (salvo si cambiaron tus Pages).
  **Resultado:** OK: hash idéntico

- [x] **7.4 Sin marcadores**
  Quita los marcadores y repite. Esperado: error claro, código `2`, el archivo queda **sin tocar**.
  **Resultado:** OK: código 2, archivo intacto

- [x] **7.5 Archivo inexistente**
  ```powershell
  uv run github-pages-auditor -u alberto2005-coder --inject no-existe.md; $LASTEXITCODE
  ```
  Esperado: "No existe el archivo para --inject", código `2`, antes de auditar.
  **Resultado:** OK: código 2

- [x] **7.6 `--inject` + `-o`**
  ```powershell
  uv run github-pages-auditor -u alberto2005-coder --inject prueba-readme.md -o informe.txt
  ```
  Esperado: actualiza el README **y** escribe `informe.txt`.
  **Resultado:** Auto (1.2.1): `tests/test_config.py::test_inject_con_o_explicito_tambien_escribe_informe`

---

## 8. Filtros

- [x] **8.1 `--exclude-forks`**
  ```powershell
  uv run github-pages-auditor -u alberto2005-coder --exclude-forks -q -f json -o - | ConvertFrom-Json | Select-Object -Expand summary
  ```
  Esperado: `total` ≈ 71 (82 − 11 forks) y `forks` = 0.
  **Resultado:** Auto (1.2.1): `tests/test_e2e.py::test_8_1_exclude_forks`

- [x] **8.2 `--exclude-archived`**
  Esperado: `archived` = 0 y menos peticiones (no se analizan los archivados).
  **Resultado:** Auto (1.2.1): `tests/test_e2e.py::test_8_2_exclude_archived_ni_siquiera_se_analizan`

---

## 9. Configuración y `.env`

- [x] **9.1 Solo `.env`**
  ```powershell
  Copy-Item .env.example .env
  # edita .env y rellena solo USUARIO_GITHUB=alberto2005-coder
  uv run github-pages-auditor
  ```
  Esperado: funciona sin parámetros.
  **Resultado:** Auto (1.2.1): `tests/test_env_real.py::test_9_1_solo_con_env_funciona_sin_parametros` (python-dotenv real sobre un .env temporal)

- [x] **9.2 `--no-env`**
  ```powershell
  uv run github-pages-auditor --no-env; $LASTEXITCODE
  ```
  Esperado: vuelve a pedir el usuario (código `2`).
  **Resultado:** Auto (1.2.1): `tests/test_env_real.py::test_9_2_no_env_ignora_el_archivo` (python-dotenv real sobre un .env temporal)

- [x] **9.3 Prioridad parámetros > entorno**
  Con `USUARIO_GITHUB=otro` en `.env`, ejecuta con `-u alberto2005-coder`. Esperado: audita `alberto2005-coder`.
  **Resultado:** Auto (1.2.1): `tests/test_env_real.py::test_9_3_los_parametros_ganan_al_env` (python-dotenv real sobre un .env temporal)

- [x] **9.4 Variables vacías se ignoran**
  Deja `GITHUB_TOKEN=` vacío en `.env`. Esperado: modo web (no intenta usar la API con un token vacío).
  **Resultado:** Auto (1.2.1): `tests/test_env_real.py::test_9_4_variables_vacias_se_ignoran` (python-dotenv real sobre un .env temporal)

- [x] **9.5 El `.env` se encuentra desde otra carpeta** (instalado como paquete)
  Instala (`uv tool install .`), colócate en una carpeta con un `.env` y ejecuta `github-pages-auditor`. Esperado: lo lee del directorio actual.
  **Resultado:** Auto (1.2.1): `tests/test_env_real.py::test_9_5_el_env_se_busca_en_el_directorio_actual` (python-dotenv real sobre un .env temporal)

---

## 10. Robustez

- [x] **10.1 Sin conexión**
  Desactiva la red y ejecuta. Esperado: mensaje de error de red claro y código `2`, sin traceback.
  **Resultado:** Auto (1.2.1): `tests/test_e2e.py::test_10_1_sin_conexion_da_2_sin_traceback` (red simulada caída)

- [x] **10.2 `--timeout` bajo**
  ```powershell
  uv run github-pages-auditor -u alberto2005-coder --timeout 0.05 -q -f json -o - | ConvertFrom-Json | Select-Object -Expand summary
  ```
  Esperado: no se cuelga; algunos repos pueden salir en `errors` (sección "no analizados") sin tumbar el resto.
  **Resultado:** Auto (1.2.1): `tests/test_e2e.py::test_10_2_timeout_en_un_repo_no_tumba_el_resto`

- [x] **10.3 `--workers 1` y `--workers 40`**
  Esperado: funcionan y dan los mismos resultados; el orden del informe es siempre el mismo.
  **Resultado:** Auto (1.2.1): `tests/test_e2e.py::test_10_3_y_10_4_mismo_resultado_con_1_o_40_hilos_y_orden_estable`

- [x] **10.4 Orden determinista**
  Ejecuta dos veces `-f json` y compara los `repos` (ignorando `generated_at`). Esperado: idénticos.
  **Resultado:** Auto (1.2.1): `tests/test_e2e.py::test_10_3_y_10_4_mismo_resultado_con_1_o_40_hilos_y_orden_estable`

- [x] **10.5 Límite de tasa sin token** (opcional)
  Ejecuta el modo web varias veces seguidas hasta recibir un 429. Esperado: mensaje "GitHub limitó las peticiones" sugiriendo usar token, código `2`.
  **Resultado:** Auto (1.2.1): `tests/test_e2e.py::test_10_5_limite_de_tasa_da_2_con_mensaje` (simulado)

---

## 11. Publicación en PyPI (tras la release)

- [x] **11.1 Configurar el publisher** (una sola vez)
  pypi.org → Publishing → pending publisher: proyecto `github-pages-auditor`, owner `alberto2005-coder`, repo `github-pages-auditor`, workflow `publish.yml`, environment `pypi`. Crea el environment `pypi` en GitHub.
  **Resultado:** OK: publisher y environment configurados

- [x] **11.2 Release y workflow**
  Commit, `git tag v1.2.0`, push y crea la Release. Esperado: en Actions pasa "Publish to PyPI" (build + tests + publish).
  **Resultado:** OK: release v1.2.0 publicada y paquete disponible en PyPI (12-nov)

- [ ] **11.3 El tag debe coincidir con la versión**
  (Opcional) crea una release con un tag distinto (`v9.9.9`). Esperado: el workflow falla en "Check that the tag matches the package version" y no publica.
  **Resultado:**

- [x] **11.4 `uvx` sin instalar nada**
  ```powershell
  uvx github-pages-auditor -V
  uvx github-pages-auditor -u alberto2005-coder -f json -o - -q
  ```
  Esperado: versión 1.2.0 con créditos y JSON válido.
  **Resultado:** OK: `uvx github-pages-auditor -V` → 1.2.0 con créditos; JSON válido (82 repos, 12 Pages)

- [x] **11.4b Instalación desde GitHub**
  ```powershell
  uv tool install git+https://github.com/alberto2005-coder/github-pages-auditor.git@v1.2.0
  github-pages-auditor -V
  ```
  Esperado: instala 11 paquetes y los ejecutables `github-pages-auditor` y `ver-github-pages`.
  **Resultado:** OK, 1.2.0 con créditos; desinstalado con `uv tool uninstall github-pages-auditor`.

- [x] **11.5 Instalación con `pip` en un entorno limpio**
  ```powershell
  python -m venv prueba-venv; .\prueba-venv\Scripts\pip install github-pages-auditor; .\prueba-venv\Scripts\github-pages-auditor -V
  ```
  **Resultado:** OK: `pip install github-pages-auditor` descarga e instala `github_pages_auditor-1.2.0-py3-none-any.whl` y sus dependencias (`rich`, `requests`, `python-dotenv`) en Python 3.14, creando los ejecutables `github-pages-auditor.exe` y `ver-github-pages.exe`.

- [ ] **11.6 Página del proyecto en PyPI**
  Esperado: el README se ve bien, los enlaces funcionan y las URLs del proyecto apuntan a `github-pages-auditor`.
  **Resultado:**

---

## 12. Integración continua

- [ ] **12.1 Workflow de tests**
  Haz push a `master` y mira Actions. Esperado: pasan las 6 combinaciones (Ubuntu/macOS/Windows × Python 3.10/3.13).
  **Resultado:**

- [ ] **12.2 Uso en CI real** (opcional)
  En un repo de prueba, añade el paso:
  ```yaml
  - run: uvx github-pages-auditor -u ${{ github.repository_owner }} -k ${{ secrets.GITHUB_TOKEN }} -f json -o report.json --fail-on missing-license,broken-pages
  ```
  Esperado: el job falla (exit 1) si hay hallazgos y pasa si no.
  **Resultado:**

---

## 13. Documentación

- [ ] **13.1 README en GitHub**: los índices ES/EN llevan a su sección, la tabla de opciones coincide con `--help`, y el comando `git clone` apunta a `github-pages-auditor`.
  **Resultado:**

- [x] **13.2 CHANGELOG**: cambia «Unreleased» por la fecha de la release de la 1.2.0.
  **Resultado:** Auto (1.2.1): `tests/test_release.py::test_changelog_tiene_la_version_actual` (la entrada 1.2.1 lleva fecha)

- [ ] **13.3 Descripción de la release v1.1.0**: corrige la URL de instalación a `github-pages-auditor.git@v1.1.0`.
  **Resultado:**

---

## 14. Novedades de la 1.2.1

- [x] **14.1 Versión, CHANGELOG y `uv.lock` coherentes**
  Esperado: `__version__`, `pyproject.toml`, entrada del CHANGELOG y `uv.lock` dicen 1.2.1 (si el lock se queda viejo, el workflow con `--frozen` falla).
  **Resultado:** Auto (1.2.1): `tests/test_release.py::test_changelog_tiene_la_version_actual`, `::test_uv_lock_coincide_con_la_version`. Este test detectó un `uv.lock` viejo durante la preparación y se regeneró.

- [x] **14.2 Metadatos públicos sin correo**
  Esperado: ningún autor/mantenedor con `email` en `pyproject.toml`.
  **Resultado:** Auto (1.2.1): `tests/test_release.py::test_metadatos_publicos`.

- [x] **14.3 Classifiers cubren la matriz del CI (3.10, 3.13, 3.14)**
  **Resultado:** Auto (1.2.1): `tests/test_release.py::test_classifiers_cubren_las_versiones_del_ci`.

- [x] **14.4 El JSON está documentado campo a campo**
  Esperado: `docs/json-schema.md` menciona todos los campos que emite `-f json`.
  **Resultado:** Auto (1.2.1): `tests/test_release.py::test_la_documentacion_del_json_cubre_todos_los_campos`.

- [x] **14.5 README sin tokens `ghp_`, con enlaces absolutos a `docs/`**
  **Resultado:** Auto (1.2.1): `tests/test_release.py::test_readme_enlaces_absolutos_a_docs_y_sin_tokens_ghp`.

- [x] **14.6 Paquete construido e instalable** (en entorno limpio, con `uv` y con `pip`)
  **Resultado:** OK (2026-11-14): `uv build` genera wheel y sdist 1.2.1; instalado en entorno limpio con `uv pip`, con `pip` y con `uv tool install` (sdist); `github-pages-auditor -V` y el alias `ver-github-pages -V` dan 1.2.1. Metadatos: autor sin correo, classifier 3.14.

- [ ] **14.7 CI en verde con Python 3.14** (tras el push)
  Esperado: las 9 combinaciones (Ubuntu/macOS/Windows × 3.10/3.13/3.14) pasan en Actions.
  **Resultado:**

- [ ] **14.8 Badges del README** (tras el push y la release)
  Esperado: se ven los 4 badges (PyPI, Python, Tests, licencia) en GitHub; el de PyPI muestra `1.2.1` tras publicar.
  **Resultado:**

- [ ] **14.9 Receta de resumen del job** (opcional)
  En un repo de prueba, añade el paso de `docs/ci.md` §2 y mira la pestaña *Summary* del job. Esperado: aparece la tabla de demos.
  **Resultado:**

- [ ] **14.10 Receta de refresco semanal del README** (opcional)
  Copia el workflow de `docs/ci.md` §3 a un repo con los marcadores y lánzalo con *Run workflow*. Esperado: un commit «docs: actualizar demos» solo si hubo cambios.
  **Resultado:**

- [ ] **14.11 Publicación de la 1.2.1** (tras la release `v1.2.1`)
  ```powershell
  cd $env:TEMP
  uvx github-pages-auditor@1.2.1 -V
  uvx github-pages-auditor@1.2.1 -u alberto2005-coder -f json -o - -q | ConvertFrom-Json | Select-Object -Expand summary
  ```
  Esperado: `github-pages-auditor 1.2.1` con créditos y el resumen (82 repos, 12 Pages). En `https://pypi.org/project/github-pages-auditor/` ya no aparece tu correo y el README es el nuevo.
  **Resultado:**

---

## Resumen final

| Bloque | Pasan | Fallan | Notas |
| --- | :---: | :---: | --- |
| 0. Preparación | 2 | 0 | 2/2 hechas |
| 1. Ayuda y errores de uso | 5 | 0 | 5/5 hechas |
| 2. Modo web | 3 | 0 | 3/4 hechas; el resto, pendiente u opcional |
| 3. Modo API | 6 | 0 | 6/6 hechas |
| 4. Formatos | 4 | 0 | 4/4 hechas |
| 5. Códigos de salida | 8 | 0 | 8/8 hechas |
| 6. Salud de Pages | 5 | 0 | 5/5 hechas |
| 7. `--inject` | 5 | 0 | 5/6 hechas; el resto, pendiente u opcional |
| 8. Filtros | 2 | 0 | 2/2 hechas |
| 9. Configuración / `.env` | 5 | 0 | 5/5 hechas |
| 10. Robustez | 5 | 0 | 5/5 hechas |
| 11. PyPI | 5 | 0 | 5/7 hechas; el resto, pendiente u opcional |
| 12. CI | 0 | 0 | 0/2 hechas; el resto, pendiente u opcional |
| 13. Documentación | 0 | 0 | 0/3 hechas; el resto, pendiente u opcional |
| 14. Novedades 1.2.1 | 6 | 0 | 6/11 hechas; el resto, pendiente u opcional |

**Bugs encontrados** (comando, resultado obtenido, resultado esperado):

1. Pages de proyecto con `http://` en modo API → corregido (prefiere https).
2. `-f json -o -` con UnicodeEncodeError en Windows (cp1252) → corregido (JSON ASCII por stdout, UTF-8 en el resto).
3. Nota: un token revocado definido en `$env:GITHUB_TOKEN` hace que el modo por defecto dé 401 (comportamiento correcto).

**¿Listo para publicar la 1.2.1?** [x] Sí [ ] No — todo lo automatizable pasa; faltan las comprobaciones que necesitan GitHub/PyPI reales (14.7, 14.8, 14.11).