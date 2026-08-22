# DuckTap Architecture

DuckTap is organized around one normalized data model (`APISpec`) sitting
between two extensible plugin layers (Discoverers and Generators).

## Modules

| Module | Responsibility |
|---|---|
| `ducktap.core.spec` | `APISpec` (pydantic) — the intermediate representation. |
| `ducktap.core.naming` | Slugify, snake/kebab case, flag/env-var conventions. |
| `ducktap.core.plugins` | Plugin registry + entry-point loader. |
| `ducktap.core.pipeline` | High-level `discover()` and `press()`. |
| `ducktap.discovery.openapi` | OpenAPI 2/3 → `APISpec`. |
| `ducktap.discovery.har` | HAR file → `APISpec` (clustered request grouping). |
| `ducktap.discovery.browser_sniff` | Playwright → HAR → `APISpec`. |
| `ducktap.generator.python_cli` | `APISpec` → Click-based Python CLI package. |
| `ducktap.generator.typescript_cli` | `APISpec` → oclif TypeScript CLI (`tsc`-verified). |
| `ducktap.generator.go_cli` | `APISpec` → cobra Go CLI (`go build`-verified). |
| `ducktap.generator.rust_cli` | `APISpec` → clap Rust CLI (`cargo build`-verified). |
| `ducktap.generator.mcp_server` | `APISpec` → MCP server package (stdio). |
| `ducktap.generator.skill` | `APISpec` → `SKILL.md`, `.mdc`, `tools.json`. |
| `ducktap.discovery.mitm_sniff` | mitmproxy → HAR → `APISpec` (no headless browser). |
| `ducktap.plugins.builtin.graphql_intro` | GraphQL introspection → `APISpec`. |
| `ducktap.llm.base` | LiteLLM wrapper — multi-provider chat (the `[llm]` extra). |
| `ducktap.verify.scorecard` | Quality grading (7 dimensions). |
| `ducktap.verify.proof` | Proof of behavior — spec vs. generated source. |
| `ducktap.manifest` | `.ducktap.json` provenance manifest. |
| `ducktap.verify.shipcheck` | Structural + runtime sanity checks. |
| `ducktap.catalog.registry` | YAML recipe loader. |
| `ducktap.webui.app` | FastAPI dashboard. |
| `ducktap.cli` | Top-level `ducktap` Typer entry point. |

## Architecture Diagram

The following diagram shows DuckTap's end-to-end discovery, normalization, generation, and verification pipeline.

```mermaid
flowchart TD
    A["Input<br/>URL / OpenAPI spec / HAR / website"] --> B{Discovery}

    B --> B1["ducktap.discovery.openapi<br/>OpenAPI 2/3"]
    B --> B2["ducktap.discovery.har<br/>HAR file"]
    B --> B3["ducktap.discovery.browser_sniff<br/>Playwright → HAR"]
  B --> B4["ducktap.discovery.mitm_sniff<br/>mitmproxy → HAR"]
  B --> B5["ducktap.plugins.builtin.graphql_intro<br/>GraphQL introspection"]

    B1 --> C["APISpec (Pydantic)<br/>normalized intermediate representation"]
    B2 --> C
    B3 --> C
    B4 --> C
  B5 --> C

    C --> D{Generators}

    D --> D1["python_cli<br/>Click-based CLI"]
    D --> D2["typescript_cli<br/>oclif CLI"]
    D --> D3["go_cli<br/>cobra CLI"]
    D --> D4["rust_cli<br/>clap CLI"]
    D --> D5["mcp_server<br/>stdio MCP server"]
    D --> D6["skill<br/>SKILL.md / .mdc / tools.json"]

    D1 --> E["Generated artifacts<br/>target-specific output directories"]
    D2 --> E
    D3 --> E
    D4 --> E
    D5 --> E
    D6 --> E

    E --> F1["scorecard<br/>7-dimension quality grading"]
    E --> F2["shipcheck<br/>structural + runtime checks"]
    E --> F3["proof<br/>spec vs. generated behavior"]
    E --> F4["optional live smoke test"]

    G["Catalog<br/>YAML recipe loader"] -.-> A
    H["Web UI<br/>FastAPI dashboard"] -.-> A
```

## The pipeline


## The pipeline

```
press(source, out_dir)
  │
  ├── discover(source)
  │     for d in [openapi, graphql, har, browser-sniff, …]:
  │       if d.can_handle(source): return d.discover(source).normalize()
  │
  ├── archetype detection + Non-Obvious Insight   (deterministic unless use_llm)
  │
  ├── for tgt in targets:
  │     generators[tgt].generate(spec, out_dir)
  │
  ├── write .ducktap.json provenance manifest
  │
  └── PressResult(spec, out_dir, artifacts, manifest)
```

`normalize()` is the contract between discovery and generation: it guarantees
the invariants every generator relies on (a slug name, unique operation ids).
Put shared invariants there rather than in each generator.

## Why this shape

- **One intermediate format** means new discoverers and new generators evolve independently.
- **Plugins via entry points** means improvements ship as PyPI packages, not forks.
- **Pydantic models** give us free JSON serialization (research command writes the spec to disk for inspection / debugging / LLM polish steps).
- **Click for generated CLIs** because every Python user already has it and Click subcommands have richer help output than argparse out of the box.
- **MCP SDK** rather than hand-rolled JSON-RPC, so we get protocol-version updates for free.
