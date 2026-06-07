# Changelog

## 0.7.0 -- 2026-06-07

Multi-language generators are now reachable, compile-verified, and share an
agent-parity command bundle with the Python CLI.

### Added

- **Agent-parity bundle in the Go, Rust, and TypeScript CLIs** — the three
  non-Python generators now match the Python CLI on the agent-facing basics:
  - `--dry-run` global flag — prints the assembled request
    (method/path/url/query) as JSON and exits without calling the API.
  - `agent-context` command — emits a JSON manifest (cli, version, exit codes,
    and every operation's command/method/path/summary) so an agent can
    self-introspect without parsing `--help`.
  - **Typed exit codes** — `3` (404), `4` (401/403), `5` (other API error),
    `7` (429) on every command, mapped from the HTTP status.
  - `--base-url` override flag on all three.
- `tests/test_generated_multilang.py` — a render-smoke test (always on) plus
  per-language compile tests gated behind `DUCKTAP_COMPILE_TESTS=1`. The compile
  tests build each project *and* run `agent-context`, validating the shared
  manifest shape across languages.
- A `generated-clis` CI job that builds the generated Go, Rust, and TypeScript
  projects with their real toolchains on every push.
- Type checking (`mypy`) is now a required CI step.

### Fixed

- **Go/Rust/TypeScript generators were unreachable.** `autoload_builtins()`
  never imported them, so `ducktap press -t go-cli|rust-cli|typescript-cli`
  failed with "unknown target". All three are now registered by default.
- **TypeScript generator crashed on render** — it referenced an unregistered
  `json` Jinja filter. Fixed, plus string literals are now JSON-escaped so
  summaries/descriptions with quotes or newlines can't break the output.
- **Generated Go CLI did not compile** — `main.go` imported a `cmd` package
  that did not exist. Reworked to a flat, idiomatic cobra `cmd` package with a
  real `root.go`/`Execute()`; the HTTP client now decodes array responses.
- **Generated Rust CLI did not compile** (12 errors) — deduplicated colliding
  path/body argument fields, fixed borrow-of-temporary in query building,
  handled array query params, and silenced naming lints. Builds with **zero
  warnings**; switched reqwest to `rustls` to drop the system-OpenSSL build dep.
- **Generated TypeScript CLI did not type-check** — fixed the `../base` import
  depth and added a runnable `bin/run.js` entrypoint.

### Added

- `tests/test_generated_multilang.py` — a render-smoke test (always on) plus
  per-language compile tests gated behind `DUCKTAP_COMPILE_TESTS=1`.
- A `generated-clis` CI job that builds the generated Go, Rust, and TypeScript
  projects with their real toolchains on every push.
- Type checking (`mypy`) is now a required CI step.

## 0.6.0 -- 2026-05-26

Multi-language generators + deferred features shipped.

### Added

- **TypeScript CLI generator** (`src/ducktap/generator/typescript_cli.py`)
  -- oclif-based TypeScript CLI with per-command files, axios HTTP client,
  and standard npm packaging.
- **Go CLI generator** (`src/ducktap/generator/go_cli.py`)
  -- cobra-based Go CLI with internal HTTP client, single binary output.
- **Rust CLI generator** (`src/ducktap/generator/rust_cli.py`)
  -- clap-based Rust CLI with reqwest async client, Cargo packaging.
- **30+ catalog entries** -- expanded from 17 to 30 APIs
  (Spotify, Shopify, Mailchimp, Adyen, Slack, Linear, Supabase,
  Reddit, Twitch, Trello, Box, Postman, Zendesk).
- **Domain-specific SQLite tables** (`mirror.py.j2`)
  -- `domain_entities` table for per-endpoint structured storage.
- **Compound query commands** (`commands.py.j2`)
  -- `stale`, `health`, and `bottleneck` commands on every generated CLI.
- **2-tier scorecard** (`verify/scorecard.py`)
  -- new `domain_correctness` dimension scoring RESTful patterns,
  response schemas, and base URL validity.
- **Live API smoke test** (`cli.py`)
  -- `ducktap smoke <source>` probes GET endpoints and reports latency.
- **Emboss brand-stamp** (`emboss.py`)
  -- `ducktap emboss <name>` rewrites pyproject.toml and README
  with custom branding.
- **Vision screenshot reading** (`vision.py`)
  -- `ducktap vision <url>` captures a screenshot and sends it to
  a vision-capable LLM for API documentation extraction.

### Changed

- README updated: 30+ catalog entries, multi-language generators,
  compound query commands.

## 0.5.0 -- 2026-05-26

Publish to PyPI/GitHub + auto-generated CI + DuckTap Library.

### Added

- `ducktap publish {name}` (`src/ducktap/publish.py`)
  -- one-command publish workflow that runs shipcheck, commits code,
  creates/pushes a GitHub repo via `gh`, builds a wheel, and uploads
  to PyPI via `twine`. Supports `--dry-run`, `--private`, and
  `--skip-shipcheck`.
- Auto-generated GitHub Actions (`generator/templates/cli/.github/workflows/test_and_release.yml.j2`)
  -- every generated CLI now includes a CI workflow that runs pytest
  on push/PR and publishes to PyPI on release creation.
- DuckTap Library (`src/ducktap/library.py`)
  -- local JSON registry of printed CLIs. New `ducktap library`
  subcommands: `list`, `search`, `add`, `remove`.

### Changed

- `ROADMAP.md` "Known gaps" table updated: compound use-case recipes
  marked landed v0.4.0; deferred items now accurately labelled.

## 0.4.0 -- 2026-05-26

Compound queries + FTS5 search + DuckDB backend + macro recipes.

### Added

- **Compound command macros** (`src/ducktap/macros.py`)
  -- declarative YAML recipes that chain multiple API operations with
  Jinja2-style step references (`{{ steps[0].id }}`).
  New `ducktap macro` subcommands: `list`, `run`, `new`.
- **FTS5 full-text search** in generated CLI mirrors (`mirror.py.j2`)
  -- SQLite FTS5 virtual table with triggers keeps the search index in
  sync with the `records` table. `search()` now uses MATCH/rank instead
  of slow LIKE queries.
- **DuckDB backend option** (`mirror.py.j2`)
  -- set `DUCKTAP_MIRROR_BACKEND=duckdb` or pass `backend="duckdb"`
  to use DuckDB instead of sqlite3 for analytical workloads.
- **Top-level `query` command** in generated CLIs (`commands.py.j2`)
  -- `<api>-dt-cli query "SELECT ..."` as a shortcut to `data query`.

### Changed

- Generated `Mirror` class now supports pluggable backends via
  `_SQLiteBackend` and `_DuckDBBackend` internal adapters.

## 0.3.0 — 2026-05-26

Sniffing v2 + first-class GraphQL + community research.

### Added

- **GraphQL first-class discoverer** (`src/ducktap/plugins/builtin/graphql_intro.py`)
  — full introspection for Query, Mutation, and Subscription types,
  persisted query support, and proper type unwrapping (NON_NULL, LIST).
- **Crowd-sniff research** (`src/ducktap/crowd_sniff.py`)
  — DuckDuckGo web search + LiteLLM to study existing community CLIs and
  MCP servers for an API name, returning a structured report.
  Registered as `ducktap research --crowd`.
- **Smart action recording** (`src/ducktap/discovery/action_recorder.py`)
  — record clicks, fills, scrolls, waits, and navigation during a
  browser-sniff session. Save to JSON and replay later with
  `--replay-actions`.
- **mitmproxy-backed sniff** (`src/ducktap/discovery/mitm_sniff.py`)
  — alternative to headless Chromium. Run a local mitmproxy, browse with
  any client, then convert captured traffic into an APISpec.
- **Rate-limit + retry inference** — HAR discoverer now scans for
  `X-RateLimit-*`, `Retry-After`, and `429`/`503` responses. Inferred
  backoff strategy is stored in `APISpec.extensions`.
- **`APISpec.extensions`** field added for vendor extensions (used by
  rate-limit metadata).

### Fixed

- **Python 3.14 `CliRunner` compatibility** — tests that inspect
  `r.stderr` now pass `mix_stderr=False` to avoid Click's
  `ValueError: stderr not separately captured`.

## 0.1.2 — 2026-05-12

Quality pass. Generated CLIs are now actually usable end-to-end against
real APIs.

### Fixed

- **Spec naming**: titles like "Swagger Petstore - OpenAPI 3.0" now slugify
  to `petstore` instead of `swagger-petstore-openapi-3-0`, which cascades
  into project dir, binary name, and env-var prefix
  (`PETSTORE_TOKEN` instead of `SWAGGER_PETSTORE_OPENAPI_3_0_TOKEN`).
- **Relative server URLs**: when a spec ships `servers: [{url: /api/v3}]`
  and is fetched over HTTP, the discoverer now resolves it against the
  source URL, so the generated client gets a working absolute base_url.
- Generated client sends `Accept: application/json` and `User-Agent`.
- Generated client raises a clear `APIError` (instead of silently
  failing) when no `base_url` is configured.
- Flag collisions (e.g. `id` in path and body of the same operation)
  no longer crash Click at decorator time; the body-side flag is
  auto-renamed to `--body-<name>`.

### Changed

- Dropped redundant `--json/--no-json` flag (`--pretty` already toggles).
- Added `--debug` / `<NAME>_DEBUG` env var: logs requests to stderr
  with `Authorization`/`api_key`/`X-API-Key` redacted.
- Body decode boilerplate extracted into a `_coerce()` helper.
- `ducktap scorecard --fail-under N` exits 2 for CI gating.

### Tests

- New `tests/test_generated_cli_runtime.py`: presses a tiny spec, runs
  the generated CLI through `httpx.MockTransport`, and verifies query
  params, path substitution, POST bodies, 4xx-to-stderr, and absolute
  base_url resolution all work end-to-end.

## 0.1.1 — 2026-05-11

- First release published via PyPI Trusted Publishing (OIDC).
- Catalog loader now recurses one level into category subdirs, so the
  community catalog at `zanni098/ducktap-library` works without flattening.
- Lint fixes (E701/E702); CI ignores B008 for Typer's option default idiom.
- README: dashboard screenshot, demo block, PyPI + Release badges,
  community-library quick-start.

## 0.1.0 — 2026-05-11

Initial release. The lean loop end-to-end:

- OpenAPI / HAR / browser-sniff discoverers
- Python CLI + MCP server + skill generators
- Multi-LLM (LiteLLM)
- Plugin registry (entry points)
- Scorecard + shipcheck
- FastAPI dashboard
- Catalog (petstore, github, stripe)
