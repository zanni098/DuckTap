# Reddit + X launch copy

## Reddit — r/LocalLLaMA, r/mcp, r/ClaudeAI

Subreddit rules vary; r/LocalLLaMA dislikes pure self-promo, so lead with the
artifact and a question, not a pitch. Flair as a tool/project. Post the demo GIF
directly (Reddit ranks native media higher than links).

**Title:**
```
I made a tool that turns any OpenAPI spec into an MCP server in one command (deterministic, no LLM in the loop)
```

**Body:**
> I wanted my agents to call real APIs without hand-writing an MCP server each
> time, so I built **DuckTap**. Point it at an OpenAPI spec or a HAR file and it
> prints an MCP server + a CLI + an agent skill:
>
> ```
> pip install ducktap
> ducktap press ./openapi.yaml --name myapi
> ```
>
> The part I care about: it's **deterministic** — it parses the spec and emits
> code, no model in the loop. Same spec → same output, no API key, runs in CI.
> (It's spec-first by design; Printing Press is the prompt-driven, Claude-Code
> version if that's what you want — honest comparison in the repo.)
>
> 30-sec demo GIF below. It's early/alpha and solo — I'd really like to hear
> where it falls over and what API you'd point it at first.
>
> Repo: https://github.com/zanni098/DuckTap

**Then:** reply to every comment, and when someone names an API, actually run
DuckTap on it and reply with the result. That thread *is* your user research.

---

## X / Twitter thread

Tag @mvanhorn (credit Printing Press — he has the audience and it's genuine
lineage). Attach the GIF to tweet 1; media-first tweets travel further.

**1/**
> Turn any OpenAPI spec into an MCP server your agent can call — in one command.
>
> Deterministic. No LLM in the loop, no API key, runs in CI. Same spec → same
> output, every time.
>
> `pip install ducktap`
> [attach demo/ducktap.gif]

**2/**
> Most "API → agent tool" generators ask a model to write the wrapper each run.
> DuckTap just parses the spec and emits the code, so the output is reproducible
> and reviewable in a diff. Boring on purpose.

**3/**
> One command prints three things from a spec: an MCP server (drop into Claude
> Desktop/Cursor), a Python CLI, and an agent skill. Plus a scorecard grading the
> generated surface (coverage, docs, auth, typed params).

**4/**
> Openly inspired by @mvanhorn's Printing Press — same north star (muscle memory
> for agents). PP is prompt-driven inside Claude Code with a great library;
> DuckTap is the spec-first, deterministic, CI-friendly take. When to use which:
> [comparison link]

**5/**
> It's v0.6 and early. If you maintain an API or live in an agent harness, I'd
> love for you to point it at one spec and tell me what broke.
> https://github.com/zanni098/DuckTap

---

## Posting order (one launch day)
1. Push the README rewrite + demo GIF first. Nothing launches before the GIF is live.
2. Show HN in the morning.
3. The X thread ~30 min later, linking nothing to HN (HN hates vote brigading).
4. r/LocalLLaMA / r/mcp in the afternoon.
5. Spend the rest of the day replying, not posting.
