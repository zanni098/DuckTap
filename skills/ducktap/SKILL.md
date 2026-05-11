---
name: ducktap
description: Print an agent-native CLI, MCP server, and skill for any API or website. Uses the DuckTap factory.
version: 0.1.0
min-binary-version: "0.1.0"
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - WebFetch
---

# /ducktap

Generate a production-quality CLI for an API in one lean loop.

```bash
/ducktap Petstore
/ducktap https://api.example.com/openapi.yaml
/ducktap --har ./capture.har --name MyAPI
/ducktap https://flights.google.com   # browser-sniff a site
```

## The loop

1. **Resolve the source.** If it's a catalog name, look it up. If it's a URL ending in `.json`/`.yaml`, treat as OpenAPI. If it's a website URL, browser-sniff it. If it's a `.har` file, parse it.
2. **Discover.** Run `ducktap research <source>` and write the normalized `APISpec` to `./out/<name>.spec.json`.
3. **Press.** Run `ducktap press <source> --out ./out` to emit:
   - `out/<name>-dt-cli/`  — Python CLI (Click-based)
   - `out/<name>-dt-mcp/`  — MCP server
   - `out/skills/ducktap-<name>/`  — Claude/Cursor/JSON skill manifests
4. **Score.** Run `ducktap scorecard ./out/<name>.spec.json` and surface the breakdown.
5. **Shipcheck.** Run `ducktap shipcheck <name>`. If anything fails, stop and report.
6. **Try it.** `cd out/<name>-dt-cli && pip install -e . && <name>-dt-cli --help` then run one read-only command as a smoke test.

## Auth

If the user's request requires auth, infer the env var names from the printed `SKILL.md`'s "Auth" section. Don't put secrets in the repo.

## Output contract

Tell the user:
- Where the CLI lives (`./out/<name>-dt-cli`)
- The overall scorecard grade
- Top 3 commands to try, with full example invocations
- How to add the MCP server to Claude Desktop / Cursor
