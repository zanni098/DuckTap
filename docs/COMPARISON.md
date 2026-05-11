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

| Capability | Printing Press 4.x | DuckTap 0.1 | Notes |
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
| Auth-doctor | ✓ | ⌛ v0.2 | |
| Vision (LLM screenshot OCR) | ✓ | ⌛ v0.3 | |
| Plugin system | source fork | entry points | Drop-in PyPI plugins in DuckTap. |
| Web UI / dashboard | ✗ | ✓ | `ducktap ui`. |
| Catalog size | 30+ recipes | 3 starter + community | DuckTap catalog is open YAML; PR to add. |
| Compound query macros | ✓ | ⌛ v0.4 | |
| Publish to PyPI/GitHub | ✗ | ⌛ v0.5 | |
| Multi-language CLI output | Go only | Python now; TS/Go/Rust planned v0.6 | |

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
