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

## 4. Token / Token

En Actions `secrets.GITHUB_TOKEN` basta. Fuera de Actions, un token *fine-grained* sin permisos (solo repos públicos) es suficiente;
pásalo por la variable `GITHUB_TOKEN`, no con `-k`, para que no quede en el historial.
In Actions `secrets.GITHUB_TOKEN` is enough. Elsewhere, a fine-grained token with no permissions (public repos only) is enough;
pass it through the `GITHUB_TOKEN` variable rather than `-k` so it stays out of your shell history.
