# Pruebas manuales — github-pages-auditor v1.2.0

Marca cada prueba con `[x]` cuando pase, `[!]` si falla, y anota lo que veas en **Resultado**.
Los comandos están pensados para **PowerShell** en la carpeta del proyecto. Los números de ejemplo
(82 repos, 12 Pages...) son los de la ejecución del 2026-11-11 y pueden cambiar si cambian tus repos.

| Dato | Valor |
| --- | --- |
| Fecha | |
| Versión probada | 1.2.0 |
| Sistema / Python | |
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
  Esperado: `122 passed`.
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
  Esperado: `github-pages-auditor 1.2.0` + créditos.
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

- [ ] **3.3 URLs reales de Pages** (⚠️ en la v1.2.0 del 12-nov salían `http://` en proyectos; arreglado ahora → repetir y exigir `https://`)
  Esperado: las URLs salen con tu dominio personalizado (`html_url` de GitHub), también sin `-w`.
  **Resultado:**

- [ ] **3.4 Forzar modo web con token**
  ```powershell
  uv run github-pages-auditor -u alberto2005-coder --no-api
  ```
  Esperado: proveedor "Scraping Web Público".
  **Resultado:**

- [x] **3.5 Token falso**
  ```powershell
  uv run github-pages-auditor -u alberto2005-coder -k token_falso; $LASTEXITCODE
  ```
  Esperado: "GitHub rechazó el token (401)", sin traceback, código `2`.
  **Resultado:** OK: 401 sin traceback, código 2

- [ ] **3.6 El token no se filtra** (opcional, avanzado)
  Ejecuta con un proxy/inspector de tráfico (p. ej. mitmproxy) y comprueba que la cabecera `Authorization` solo aparece en peticiones a `api.github.com`.
  **Resultado:**

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

- [!] **4.2 JSON por stdout (apto para tuberías)** — FALLÓ en v1.2.0 con UnicodeEncodeError (cp1252); corregido, repetir
  ```powershell
  uv run github-pages-auditor -u alberto2005-coder -f json -o - -q | ConvertFrom-Json | Select-Object -Expand summary
  ```
  Esperado: se imprime el resumen sin errores de parseo (stdout es JSON puro; la interfaz va a stderr).
  **Resultado:**

- [x] **4.3 Markdown**
  ```powershell
  uv run github-pages-auditor -u alberto2005-coder -f md
  ```
  Esperado: `paginas_github.md` con la tabla "Demos en vivo" entre los marcadores, ordenada alfabéticamente, sin forks, con enlace al repo y "Abrir" a la demo. Los textos con `|` no rompen la tabla.
  **Resultado:** OK (en PowerShell usar Get-Content -Encoding utf8 para ver bien los acentos)

- [ ] **4.4 `-q` (silencioso)**
  ```powershell
  uv run github-pages-auditor -u alberto2005-coder -q
  ```
  Esperado: no se ven tablas ni barra de progreso; el archivo se escribe igualmente.
  **Resultado:**

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
  **Resultado:** OK: código 2

- [ ] **5.6 Sin repositorios → 3**
  ```powershell
  uv run github-pages-auditor -u alberto2005-coder --exclude-forks --exclude-archived -q --fail-on any; $LASTEXITCODE
  ```
  Esperado: este NO da 3 (tienes repos propios). Para forzar el 3, usa una cuenta sin repos públicos y comprueba el código `3` y que no se crea archivo.
  **Resultado:**

- [ ] **5.7 Ctrl+C → 130**
  Lanza una auditoría y pulsa Ctrl+C a media barra.
  Esperado: "Operación cancelada" y código `130`, sin traceback.
  **Resultado:**

- [x] **5.8 Carpeta de salida inexistente**
  ```powershell
  uv run github-pages-auditor -u alberto2005-coder -o C:\ruta\que\no\existe\x.txt; $LASTEXITCODE
  ```
  Esperado: falla al instante (sin barra de progreso) con "La carpeta de salida no existe" y código `2`.
  **Resultado:** OK: código 2

---

## 6. Salud de Pages

- [ ] **6.1 Pages sanas**
  ```powershell
  uv run github-pages-auditor -u alberto2005-coder -k $env:GITHUB_TOKEN -f json -o - -q | ConvertFrom-Json | Select-Object -Expand repos | Where-Object { $_.pages } | Select-Object name, @{n='estado';e={$_.pages.status}}, @{n='ms';e={$_.pages.response_ms}}, @{n='titulo';e={$_.pages.title}}
  ```
  Esperado: tus ~12 Pages con estado `ok`, tiempo de respuesta y título de la página.
  **Resultado:**

- [ ] **6.2 Pages rota (404 / sin index)** — requiere un repo de prueba
  1. Crea un repo `pruebas-pages-roto` y activa Pages (Settings → Pages) **sin** subir `index.html`.
  2. Ejecuta con token:
  ```powershell
  uv run github-pages-auditor -u alberto2005-coder -k $env:GITHUB_TOKEN --fail-on broken-pages; $LASTEXITCODE
  ```
  Esperado: aparece la fila "Pages rotas", la sección "GITHUB PAGES ROTAS" en el `.txt` con `404`, y código `1`.
  **Resultado:**

- [ ] **6.3 Sin token no marca "rotas"**
  Repite 6.2 con `--no-api`. Esperado: ese repo simplemente no aparece como Pages (no se puede saber que debería tenerla); no hay "Pages rotas".
  **Resultado:**

- [ ] **6.4 Aviso de HTTPS no forzado / build** (opcional)
  En un repo de prueba desactiva "Enforce HTTPS" y comprueba que el JSON trae `warnings: ["https-no-forzado"]`.
  **Resultado:**

- [ ] **6.5 Dominio personalizado caído/mal configurado** (opcional)
  Apunta temporalmente un CNAME a un dominio sin DNS. Esperado (con token): estado `roto` con `sin-conexion` o `tls-error`.
  **Resultado:**

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

- [ ] **7.6 `--inject` + `-o`**
  ```powershell
  uv run github-pages-auditor -u alberto2005-coder --inject prueba-readme.md -o informe.txt
  ```
  Esperado: actualiza el README **y** escribe `informe.txt`.
  **Resultado:**

---

## 8. Filtros

- [ ] **8.1 `--exclude-forks`**
  ```powershell
  uv run github-pages-auditor -u alberto2005-coder --exclude-forks -q -f json -o - | ConvertFrom-Json | Select-Object -Expand summary
  ```
  Esperado: `total` ≈ 71 (82 − 11 forks) y `forks` = 0.
  **Resultado:**

- [ ] **8.2 `--exclude-archived`**
  Esperado: `archived` = 0 y menos peticiones (no se analizan los archivados).
  **Resultado:**

---

## 9. Configuración y `.env`

- [ ] **9.1 Solo `.env`**
  ```powershell
  Copy-Item .env.example .env
  # edita .env y rellena solo USUARIO_GITHUB=alberto2005-coder
  uv run github-pages-auditor
  ```
  Esperado: funciona sin parámetros.
  **Resultado:**

- [ ] **9.2 `--no-env`**
  ```powershell
  uv run github-pages-auditor --no-env; $LASTEXITCODE
  ```
  Esperado: vuelve a pedir el usuario (código `2`).
  **Resultado:**

- [ ] **9.3 Prioridad parámetros > entorno**
  Con `USUARIO_GITHUB=otro` en `.env`, ejecuta con `-u alberto2005-coder`. Esperado: audita `alberto2005-coder`.
  **Resultado:**

- [ ] **9.4 Variables vacías se ignoran**
  Deja `GITHUB_TOKEN=` vacío en `.env`. Esperado: modo web (no intenta usar la API con un token vacío).
  **Resultado:**

- [ ] **9.5 El `.env` se encuentra desde otra carpeta** (instalado como paquete)
  Instala (`uv tool install .`), colócate en una carpeta con un `.env` y ejecuta `github-pages-auditor`. Esperado: lo lee del directorio actual.
  **Resultado:**

---

## 10. Robustez

- [ ] **10.1 Sin conexión**
  Desactiva la red y ejecuta. Esperado: mensaje de error de red claro y código `2`, sin traceback.
  **Resultado:**

- [ ] **10.2 `--timeout` bajo**
  ```powershell
  uv run github-pages-auditor -u alberto2005-coder --timeout 0.05 -q -f json -o - | ConvertFrom-Json | Select-Object -Expand summary
  ```
  Esperado: no se cuelga; algunos repos pueden salir en `errors` (sección "no analizados") sin tumbar el resto.
  **Resultado:**

- [ ] **10.3 `--workers 1` y `--workers 40`**
  Esperado: funcionan y dan los mismos resultados; el orden del informe es siempre el mismo.
  **Resultado:**

- [ ] **10.4 Orden determinista**
  Ejecuta dos veces `-f json` y compara los `repos` (ignorando `generated_at`). Esperado: idénticos.
  **Resultado:**

- [ ] **10.5 Límite de tasa sin token** (opcional)
  Ejecuta el modo web varias veces seguidas hasta recibir un 429. Esperado: mensaje "GitHub limitó las peticiones" sugiriendo usar token, código `2`.
  **Resultado:**

---

## 11. Publicación en PyPI (tras la release)

- [ ] **11.1 Configurar el publisher** (una sola vez)
  pypi.org → Publishing → pending publisher: proyecto `github-pages-auditor`, owner `alberto2005-coder`, repo `github-pages-auditor`, workflow `publish.yml`, environment `pypi`. Crea el environment `pypi` en GitHub.
  **Resultado:**

- [ ] **11.2 Release y workflow**
  Commit, `git tag v1.2.0`, push y crea la Release. Esperado: en Actions pasa "Publish to PyPI" (build + tests + publish).
  **Resultado:**

- [ ] **11.3 El tag debe coincidir con la versión**
  (Opcional) crea una release con un tag distinto (`v9.9.9`). Esperado: el workflow falla en "Check that the tag matches the package version" y no publica.
  **Resultado:**

- [ ] **11.4 `uvx` sin instalar nada**
  ```powershell
  uvx github-pages-auditor -V
  uvx github-pages-auditor -u alberto2005-coder -f json -o - -q
  ```
  Esperado: versión 1.2.0 con créditos y JSON válido.
  **Resultado:**

- [ ] **11.5 Instalación con `pip` en un entorno limpio**
  ```powershell
  python -m venv prueba-venv; .\prueba-venv\Scripts\pip install github-pages-auditor; .\prueba-venv\Scripts\github-pages-auditor -V
  ```
  **Resultado:**

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

- [ ] **13.2 CHANGELOG**: cambia «Unreleased» por la fecha de la release de la 1.2.0.
  **Resultado:**

- [ ] **13.3 Descripción de la release v1.1.0**: corrige la URL de instalación a `github-pages-auditor.git@v1.1.0`.
  **Resultado:**

---

## Resumen final

| Bloque | Pasan | Fallan | Notas |
| --- | :---: | :---: | --- |
| 0. Preparación | | | |
| 1. Ayuda y errores de uso | | | |
| 2. Modo web | | | |
| 3. Modo API | | | |
| 4. Formatos | | | |
| 5. Códigos de salida | | | |
| 6. Salud de Pages | | | |
| 7. `--inject` | | | |
| 8. Filtros | | | |
| 9. Configuración / `.env` | | | |
| 10. Robustez | | | |
| 11. PyPI | | | |
| 12. CI | | | |
| 13. Documentación | | | |

**Bugs encontrados** (comando, resultado obtenido, resultado esperado):

1.
2.
3.

**¿Listo para publicar la 1.2.0?** [ ] Sí [ ] No — motivo:
