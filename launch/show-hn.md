# Show HN post

Post at https://news.ycombinator.com/submit
Best time: weekday ~8–10am ET. Submit the GitHub repo as the URL.
Then immediately add the first comment below.

---

**Title** (80 char max, no hype words, must start with "Show HN:"):

```
Show HN: DuckTap – Turn an OpenAPI spec into an MCP server, deterministically
```

**URL:**
```
https://github.com/zanni098/DuckTap
```

---

**First comment (post this yourself right after submitting):**

I built DuckTap because I kept hand-writing the same glue to make agents talk to
APIs. It takes an OpenAPI spec (or a HAR file) and prints an MCP server + a CLI +
an agent skill in one command:

    pip install ducktap
    ducktap press ./openapi.yaml --name myapi

The one design choice everything follows from: generation is **deterministic** —
it parses the spec and emits code directly. No model in the loop, no API key, no
per-run token cost, and the same spec produces the same output, so you can run it
in CI and code-review the diff.

It's openly inspired by Matt Van Horn's Printing Press, which makes the opposite
bet — prompt-driven generation inside Claude Code, with a great community library.
I wanted the spec-first, reproducible, harness-independent version. I wrote an
honest comparison of when to use which here: [link to docs/ducktap-vs-printing-press.md]

It's early (v0.6, alpha, solo) and I'd genuinely like to know where it breaks.
What would make this useful in your agent setup — and what's missing? 30-second
demo GIF is at the top of the README.

---

## Notes for yourself
- Reply to *every* comment in the first 2 hours; HN ranking is engagement-sensitive.
- Don't be defensive about Printing Press comparisons — agree, point to the comparison doc, and explain the deterministic/CI angle.
- If someone finds a bug, thank them and open an issue live. That earns more than a perfect launch.
- Do NOT ask for upvotes anywhere (instant flag).
