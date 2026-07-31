# Agent notes for DuckTap

## Build / test commands

- Install dev deps: `pip install -e ".[dev]"`
- Run unit tests: `pytest -q`
- Lint: `ruff check src tests`
- Type check (CI-gated, must pass): `mypy`
- Compile generated Go/Rust/TS CLIs (needs go, cargo, node):
  `DUCKTAP_COMPILE_TESTS=1 pytest -q tests/test_generated_multilang.py`

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
  with `ducktap.core.plugins.register_*`, **and** import them in
  `plugins.autoload_builtins()` — `discover()` looks discoverers up by name, so
  a module nobody imports is a feature that silently does not exist.
- Don't break the `APISpec` schema casually — every generator depends on it.
- Invariants every generator needs (slug name, unique operation ids) belong in
  `APISpec.normalize()`, not in the generators.
- Anything that becomes an identifier in generated code goes through
  `core.naming.safe_identifier` (keywords!); anything that becomes a package
  version goes through `pep440_version` / `semver_version`.
- `press` is deterministic by default. Keep it that way: LLM steps are opt-in
  (`--llm`) and must fall back cleanly when `litellm` is not installed.
- The generated skill is a contract — if you change how commands or flags are
  named, `tests/test_skill_matches_cli.py` must still pass.
