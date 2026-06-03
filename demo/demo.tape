# DuckTap 30-second demo — render with: vhs demo/demo.tape
# Produces demo/ducktap.gif. Requires: https://github.com/charmbracelet/vhs
#
# Goal: show the ONE claim — deterministic OpenAPI -> MCP server in one command.
# Keep it under ~30s. No dashboard, no other languages, no sniffing.

Output demo/ducktap.gif

Set Theme "Catppuccin Mocha"
Set FontSize 18
Set Width 1100
Set Height 640
Set Padding 18
Set TypingSpeed 55ms
Set PlaybackSpeed 1.0

# --- 1. The one-line install (the low bar to try) ---
Type "pip install ducktap"
Sleep 400ms
Enter
Sleep 1200ms
Type "clear"
Enter
Sleep 300ms

# --- 2. The single command: spec in, agent tooling out ---
Type "# Turn the Stripe OpenAPI spec into an MCP server — deterministically"
Enter
Sleep 600ms
Type "ducktap catalog print stripe --out ./out"
Sleep 500ms
Enter

# Let the real scorecard + file counts print
Sleep 3500ms

# --- 3. Prove the artifacts are real ---
Type "ls ./out"
Sleep 400ms
Enter
Sleep 2000ms

Type "ls ./out/mcp-server"
Sleep 400ms
Enter
Sleep 2000ms

# --- 4. The payoff line ---
Type "# Drop ./out/mcp-server into Claude Desktop and your agent can call Stripe."
Enter
Sleep 400ms
Type "# No LLM. No API key. Same spec -> same output, every time."
Enter
Sleep 2500ms
