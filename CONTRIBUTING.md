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
name: yourapi                          # required — lowercase, matches the filename
display_name: Your API                 # human-readable name
description: One sentence — what does this API do?
category: devtools                     # see the list below
spec_url: https://example.com/openapi.yaml
spec_format: yaml                      # json | yaml | har | sniff
tier: official                         # official | community
homepage: https://example.com/docs
```

**Fields** are defined by `CatalogEntry` in `src/ducktap/catalog/registry.py` —
that model is the source of truth. Unknown keys are silently ignored, so a typo
won't raise an error; it will just quietly drop the value. Run
`ducktap catalog list` after adding your file and confirm your entry appears with
the right category.

`category` values currently in use: `ai`, `collaboration`, `commerce`,
`developer`, `entertainment`, `example`, `finance`, `maps`, `marketing`,
`monitoring`, `payments`, `productivity`, `project-management`,
`sales-and-crm`, `social`, `social-and-messaging`, `support`.

Reproduce this list with:

```python
from ducktap.catalog.registry import load_catalog
sorted({e.category for e in load_catalog().values()})
```

`spec_url` must point at a **machine-readable spec** — a `.json`/`.yaml` OpenAPI
document or a HAR file. An HTML documentation page will not work. Use
`spec_path` instead if the spec lives in this repo, or `sniff_url` if the API has
no published spec and needs browser sniffing.

Copy [`catalog/stripe.yaml`](catalog/stripe.yaml) as a working reference.

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
python -m pytest tests/ -q     # all tests should pass
```

---

## Project layout

```
src/ducktap/
├── core/           APISpec pydantic model + pipeline runner
├── discovery/      OpenAPI, HAR, browser-sniff discoverers
├── generator/      python/go/rust/typescript CLI, mcp-server, skill generators
│   └── templates/
│       ├── cli/    commands.py.j2, client.py.j2, main.py.j2, …
│       ├── mcp/    server.py.j2
│       └── skill/  SKILL.md.j2, cursor.mdc.j2, tools.json.j2
├── verify/         scorecard + shipcheck
├── catalog/        catalog loader (YAML files live at repo root /catalog/)
├── plugins/        plugin registry + built-in GraphQL plugin
├── llm/            LiteLLM abstraction (used by polish step)
├── webui/          FastAPI dashboard
└── *.py            top-level commands: macros, publish, emboss, library,
                    absorb, insight, vision, manifest, crowd_sniff
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
| New generator (e.g. Ruby, C#) | `src/ducktap/generator/` | Python/Go/Rust/TypeScript already exist — see `python_cli.py` as the reference |
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

## What gets merged

Merged readily, no discussion needed first:

- Catalog entries, and fixes to broken ones
- Template fixes and improvements to generated output
- Documentation, including fixes to this file
- Tests, especially ones that cover an untested edge case
- Plugins and new discoverers that follow the existing protocol

Please open an issue before writing code for:

- Anything adding a **required** dependency (optional extras are easier)
- Changes to the `APISpec` model in `core/spec.py` — everything downstream reads it
- Anything that makes `ducktap press` non-deterministic. Determinism is the whole
  point of the project; an LLM call in the default path won't be merged.

I try to respond to PRs within 48 hours. If it's been longer, ping the thread —
it means I missed the notification, not that the PR was rejected.

---

## Questions

Open a [GitHub Discussion](https://github.com/zanni098/DuckTap/discussions) or
drop a comment on the relevant issue. PRs don't need to be perfect on the first
push — open a draft early if you want feedback on direction.
