# DuckTap vs Printing Press

A frank, feature-level comparison. **Printing Press is the established Go
tool**; DuckTap is the Python-native, multi-agent reimagining.

## Philosophy

Both tools share the same core thesis: agents thrive on stable, well-named
CLIs more than on raw APIs. Both produce a CLI, MCP server, and agent skill
material.

Where they diverge:

- **Printing Press** optimizes for Claude Code and single-binary Go output.
  Performance and one-file distribution are first-class.
- **DuckTap** optimizes for hackability and multi-agent reach: editable Python,
  LiteLLM, plugin entry points, multiple skill formats, a local web dashboard,
  local data querying, and now TypeScript/Go/Rust scaffolds.

## Feature Matrix

| Capability | Printing Press 4.x | DuckTap 0.6.0 | Notes |
|---|---|---|---|
| OpenAPI 2/3 to CLI | yes | yes | DuckTap normalizes into `APISpec`. |
| HAR to CLI | yes | yes | DuckTap clusters by method, host, and generalized path. |
| Browser-sniff to CLI | yes | yes | DuckTap uses Playwright and HAR export. |
| GraphQL introspection | partial | yes | First-class DuckTap discoverer in v0.6.0. |
| Generated primary CLI | Go | Python | DuckTap prioritizes editable runtime code. |
| Additional CLI outputs | Go primary | TypeScript, Go, Rust scaffolds | v0.6.0 default targets. |
| Local SQLite mirror | yes | yes | DuckTap also adds saved response records. |
| Local SQL/search over saved responses | partial/domain-specific | yes | `--save`, `data query`, `data search`. |
| MCP server output | yes | yes | DuckTap uses the Python MCP SDK. |
| Claude Code skill | yes | yes | Both produce `SKILL.md`. |
| Cursor `.mdc` skill | no/limited | yes | DuckTap emits Cursor rules. |
| Generic `tools.json` | no/limited | yes | Useful for non-Claude agent harnesses. |
| Multi-LLM support | Claude-oriented | yes | LiteLLM: Anthropic, OpenAI, Gemini, Ollama, Groq, Azure. |
| Scorecard | yes | yes | DuckTap now scores agent and local-data affordances too. |
| Shipcheck | yes | yes | Structural/runtime sanity checks. |
| Auth doctor | yes | yes | DuckTap validates env vars and can probe live auth. |
| `--agent` one-flag mode | yes | yes | Toggles JSON, compact output, and no color. |
| `--format jsonl/csv/plain` | yes | yes | DuckTap keeps JSON/pretty toggles too. |
| `--rate-limit` / `--timeout` | yes | yes | Token bucket plus per-request timeout. |
| Saved profiles | yes | yes | JSON under `~/.ducktap/<api>/profiles/`. |
| `agent-context` | yes | yes | Structured command manifest for agents. |
| `which <keyword>` | yes | yes | Search operations by id/path/summary. |
| Plugin system | source fork | entry points | DuckTap supports drop-in discoverers/generators. |
| Web UI / dashboard | no | yes | `ducktap ui` local workbench. |
| Publish command | no direct equivalent | dry-run package manifest | Live PyPI/GitHub backends remain future work. |
| Catalog size | 30+ recipes | 17 recipes | Printing Press still leads catalog breadth. |
| LLM polish / command rewrite | yes | planned | DuckTap keeps this on the post-v0.6 roadmap. |
| Vision screenshot OCR | yes | planned | Future sniffing v2 work. |

## When To Pick Which

Pick **Printing Press** if you want the most mature Claude Code focused
experience today, a single Go binary, and the larger built-in catalog.

Pick **DuckTap** if you want Python you can inspect and edit, Cursor/Codex and
generic agent assets, multi-LLM plumbing, a web workbench, GraphQL, local
response querying, plugin-based extension, and language scaffolds beyond the
primary runtime.

Both projects are MIT-licensed. DuckTap intentionally keeps the good
agent-CLI ideas from Printing Press while pushing into a broader multi-agent
and multi-language shape.
