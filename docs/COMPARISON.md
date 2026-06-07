# DuckTap vs Printing Press

A frank, feature-level comparison. **Printing Press is the established tool**;
DuckTap is the Python-native, multi-agent reimagining.

## Philosophy

Both tools share the same core thesis: agents thrive on stable, well-named
CLIs more than on raw APIs. Both produce a CLI **plus** an MCP server **plus**
agent skill manifests.

Where they diverge:

- **Printing Press** optimizes for Claude Code (the harness it tests against) and ships everything as a single Go binary plus distributed skills. Performance and single-binary deployment are first-class.
- **DuckTap** optimizes for *hackability and multi-agent reach*: hot-editable Python, multi-LLM via LiteLLM, plugins via entry points, multiple skill formats, and a local web dashboard for visual workflows.

## Feature matrix

| Capability | Printing Press 4.x | DuckTap 0.7.0 | Notes |
|---|---|---|---|
| OpenAPI 2/3 → CLI | ✓ | ✓ | Both via `kin-openapi`/`openapi-spec-validator`. |
| HAR → CLI | ✓ | ✓ | DuckTap clusters by `(method, generalized_path, host)`. |
| Browser-sniff → CLI | ✓ (custom) | ✓ (Playwright) | DuckTap exposes raw Playwright actions for scripting. |
| GraphQL introspection → CLI | partial | ✓ (plugin) | First-class in DuckTap v0.3. |
| Crowd-sniff (study community CLIs) | ✓ | ⌛ v0.3 | |
| Generated CLI runtime | Go single binary | Python pip-installable | DuckTap CLIs are hackable; PP CLIs are 5-15MB single binaries. |
| Local SQLite mirror | ✓ | ✓ | Same TTL+cache-key model. |
| MCP server output | ✓ | ✓ | Both stdio. DuckTap uses official `mcp` Python SDK. |
| Claude Code skill | ✓ | ✓ | Both produce `SKILL.md` with YAML frontmatter. |
| Cursor `.mdc` skill | ⌛ | ✓ | |
| Generic `tools.json` | ⌛ | ✓ | For non-Claude agent harnesses. |
| Multi-LLM (OpenAI/Gemini/Ollama) | ✗ (Claude) | ✓ | Via LiteLLM. |
| Scorecard | ✓ | ✓ | DuckTap: 6 dimensions, deterministic, no LLM needed. |
| Shipcheck | ✓ | ✓ | DuckTap parses generated Python with `ast`. |
| Polish (LLM rewrite) | ✓ | ⌛ v0.2 | |
| Auth-doctor | ✓ | ✓ (v0.2.2) | See dedicated row below for behavior details. |
| Vision (LLM screenshot OCR) | ✓ | ⌛ v0.3 | |
| Plugin system | source fork | entry points | Drop-in PyPI plugins in DuckTap. |
| Web UI / dashboard | ✗ | ✓ | `ducktap ui`. |
| Catalog size | 30+ recipes | **30 entries** (v0.6.0) | DuckTap catalog is open YAML; PR to add. |
| Tag-grouped command tree (`<api> pet add`) | ✓ | ✓ (v0.2.1) | DuckTap groups by first OpenAPI tag. |
| `--agent` one-flag mode | ✓ | ✓ (v0.2.1) | Toggles `--json`, `--compact`, `--no-color` atomically. |
| `--format jsonl/csv/plain` | ✓ | ✓ (v0.2.1) | DuckTap also keeps `--json/--pretty`. |
| `--rate-limit` and `--timeout` globals | ✓ | ✓ (v0.2.1) | Token-bucket + per-request timeout. |
| Saved profiles (`profile save/list`) | ✓ | ✓ (v0.2.1) | DuckTap stores JSON under `~/.ducktap/<api>/profiles/`. |
| `agent-context` introspection | ✓ | ✓ (v0.2.1) | Emits full command/group/flag manifest as JSON. |
| `which <keyword>` operation search | ✓ | ✓ (v0.2.1) | Matches id, raw id, path, and summary. |
| `auth-doctor` (env-var validation + live probe) | partial (`doctor`) | ✓ (v0.2.2) | DuckTap classifies live response (`auth_works`/`auth_failed`/`rate_limited`/...). |
| `--agent --dry-run` preserves full request payload | ✓ | ✓ (v0.2.2) | Metadata views skip `--compact`; only response data gets compacted. |
| Compound query macros | ✓ | ✓ (v0.4) | |
| Publish to PyPI/GitHub | ✗ | ✓ (v0.5) | DuckTap `ducktap publish`. |
| Multi-language CLI output | **Go only** | **Python + Go + TypeScript + Rust** (v0.7) | All four compile in CI; Go=cobra, TS=oclif, Rust=clap. |
| `--dry-run` in every generated language | Go | ✓ all 4 (v0.7) | Prints the assembled request, no call made. |
| `agent-context` in every generated language | Go | ✓ all 4 (v0.7) | JSON self-introspection manifest. |
| Typed exit codes in every generated language | Go | ✓ all 4 (v0.7) | `3`/`4`/`5`/`7` from HTTP status. |
| Local SQLite mirror + FTS5 in non-Python CLIs | n/a | Python only (Go/TS/Rust: ⌛) | Tracked post-0.7. |

## When to pick which

**Pick Printing Press if:**
- You want the maximally curated agent-CLI experience today.
- You're all-in on Claude Code.
- You want single-binary distribution.
- You want the largest catalog of pre-printed CLIs immediately.

**Pick DuckTap if:**
- You want Python (easy to read, hack, embed).
- You use Cursor, OpenAI/Gemini/Ollama, or mix multiple harnesses.
- You want a plugin ecosystem rather than a monorepo.
- You want a local dashboard for non-CLI users on your team.
- You want to fork minimal code to add a new discoverer or generator.

Both projects are MIT-licensed and the design ideas flow freely. DuckTap will
upstream improvements to Printing Press where it makes sense, and adopts the
same `<api>-<suffix>-cli` and `<api>-<suffix>-mcp` naming convention (with
`-dt-` instead of `-pp-`).
