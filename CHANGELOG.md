# Changelog

## 0.8.2 -- 2026-07-31

A correctness, security and packaging pass over the whole repo. No new
features; several long-standing ways to get silently-wrong output are gone.

> **Note:** 0.8.1 was never tagged, so it never reached PyPI — the latest
> published release was 0.8.0. Releasing 0.8.2 ships the 0.8.1 work
> (`ducktap verify`, the rebuilt dashboard) along with everything below. The
> publish workflow now refuses to run when the tag and the package version
> disagree.

### Fixed — generated output was wrong or unusable

- **Recursive `$ref` schemas crashed `press`.** A schema referencing itself
  (GitHub, Stripe, Notion and most real specs) resolved into a cyclic object
  graph, and building the MCP tool schema walked it until `RecursionError`.
  `research` failed the same way with "Circular reference detected". The
  OpenAPI discoverer now materializes the resolved document into plain,
  acyclic data once, at the boundary.
- **A Python keyword as an `operationId` produced a CLI that would not parse**
  (`operationId: class` → `def class(...)`). Identifiers are now escaped per
  target language (Python, Go, Rust, TypeScript).
- **Duplicate operation ids silently dropped operations.** Two operations
  whose ids collide after snake-casing registered the same Click command, so
  the second overwrote the first. `APISpec.normalize()` now disambiguates ids
  for every discoverer.
- **Two parameters with the same name built the wrong request.** A path `id`
  and a body `id` shared one Click destination, so the body value landed in
  the URL and the body field was dropped. Flags and destinations are now
  disambiguated by location; the wire name is unchanged.
- **Generated packages could not be installed.** `version` was copied
  verbatim from `info.version`, so a spec versioned `2022-11-15` produced a
  `pyproject.toml` / `Cargo.toml` / `package.json` that pip, cargo and npm all
  reject. Versions are normalized to PEP 440 / semver.
- **The generated skill documented commands that do not exist.** `SKILL.md`,
  `cursor.mdc` and `tools.json` listed `<cli> get-pet-by-id --petId`, but
  operations are grouped by tag and flags are kebab-cased, so the real command
  is `<cli> pet get-pet-by-id --pet-id`. They now emit the real invocation,
  the real flags, and the real typed exit codes (they claimed "exit code 1").
- **`--no-cache` was ignored** whenever `--save` was also passed: cache reads
  were keyed off the HTTP method alone.
- **`--watch` did nothing.** The flag was parsed and stored, and never read.
- **`--cache-ttl 0` / `--timeout 0` / `--rate-limit 0` were ignored**, because
  an explicit zero lost to the profile fallback in an `or` chain.
- **The DuckDB mirror backend could not insert.** `records.id` was a primary
  key with no default (DuckDB has no `AUTOINCREMENT`); it now uses a sequence.
- **`ducktap publish` never retried a push.** `_step(required=False)` reported
  `ok=True` unconditionally, so the "repo already exists, push instead"
  fallback after `gh repo create` was unreachable and a failed publish could
  report success.
- **`ducktap vision` never sent the screenshot** — the multi-part content was
  stringified with `str()`, so the model received the repr of a Python list.
- **`mitm-sniff` could not run and could not be reached.** It shelled out to
  `python -m mitmproxy` / `python -m mitmweb`, neither of which exists, and
  nothing imported the module so the discoverer was invisible. The built-in
  GraphQL discoverer was unreachable for the same reason.
- **Six commands were exposed under the wrong name** — `ducktap publish-cmd`,
  `polish-cmd`, `rename-cmd`, `emboss-cmd`, `vision-cmd`, `crowd-sniff-cmd`.
  They are now `publish`, `polish`, `rename`, `emboss`, `vision`,
  `crowd-sniff`.
- The website's `vercel.json` favicon route used a `:match` placeholder with
  no capture group, so favicons fell through to the SPA catch-all.

### Fixed — security

- **The dashboard was open to cross-site requests.** Any page in the user's
  browser could POST to `http://127.0.0.1:8765/generate` and drive the local
  install into fetching a URL and writing files. `/generate` now requires a
  per-process CSRF token and rejects cross-site `Sec-Fetch-Site`.
- **The dashboard rendered untrusted values into HTML unescaped**, server-side
  (catalog recipes) and client-side (`innerHTML` with the spec's name,
  archetype and insight). The page moved to an autoescaping template and the
  client escapes before interpolating.
- **Generated CLIs leaked credentials across redirects.** httpx strips
  `Authorization` on a cross-origin redirect but knows nothing about
  `X-API-Key`; redirects are now followed by hand and only benign headers
  cross an origin boundary. Redirect chains are bounded.
- **Path parameters were spliced into the URL unencoded**, so a value like
  `../admin` retargeted the request. They are percent-encoded.
- **`<cli> query` enforced read-only with a `startswith("select")` check**,
  which `WITH ... DELETE` walks straight past. User SQL now runs on a
  connection SQLite opens read-only; `WITH` queries are supported.
- `--name` (and the dashboard's name field) could escape the output directory;
  `APISpec.name` is slugified in one place for every discoverer.
- Remote spec downloads are capped (64 MiB) instead of being read unbounded.
- `ducktap emboss` wrote brand strings into `pyproject.toml` without escaping.

### Changed

- **`press` is deterministic by default.** It used to call an LLM unless
  `--no-llm` was passed, which contradicted the headline claim of byte-for-byte
  reproducibility. Opt in with `ducktap press --llm`; `--no-llm` still works.
- **`pip install ducktap` is much smaller.** `litellm` moved to a new `[llm]`
  extra, `mcp` was dropped (only the *generated* server needs it), and the
  unused `openapi-spec-validator` dependency was removed. `[all]` installs
  everything.
- `ducktap polish` issues its per-operation requests in parallel and no longer
  aborts the whole run when one of them fails.

### Performance

- The catalog is parsed once and cached against file mtimes; a single
  dashboard render used to re-read and re-parse every recipe several times.
- The generated mirror indexes `records` on `saved_at`, `collection` and
  `(method, path)` — `stale`, `health` and `bottleneck` were full scans.
- The mitmproxy addon flushes the HAR at most once a second instead of
  rewriting the whole archive on every response.

## 0.8.1 -- 2026-06-08

Additive depth + UI polish on top of 0.8.0. (Not the full v0.8.0 "Verification
& Depth" milestone — see `docs/ROADMAP.md` for what remains.)

### Added

- **`ducktap verify` — proof of behavior** (`verify/proof.py`): four deterministic
  proofs against the spec + generated Python CLI — Path Proof (no hallucinated
  endpoints), Coverage Proof (every operation exposed), Auth Proof (auth header
  matches the scheme type), and Pipeline Proof (no write-only mirror tables).
  Emits a table or `--json` report; exits 5 on failure.
- **Polished dashboard** (`ducktap ui`): rebuilt into a finished, dark-themed
  workbench — multi-target press console (Python/Go/Rust/TS/MCP/skill +
  archetype override + deterministic toggle) and a live result panel showing the
  detected archetype, the Non-Obvious Insight, an animated per-dimension
  scorecard, the artifact tree, and the provenance manifest. New `/api/health`.

### Fixed

- The Pipeline Proof caught a real dead table: the legacy generic
  `domain_entities` blob (superseded by the v0.7.x typed archetype tables) was
  created in the generated mirror but never read or written. Removed.

## 0.8.0 -- 2026-06-08

The **Creative Layer** (the v0.7.x roadmap) lands. Press now front-loads a
research phase: it detects a domain archetype, generates a Non-Obvious Insight,
and emits a provenance manifest. All of it is deterministic (no API key needed)
so it runs in CI, with optional LLM enrichment.

### Added

- **Domain archetype detection** (`core/archetype.py`) — classifies any APISpec
  into `project_management` / `communication` / `payments` / `infrastructure` /
  `content` (or `unknown`) from resource + field signals. Stored on
  `APISpec.archetype`; override with `ducktap press --archetype`.
- **Non-Obvious Insight (NOI)** (`insight.py`) — `ducktap insight <api>` plus a
  Phase-0 step in `press`. Archetype-driven deterministic templates, optionally
  sharpened by an LLM; `--insight "..."` / `--no-llm` control it. The NOI is
  embedded in the generated README and `agent-context` output.
- **Provenance manifest** (`manifest.py`) — every `press` writes `.ducktap.json`
  (NOI, archetype, source, spec checksum, version, timestamp, scorecard grade,
  targets, auth env vars). `ducktap info` reads and pretty-prints it.
- **Ecosystem absorb gate** (`absorb.py`) — `ducktap absorb <api>` emits a
  structured feature manifest (`must_match` / `transcend`) from the agent-CLI
  playbook baseline + crowd-sniff enrichment. `ducktap absorb --check <dir>`
  mechanically verifies a generated CLI matches every `must_match` feature.
- **Typed per-resource SQLite tables** in the generated Python CLI — an
  archetype-specific table (`issues` / `messages` / `charges` / `resources` /
  `documents`) with `upsert_domain()` / `search_domain()`, an FTS5 index over
  the natural text column, a `domain_since()` incremental filter, and a sync
  cursor persisted to `cursor.json`. DuckDB gets the typed table with a LIKE
  fallback.

### Notes

- See `docs/ROADMAP.md` → "v0.7.x — The Creative Layer → Scoping notes (0.8.0)"
  for where the implementation deviates from the literal roadmap text (manifest
  path, absorb gate surfaced via `absorb --check` rather than wired into
  `scorecard`, and the per-CLI `sync --since` subcommand deferred to v0.8.0's
  Rung 5 work).
- 18 new tests (archetype / NOI / manifest / absorb / typed tables); full suite
  104 passed, plus the multi-language compile suite (4 passed). ruff + mypy clean.

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
