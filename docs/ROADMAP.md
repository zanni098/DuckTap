# DuckTap Roadmap

DuckTap now targets the same agent-CLI muscle memory as Printing Press while
leaning into Python hackability, multi-agent output, and a local workbench.
This document records what has landed through v0.6.0 and what remains.

## v0.1.0 — Foundation ✓

- [x] Repo skeleton, MIT license, GH Actions CI
- [x] `APISpec` intermediate model
- [x] OpenAPI 2/3 discoverer
- [x] HAR discoverer
- [x] Browser-sniff scaffold with Playwright
- [x] Python CLI generator with Click, httpx, auth from env, retries, and SQLite mirror
- [x] MCP server generator using the Python MCP SDK
- [x] Skill generator for Claude Code, Cursor `.mdc`, and generic `tools.json`
- [x] Multi-LLM abstraction via LiteLLM
- [x] Plugin registry with entry-point loading
- [x] Scorecard, shipcheck, catalog loader, FastAPI dashboard, and Typer CLI

## v0.2.x — Agent-Native Polish ✓

- [x] `--select`, `--compact`, `--quiet`, and `--dry-run`
- [x] Typed exit codes: `3` not found, `4` auth, `5` API, `7` rate limit, `10` local config
- [x] `doctor` and `auth-doctor` with optional live auth probe
- [x] Tag-grouped command tree: `<api>-dt-cli pet add-pet`
- [x] `--agent`, `--format json|jsonl|csv|plain|pretty`, `--no-color`
- [x] `agent-context` and `which <keyword>` for agent introspection
- [x] Saved profiles plus `--profile NAME`
- [x] `--rate-limit` and `--timeout`
- [x] Catalog expansion to 17 built-in recipes
- [x] Dashboard workbench with source press panel, catalog filters, scorecard panel, and JSON APIs
- [x] Generated README polish and version sync checks

## v0.3.0 — Discovery Expansion ✓

- [x] GraphQL promoted to a first-class discoverer through introspection
- [x] GraphQL operations normalized into the same `APISpec` model as OpenAPI/HAR
- [x] Plugin autoload includes GraphQL by default

Still open for future sniffing work:

- [ ] Crowd-sniff community CLIs/MCP servers before generating a new one
- [ ] Smart action recording for browser sniffing
- [ ] mitmproxy-backed sniffing as a Chromium-free alternative
- [ ] Rate-limit-aware request inference during sniffing

## v0.4.0 — Local Data Layer ✓

- [x] Generated CLIs gained `--save NAME`
- [x] Successful responses can be stored as rows in a local SQLite `records` table
- [x] `data query "<select ...>"` runs read-only SQL over saved/cache data
- [x] `data search <text>` searches stored JSON bodies
- [x] Scorecard now includes a `local_data` dimension

Future data work:

- [ ] DuckDB backend option
- [ ] FTS5 indexes and domain-specific tables
- [ ] Declarative compound command macros such as `health`, `stale`, and `bottleneck`

## v0.5.0 — Publish Workflow ✓

- [x] `ducktap publish <name>` packages generated artifacts into a zip
- [x] Publish manifest records artifacts, scorecard, shipcheck, dry-run state, and next steps
- [x] Publish uses the saved APISpec manifest from `press`

Future release work:

- [ ] Live PyPI upload backend
- [ ] GitHub release backend
- [ ] Auto-generated GitHub Actions for generated CLIs
- [ ] Public DuckTap Library registry for community-printed CLIs

## v0.6.0 — Multi-Language Generators ✓

- [x] TypeScript CLI scaffold with command manifest and npm metadata
- [x] Go CLI scaffold with runnable `agent-context` command
- [x] Rust CLI scaffold with Cargo metadata and command manifest
- [x] `ducktap press` now defaults to all six built-in targets:
  `python-cli`, `mcp-server`, `skill`, `typescript-cli`, `go-cli`, and `rust-cli`
- [x] Dashboard target selector exposes all six outputs

## Known Gaps vs Printing Press

| PP feature | DuckTap status |
|---|---|
| `--compact` / `--select` flags | landed v0.2.0 |
| Typed exit codes | landed v0.2.0 |
| `doctor` / `auth-doctor` | landed v0.2.2 |
| Tag-grouped command tree | landed v0.2.1 |
| `--agent`, `--format`, profiles, `agent-context`, `which` | landed v0.2.1 |
| `--rate-limit` and `--timeout` globals | landed v0.2.1 |
| GraphQL discovery | landed v0.6.0 |
| Local data lake / query / search | landed v0.6.0 |
| Publish command | dry-run packaging landed v0.6.0; live backends planned |
| Multi-language output | TS/Go/Rust scaffolds landed v0.6.0 |
| 30+ catalog entries | 17 entries; catalog growth remains ongoing |
| Domain-specific SQLite tables + FTS5 | planned after v0.6 |
| Compound query recipes | planned after v0.6 |
| Live API smoke test | planned after v0.6 |
| LLM polish / command renaming | planned after v0.6 |
| Vision screenshot reading | planned for sniffing v2 |
