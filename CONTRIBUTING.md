# Contributing to DuckTap

Thanks for your interest. DuckTap is a small, fast-moving project and outside
contributions are genuinely welcome — from a one-line catalog entry to a full
new discoverer.

---

## Quickest way to contribute: add a catalog entry

The catalog is a folder of YAML files under `catalog/`. Adding a new API takes
about 10 minutes and zero Python knowledge. We need entries for every popular
API; check the [open issues](https://github.com/zanni098/DuckTap/issues?q=is%3Aopen+label%3A%22good+first+issue%22) for specific requests.

```yaml
# catalog/yourapi.yaml
name: yourapi
description: One sentence — what does this API do?
spec_url: https://example.com/openapi.yaml   # or a HAR file URL
home_url: https://example.com
auth:
  type: bearer          # bearer | apikey | basic | oauth2 | none
  env_var: YOURAPI_KEY  # env var agents should set
tags:
  - productivity        # pick from: productivity, devtools, payments,
                        # messaging, ai, data, infra, crm, media, other
```

Open a PR titled `catalog: add <yourapi>`. That's it.

---

## Local setup

```bash
git clone https://github.com/zanni098/DuckTap
cd DuckTap
pip install -e ".[dev]"        # installs ducktap + all dev deps
playwright install chromium    # only needed for browser-sniff features
```

Verify everything works:

```bash
ducktap --version
python -m pytest tests/ -q     # should be 44 passed, 0 failed
```

---

## Project layout

```
src/ducktap/
├── core/           APISpec pydantic model + pipeline runner
├── discovery/      OpenAPI, HAR, browser-sniff discoverers
├── generator/      python-cli, mcp-server, skill generators + Jinja2 templates
│   └── templates/
│       ├── cli/    commands.py.j2, client.py.j2, main.py.j2, …
│       ├── mcp/    server.py.j2
│       └── skill/  SKILL.md.j2, cursor.mdc.j2, tools.json.j2
├── verify/         scorecard + shipcheck
├── catalog/        catalog loader (YAML files live at repo root /catalog/)
├── plugins/        plugin registry + built-in GraphQL plugin
├── llm/            LiteLLM abstraction (used by polish step, v0.2.x)
└── webui/          FastAPI dashboard
catalog/            one YAML file per API
tests/
docs/
```

---

## Making a change

1. **Fork** the repo and create a branch: `git checkout -b feat/your-thing`
2. **Write tests first** if you're changing behaviour. Tests live in `tests/`
   and use `pytest`. Generated CLI behaviour is tested via `httpx.MockTransport`
   in `tests/test_generated_cli_runtime.py` — follow the patterns there.
3. **Lint before pushing**: `ruff check src tests` (CI will block on failures)
4. **Run the full suite**: `python -m pytest tests/ -q`
5. Open a PR against `main`. Keep the title in the form
   `<type>: <short description>` — e.g. `feat: add Slack catalog entry`,
   `fix: resolve $ref in allOf schemas`, `docs: add plugin authoring guide`.

---

## Types of contribution

| Type | Where to look | Notes |
|---|---|---|
| New catalog entry | `catalog/` | One YAML file, no Python needed |
| Bug fix | [open issues](https://github.com/zanni098/DuckTap/issues) | Link the issue in your PR |
| New discoverer (e.g. Postman) | `src/ducktap/discovery/` | Must implement `Discoverer` protocol, add test |
| Template improvement | `src/ducktap/generator/templates/` | Run `ducktap press tests/fixtures/petstore.yaml` and eyeball the diff |
| New generator (e.g. TypeScript CLI) | `src/ducktap/generator/` | See `python_cli.py` as the reference implementation |
| Scorecard dimension | `src/ducktap/verify/scorecard.py` | Add a test that exercises the new dimension |
| Dashboard feature | `src/ducktap/webui/` | FastAPI + vanilla JS, no bundler |

---

## Code style

- **Python 3.11+**, formatted and linted with `ruff` (config in `pyproject.toml`)
- **Pydantic v2** for all data models
- **No new required dependencies** without discussion — keep the install lightweight
- Type annotations on all public functions
- Docstrings on public classes and non-obvious functions

---

## Commit messages

```
feat: add Twilio catalog entry
fix: resolve relative $ref paths in OpenAPI 3.1 specs
docs: document the plugin entry-point protocol
test: add runtime test for --format=csv with nested arrays
chore: bump ruff to 0.9
```

One subject line, imperative mood, under 72 chars. Body optional.

---

## Questions

Open a [GitHub Discussion](https://github.com/zanni098/DuckTap/discussions) or
drop a comment on the relevant issue. PRs don't need to be perfect on the first
push — open a draft early if you want feedback on direction.
