# Contribuir / Contributing

1. `uv sync` y `uv run pytest` (los tests no usan red). / `uv sync` and `uv run pytest` (tests use no network).
2. `uv run ruff check .` debe pasar. / must pass.
3. Cada novedad lleva test, entrada en `CHANGELOG.md` y documentación; el JSON solo puede **añadir** campos. / Each change needs tests, a CHANGELOG entry and docs; JSON may only gain fields.
