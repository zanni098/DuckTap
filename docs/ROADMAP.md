# DuckTap Roadmap

DuckTap v0.1 ships the **lean loop end-to-end**. The roadmap below charts the
path from "scaffold + working core" to feature parity with (and improvements
over) Printing Press.

## v0.1.0 — Foundation (this release)

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

## v0.2.0 — Polish

- [ ] LLM-assisted **operation description rewrite** (`ducktap polish <name>`)
- [ ] LLM-assisted **command renaming** for unwieldy operation IDs
- [ ] Auth-doctor: detect login flows during sniffing, emit accurate auth env-var docs
- [ ] Generated CLIs gain `--watch` and `--save` for ad-hoc local data lakes
- [x] Scorecard CI mode (fail builds below threshold) — `ducktap scorecard --fail-under N` (0.1.2)
- [ ] More catalog entries (Slack, Linear, Discord, Telegram, Twilio, Notion, …)

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

## v0.3.0 — Sniffing v2

- [ ] **Crowd-sniff**: study existing community CLIs/MCP servers via web search
- [ ] **GraphQL** promoted to first-class discoverer (introspection + persisted queries)
- [ ] Smart action recording for sniff (record clicks/forms, replay headless)
- [ ] mitmproxy-backed sniff (no headless Chromium needed) as an alternative
- [ ] Rate-limit + retry-with-backoff aware request inference

## v0.4.0 — Compound queries

- [ ] **Compound command macros**: declarative recipes that chain multiple operations
- [ ] Local "data lake" mode: persistent mirror, full-text search over JSON
- [ ] DuckDB backend option as alternative to SQLite
- [ ] Built-in `<api>-dt-cli query "SELECT …"` for SQL over the mirror

## v0.5.0 — Publish

- [ ] `ducktap publish <name>` → PyPI + GitHub in one command (`gh` + `twine`)
- [ ] Auto-generated GitHub Actions for the generated CLIs (test + release)
- [ ] DuckTap Library: a public registry of community-printed CLIs (separate repo)

## v0.6.0 — Multi-language generators

- [ ] TypeScript CLI generator (oclif)
- [ ] Go CLI generator (cobra) — for users who want the Printing Press output shape
- [ ] Rust CLI generator (clap) — single-binary distribution

## Known gaps vs Printing Press

| PP feature | DuckTap status |
|---|---|
| 30+ catalog entries | 3 starter entries (more in v0.2) |
| `emboss` brand-stamp step | Not planned |
| `mcp-audit` | Subsumed by scorecard `artifacts` dimension |
| `tools-audit` | Subsumed by `public_param_audit` (v0.2) |
| `vision` (LLM screenshot reading) | Planned for v0.3 (sniffing v2) |
| Compound use-case recipes | Planned for v0.4 |
