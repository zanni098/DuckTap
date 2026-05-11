# DuckTap

> **Tape any API to your agent in one command.**
> DuckTap is a CLI factory for AI agents. Point it at an OpenAPI spec, a HAR
> file, or a plain website, and it *prints* a Python CLI, an MCP server, and a
> Claude/Cursor/Codex skill — wired up, cached, scored, ready to ship.

[![CI](https://github.com/zanni098/DuckTap/actions/workflows/ci.yml/badge.svg)](https://github.com/zanni098/DuckTap/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](pyproject.toml)

DuckTap is inspired by [Printing Press](https://printingpress.dev) by
[@mvanhorn](https://github.com/mvanhorn) — same north star (*muscle memory for
agents*) — rebuilt in Python with multi-LLM support, a web dashboard,
Playwright-powered browser sniffing, and a real plugin system.

## Why a CLI factory?

In a world of AI agents, **a well-designed CLI is muscle memory**. No hunting
through docs, no wrong turns, no wasted tokens. DuckTap reads the spec, sniffs
the traffic when no spec exists, and prints:

- **A Python CLI** (`<api>-dt-cli`) — Click-based, auth from env vars, JSON by default, pretty mode for humans, local SQLite mirror for compound queries, retries on transient errors.
- **An MCP server** (`<api>-dt-mcp`) — every operation exposed as an MCP tool, stdio transport, drop into Claude Desktop or Cursor in 60 seconds.
- **A skill** for Claude Code, Cursor (`.mdc`), and a generic `tools.json` — so any agent harness can pick up where the others left off.
- **A scorecard** grading coverage, docs, auth clarity, typed params, artifacts, and naming.

## Install

```bash
git clone https://github.com/zanni098/DuckTap
cd ducktap
pip install -e ".[dev]"
ducktap --version
```

For browser sniffing:

```bash
pip install -e ".[dev,sniff]"
playwright install chromium
```

## Quick start

```bash
# 1. From an OpenAPI spec (file or URL)
ducktap press https://petstore3.swagger.io/api/v3/openapi.yaml

# 2. From a HAR file (recorded browser traffic)
ducktap press ./capture.har --name myapi

# 3. From a website with no public spec
ducktap sniff https://example.com

# 4. From the curated catalog
ducktap catalog list
ducktap catalog print stripe

# 5. Browse + drive everything from the dashboard
ducktap ui    # http://127.0.0.1:8765
```

What you get under `./out/`:

```
out/
├── petstore-dt-cli/        # pip install -e .  →  petstore-dt-cli --help
│   ├── pyproject.toml
│   ├── README.md
│   ├── petstore_dt_cli/
│   │   ├── main.py
│   │   ├── commands.py     # one click subcommand per API operation
│   │   ├── client.py       # httpx + env-var auth + retries
│   │   └── mirror.py       # local SQLite cache
│   └── tests/test_smoke.py
├── petstore-dt-mcp/        # pip install -e .  →  add to Claude Desktop config
│   └── petstore_dt_mcp/server.py
└── skills/ducktap-petstore/
    ├── SKILL.md            # Claude Code skill
    ├── ducktap-petstore.mdc  # Cursor rule
    └── tools.json          # generic agent tool definitions
```

## How DuckTap improves on Printing Press

| | Printing Press | **DuckTap** |
|---|---|---|
| Language | Go | Python — easier to extend, richer LLM ecosystem |
| LLM | Claude only | **Multi-LLM via LiteLLM** (Anthropic, OpenAI, Gemini, Ollama, Groq, Azure) |
| Skills | Claude Code | **Claude Code + Cursor `.mdc` + generic `tools.json`** |
| UI | None | **Local FastAPI dashboard** (`ducktap ui`) |
| Plugins | Source fork | **Entry-point plugin system** — drop-in discoverers & generators |
| Browser sniff | Custom Go browser | **Playwright** — full HAR export, scriptable actions |
| Generated CLI runtime | Single Go binary | Python (pip-installable, hackable, single-file editable) |

See [`docs/COMPARISON.md`](docs/COMPARISON.md) for the full feature matrix.

## Commands

```text
ducktap press <source>          # discover + generate (the default loop)
ducktap research <source>       # discover only — emit normalized APISpec JSON
ducktap sniff <url>             # browser-sniff a site (needs [sniff] extra)
ducktap scorecard <source>      # quality scorecard
ducktap shipcheck <name>        # structural & runtime sanity checks
ducktap catalog list|print      # browse the recipe library
ducktap plugins list            # show installed discoverers + generators
ducktap ui                      # local web dashboard
```

## Plugins

Add a discoverer or generator without forking. Register via Python entry points:

```toml
# your_plugin/pyproject.toml
[project.entry-points."ducktap.plugins"]
mything = "your_plugin.module"   # module just calls plugins.register_discoverer(...)
```

See [`docs/PLUGINS.md`](docs/PLUGINS.md) and the sample at
`src/ducktap/plugins/builtin/graphql_intro.py`.

## Architecture

```
input (URL | spec | HAR)
        │
        ▼
  ┌─────────────┐
  │  Discovery  │   openapi / har / browser-sniff / graphql (plugin) / …
  └──────┬──────┘
         ▼
   APISpec (Pydantic) ──── intermediate normalized representation
         │
         ▼
  ┌─────────────┐
  │  Generator  │   python-cli / mcp-server / skill / …
  └──────┬──────┘
         ▼
  artifacts/       (CLI pkg + MCP pkg + SKILL.md + cursor.mdc + tools.json)
         │
         ▼
  ┌─────────────┐
  │   Verify    │   scorecard + shipcheck + (optional) live smoke test
  └─────────────┘
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Roadmap

See [`docs/ROADMAP.md`](docs/ROADMAP.md). Highlights for v0.2+:

- LLM-assisted **polish** step (operation descriptions, command names, doc strings)
- **GraphQL** first-class (today: plugin, beta)
- **Auth doctor** — detect login flows during sniffing, emit accurate auth blocks
- **Compound query** macros (canonical "what's interesting about X" recipes)
- **CLI publish** to PyPI + GitHub in one command

## License

MIT — see [`LICENSE`](LICENSE).

## Acknowledgements

Inspired by [Printing Press](https://github.com/mvanhorn/cli-printing-press) by
Matt Van Horn and the agent-CLI playbook proved out by
[discrawl](https://github.com/steipete/discrawl) and
[gogcli](https://github.com/steipete/gogcli).
