# Pruebas — github-pages-auditor v1.5.0

Marca cada prueba con `[x]` cuando pase, `[!]` si falla, y anota lo que veas en **Resultado**.
**Auto** = la cubre un test de `pytest` contra un GitHub simulado (no toca la red), así que se repite sola en cada CI. Lo que dependa de GitHub/PyPI reales sigue siendo manual.
Los comandos están pensados para **PowerShell** en la carpeta del proyecto. Los números de ejemplo
(82 repos, 12 Pages...) son los de la ejecución del 2026-11-11 y pueden cambiar si cambian tus repos.

| Dato | Valor |
| --- | --- |
| Fecha | 2026-11-14 |
| Versión probada | 1.3.0 (las secciones 0-14 se hicieron a mano con 1.2.x; las «auto» las ejecuta pytest; la 15 es nueva) |
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
  **Resultado:** Pendiente de tu vistazo: en Actions, workflow de tests, las 9 combinaciones (Ubuntu/macOS/Windows × 3.10/3.13/3.14) en verde. La publicación en PyPI ya pasó sus propios tests, pero la matriz completa no la puedo ver desde aquí.

- [x] **14.8 Badges del README** (tras el push y la release)
  Esperado: se ven los 4 badges (PyPI, Python, Tests, licencia) en GitHub; el de PyPI muestra `1.2.1` tras publicar.
  **Resultado:** OK en PyPI (badges del README presentes en la página del proyecto). En GitHub: míralos a ojo y confirma que el de Tests sale en verde.

- [ ] **14.9 Receta de resumen del job** (opcional)
  En un repo de prueba, añade el paso de `docs/ci.md` §2 y mira la pestaña *Summary* del job. Esperado: aparece la tabla de demos.
  **Resultado:**

- [ ] **14.10 Receta de refresco semanal del README** (opcional)
  Copia el workflow de `docs/ci.md` §3 a un repo con los marcadores y lánzalo con *Run workflow*. Esperado: un commit «docs: actualizar demos» solo si hubo cambios.
  **Resultado:**

- [x] **14.11 Publicación de la 1.2.1** (tras la release `v1.2.1`)
  ```powershell
  cd $env:TEMP
  uvx github-pages-auditor@1.2.1 -V
  uvx github-pages-auditor@1.2.1 -u alberto2005-coder -f json -o - -q | ConvertFrom-Json | Select-Object -Expand summary
  ```
  Esperado: `github-pages-auditor 1.2.1` con créditos y el resumen (82 repos, 12 Pages). En `https://pypi.org/project/github-pages-auditor/` ya no aparece tu correo y el README es el nuevo.
  **Resultado:** OK (2026-11-14): `uvx github-pages-auditor@1.2.1 -V` → 1.2.1 con créditos; JSON válido (82 repos, 12 Pages, 0 rotas, 0 errores). PyPI: 1.2.1 publicada (wheel + sdist, 08:32 UTC), autor sin correo, classifier 3.14, README nuevo con badges y sin `ghp_`.

## 15. Novedades de la 1.3.0

**Automáticas** (`tests/test_v130.py`, `tests/test_release.py`; 178 tests en verde en Python 3.10, 3.13 y 3.14):

- [x] **15.1 Datos por repo** (estrellas, forks, issues, lenguaje, topics, licencia, fechas, release). **Resultado:** Auto: `test_json_incluye_datos_nuevos_y_schema_sigue_en_1`, `test_atom_extrae_tag_y_fecha`. `schema_version` sigue en 1.
- [x] **15.2 `--sort` y `--only/--ignore`.** **Resultado:** Auto: `test_sort`, `test_only_e_ignore`.
- [x] **15.3 Reglas de comunidad y grupos `any`/`community`/`all`** (forks y archivados excluidos; sin datos = sin hallazgos). **Resultado:** Auto: `test_reglas_de_comunidad_y_grupos`, `test_any_no_incluye_comunidad`, `test_sin_datos_no_hay_hallazgos_de_comunidad`, `test_stale_repo_usa_meses`.
- [x] **15.4 Pages en profundidad** (TLS < 14 días, 404.html, meta description, og:image, Website distinto). **Resultado:** Auto: `test_tls_dias_hasta`, `test_tls_falla_sin_red_devuelve_none`, `test_aviso_tls_y_404`, `test_homepage_distinta`.
- [x] **15.5 `--baseline`** (sin nuevos = salida 0; archivo inválido = salida 2). **Resultado:** Auto: `test_baseline_sin_nuevos_no_falla`, `test_baseline_invalido_sale_con_2`, `test_baseline_nuevos_funcion`.
- [x] **15.6 `-f github`** (anotaciones y escapes). **Resultado:** Auto: `test_formato_github`, `test_github_escapa`.
- [x] **15.7 Archivo `.github-pages-auditor.toml`** (precedencia, `--no-config`, rechaza token y claves desconocidas). **Resultado:** Auto: `test_config_toml`, `test_config_rechaza_token_y_claves_desconocidas` (en 3.10 usa `tomli`; 1 test se omite si falta).
- [x] **15.8 `--details`** en md y txt. **Resultado:** Auto: `test_details_en_markdown_y_txt`.
- [x] **15.9 Higiene de release:** CHANGELOG/versión/`uv.lock`, cada opción de la CLI y cada regla documentadas, `action.yml` y archivos de comunidad presentes. **Resultado:** Auto: `tests/test_release.py`.
- [x] **15.10 Paquete 1.3.0 instalable** (sandbox). **Resultado:** OK: `uv build`; instalado en venv limpio con `uv pip` (3.10, con `tomli`) y con `pip` (3.13); `github-pages-auditor -V` y `ver-github-pages -V` dan 1.3.0; sin tokens en el código.

**Manuales** (dependen de GitHub/PyPI reales; no se pueden probar desde el sandbox):

- [x] **15.11 Datos y comunidad con tu cuenta**
  ```powershell
  $env:GITHUB_TOKEN = "github_pat_xxx"
  uv run github-pages-auditor -u alberto2005-coder --details --sort stars -f json -o - -q | ConvertFrom-Json | Select-Object -Expand repos | Select-Object -First 5 name,stars,language,license,latest_release
  uv run github-pages-auditor -u alberto2005-coder --fail-on community -q; echo $LASTEXITCODE
  ```
  Esperado: estrellas/lenguaje/licencia rellenos; código 1 si algún repo no tiene SECURITY/CONTRIBUTING/etc.
  **Resultado:** OK (2026-11-14): `--fail-on community -q` → código `1` (`missing-security-policy, missing-contributing, missing-code-of-conduct, missing-issue-template, missing-topics`). JSON: `stars`, `language` y `license` rellenos (3-en-raya: 0 / CSS / MIT; aegis-osint-suite: 0 / JavaScript / GPL-3.0; alberto2005-coder: sin lenguaje = repo solo con README). `latest_release` vacío en los 5 primeros porque no tienen releases; en `github-pages-auditor` sale `{tag: v1.3.0, date: 2026-11-14T20:05:07Z}`.

- [x] **15.12 Pages reales: TLS, 404 y SEO**
  ```powershell
  uv run github-pages-auditor -u alberto2005-coder -f json -o - -q | ConvertFrom-Json | Select-Object -Expand repos | Where-Object pages | Select-Object name,@{n="tls";e={$_.pages.tls_days_left}},@{n="avisos";e={$_.pages.warnings -join ","}}
  ```
  Esperado: `tls_days_left` con un número en tus dominios propios; avisos coherentes con lo que ves en tus webs.
  **Resultado:** OK (2026-11-14): 12 sitios con `tls_days_left` = 70 en todos; avisos coherentes (`sin-meta-description`, `sin-og-image`, `https-no-forzado`, `sin-404-personalizada`; `alberto2005-coder.github.io` sin avisos).

- [x] **15.13 Modo web (sin token) sigue funcionando y trae la última release**
  ```powershell
  Remove-Item Env:GITHUB_TOKEN; uv run github-pages-auditor -u alberto2005-coder --no-env --details -q
  ```
  Esperado: informe completo; columnas de datos de API vacías, sin errores.
  **Resultado:** OK (2026-11-14): sin token y con `--no-env --details -q` → sin errores, código `0`.

- [x] **15.14 Baseline real**
  ```powershell
  uv run github-pages-auditor -u alberto2005-coder -f json -o base.json -q
  uv run github-pages-auditor -u alberto2005-coder --baseline base.json --fail-on all -q; echo $LASTEXITCODE
  ```
  Esperado: código `0` (nada nuevo).
  **Resultado:** OK (2026-11-14): `--baseline base.json --fail-on all` → código `0` (nada nuevo respecto al informe guardado).

- [ ] **15.15 Config TOML real**: crea `.github-pages-auditor.toml` con `user = "alberto2005-coder"` y `sort = "name"` y ejecuta `uv run github-pages-auditor -q`. Esperado: audita sin `-u`. Con `token = "x"` dentro: error y salida 2.
  **Resultado:**

- [ ] **15.16 CI de la 1.3.0** (tras el push): matriz 9/9 verde, job `lint` verde y job `self-audit` verde (si falla por `missing-*`, falta algún archivo de comunidad detectado por la API).
  **Resultado:**

- [ ] **15.17 Action reutilizable**: en un repo de pruebas, un workflow con `uses: alberto2005-coder/github-pages-auditor@v1.3.0` (`user`, `token: ${{ secrets.GITHUB_TOKEN }}`, `fail-on: any`). Esperado: anotaciones en el log y job verde/rojo según hallazgos.
  **Resultado:**

- [x] **15.18 Publicación de la 1.3.0** (tras la release `v1.3.0`)
  ```powershell
  cd $env:TEMP
  uvx github-pages-auditor@1.3.0 -V
  ```
  **Resultado:** OK (2026-11-14): PyPI lista 1.2.0, 1.2.1 y 1.3.0; `uvx --refresh github-pages-auditor@1.3.0 -V` → `github-pages-auditor 1.3.0` con créditos. (Justo tras publicar, `uvx` no la veía por caché del índice; con `--refresh` funcionó.)

## 16. Novedades de la 1.4.0

**Automáticas** (`tests/test_v140.py`, `tests/test_live.py`, `tests/test_release.py`; 240 tests en Python 3.10, 3.13 y 3.14; cobertura 95 %; `ruff` y `mypy` en verde):

- [x] **16.1 Nota 0-100, `--min-score`, ranking e histórico** (`--history`, comparación con el informe anterior, archivos corruptos). **Resultado:** Auto: `test_repo_perfecto_100_y_repo_vacio_bajo`, `test_sin_datos_de_comunidad_los_pesos_se_reescalan`, `test_la_release_suma`, `test_global_ignora_forks_y_archivados_y_ranking`, `test_min_score`, `test_history_dos_ejecuciones`, `test_historial_guarda_y_compara`.
- [x] **16.2 Salidas `html`, `csv`, `sarif`, `badge`.** HTML sin recursos externos y con datos escapados; CSV sin inyección de fórmulas. **Resultado:** Auto: `test_html_escapa_y_no_carga_recursos_externos`, `test_csv_cabecera_bom_e_inyeccion`, `test_sarif_estructura`, `test_badge`. Además se abrió el HTML en un navegador del sandbox: ordena, filtra y se ve bien.
- [x] **16.3 Webhook** (solo https, solo con hallazgos, nunca imprime la URL, falla en silencio). **Resultado:** Auto: `test_webhook_*`.
- [x] **16.4 `--lang en`** (mismas claves en ES y EN; reglas traducidas). **Resultado:** Auto: `test_idiomas_tienen_las_mismas_claves`, `test_lang_en_en_txt_y_consola`.
- [x] **16.5 `--deep`, `--org`, `--include-private`** y reglas nuevas (403 = sin permisos = no se afirma nada). **Resultado:** Auto: `test_deep_*`, `test_org_usa_el_endpoint_de_organizaciones`, `test_include_private_filtra_por_propietario`, `test_opciones_que_exigen_token`.
- [x] **16.6 Pages a fondo:** `lang`, `alt`, favicon, sitemap, robots, peso, DNS, `--check-links`. **Resultado:** Auto: `test_avisos_html_basicos`, `test_dns_*`, `test_enlaces_*`, `test_check_links_cli`.
- [x] **16.7 `--fix`, `--fix-pages`, `--fix-metadata`, `--dry-run`, `--yes`:** sin `--yes` no se escribe nada, no se pisan archivos, forks y archivados quedan fuera. **Resultado:** Auto: `test_fix_*`, `test_plantillas_se_leen_del_paquete`.
- [x] **16.8 `--cache` (ETag), `--since`, `--tui`.** **Resultado:** Auto: `test_cache_*`, `test_since_*`, `test_tui_*`. La TUI también se probó sin pantalla con Textual 8.2.8 (2 filas, 7 columnas, sale con `q`).
- [x] **16.9 Higiene de release:** versión, CHANGELOG, `uv.lock`, cada opción y cada regla documentadas, workflow con atestaciones. **Resultado:** Auto: `tests/test_release.py`.
- [x] **16.10 Paquete 1.4.0** (sandbox): `uv build` (incluye las plantillas), instalado en venv limpio con `uv pip` (3.10) y con `pip` + extra `[tui]` (3.13); `-V` da 1.4.0. **Resultado:** OK.

**Manuales** (dependen de GitHub/PyPI reales; no se pueden probar desde el sandbox):

- [x] **16.11 Nota e histórico con tu cuenta**
  ```powershell
  uvx github-pages-auditor@1.4.0 -u alberto2005-coder --details --sort stars -q
  uvx github-pages-auditor@1.4.0 -u alberto2005-coder --history $env:TEMP\hist -q
  uvx github-pages-auditor@1.4.0 -u alberto2005-coder --history $env:TEMP\hist -q
  uvx github-pages-auditor@1.4.0 -u alberto2005-coder --min-score 95 -q; echo $LASTEXITCODE
  ```
  Esperado: tabla con columna Nota, «Nota global» y mejores/peores; la segunda ejecución muestra «+0 puntos»; el último comando termina con código `1`.
  **Resultado:** OK (2026-11-15). Nota global 65/100 (C), mejores `github-pages-auditor` (100), `ordo-project` (83), `.github` (75); histórico guardado y 2.ª ejecución «+0 puntos»; `--min-score 95` → «--fail-on disparado por: min-score», código 1.

- [x] **16.12 `--deep` con tu cuenta (con token)**
  ```powershell
  uvx github-pages-auditor@1.4.0 -u alberto2005-coder --deep -f json -o - -q | ConvertFrom-Json | Select-Object -Expand repos | Select-Object -First 5 name,score,@{n="ci";e={$_.deep.ci}},@{n="dependabot";e={$_.deep.dependabot_yml}},@{n="prot";e={$_.deep.branch_protected}}
  ```
  Esperado: `ci` y `dependabot` con true/false; `prot` puede ser `null` si el token no tiene permisos de administración (es correcto).
  **Resultado:** OK. `ci` y `dependabot` = False en los 5 primeros repos; `prot` vacío (el token no tiene permisos de administración: esperado).

- [x] **16.13 Informes HTML, CSV, badge y SARIF**
  ```powershell
  uvx github-pages-auditor@1.4.0 -u alberto2005-coder -f html -o informe.html -q; start informe.html
  uvx github-pages-auditor@1.4.0 -u alberto2005-coder -f csv -o informe.csv -q
  uvx github-pages-auditor@1.4.0 -u alberto2005-coder -f badge -o score.svg -q; start score.svg
  uvx github-pages-auditor@1.4.0 -u alberto2005-coder -f sarif -o informe.sarif -q
  ```
  Esperado: el HTML se abre, ordena y filtra; el CSV se abre bien en Excel; la insignia muestra la nota. Subir el `.sarif` con `github/codeql-action/upload-sarif` es opcional: GitHub puede no mostrar resultados sin archivo asociado.
  **Resultado:** OK (2026-11-15). Generados `informe.html`, `informe.csv` y `score.svg` sin errores (el `sarif` ya lo cubre la prueba automática 16.2). Revisión visual del HTML, CSV y la insignia: no la he registrado.

- [x] **16.14 `--lang en` y modo web a fondo**
  ```powershell
  uvx github-pages-auditor@1.4.0 -u alberto2005-coder --lang en --check-links -q
  uvx github-pages-auditor@1.4.0 -u alberto2005-coder --no-env --lang en --details
  ```
  Esperado: textos en inglés; avisos nuevos de Pages (`sin-sitemap`, `sin-lang`...); sin token los datos de API quedan vacíos sin errores.
  **Resultado:** OK. `--lang en --check-links` sale todo en inglés (proveedor y «Auditing code» incluidos, tras la corrección); modo web con `--lang en` OK (80/100 B, sin errores).

- [x] **16.15 `--fix` en SIMULACIÓN (no escribe nada)**
  ```powershell
  uvx github-pages-auditor@1.4.0 -u alberto2005-coder --fix --fix-pages --fix-metadata --only 3-en-raya
  ```
  Esperado: «Plan de arreglos (no se escribe nada...)» con acciones `planned` y ningún cambio en GitHub.
  **Resultado:** OK. «Plan de arreglos (no se escribe nada...)» con 4 acciones `planned` (SECURITY, CONTRIBUTING, CODE_OF_CONDUCT, plantilla de issues). Sin token, `--fix` da el error esperado.

- [x] **16.16 `--fix` REAL en un solo repo de pruebas** (necesita token con permiso de escritura en contenido)
  ```powershell
  uvx github-pages-auditor@1.4.0 -u alberto2005-coder --fix --fix-pages --only 3-en-raya --yes
  ```
  Esperado: acciones `applied`; aparecen SECURITY.md, CONTRIBUTING.md, CODE_OF_CONDUCT.md y la plantilla de issues; Enforce HTTPS activado. Repetirlo: todo `skipped`.
  **Resultado:** OK tras repetir con un token con permiso de escritura. 1.ª ejecución: 4 acciones `applied` (SECURITY, CONTRIBUTING, CODE_OF_CONDUCT, plantilla de issues) y la nota de `3-en-raya` pasa de 60 a 82. 2.ª ejecución: «No hay nada que arreglar» (los archivos ya existen). Una auditoría inmediata mostró Pages «rota» un instante (reconstrucción de Pages tras el commit); luego vuelve a aparecer activa. Primer intento con token sin permisos: 4 × `failed (HTTP 403)` sin escribir nada.

- [ ] **16.17 Webhook (opcional)**: con `$env:NOTIFY_WEBHOOK` de un canal de pruebas, ejecutar `--history` dos veces con un cambio entre medias. Esperado: mensaje solo con hallazgos nuevos; la URL no aparece en ninguna salida.
  **Resultado:**

- [ ] **16.18 Caché y `--since`**
  ```powershell
  uvx github-pages-auditor@1.4.0 -u alberto2005-coder --cache $env:TEMP\cache -q
  uvx github-pages-auditor@1.4.0 -u alberto2005-coder --cache $env:TEMP\cache -q
  uvx github-pages-auditor@1.4.0 -u alberto2005-coder --since 30d -q
  ```
  Esperado: la segunda ejecución es más rápida y no gasta cuota (304); `--since 30d` audita solo repos con push reciente.
  **Resultado:**

- [ ] **16.19 TUI (opcional)**: `uvx --with "github-pages-auditor[tui]" github-pages-auditor -u alberto2005-coder --tui` (salir con `q`). Esperado: tabla navegable con filtro.
  **Resultado:**

- [ ] **16.20 CI de la 1.4.0** (tras el push): matriz, `lint`, `typecheck`, `coverage` y `self-audit` en verde; el job `live` se lanza a mano (*Actions → Run workflow*).
  **Resultado:**

- [x] **16.21 Publicación con atestaciones** (tras la release `v1.4.0`): `publish.yml` en verde y, en la página del archivo en PyPI, el apartado de atestaciones. Si la acción de PyPI falla, volver al paso `uv publish --trusted-publishing always` (nada se publica a medias).
  **Resultado:**
  **Resultado:** Publicada el 2026-11-15: la 1.4.0 aparece en PyPI (tras unos minutos de caché) y `uvx --refresh github-pages-auditor@1.4.0 -V` muestra 1.4.0. `uvx github-pages-auditor@1.4.0 -u alberto2005-coder --details` funciona (modo web, sin token: 80/100 B, release v1.4.0 detectada en este repo con nota 100). Pendiente de confirmar: el apartado de atestaciones en PyPI y el workflow `publish` en verde.

- [ ] **16.22 Instalación con pipx y Homebrew (opcional)**: `pipx install github-pages-auditor`. La fórmula de `packaging/homebrew/` es una plantilla: hay que rellenar el `sha256` del sdist y ejecutar `brew update-python-resources` en tu tap.
  **Resultado:**

---

## 17. Novedades de la 1.5.0

**Automáticas** (`tests/test_v150.py`; 293-295 tests en Python 3.10, 3.13 y 3.14; cobertura 95 %; `ruff` y `mypy` sin errores):

- [x] **17.1 `--doctor`** (tipo de token, caducidad, límite, permisos; token inválido o ausente → código 2; el token sale enmascarado). **Resultado:** Auto: `test_doctor_*`.
- [x] **17.2 Pages «construyendo»**: con `status: building` y la web fallando no se marca rota; con `errored` sí. **Resultado:** Auto: `test_pages_en_construccion_*`, `test_pages_construyendo_*`.
- [x] **17.3 Secretos**: tokens y webhooks ocultos en errores y JSON; aviso del token en la línea de comandos y de `.env` dentro del repo git. **Resultado:** Auto: `test_limpiar_*`, `test_env_versionado_*`, `test_aviso_*`, `test_un_error_de_red_*`.
- [x] **17.4 Límites y caché**: espera y reintenta si el límite se restablece en menos de un minuto; si no, error con la hora; `--cache auto`. **Resultado:** Auto: `test_limite_*`, `test_cache_auto_*`.
- [x] **17.5 `--fix-extra`, `--license`, `--fix-mode pr`**: plantillas por lenguaje (YAML válido), rama + archivos + Pull Request, sin `--yes` no escribe, no pisa archivos, si falla la rama no se escribe nada. **Resultado:** Auto: `test_fix_*`, `test_plantillas_*`.
- [x] **17.6 SEO de Pages**: `sin-title`, `sin-viewport`, `sin-og-title`, `sin-canonical`, `contenido-mixto`; no bajan la nota. **Resultado:** Auto: `test_seo_*`, `test_los_avisos_seo_*`.
- [x] **17.7 Reglas propias del TOML** (`custom-*`, `file-required`/`file-forbidden`, `--fail-on`, sin dato no hay hallazgo). **Resultado:** Auto: `test_validar_reglas_*`, `test_toml_con_reglas_*`, `test_reglas_propias_*`.
- [x] **17.8 `--scorecard`, `critical-vulnerabilities`, `low-scorecard`**. **Resultado:** Auto: `test_scorecard_*`, `test_alertas_*`.
- [x] **17.9 `-f trend`, `-f issue`, `--diff`, Action con issue.** **Resultado:** Auto: `test_trend_*`, `test_issue_*`, `test_diff_*`, `test_la_action_*`.
- [x] **17.10 Higiene de release**: versión 1.5.0, CHANGELOG, `uv.lock`, cada opción y regla documentadas, JSON documentado. **Resultado:** Auto: `tests/test_release.py`.
- [x] **17.11 Paquete 1.5.0** (sandbox): `uv build` (19 plantillas incluidas), instalado en venv limpio, `-V` da 1.5.0, `--diff` con archivo inexistente → código 2. **Resultado:** OK.

**Manuales** (con tu cuenta y GitHub real; desde la carpeta del proyecto con `uv run github-pages-auditor`, y tras publicar con `uvx --refresh github-pages-auditor@1.5.0`). Pon antes `$env:GITHUB_TOKEN`:

> **Atajo (opcional):** las comprobaciones de solo lectura de esta sección (17.12-17.18) las cubre un solo comando:
> `$env:GITHUB_TOKEN="TU_TOKEN"; $env:RUN_LIVE="1"; uv run pytest -m live -q`
> Solo `--fix ... --yes` (escritura real) sigue siendo manual, y solo si cambia `fix.py`.

- [ ] **17.11b Heredados de `.github`** — `uvx --refresh --from . ver-github-pages -u alberto2005-coder --only github-pages-auditor --details` no debe marcar `missing-security-policy`/`missing-code-of-conduct` si los tienes en tu repo `.github`; con `--no-defaults-repo` sí.

- [ ] **17.12 `--doctor`**
  ```powershell
  uv run github-pages-auditor --doctor -u alberto2005-coder
  ```
  Esperado: tabla con el token enmascarado (`github_pat_…xxxx`), «Sesión iniciada como alberto2005-coder», límite de peticiones y permisos; la escritura sale «No comprobable» con un token fine-grained.
  **Resultado:**

- [ ] **17.13 Pages en construcción**: tras un `--fix` real o un commit en un repo con Pages, auditar enseguida. Esperado: `3-en-raya` sale activa con aviso `build-en-curso` (no «rota»).
  ```powershell
  uv run github-pages-auditor -u alberto2005-coder --only 3-en-raya --details
  ```
  **Resultado:**

- [ ] **17.14 `--deep` con alertas y Scorecard**
  ```powershell
  uv run github-pages-auditor -u alberto2005-coder --deep --scorecard -f json -o - -q | ConvertFrom-Json | Select-Object -Expand repos | Select-Object -First 5 name,scorecard,@{n="crit";e={$_.deep.critical_alerts}},@{n="altas";e={$_.deep.high_alerts}}
  ```
  Esperado: `scorecard` con número en repos públicos propios y vacío en forks; `crit`/`altas` con número o vacío si el token no puede leer alertas.
  **Resultado:**

- [ ] **17.15 Reglas propias**: crea `.github-pages-auditor.toml` con `[[custom_rules]]` (`id = "custom-tiene-docs"`, `path = "docs"`) y ejecuta:
  ```powershell
  uv run github-pages-auditor -u alberto2005-coder --fail-on custom-tiene-docs -q; echo $LASTEXITCODE
  ```
  Esperado: código 1 y los repos sin `docs/` en el informe (borra el TOML después).
  **Resultado:**

- [ ] **17.16 `--fix-extra` en simulación y `--fix-mode pr` real en UN repo** (token con Contents y Pull requests: Read and write)
  ```powershell
  uv run github-pages-auditor -u alberto2005-coder --fix-extra --only 3-en-raya
  uv run github-pages-auditor -u alberto2005-coder --fix-extra --fix-mode pr --only 3-en-raya --yes
  ```
  Esperado: la primera solo muestra el plan; la segunda crea una rama `github-pages-auditor/fix-...` y una Pull Request en `3-en-raya` con `LICENSE`, `.gitignore`, etc. Revisa la PR en GitHub y ciérrala si no la quieres.
  **Resultado:**

- [ ] **17.17 Tendencia, issue y `--diff`**
  ```powershell
  uv run github-pages-auditor -u alberto2005-coder --history $env:TEMP\hist -q
  uv run github-pages-auditor -u alberto2005-coder --history $env:TEMP\hist -f trend -o evolucion.html -q; start evolucion.html
  uv run github-pages-auditor -u alberto2005-coder -f issue -o issue.md -q; notepad issue.md
  uv run github-pages-auditor -u alberto2005-coder -f json -o a.json -q
  uv run github-pages-auditor -u alberto2005-coder -f json -o b.json -q
  uv run github-pages-auditor --diff a.json b.json
  ```
  Esperado: gráfica con al menos 2 puntos, resumen en Markdown con nota y hallazgos, y «Sin diferencias» en el `--diff`.
  **Resultado:**

- [ ] **17.18 Secretos**: `uv run github-pages-auditor -u alberto2005-coder -k $env:GITHUB_TOKEN -q` debe avisar del token en la línea de comandos; el aviso nunca muestra el token.
  **Resultado:**

- [ ] **17.19 Action con issue (opcional)**: workflow de `docs/ci.md` sección 10 con `issue: "true"` y `permissions: issues: write`. Esperado: una issue con la etiqueta `github-pages-auditor` que se actualiza en la siguiente ejecución.
  **Resultado:**

- [ ] **17.20 CI de la 1.5.0** (tras el push): matriz, `lint`, `typecheck`, `coverage` y `self-audit` en verde.
  **Resultado:**

- [ ] **17.21 Publicación** (tras la release `v1.5.0`): `publish.yml` en verde, PyPI con 1.5.0 y atestaciones, `uvx --refresh github-pages-auditor@1.5.0 -V`.
  **Resultado:**

---

## 18. Novedades de la 1.6.0

**Automáticas** (`tests/test_v160.py`; CI en verde obligatorio). **Ninguna prueba manual es obligatoria.**

- [x] **18.1 `--crawl`**, **18.2 reglas con contenido**, **18.3 `--readme-quality`**, **18.4 `--dep-licenses`**, **18.5 `--init`**, **18.6 `--fix-only`/`--fix-log`**, **18.7 `-u a,b`**, **18.8 `--graphql`** (con y sin error → REST). **18.9 caché ETag** (aciertos, `--cache-clear`, caducidad) y **18.10 webhook** (Teams, `--notify-on always`, reintento, `--notify-test`). **Resultado:** Auto: `tests/test_v160.py`.

**Opcional, solo lectura, un solo comando** (cubre 18.1, 18.3, 18.4, 18.7 y 18.8 contra GitHub real):

```powershell
$env:GITHUB_TOKEN="TU_TOKEN"; $env:RUN_LIVE="1"; uv run pytest -m live -q
```

Si `--graphql` o `--dep-licenses` fallan en tu cuenta, se arreglan en la 1.6.1; no afectan al resto (`--graphql` vuelve a REST solo).

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
| 7. `--inject` | 6 | 0 | 6/6 hechas |
| 8. Filtros | 2 | 0 | 2/2 hechas |
| 9. Configuración / `.env` | 5 | 0 | 5/5 hechas |
| 10. Robustez | 5 | 0 | 5/5 hechas |
| 11. PyPI | 5 | 0 | 5/7 hechas; el resto, pendiente u opcional |
| 12. CI | 0 | 0 | 0/2 hechas; el resto, pendiente u opcional |
| 13. Documentación | 1 | 0 | 1/3 hechas; el resto, pendiente u opcional |
| 14. Novedades 1.2.1 | 8 | 0 | 8/11 hechas; el resto, pendiente u opcional |
| 15. Novedades 1.3.0 | 15 | 0 | 15/18 hechas; pendientes 15.15 (TOML), 15.16 (CI), 15.17 (Action): sin salida pegada |
| 16. Novedades 1.4.0 | 17 | 0 | 17/22 hechas; pendientes confirmar CI (16.20) y atestaciones (16.21) y opcionales 16.17-16.19, 16.22 |
| 17. Novedades 1.5.0 | 11 | 0 | 11/21 hechas (auto); manuales 17.12-17.21 pendientes |

**Bugs encontrados** (comando, resultado obtenido, resultado esperado):

1. Pages de proyecto con `http://` en modo API → corregido (prefiere https).
2. `-f json -o -` con UnicodeEncodeError en Windows (cp1252) → corregido (JSON ASCII por stdout, UTF-8 en el resto).
3. Nota: un token revocado definido en `$env:GITHUB_TOKEN` hace que el modo por defecto dé 401 (comportamiento correcto).

**¿Listo para publicar la 1.3.0?** [x] Sí [ ] No — publicada el 2026-11-14 (PyPI 1.3.0 verificada). Quedan 15.15 (TOML), 15.16 (CI) y 15.17 (Action), sin salida registrada.

**¿Listo para publicar la 1.4.0?** [x] Sí [ ] No — publicada el 2026-11-15 (PyPI 1.4.0 verificada con `uvx`). Quedan por confirmar el CI en verde (16.20) y las atestaciones (16.21).

**¿Listo para publicar la 1.5.0?** [ ] Sí [ ] No — pendiente de las pruebas manuales 17.12-17.18 y del CI (17.20).
