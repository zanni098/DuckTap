# DuckTap vs Printing Press

DuckTap was inspired by [Printing Press](https://printingpress.dev) by
[Matt Van Horn](https://x.com/mvanhorn) and [Trevin Chow](https://x.com/trevin) —
same north star: **agent-native CLIs are muscle memory for agents.** Printing
Press is excellent and more established (its
[generator](https://github.com/mvanhorn/cli-printing-press) and
[community library](https://github.com/mvanhorn/printing-press-library) have a
large following and 250+ ready-made CLIs). If it fits your workflow, use it.

DuckTap exists because the two tools make **opposite core bets**, and that bet
changes who each one is for.

## The one difference everything else follows from

| | **DuckTap** | **Printing Press** |
|---|---|---|
| **How it generates** | **Deterministic.** Parses your OpenAPI/HAR spec and emits code directly — no LLM in the loop. | **Prompt-driven.** Runs inside Claude Code and uses the model to author the CLI from a prompt or website. |
| **What it needs to run** | `pip install ducktap`. A Python interpreter. That's it. | Go toolchain + Node + Claude Code. |
| **Same spec → same output?** | Yes, byte-for-byte. CI-friendly, no token cost, reviewable diffs. | Re-generation is a fresh model run. |

Everything below is downstream of that.

## Side by side

| | **DuckTap** | **Printing Press** |
|---|---|---|
| Primary input | OpenAPI spec, HAR file (browser-sniff for spec-less sites) | A prompt / app name / website, interpreted by the model |
| Output languages | **Python, Go, Rust, TypeScript** from one spec | Go |
| Also emits | MCP server + Claude/Cursor skill + `tools.json` | MCP server + Claude Code skill + OpenClaw skill |
| Agent harness | **Decoupled** — output works in any harness, or none | Authored from inside Claude Code |
| Quality signal | **Scorecard** (coverage, docs, auth, typed params, naming) | Curated "magic moment" demos |
| Community library | Nascent (30-API catalog) | **Large** (250+ CLIs, 17 categories) — a real strength |
| Maturity / audience | New, solo, unproven | Established, named builders, real traction |

## When to use which (honestly)

**Reach for Printing Press when:**
- You live in Claude Code and want to point at *any* app or website and get a CLI from a single prompt — no spec required.
- You want to install from a big, curated community library today.
- You want the polished, demo-ready "magic moments" and a Go single-binary.

**Reach for DuckTap when:**
- **You have an OpenAPI or HAR spec** and want a CLI + MCP server generated **deterministically** — same input, same output, every time.
- You want generation in **CI / a build step** with **no LLM, no API key, no per-run token cost**, and a diff you can code-review.
- You're a **Python shop**, or you need the **same API in several languages** (Python/Go/Rust/TS) from one source.
- You want the result **decoupled from any one agent harness** — drop the MCP server into Claude Desktop, Cursor, or your own runtime.
- You want a **scorecard** to tell you how good the generated surface actually is.

## The honest summary

Printing Press is the better choice for **prompt-driven, Claude-Code-native,
community-library** CLI generation, and it has the head start. DuckTap is the
better choice when you already have a spec and want **deterministic,
reproducible, language-flexible, harness-independent** generation you can run in
a pipeline. Different bets, different jobs — pick the one that matches how you
work.
