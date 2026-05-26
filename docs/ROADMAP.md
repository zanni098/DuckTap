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

- [ ] `ducktap publish <name>` → PyPI + GitHub in one command (`gh` + `twine`)
- [ ] Auto-generated GitHub Actions for the generated CLIs (test + release)
- [ ] DuckTap Library: a public registry of community-printed CLIs (separate repo)

## v0.6.0 -- Multi-language generators

- [ ] TypeScript CLI generator (oclif)
- [ ] Go CLI generator (cobra) -- for users who want the Printing Press output shape
- [ ] Rust CLI generator (clap) -- single-binary distribution

## Known gaps vs Printing Press

| PP feature | DuckTap status |
|---|---|
| `--compact` / `--select` flags | ✅ landed v0.2.0 |
| Typed exit codes | ✅ landed v0.2.0 |
| `doctor` command | ✅ landed v0.2.0 |
| 30+ catalog entries | 17 entries (v0.2.1) -- more in v0.2.x |
| Tag-grouped command tree | ✅ landed v0.2.1 |
| `--agent` mega-flag | ✅ landed v0.2.1 |
| `--format` jsonl/csv/plain | ✅ landed v0.2.1 |
| Saved profiles | ✅ landed v0.2.1 |
| `agent-context` introspection | ✅ landed v0.2.1 |
| `which <keyword>` search | ✅ landed v0.2.1 |
| `--rate-limit` and `--timeout` globals | ✅ landed v0.2.1 |
| `auth-doctor` (env-var validation + live probe) | ✅ landed v0.2.2 |
| `--agent --dry-run` preserves full metadata payload | ✅ landed v0.2.2 |
| LLM-assisted polish + rename | ✅ landed v0.2.x |
| Auth flow detection in sniff | ✅ landed v0.2.x |
| Generated CLI data lake (`--watch`/`--save`) | ✅ landed v0.2.x |
| Crowd-sniff research | ✅ landed v0.3.0 |
| GraphQL first-class discoverer | ✅ landed v0.3.0 |
| Smart action recording + replay | ✅ landed v0.3.0 |
| mitmproxy-backed sniff | ✅ landed v0.3.0 |
| Rate-limit aware inference | ✅ landed v0.3.0 |
| Compound command macros | ✅ landed v0.4.0 |
| FTS5 full-text search | ✅ landed v0.4.0 |
| DuckDB mirror backend | ✅ landed v0.4.0 |
| Top-level `query` command | ✅ landed v0.4.0 |
| Domain-specific SQLite tables + FTS5 | key-value cache only (planned v0.4) |
| Compound query commands (`stale`, `health`, `bottleneck`) | planned v0.4 |
| 2-tier scorecard (domain correctness) | 1-tier structural only (planned v0.4) |
| Live API smoke test | not yet planned |
| `emboss` brand-stamp step | not planned |
| `mcp-audit` | subsumed by scorecard `artifacts` dimension |
| `tools-audit` | subsumed by `public_param_audit` (v0.2.x) |
| `vision` (LLM screenshot reading) | planned v0.3 (sniffing v2) |
| Compound use-case recipes | planned v0.4 |
