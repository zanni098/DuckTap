# Agent notes for DuckTap

## Build / test commands

- Install dev deps: `pip install -e ".[dev]"`
- Run unit tests: `pytest -q`
- Lint: `ruff check src tests`
- Type check (CI-gated, must pass): `mypy`

## End-to-end smoke

```bash
ducktap press tests/fixtures/petstore.yaml --out ./out
ducktap shipcheck petstore --out-dir ./out
```

## Layout

- `src/ducktap/` — package
- `src/ducktap/generator/templates/` — Jinja2 templates (use `StrictUndefined`)
- `catalog/*.yaml` — recipe library
- `skills/` — Claude Code skills that drive DuckTap itself

## Conventions

- Generated CLIs are named `<api>-dt-cli`; MCP servers `<api>-dt-mcp`;
  Claude skills `ducktap-<api>`.
- Discoverers and generators are plugins (see `docs/PLUGINS.md`); register them
  with `ducktap.core.plugins.register_*`.
- Don't break the `APISpec` schema casually — every generator depends on it.
