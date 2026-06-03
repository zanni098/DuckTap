# Get 5 real users (before the next feature)

The goal isn't 5 downloads — it's **5 people you watch go from `pip install` to
"my agent called the API," and who tell you what confused them.** That's worth
more than any feature you could build this month.

## Who to target (people who feel this pain today)

1. People building MCP servers by hand — search GitHub for recently-updated repos
   matching `mcp server` in Python/TS; the authors hand-wrote what DuckTap prints.
2. People who commented on Printing Press / MCP threads on HN, r/mcp, X.
3. Anyone in your network shipping an agent that calls a REST API.
4. Maintainers of a mid-size API with a public OpenAPI spec (they want their API
   to be agent-reachable).

You only need 5. Quality of feedback > volume.

## Where to find them
- r/mcp and r/LocalLLaMA comment sections (your own launch threads).
- The MCP Discord / community servers (see `mcp-community.md`).
- GitHub: `is:issue mcp server "how do I"` — people actively stuck.
- X search: `MCP server` + `OpenAPI`.

## Cold-but-warm DM template (X / Discord / GitHub)

> Hey — saw you [built an MCP server for X / asked about Y]. I made a tool that
> generates an MCP server straight from an OpenAPI spec in one command
> (deterministic, no LLM), and I'm trying to find out if it actually saves
> anyone time before I build more. Would you try it on one API you care about
> and tell me where it breaks? 10 min, I'll watch and fix anything live. No ask
> beyond honest feedback. Repo: [link]

Keep it specific to *them*. Never paste the same line to 20 people — 5 tailored
messages beat 50 generic ones.

## The "watch them use it" session (15 min, the important part)

Get on a call/screen-share, or async with a screen recording. **Say almost
nothing.** You're looking for the moment they hesitate.

Script:
1. "Pretend I'm not here. Install it and make your agent able to call [their API].
   Talk out loud as you go."
2. **Shut up and watch.** Write down every place they pause, re-read, or guess.
3. Only help once they're truly stuck — and note exactly what unblocked them.
4. At the end, three questions:
   - "Where did you almost give up?"
   - "What did you expect to happen that didn't?"
   - "On a scale of 1–10, how disappointed would you be if this disappeared?
     Why that number?" (The Sean Ellis test — if most say <7, the pitch or
     product isn't there yet.)
5. "Who else has this problem?" → your next user.

## What to do with what you learn
- Every hesitation = a README/onboarding fix. Do those *before* any feature.
- Every "I expected X" = a defaults/UX bug. File it.
- One quoted sentence from a happy user → goes in the README and your next post.

## Tracker

| # | Who | Found via | API they tried | Got to "agent called it"? | Biggest friction | Disappointment 1–10 | Quote? |
|---|-----|-----------|----------------|---------------------------|------------------|---------------------|--------|
| 1 |     |           |                |                           |                  |                     |        |
| 2 |     |           |                |                           |                  |                     |        |
| 3 |     |           |                |                           |                  |                     |        |
| 4 |     |           |                |                           |                  |                     |        |
| 5 |     |           |                |                           |                  |                     |        |

Don't ship the next feature until this table is full and the frictions are fixed.
