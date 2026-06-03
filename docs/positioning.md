# DuckTap positioning — pick one sharp edge

## The problem with the current pitch

The README leads with breadth: Python + TypeScript + Go + Rust CLIs, MCP
servers, skills, browser sniffing, a web dashboard, a scorecard, a plugin
system. That's a lot of surface for a project with no traction yet. Breadth
reads as "a pile of features," invites the reaction *"Printing Press already
does most of this,"* and gives a first-time user no single reason to care.

A 1-star project cannot win on breadth. It wins on **one sharp edge** that the
incumbent structurally cannot copy.

## The one edge

> **Deterministic OpenAPI → MCP server, in one command. No LLM, no API key, no Claude Code.**

This is the wedge Printing Press *can't* take, because its core bet is the
opposite: it's prompt/LLM-driven and authored inside Claude Code. DuckTap parses
a spec and emits code directly — so it's reproducible, free to run, reviewable
in a diff, and works in CI. That's the whole story. Lead with it everywhere.

## What to lead with (the hero)

Proposed README hero — replaces the current multi-paragraph intro:

> # DuckTap
> **Turn any OpenAPI spec into a working MCP server in one command — deterministically.**
>
> No LLM. No API key. No Claude Code. `ducktap press ./openapi.yaml` reads the
> spec and *prints* an MCP server (plus a Python CLI and an agent skill) that
> any agent can use — same spec, same output, every time. Runs in CI.
>
> ```bash
> pip install ducktap
> ducktap press https://api.example.com/openapi.yaml --name example
> # → MCP server + CLI + skill, scored 92/100, ready to ship
> ```
>
> Coming from Claude Code and want prompt-from-a-website generation instead?
> See [DuckTap vs Printing Press](docs/ducktap-vs-printing-press.md).

One sentence. One command. One reason to care. The comparison link disarms the
"isn't this just Printing Press?" reaction up front instead of pretending the
incumbent doesn't exist.

## Keep building, stop *leading* with

These stay in the repo — they're real and some users will want them — but they
move **below the fold**, not in the hero, because each one dilutes the wedge and
invites a "PP does that too / better" comparison:

- **Go / Rust / TypeScript generators** → a "multi-language output" section lower down.
- **Web dashboard (`ducktap ui`)** → a screenshot in a "more" section, not the pitch.
- **Browser sniffing (`sniff`)** → a "no spec? sniff it" footnote; it's PP's strongest turf, so don't fight there first.
- **Plugin system** → contributor docs.

## The discipline

Until DuckTap has real users, **the next feature is almost always the wrong
move.** The bottleneck is "nobody knows the one thing this does best," not
"not enough features." Every hour goes to sharpening and shipping the one edge —
the demo, the comparison, the launch — not widening the surface.

## Definition of done for this phase

- README hero rewritten to the single deterministic-OpenAPI→MCP claim.
- The 30-second demo (see `demo/DEMO.md`) recorded and embedded at the top.
- Comparison page linked from the hero.
- Launch posts shipped (see `launch/`).
- 5 real users watched through the demo path (see `launch/feedback-script.md`).
