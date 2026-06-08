# DuckTap Roadmap

DuckTap v0.1 ships the **lean loop end-to-end**. The roadmap below charts the
path from "scaffold + working core" to feature parity with (and improvements
over) Printing Press.

## v0.1.0 -- Foundation ✓

- [x] Repo skeleton, MIT license, GH Actions CI
- [x] `APISpec` intermediate model
- [x] OpenAPI 2/3 discoverer
- [x] HAR discoverer (request clustering, path generalization)
- [x] Browser-sniff scaffold (Playwright)
- [x] Python CLI generator (Click, httpx, SQLite mirror, auth from env)
- [x] MCP server generator (mcp SDK, stdio)
- [x] Skill generator (Claude SKILL.md, Cursor .mdc, generic tools.json)
- [x] Multi-LLM abstraction (LiteLLM)
- [x] Plugin registry + entry-point loader + sample GraphQL plugin
- [x] Scorecard (6 dimensions) + shipcheck
- [x] Catalog YAML loader + 3 starter entries (petstore, github, stripe)
- [x] FastAPI dashboard
- [x] Top-level Typer CLI (`press`, `research`, `sniff`, `scorecard`, `shipcheck`, `catalog`, `plugins`, `ui`)
- [x] Petstore E2E test

### Quality work landed in 0.1.2 (out of band)

- Smarter spec naming: drops `OpenAPI`/`v3`/`REST` noise so titles like
  "Swagger Petstore - OpenAPI 3.0" become `petstore`, not the
  unwieldy `swagger-petstore-openapi-3-0`.
- Relative `servers:` URLs in OpenAPI specs are resolved against the
  source URL when fetched over HTTP, fixing broken `BASE_URL` for
  petstore-shaped specs.
- Generated client: `Accept: application/json`, `User-Agent`, redacted
  request logging via `--debug`/`<NAME>_DEBUG`, clear errors when
  `base_url` is unset.
- Generated CLI: `--debug`; `--json/--no-json` removed (redundant with
  `--pretty`); flag-collision auto-rename for shared path/body names.
- Runtime tests: generated CLIs are now exercised end-to-end against
  `httpx.MockTransport`, not just parsed.

## v0.2.0 -- Polish ✓

### Landed in 0.2.0 (merged 2026-05-18)

- [x] **Agent-native CLI controls** -- `--select`, `--compact`, `--quiet`, `--dry-run`
  added as global options to every generated CLI
- [x] **Typed exit codes** -- `3` (404), `4` (401/403), `5` (other API error),
  `7` (429), `10` (local config error) on every generated command
- [x] **`doctor` command** -- reports base URL validity, auth env var presence
  with redacted fingerprints, and cache location; no write calls made
- [x] **Dashboard upgrade** -- minimal page replaced with a full workbench:
  status rail, source press panel, catalog table with filters, result/scorecard
  panel, recent-run display, and `/api/catalog` JSON endpoint
- [x] **README polish** -- generated READMEs now use clean Markdown tables,
  agent usage examples, and separate lines per auth var / command bullet
- [x] **Version sync** -- `ducktap.__version__` is now asserted to match
  `pyproject.toml` in CI; `mix_stderr` Click compatibility fixed
- [x] Scorecard CI mode (`ducktap scorecard --fail-under N`) -- landed 0.1.2

### Landed in 0.2.1

- [x] **Tag-grouped command tree** in generated CLIs -- operations with tags
  are organized under their first tag (e.g. `petstore-dt-cli pet add-pet`),
  matching Printing Press's `<api>-pp-cli <resource> <verb>` muscle memory.
- [x] **`--agent` mega-flag** on every generated CLI -- toggles `--json`,
  `--compact`, and `--no-color` at once for one-flag agent invocation.
- [x] **Multi-format output** -- `--format {json|jsonl|csv|plain|pretty}`
  on every generated CLI, alongside the original `--json/--pretty` toggle.
- [x] **`agent-context` command** -- generated CLIs emit structured JSON
  describing every command, group, global flag, and exit code so an agent
  can self-introspect without parsing `--help`.
- [x] **`which <keyword>` command** -- search the operation tree by
  substring across operation ids, paths, and summaries.
- [x] **Saved profiles** -- `profile save / list / show` subcommands and a
  global `--profile NAME` to load flag presets from
  `~/.ducktap/<api>/profiles/<name>.json`.
- [x] **`--rate-limit` and `--timeout`** as global flags, plumbed through
  the generated HTTP client (token-bucket throttle + per-request timeout).
- [x] **Catalog expansion** -- 3 → 17 entries (Sentry, Asana, Telegram,
  Twilio, Plaid, HubSpot, Jira, Discord, ElevenLabs, Mercury,
  LaunchDarkly, DigitalOcean, openrouteservice, Notion).
- [x] **Doctor enriched** -- also reports cache db existence/size, active
  profile, available profile names, and the operation count + group list.

### Landed in 0.2.2

- [x] **`auth-doctor` command** on every generated CLI -- env-var validation
  with actionable hints sourced from the OpenAPI `description`, plus
  optional `--probe` that makes a real GET request against the first
  parameter-free endpoint and classifies the response (`auth_works`,
  `auth_failed`, `auth_missing`, `rate_limited`, `inconclusive`,
  `network_error`). Exit codes match the global palette (4 auth, 7 rate
  limit, 5 API error, 10 local config) so agents can branch on them
  without parsing JSON.
- [x] **`--agent --dry-run` is no longer compacted** -- dry-run payloads
  describe the *request* (method/path/url/query/headers/body), not the
  response, so applying `--compact` to them collapsed the payload to a
  single high-gravity key. `_emit(..., raw=True)` is now used for every
  metadata view (dry-run, agent-context, doctor, profile management) so
  the CLI's self-description stays complete regardless of `--agent`.

### Landed in 0.2.x (this branch)

- [x] LLM-assisted **operation description rewrite** (`ducktap polish <name>`)
- [x] LLM-assisted **command renaming** for unwieldy operation IDs (`ducktap rename <name>`)
- [x] Detect login flows during sniffing, emit accurate auth env-var docs
- [x] Generated CLIs gain `--watch` and `--save` for ad-hoc local data lakes

## v0.3.0 -- Sniffing v2 ✓

- [x] **Crowd-sniff**: study existing community CLIs/MCP servers via web search
- [x] **GraphQL** promoted to first-class discoverer (introspection + persisted queries)
- [x] Smart action recording for sniff (record clicks/forms, replay headless)
- [x] mitmproxy-backed sniff (no headless Chromium needed) as an alternative
- [x] Rate-limit + retry-with-backoff aware request inference

## v0.4.0 -- Compound queries ✓

- [x] **Compound command macros**: declarative recipes that chain multiple operations
- [x] Local "data lake" mode: persistent mirror, full-text search over JSON (FTS5)
- [x] DuckDB backend option as alternative to SQLite
- [x] Built-in `<api>-dt-cli query "SELECT ..."` for SQL over the mirror

## v0.5.0 -- Publish

- [x] `ducktap publish <name>` → PyPI + GitHub in one command (`gh` + `twine`)
- [x] Auto-generated GitHub Actions for the generated CLIs (test + release)
- [x] DuckTap Library: local registry of community-printed CLIs (`ducktap library list/search/add/remove`)

## v0.6.0 -- Multi-language generators

- [x] TypeScript CLI generator (oclif)
- [x] Go CLI generator (cobra) -- for users who want the Printing Press output shape
- [x] Rust CLI generator (clap) -- single-binary distribution

  > **0.7.0 correction:** these three generators shipped in 0.6.0 but were not
  > wired into `autoload_builtins` and did not compile. v0.7.0 makes them
  > reachable, compile-verified in CI, and brings them to agent parity (see
  > the v0.7.0 section below).
- [x] 30+ catalog entries (30 APIs)
- [x] Domain-specific SQLite tables + FTS5 in generated mirror
- [x] Compound query commands (`stale`, `health`, `bottleneck`) in generated CLIs
- [x] 2-tier scorecard with domain correctness dimension
- [x] Live API smoke test (`ducktap smoke`)
- [x] `emboss` brand-stamp step (`ducktap emboss`)
- [x] `vision` LLM screenshot reading (`ducktap vision`)

## Known gaps vs Printing Press (updated v0.6.0)

| PP feature | DuckTap status |
|---|---|
| `--compact` / `--select` flags | ✅ landed v0.2.0 |
| Typed exit codes | ✅ landed v0.2.0 |
| `doctor` command | ✅ landed v0.2.0 |
| Tag-grouped command tree | ✅ landed v0.2.1 |
| `--agent` mega-flag | ✅ landed v0.2.1 |
| `--format` jsonl/csv/plain | ✅ landed v0.2.1 |
| Saved profiles | ✅ landed v0.2.1 |
| `agent-context` introspection | ✅ landed v0.2.1 |
| `which <keyword>` search | ✅ landed v0.2.1 |
| `--rate-limit` and `--timeout` globals | ✅ landed v0.2.1 |
| `auth-doctor` (env-var validation + live probe) | ✅ landed v0.2.2 |
| LLM-assisted polish + rename | ✅ landed v0.2.x |
| GraphQL first-class discoverer | ✅ landed v0.3.0 |
| Smart action recording + replay | ✅ landed v0.3.0 |
| mitmproxy-backed sniff | ✅ landed v0.3.0 |
| Rate-limit aware inference | ✅ landed v0.3.0 |
| Compound command macros | ✅ landed v0.4.0 |
| FTS5 full-text search | ✅ landed v0.4.0 |
| DuckDB mirror backend | ✅ landed v0.4.0 |
| Top-level `query` command | ✅ landed v0.4.0 |
| `ducktap publish` → PyPI + GitHub | ✅ landed v0.5.0 |
| Auto-generated GitHub Actions | ✅ landed v0.5.0 |
| Library registry | ✅ landed v0.5.0 |
| Multi-language generators (Go/TS/Rust) | ✅ landed v0.6.0; **compile-verified in CI v0.7.0** |
| Go/Rust/TS `--dry-run`, `agent-context`, typed exit codes | ✅ landed v0.7.0 |
| Compound query commands (`stale`, `health`, `bottleneck`) | ✅ landed v0.6.0 (Python CLI) |
| 2-tier scorecard (domain correctness dimension) | ✅ landed v0.6.0 (structural; deep pipeline verification → v0.8) |
| Live API smoke test | ✅ landed v0.6.0 |
| `emboss` brand-stamp | ✅ landed v0.6.0 |
| `vision` LLM screenshot reading | ✅ landed v0.6.0 |
| 30+ catalog entries | ✅ landed v0.6.0 (30 entries) |
| Non-Obvious Insight (NOI) generation | ✅ landed v0.8.0 |
| Ecosystem absorb gate | ✅ landed v0.8.0 |
| Domain archetypes (5 archetypes, typed commands) | ✅ landed v0.8.0 |
| True domain-specific SQLite (typed per-resource tables) | ✅ landed v0.8.0 |
| Proof of behavior (4 mechanical proofs) | ⏳ v0.8 |
| Rung 5 behavioral insights (`similar`, `trends`, `forecast`) | ⏳ v0.8 |
| Cursor-based incremental sync | ⏳ v0.8 |
| Auto-JSON when piped (no `--json` needed) | ⏳ v0.8 |
| Published real CLIs users can install | ⏳ v0.9 |
| Homebrew formula + single-binary distribution | ⏳ v0.9 |
| `ducktap reprint` | ⏳ v0.9 |
| `ducktap amend` (session transcript mining) | ⏳ v0.9 |
| Global `auth-doctor` (across all installed CLIs) | ⏳ v0.9 |
| Agent delegation mode (Codex equivalent) | ⏳ v0.9 |
| printingpress.dev equivalent | ⏳ v1.0 |
| Plugin marketplace | ⏳ v1.0 |

### DuckTap-only advantages (not in Printing Press)

| Feature | Status |
|---|---|
| Multi-LLM support (LiteLLM) | landed v0.1.0 |
| Browser sniffing (Playwright + mitmproxy) | landed v0.3.0 |
| Web dashboard (ducktap ui) | landed v0.2.0 |
| --agent mega-flag + agent-context introspection | landed v0.2.1 |
| auth-doctor with live probe | landed v0.2.2 |
| Compound command macros (YAML recipes) | landed v0.4.0 |
| FTS5 full-text search in generated CLI | landed v0.4.0 |
| DuckDB mirror backend | landed v0.4.0 |
| Multi-language generators (Python/Go/TS/Rust) | landed v0.6.0 |
| Vision screenshot reading | landed v0.6.0 |
| ducktap publish one-command PyPI + GitHub | landed v0.5.0 |

---

## v0.7.0 — Multi-language parity ✓ (shipped 2026-06-07)

The 0.6.0 multi-language generators were advertised but broken. v0.7.0 makes
them real and brings them up to agent parity with the Python CLI.

- [x] **Generators reachable** — Go/Rust/TS registered in `autoload_builtins`;
  `ducktap press -t go-cli,rust-cli,typescript-cli` now works.
- [x] **All three compile** — flat cobra `cmd` package + `root.go` for Go;
  deduped clap args, owned query strings, array params, zero-warning build for
  Rust; fixed import depth + runnable `bin/run.js` for TypeScript.
- [x] **`generated-clis` CI job** — `go build`, `cargo build`, and `tsc` run on
  every push so the templates cannot silently drift.
- [x] **Agent-parity bundle** in Go/Rust/TS generated CLIs:
  - `--dry-run` (print request, don't call)
  - `agent-context` (JSON self-introspection manifest)
  - typed exit codes (3/4/5/7) mapped from HTTP status
  - `--base-url` override
- [x] **Compile tests also run `agent-context`** and assert a shared manifest
  shape across languages.

The remaining feature delta in the non-Python CLIs (local SQLite mirror, FTS5,
compound query commands) is tracked for a later release.

---

## v0.7.x — The Creative Layer ✓ (shipped in 0.8.0)

The single most important gap between DuckTap and Printing Press is not features — it is
creative depth. PP generates CLIs *around an insight*. DuckTap generates CLIs *from a spec*.
v0.7.x closes that conceptual gap and front-loads research in the press pipeline.
Everything below is implemented **deterministically** (no API key required) so it runs
in CI, with optional LLM enrichment when a LiteLLM model is configured.

### Non-Obvious Insight (NOI)

- [x] `ducktap insight <api>` — standalone command that produces a one-sentence NOI:
  `"[API] isn't just [obvious thing]. It's [non-obvious thing]. Every [data point] is a signal about [hidden truth]."`
- [x] NOI is generated in Phase 0 of `ducktap press` and written to the `.ducktap.json` provenance manifest
- [x] A NOI is always available: a deterministic archetype-driven template is produced (and
  used as the LLM seed); `--insight "..."` overrides it. (Supersedes the "block with a warning"
  design — generation never fails for lack of a NOI.)
- [x] NOI is embedded in the generated CLI's README and `agent-context` output

### Ecosystem Absorb Gate

- [x] `ducktap absorb <api>` catalogs the agent-CLI features the API should have into an
  **absorb manifest** (deterministic agent-CLI-playbook baseline + crowd-sniff enrichment)
- [x] Absorb manifest is a structured list: `{feature, source_tool, source_url, priority}` with
  each feature classified `must_match` or `transcend`
- [x] LLM/crowd-sniff suggestions are stored as `novel_suggestions` in the manifest
- [x] `ducktap absorb --check <dir>` mechanically verifies a generated CLI matches every
  `must_match` feature (scans the source; exits non-zero on a miss)
- [x] `ducktap absorb <api>` runs standalone and emits the manifest with `-o`

### Domain Archetypes

Five archetypes auto-detected from the spec. Each drives a typed data layer.

- [x] **Archetype detector** (`src/ducktap/core/archetype.py`) — classifies any APISpec into
  one of 5 archetypes from resource + field signals:
  - `project_management` — issue/task/ticket resources, assignee, priority, state fields
  - `communication` — message/channel/thread resources, threading fields, timestamps
  - `payments` — charge/payment/invoice resources, amount, currency, status fields
  - `infrastructure` — server/deploy/instance resources, region, status fields
  - `content` — document/page/block resources, content, version fields
- [x] Detected archetype is stored in `APISpec.archetype` and in `.ducktap.json`
- [x] Python CLI generator switches template context based on archetype (typed tables + FTS5)
- [x] `ducktap press --archetype project_management` — manual override

### True Domain-Specific SQLite Tables

Adds typed per-resource tables per archetype alongside the generic mirror.

- [x] `mirror.py.j2` gains archetype-aware table generation:
  - `project_management` → `issues (id, title, status, assignee, priority, created_at, updated_at, body)`
  - `communication` → `messages (id, channel_id, author_id, content, timestamp, thread_id)`
  - `payments` → `charges (id, amount, currency, status, customer_id, created_at, description)`
  - `infrastructure` → `resources (id, name, type, status, region, created_at, metadata)`
  - `content` → `documents (id, title, content, author_id, updated_at, parent_id)`
- [x] Typed `upsert_domain()` / `search_domain()` methods (not generic `save_record`)
- [x] FTS5 virtual table indexes the natural text column for each archetype
- [x] DuckDB backend gets equivalent typed tables (LIKE search; DuckDB has no FTS5)
- [x] `domain_since(<ISO-date>)` incremental filter + sync cursor persisted to `cursor.json`

### Provenance Manifest

- [x] Every `ducktap press` run writes `.ducktap.json`: NOI, archetype, source, spec checksum,
  ducktap version, generation timestamp, scorecard grade, targets, auth env vars
- [x] `ducktap info` reads and pretty-prints the manifest

### Scoping notes (0.8.0)

Where the implementation differs from the literal text above:

- The provenance manifest is written to `<out>/.ducktap.json` (one per press) and read by
  `ducktap info --out-dir`, rather than `<out>/<name>/.ducktap.json` / `ducktap info <name>`.
- The absorb `must_match` gate is enforced via `ducktap absorb --check` (a standalone mechanical
  gate), not yet wired into the `ducktap scorecard` command itself.
- Typed tables ship with mirror-level `upsert_domain`/`search_domain`/`domain_since` + cursor
  persistence. Wiring a dedicated `sync --since` *subcommand* into every generated CLI (and the
  archetype-specific `sql`/workflow commands) is deferred to v0.8.0's Rung 5 work.

---

## v0.8.0 — Verification & Depth

v0.8 closes the verification gap (proof of behavior, golden harness) and pushes the
generated CLI up to Rung 5 behavioral insights now that the typed data layer from v0.7
makes them possible.

### Proof of Behavior (4 Mechanical Proofs)

- [ ] **Path Proof** — every URL in generated commands exists in the APISpec. Auto-removes commands with hallucinated paths and re-generates.
- [ ] **Flag Proof** — every registered Click option is referenced in at least one command handler. Removes dead flags.
- [ ] **Pipeline Proof** — every SQLite table written by `sync` is read by at least one of `search`, `query`, `sql`. Fails if `sync` writes to a table that nothing reads.
- [ ] **Auth Proof** — auth header format in `client.py.j2` matches the spec's `auth_schemes[*].type`. `Bearer` vs `Basic` vs `ApiKey` mismatch is a hard fail.
- [ ] `ducktap verify <name>` runs all four proofs and emits a structured JSON report
- [ ] Proof failures trigger auto-remediation: remove dead code, re-run proof, max 3 iterations
- [ ] Scorecard domain_correctness tier is rewired to use proof results instead of structural heuristics

### Rung 5 — Behavioral Insight Commands

Enabled by the typed tables from v0.7. Generated per archetype.

- [ ] `similar` — find semantically duplicate records using FTS5 similarity ranking (all archetypes)
- [ ] `trends` — plot a metric over time from the local mirror: cycle time (PM), message volume (comms), revenue (payments) — emits JSON suitable for sparkline rendering
- [ ] `diagnose` — composite score across multiple dimensions: staleness ratio, error rate in recent syncs, coverage of required fields (all archetypes). Distinct from the v0.6 `health` command (data-lake metadata); this is a behavioral health score.
- [ ] `forecast` — linear regression on a time-series column, emits next-7-day projection (payments archetype: revenue; PM archetype: issue close rate)
- [ ] `patterns` — surface recurring sequences: most active times, most common state transitions, top contributors (comms + PM archetypes)
- [ ] All Rung 5 commands are gated on the typed data layer existing — they fail gracefully if the mirror is empty or the archetype is `unknown`

### Cursor-Based Incremental Sync

- [ ] `sync` command in generated CLIs gains `--since <ISO-date>` and `--cursor` flags
- [ ] Last sync cursor stored in `~/.ducktap/<api>/cursor.json` — subsequent syncs start from there
- [ ] `--data-source auto` — pre-read refresh before serving local data if cursor is stale by more than `--max-age` seconds
- [ ] `--data-source local` — bypass sync, use mirror only
- [ ] `--data-source live` — bypass mirror, call API directly
- [ ] Batch SQLite transactions on insert (1000 records per commit) for performance

### Agent UX Parity

Small gaps that matter at scale.

- [ ] **Auto-JSON when piped** — detect `sys.stdout.isatty() == False` and switch to JSON output automatically, no `--json` flag needed
- [ ] `--no-input` — disable all interactive prompts, fail fast instead
- [ ] `--stdin` — read JSON body from stdin for POST/PUT commands (`echo '{"title":"x"}' | petstore-dt-cli pet create --stdin`)
- [ ] `--yes` — auto-confirm destructive operations without prompting
- [ ] **Bounded output messaging** — list commands append `"Showing N of M results. To narrow: add --limit, --select, or filter flags."` to every list response
- [ ] **Actionable errors** — every `APIError` includes `hint`, `flag`, and `correct_usage` fields so agents self-correct in one retry

### Golden Output Harness

- [ ] `tests/golden/` directory with deterministic, offline test cases: `command.txt` (the command), `expected_stdout.json` (structure validated, not exact text — templates evolve), `expected_exit_code`
- [ ] `scripts/golden.sh verify` — rebuilds CLI from petstore fixture, runs cases, diffs output
- [ ] `scripts/golden.sh update` — regenerates expected files (requires explicit env var to prevent accidental overwrite)
- [ ] Golden CI workflow runs separately from pytest to protect deterministic generation
- [ ] `tests/fixtures/golden-api.yaml` — purpose-built spec fixture for golden tests

---

## v0.9.0 — Distribution & Ecosystem

v0.9 closes the community gap: real published CLIs users can install, proper distribution,
and the workflow commands that make DuckTap a live tool instead of a generator.

### Published CLIs — DuckTap Library

- [ ] `zanni098/ducktap-library` GitHub repository — organized by category, one directory per CLI
- [ ] First 5 published CLIs shipped and installable via `pip install`:
  - `github-dt-cli` (developer, official spec)
  - `linear-dt-cli` (project management, archetype: project_management, compound commands)
  - `stripe-dt-cli` (payments, archetype: payments, reconcile + revenue commands)
  - `slack-dt-cli` (communication, archetype: communication, channel-health + message-stats)
  - `sentry-dt-cli` (infrastructure, archetype: infrastructure, health + trends)
- [ ] Each published CLI ships: README with NOI + cookbook, `.ducktap.json` provenance manifest, GitHub Actions CI, smoke test results
- [ ] `ducktap library install <name>` — `pip install` wrapper that fetches from ducktap-library

### Distribution

- [ ] **Single-binary build** via PyInstaller — `ducktap` ships as a standalone executable with no Python required, distributed via GitHub Releases
- [ ] **Homebrew formula** — `brew install ducktap` (tap: `zanni098/tap`)
- [ ] `scripts/install.sh` — one-liner curl installer that detects OS/arch and installs the right binary
- [ ] `ducktap update` — self-update command that pulls the latest binary from GitHub Releases

### `ducktap reprint`

- [ ] `ducktap reprint <name>` — re-runs `press` on an existing CLI using the original source from `.ducktap.json`, applies polish, re-scores, preserves local customizations in a `--merge` mode
- [ ] `--diff` flag shows what changed between the old and new generation before applying

### `ducktap amend`

- [ ] `ducktap amend [<name>]` — reads the current Claude Code / shell session transcript, identifies friction points (missing flags, hand-rolled API payloads, silent-null returns, repeated workarounds), scopes a patch with the user, applies it to the generated CLI, and opens a PR to the library
- [ ] Two checkpoints: (1) scope confirmation, (2) PR draft review before push
- [ ] Strips PII from transcript before including in PR description. Scrub rules: redact Authorization / api_key / token / password values, replace hostnames with example.com, replace local file paths with REDACTED, drop any line matching export .*SECRET
- [ ] Falls back to `--manual` mode with a prompted checklist if no transcript is available

### Agent Delegation Mode

- [ ] `ducktap press <api> --delegate codex` — offloads Phase 3 code generation (template rendering + fixture writing) to a code-generation agent (Codex CLI, Claude Code, or any tool-loop agent)
- [ ] Claude / the configured primary LLM handles research, NOI, absorb gate, archetype detection, and review
- [ ] The delegate receives scoped prompts (archetype, operations, auth schemes) and returns raw code files; DuckTap validates the returned code via proof-of-behavior before accepting it
- [ ] Falls back to local generation after 3 delegate failures with no user intervention
- [ ] `--delegate-model` accepts any LiteLLM model string for single-shot code generation (no tool loop) as a lightweight alternative to full agent delegation

### Global Auth Doctor

- [ ] `ducktap auth-doctor` (top-level, no CLI name required) — scans every installed `.ducktap.json` manifest in `~/.ducktap/*/` and reports which env vars are set, unset, or suspicious across all installed CLIs
- [ ] Fingerprints show first 4 chars, never full token
- [ ] `--json` output for agent consumption
- [ ] Exit 0 always (diagnostic, not gating)

### MCP Audit

- [ ] `ducktap mcp-audit <name>` — inspects a generated MCP server against the source APISpec: checks tool names match operation IDs, parameter types match spec types, auth env vars are declared
- [ ] Reports a coverage score: tools exposed / operations in spec
- [ ] `--fix` flag auto-regenerates the MCP server if coverage < 80%

---

## v1.0.0 — Transcendence

v1.0 is where DuckTap stops closing the gap and starts pulling ahead. The features
below are either things PP cannot do (multi-LLM, 4 generators, mitmproxy, web UI) or
things nobody has done yet (multi-agent pipeline, plugin marketplace, live event sync).

### DuckTap Surpasses PP on Its Own Terms

- [ ] **Domain archetype coverage expanded to 8** — add `analytics`, `identity`, `ecommerce` archetypes with their own typed tables and Rung 5 commands
- [ ] **Absorb gate v2** — after absorbing, runs a diff against the generated CLI and flags any `must_match` feature that is missing from the generated code (not just from the spec)
- [ ] **Proof of behavior v2** — adds a **Semantic Proof**: the NOI claim is verified against the generated compound commands (e.g. if NOI says "it's a team behavior observatory", at least one Rung 5 command must surface behavioral patterns)
- [ ] **`health` composite score** published in `agent-context` output — a single 0–100 number summarising freshness, error rate, coverage, and sync lag so agents can decide whether to `sync` before querying

### Multi-Agent Press Pipeline

- [ ] `ducktap press` optionally splits into two agents: a **Research Agent** (NOI, absorb gate, archetype, data model design) and a **Generation Agent** (code writing, template rendering, proof verification)
- [ ] Agents communicate via a structured JSON pipeline contract stored in `<out>/<name>/pipeline/`
- [ ] Any LiteLLM model can be assigned to either role: `--research-model claude-opus-4 --generation-model kimi-k2`
- [ ] Pipeline contract is resumable — interrupted runs can restart from the last completed phase

### Plugin Marketplace

- [ ] `ducktap plugins search <query>` — searches PyPI for packages tagged `ducktap-plugin`
- [ ] `ducktap plugins install <package>` — `pip install` + auto-registration
- [ ] Plugin contract v2: plugins can now register **archetype detectors**, **Rung 5 command generators**, and **proof checkers** (not just discoverers and generators)
- [ ] `ducktap plugins publish` — scaffolds a plugin package with the right entry points, README template, and CI workflow

### Web UI 2.0

- [ ] Live archetype preview — after discovery, the dashboard shows which archetype was detected and lets the user override before generation
- [ ] Absorb manifest viewer — browse the absorb manifest, mark features as `skip` or `must_match` before generation
- [ ] NOI editor — display the generated NOI, allow user to edit before pressing
- [ ] Live scorecard — WebSocket stream of proof-of-behavior results as they run
- [ ] Library browser — browse `ducktap-library` entries, install with one click

### GraphQL Subscriptions + WebSocket Discovery

- [ ] GraphQL discoverer gains Subscription type support — generates `watch-<event>` commands in the CLI
- [ ] mitmproxy sniff captures WebSocket frames and infers event schemas
- [ ] Generated CLI gains `stream <event>` command for APIs with SSE or WebSocket push

### ducktap.dev Website

- [ ] Public website listing every CLI in `ducktap-library` with: NOI, archetype, scorecard grade, install command, generated README
- [ ] Search by API name, category, archetype
- [ ] "Print your own" CTA pointing to the repo

### Quality Bar for 1.0

- [ ] 95%+ test coverage across all source modules
- [ ] All 5 published CLIs in ducktap-library have Grade A scorecards and passing proof-of-behavior
- [ ] E2E test suite runs against 3 live APIs (petstore + 2 catalog entries) in CI
- [ ] Zero known proof-of-behavior failures in published CLIs
- [ ] No generated CLI crashes on `--help` or `--agent-context` (smoke-tested in CI)
- [ ] `ducktap --version` matches `pyproject.toml` and the latest GitHub Release tag in all three places
