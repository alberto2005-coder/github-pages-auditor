# Recetas de CI / CI recipes

Todas usan `uvx`, así que no hay que instalar nada. / All of them use `uvx`, so nothing needs installing.

## 1. Fallar el job si hay hallazgos / Fail the job on findings

```yaml
- run: uvx github-pages-auditor -u ${{ github.repository_owner }} -k ${{ secrets.GITHUB_TOKEN }} -f json -o report.json --fail-on missing-license,broken-pages
```

Código de salida / exit code: `0` ok, `1` regla disparada / rule triggered, `2` error, `3` sin repos / no repos.

## 2. Resumen visible en el job / Job summary

`-f md` genera una tabla de tus demos; escribirla en `$GITHUB_STEP_SUMMARY` la muestra en la pestaña del job.
`-f md` writes a demos table; writing it to `$GITHUB_STEP_SUMMARY` shows it on the job page.

```yaml
- run: uvx github-pages-auditor -u ${{ github.repository_owner }} -f md -o "$GITHUB_STEP_SUMMARY" -q
```

## 3. Refrescar la tabla de demos de tu README cada semana / Refresh your README demos table weekly

Añade antes en tu README los marcadores / first add the markers to your README:

```markdown
<!-- github-pages-auditor:start -->
<!-- github-pages-auditor:end -->
```

```yaml
name: Update demos
on:
  schedule:
    - cron: "0 6 * * 1"
  workflow_dispatch:
permissions:
  contents: write
jobs:
  demos:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: uvx github-pages-auditor -u ${{ github.repository_owner }} -k ${{ secrets.GITHUB_TOKEN }} --inject README.md -q
      - run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git diff --quiet || (git commit -am "docs: actualizar demos" && git push)
```

## 4. Action reutilizable / Reusable Action

```yaml
- uses: alberto2005-coder/github-pages-auditor@v1.3.0
  with:
    user: ${{ github.repository_owner }}
    token: ${{ secrets.GITHUB_TOKEN }}
    fail-on: missing-license,broken-pages
```

Escribe anotaciones (`-f github`) y falla el job si se dispara una regla. / Writes annotations and fails the job when a rule triggers.

## 5. Solo hallazgos nuevos / Only new findings

Guarda el informe de la ejecución buena y compara con `--baseline` / keep the last good report and compare:

```bash
uvx github-pages-auditor -u USER -f json -o baseline.json -q          # una vez / once
uvx github-pages-auditor -u USER --baseline baseline.json --fail-on all -f github -q
```

## 6. Nota mínima y comparación con el histórico / Minimum score and history

```yaml
- uses: actions/cache@v4
  with: { path: history, key: auditor-history }
- run: uvx github-pages-auditor -u ${{ github.repository_owner }} -k ${{ secrets.GITHUB_TOKEN }} --history history --min-score 70 -f github -q
```

## 7. Informes / Reports

`-f html -o informe.html` (página autocontenida), `-f csv`, `-f badge -o score.svg` (insignia para el README) y `-f sarif`
(SARIF 2.1.0 con los hallazgos; subirlo con `github/codeql-action/upload-sarif` es una prueba manual, GitHub lo muestra según sus reglas de ubicación).

## 8. Aviso por webhook / Webhook alert

Guarda la URL en un secreto, nunca en el TOML ni en el log / keep the URL in a secret, never in the TOML:

```yaml
- run: uvx github-pages-auditor -u USER -k ${{ secrets.GITHUB_TOKEN }} --history history -q
  env:
    NOTIFY_WEBHOOK: ${{ secrets.DISCORD_WEBHOOK }}
```

## 9. Token / Token

En Actions `secrets.GITHUB_TOKEN` basta. Fuera de Actions, un token *fine-grained* sin permisos (solo repos públicos) es suficiente;
pásalo por la variable `GITHUB_TOKEN`, no con `-k`, para que no quede en el historial.
In Actions `secrets.GITHUB_TOKEN` is enough. Elsewhere, a fine-grained token with no permissions (public repos only) is enough;
pass it through the `GITHUB_TOKEN` variable rather than `-k` so it stays out of your shell history.

## 10. Issue semanal con el informe / Weekly report issue

La Action puede abrir (o actualizar) una issue con la nota, los hallazgos y los mejores y peores repos. Necesita `issues: write`:

```yaml
name: Auditoría semanal
on:
  schedule:
    - cron: "0 7 * * 1"
  workflow_dispatch:
permissions:
  contents: read
  issues: write
jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: alberto2005-coder/github-pages-auditor@master
        with:
          user: tu-usuario
          token: ${{ secrets.GITHUB_TOKEN }}
          issue: "true"
          args: "--exclude-forks --deep"
```

The Action can open or update one issue (label `github-pages-auditor`) with the score and findings. It needs `issues: write`.

## 11. Diagnóstico, comparación y tendencia / Doctor, diff and trend

```bash
github-pages-auditor --doctor                                  # qué puede hacer tu token
github-pages-auditor --diff antes.json despues.json            # qué ha cambiado entre dos informes
github-pages-auditor -u tu-usuario --history hist -f trend -o evolucion.html   # gráfica de la nota
github-pages-auditor -u tu-usuario --fix --fix-extra --fix-mode pr --yes        # arreglos mediante Pull Request
```

`--fix-mode pr` crea una rama y una Pull Request por repositorio; `Enforce HTTPS`, la descripción y los topics siguen aplicándose directamente porque no son archivos del repositorio.

