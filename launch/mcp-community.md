# MCP / agent community outreach

The MCP crowd is the single most on-target audience for DuckTap. Go where they
already are instead of waiting for them to find the repo.

## Where
- **MCP Discord / community servers** (modelcontextprotocol community, Claude
  Developers, Cursor, OpenClaw/Hermes communities).
- **awesome-mcp-servers** lists on GitHub — DuckTap-generated servers + the
  generator itself are legit additions (open a PR adding it).
- **r/mcp**, **r/ClaudeAI**, **r/LocalLLaMA** (covered in `reddit-and-x.md`).
- **MCP registry / directories** — submit the generator and a couple of
  flagship generated servers.

## Message for a #show-and-tell / #projects channel

> Built a small thing for this community: **DuckTap** turns an OpenAPI spec (or a
> HAR file) into a working MCP server in one command — `ducktap press spec.yaml`.
> It's deterministic (parses the spec, no LLM in the loop), so the same spec
> always gives the same server and it runs in CI.
>
> Trying to find out if it's actually useful before I build more. If you've been
> hand-writing MCP servers, I'd love for you to point it at one API and tell me
> what broke. 30-sec demo + repo: [link]

## Concrete, non-spammy contributions that pull people in
1. **PR DuckTap into `awesome-mcp-servers`** under generators/tools.
2. **Publish 2–3 ready-made MCP servers** from your catalog (Stripe, GitHub,
   Linear) and submit them to MCP directories — each is a doorway back to DuckTap.
3. **Answer "how do I make an MCP server for X" questions** with a one-line
   DuckTap command *that actually works* — show, don't pitch.
4. **Write one short "how I generate MCP servers from any OpenAPI spec" post**
   and share it in these channels.

## Rule
Lead with the working artifact and a question, never with "check out my project."
This community can smell a pitch — but they love a tool that removes a chore.
