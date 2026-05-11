# Contributing to DuckTap

Thanks for your interest! DuckTap is MIT-licensed and welcomes PRs.

## Dev setup

```bash
git clone https://github.com/yourname/ducktap
cd ducktap
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev,sniff]"
playwright install chromium    # optional, for browser-sniff
pytest -q
```

## Adding a catalog entry

1. Create `catalog/<name>.yaml` matching `src/ducktap/catalog/registry.py:CatalogEntry`.
2. Run `ducktap catalog print <name>` to verify it generates.
3. PR with the YAML and a one-line summary in `CHANGELOG.md`.

## Adding a plugin (better!)

See `docs/PLUGINS.md`. Publish as its own PyPI package and we'll list it in the
README.

## Commit style

Conventional commits welcome but not required. PR titles like `feat(catalog): add Notion`, `fix(openapi): handle nullable enums`, `docs: …` work great.

## Code style

- `ruff check src tests` clean.
- Type hints encouraged; not enforced by CI.
- New code paths need at least one test.
