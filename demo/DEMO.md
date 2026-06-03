# The DuckTap 30-second demo

One job for this demo: make a stranger think *"wait, that's one command and now
my agent can call Stripe?"* — in under 30 seconds, with no narration required.

The hero claim is **deterministic OpenAPI → MCP server in one command**, so the
demo must show exactly that and nothing else. Resist adding the dashboard, the
other languages, or sniffing — they dilute the punch.

---

## Variant A — terminal GIF (reproducible, no API keys, no Claude)

This is the one that goes at the top of the README and in every post. Record it
with [VHS](https://github.com/charmbracelet/vhs) so it's regenerable:

```bash
# one-time
brew install vhs            # or: go install github.com/charmbracelet/vhs@latest
# from repo root
vhs demo/demo.tape          # writes demo/ducktap.gif
```

The beats (see `demo.tape` for the exact timing):

1. `pip install ducktap` — the bar to try is *one line*.
2. `ducktap catalog print stripe --out ./out` — the single command.
3. The **scorecard** prints (92/100) and the file counts appear — proof it's real, structured output, not a toy.
4. `ls ./out` — there's an actual `mcp-server/`, `python-cli/`, `skill/`.
5. One line of caption: *"Add the MCP server to Claude Desktop — done."*

Total: ~25 seconds. No editing, no voiceover.

---

## Variant B — the money shot (manual screen recording, ~40s)

This is the emotional payoff for a launch video or a follow-up tweet: the agent
actually *using* the generated tool.

1. Run `ducktap catalog print stripe --out ./out`.
2. `cd out/mcp-server && pip install -e .`
3. Add it to Claude Desktop config (the generated `mcp-server/README.md` prints
   the exact JSON block — copy it in):
   ```json
   {
     "mcpServers": {
       "stripe": { "command": "stripe-dt-mcp", "env": { "STRIPE_API_KEY": "${STRIPE_API_KEY}" } }
     }
   }
   ```
4. Restart Claude Desktop, then ask: *"List my 3 most recent Stripe charges."*
5. Record Claude calling the generated tool and answering.

Record with QuickTime (macOS) or the Windows Game Bar (`Win+G`), then trim to the
two moments: the one command, and Claude answering. Convert to GIF with
`ffmpeg -i clip.mov -vf "fps=12,scale=900:-1" demo/ducktap-claude.gif` if you want
it inline in the README.

---

## Caption to ship with both

> One command turns any OpenAPI spec into an MCP server your agent can call.
> Deterministic — no LLM, no API key, no Claude Code. `pip install ducktap`.

## Where it goes

- Top of `README.md`, above the fold.
- The Show HN / Reddit / X posts (`launch/`) all point at this GIF.
- The DuckTap website hero.
