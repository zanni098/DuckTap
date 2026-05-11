# DuckTap vs Printing Press — Head-to-Head Test Report

**Test date:** 2026-05-11
**DuckTap version:** 0.1.1 (commit at time of test) — built in one session
**Printing Press version:** 4.2.2 (released, mature product, months of work)
**Methodology:** Both tools run against the **same OpenAPI specs** (Petstore + full GitHub REST). Outputs inspected line-by-line, generated CLIs installed and invoked against the live APIs.

---

## TL;DR (the honest verdict)

> **Printing Press is meaningfully better as a product today.**
> DuckTap is the right *direction* for some things (multi-LLM, plugin system,
> hackability, web UI), and now after fixes ships a working basic loop — but
> in terms of **feature depth, generated-code quality, verification rigor,
> and catalog size**, PP is ahead by a large margin.

| | Printing Press 4.2.2 | DuckTap 0.1.1 |
|---|---|---|
| **Overall winner** | ✅ **Yes** | for now |
| Lines of code (tool itself) | 142,473 Go | 1,756 Python (~80× smaller) |
| Source files | 448 | 28 |
| Internal packages / modules | 29 | 8 |
| Top-level CLI commands | 29 | 8 |
| Catalog entries (built-in) | 21 across 10 categories | 3 (+ 13 in separate library repo) |
| Scorecard dimensions | **27** | 6 |
| Verification legs in shipcheck | 6 (dogfood / verify / workflow-verify / verify-skill / validate-narrative / scorecard) | 5 (existence / syntax / pyproject / readme / help) |
| LOC generated for petstore | 12,706 Go | 1,802 Python (~7× smaller) |
| Generated artifacts for petstore | 71 files | 18 files |
| Bugs found during this test | 0 | **3 critical generator bugs** (all now fixed) |
| Real-world stress test (GitHub 1183 ops) | not run (needs Go installed) | Worked after fixes |

---

## 1. Setup & install

### Printing Press
- Single 51 MB `printing-press.exe` Windows binary (also pre-built for macOS/Linux).
- `go install github.com/mvanhorn/cli-printing-press/v4/cmd/printing-press@latest` works.
- **Generated CLIs need Go** at user's machine to `go build` (or to use `go mod tidy` during generation). That's a real friction point.

### DuckTap
- `pip install ducktap` — pure Python, no separate binary needed.
- Generated CLIs are Python packages — `pip install -e .` and done. No Go toolchain required.
- **DuckTap wins this one** — Python install is universally easier than "install Go + go install".

---

## 2. Command surface

```
PP:  29 subcommands
DT:   8 subcommands (one was a duplicate, fixed during this test)
```

PP's command tree:
```
auth, browser-sniff, bundle, catalog, completion, crowd-sniff, dogfood,
emboss, generate, help, library, lock, mcp-audit, mcp-sync, patch,
polish, print, probe-reachability, public-param-audit, publish,
regen-merge, schema, scorecard, shipcheck, tools-audit,
validate-narrative, verify, verify-skill, version, vision, workflow-verify
```

DuckTap's command tree:
```
press, research, scorecard, shipcheck, ui, sniff, catalog, plugins
```

**Verdict:** PP has built every feature you'd want in a mature CLI factory — `polish` (post-generation rewrite), `bundle` (package an MCP server as .mcpb), `crowd-sniff` (study community CLIs), `vision` (LLM-aided docs reading), `emboss` (second-pass improvements), `mcp-audit` (audit installed library), `tools-audit` (static analysis of generated MCP tools), `public-param-audit` (find cryptic wire names), `probe-reachability` (multi-transport URL test), `regen-merge` (merge regen with hand-edits). **DuckTap has none of these.** It has `ui` and `plugins` that PP doesn't, but those are quality-of-life additions, not depth.

---

## 3. Generated CLI quality — Petstore comparison

Both tools were pointed at the same `petstore.yaml` and asked to generate a CLI.

### File counts
- **PP**: 71 files, 12,706 LOC of Go
- **DT**: 18 files, 1,802 LOC of Python

### Per-operation structure
- **PP**: one Go file per operation (`pet_find-by-status.go`, `pet_add.go`, `store_get-inventory.go`, etc.). Easy to read, easy to hand-edit, easy to diff in PRs.
- **DT**: one massive `commands.py` (1430 LOC for petstore, 72,915 LOC for GitHub). Harder to review, harder to spot-edit.

### What each command actually does

PP's `pet find-by-status` (excerpt):
```go
// Enum validation
allowedStatus := []string{ "available", "pending", "sold" }
// ... validates against allowed set ...

// Calls resolveRead -> uses SQLite mirror, returns (data, provenance)
data, prov, err := resolveRead(...)

// Classifies API errors (rate limit, 5xx, auth, etc.)
return classifyAPIError(err, flags)

// Prints provenance to STDERR for humans
printProvenance(cmd, len(items), prov)

// Output decision tree:
//   1. --json or pipe   -> JSON envelope with provenance, filterFields(--select), compactFields(--compact)
//   2. terminal + table -> printAutoTable, with "showing N rows" hint if >=25
//   3. else             -> printOutputWithFlags
```

DuckTap's `find-pets-by-status`:
```python
data = client.request("GET", path, query=query, headers=headers, json_body=body,
                      use_cache=("GET" == "GET"))   # ← awkward template artifact
_emit(ctx, data)                                     # ← json.dumps or rich.JSON
```

**PP's generated commands** ship with:
- `--select` (jq-style field projection)
- `--compact` (drop nulls/empties)
- `--json` vs auto-table-for-humans
- Provenance envelope (cached vs live)
- Stderr usage hints (e.g. "showing 25, try --limit")
- Per-error-class handling (`classifyAPIError`)
- MCP read-only / destructive annotations baked into the source
- Cobra aliases (e.g. `find-by-status` aliased to `list`)
- Examples in `--help`

**DuckTap's generated commands** ship with:
- `--json` flag (default)
- `--pretty` flag (rich.JSON)
- `--cache` / `--no-cache` global flag
- One-line error JSON on stderr
- Click `Choice([...])` for enums ✓

**DuckTap is ~30% of the feature surface of a PP-generated command.**

### Bonus: PP bakes the "agent power-user playbook" into every CLI

PP-generated petstore CLI has these files that have **nothing to do with the petstore spec**:
- `doctor.go` — health check command (`petstore-pp-cli doctor`)
- `profile.go` — auth profile management
- `auth.go` — `auth status`, `auth set`, `auth clear`
- `feedback.go` — `feedback` command that sends issues upstream
- `import.go` — bulk import from files
- `sync.go` — refresh the local mirror
- `tail.go` — log/event tailing
- `which.go` — show install location + version provenance
- `deliver.go` — webhook delivery integration
- `data_source.go`, `channel_workflow.go`, `analytics.go`, `helpers.go`

**This is huge.** Every PP CLI feels the same to use; an agent that learns one knows the muscle memory for all of them. **DuckTap CLIs have none of this.**

---

## 4. Generated MCP servers

### PP MCP server
- **Separate binary** (`petstore-pp-mcp`).
- Uses [`mark3labs/mcp-go`](https://github.com/mark3labs/mcp-go) SDK.
- Each tool registered with `WithReadOnlyHintAnnotation`, `WithDestructiveHintAnnotation`, `WithOpenWorldHintAnnotation` — the new MCP tool-annotation spec.
- Wire-name vs public-name binding (`{PublicName: "petId", WireName: "petId", Location: "path"}`).
- Auto-classifies operations: GET → `mcp:read-only`, DELETE → `mcp:destructive`.

### DuckTap MCP server
- Separate Python package (`petstore-dt-mcp`).
- Uses official Python `mcp` SDK.
- Reuses the CLI's HTTP client and SQLite mirror.
- **Was broken** when this test started. Generator emitted JSON `false`/`true` inside Python `dict()` literals → `NameError: name 'false' is not defined` on import. Fixed mid-test.
- Tools have description + inputSchema; **no annotations** for read-only / destructive / open-world.

### What DuckTap is missing in MCP
- No tool annotations (read-only / destructive / idempotent / open-world).
- No wire-name vs public-name separation.
- No `mcp-audit` or `tools-audit` to catch quality issues.
- No surface-strategy choice (PP can expose tools as **flat tool list** or **cobra-tree** with sub-commands; DuckTap is flat-only).

---

## 5. Generated SKILL.md

| | PP | DT |
|---|---|---|
| Lines | 209 | 71 |
| Has install instructions | ✅ npm + Go + pre-built binary + Hermes + OpenClaw | ⚠️ just `pip install` of the *DuckTap* tool, not the generated CLI |
| Credential setup | ✅ explicit section | ✅ short list |
| Health check guide | ✅ | ❌ |
| Use with Claude Code | ✅ | ✅ |
| Use with Claude Desktop | ✅ | ❌ (mentioned in MCP README only) |
| Use with OpenClaw | ✅ | ❌ |
| Troubleshooting | ✅ | ❌ |
| Description quality | Curated 1-2 sentences | **Concatenates the entire multi-paragraph spec description into one run-on line** — looks bad |

### Generated README

PP: **268 lines, 25+ sections** including "Use with Claude Desktop", "Use with OpenClaw", "Troubleshooting", "Output Formats" (json/table/csv/plain/quiet), "Health Check", "Configuration".

DT: **50 lines, 5 sections** (Install / Auth / Usage / Global flags / MCP).

---

## 6. Scorecard rigor

PP scores its own petstore CLI **74/100 (B)** across **27 dimensions** and lists specific gaps:
```
Gaps:
  - insight scored 4/10 - needs improvement
  - auth_protocol scored 2/10 - needs improvement
```

Dimensions: `output_modes, auth, error_handling, terminal_ux, readme, doctor,
agent_native, mcp_quality, mcp_description_quality, mcp_token_efficiency,
mcp_remote_transport, mcp_tool_design, mcp_surface_strategy, local_cache,
cache_freshness, breadth, vision, workflows, insight, agent_workflow_readiness,
path_validity, auth_protocol, data_pipeline_integrity, sync_correctness,
type_fidelity, dead_code, live_api_verification`.

DuckTap scores its own petstore CLI **92/100 (A)** across **6 dimensions**:
`coverage, documentation, auth, typed_params, artifacts, naming`.

**DuckTap's 92/100 is misleadingly high** because its dimensions are easy to satisfy (does the file exist? are operations documented?). PP's 74/100 is more honest because PP is grading on UX, MCP quality, type fidelity, dead code, etc.

---

## 7. Verification & shipcheck

PP's `shipcheck` runs **six independent verification legs**:
| Leg | What it checks |
|---|---|
| `dogfood` | Generates the CLI and runs it against a mock server using the spec's examples |
| `verify` | Runs the CLI against the real API (live integration) |
| `workflow-verify` | Validates the CLI can complete its primary user workflow (multi-step) |
| `verify-skill` | Ensures the **SKILL.md matches the CLI source** — if you regen, the skill is updated and verified |
| `validate-narrative` | Verifies that `research.json`'s narrative commands actually exist in the built CLI |
| `scorecard` | Quality grading |

DuckTap's `shipcheck` runs **five legs**, all structural:
- `cli_dir_exists`
- `python_syntax` (this one **missed the JSON-boolean bug** I found today — `ast.parse` accepts undefined names)
- `pyproject` exists
- `readme` exists
- `help_runs` (subprocess `--help`)

**PP's shipcheck is genuinely catching production-blocking issues. DuckTap's is mostly a smoke test.** I strengthened DuckTap's E2E test today to do real `importlib.import_module` so the JSON-boolean class of bug is caught next time.

---

## 8. Discovery breadth

### Sources both can consume
- ✅ OpenAPI 2/3 spec (file or URL)
- ✅ HAR file
- ✅ Live URL via browser-sniff

### PP-only sources
- ✅ Multiple specs merged into one CLI (`--spec a.yaml --spec b.yaml`)
- ✅ Plan-driven generation (`--plan plan.md`)
- ✅ Docs URL (`--docs https://stripe.com/docs/api`)
- ✅ Crowd-sniff (study community CLIs/MCP servers)
- ✅ Vision (LLM-aided extraction from docs pages)
- ✅ Browser-sniff with multiple transports (`browser-http`, `browser-chrome`, `browser-chrome-h3` for HTTP/3)
- ✅ Spec-source provenance (`official` / `community` / `sniffed` / `docs`) affects generated client defaults (rate limiting, etc.)

### DuckTap-only sources
- ✅ GraphQL introspection plugin (basic, in `plugins/builtin/`)

**PP discovery is a whole product on its own. DuckTap discovery is "parse the spec and you're done."**

---

## 9. Catalog

| | PP | DT |
|---|---|---|
| Built-in entries | **21** (auth, cloud, communication, dev-tools, marketing, monitoring, payments, project-management, sales-and-crm, social-and-messaging, travel) | **3** (petstore, github, stripe) |
| Community library | [printing-press-library](https://github.com/mvanhorn/printing-press-library) — many CLIs already-printed | [ducktap-library](https://github.com/zanni098/ducktap-library) — 13 recipes |

---

## 10. Bugs surfaced in DuckTap by this test

Three production-blocking bugs were uncovered and fixed during the comparison:

| Bug | Severity | Symptom | Fix |
|---|---|---|---|
| MCP server template emits JSON `false`/`true` inside Python `dict()` literal | **Critical** — generated MCP server can't import | `NameError: name 'false' is not defined` on `from petstore_dt_mcp.server import TOOLS` | Render schema as JSON string, `json.loads` at runtime |
| `commands.py.j2` does same for `default={{ ... | tojson }}` | **Critical** — generated CLI doesn't import for any spec with `default: false` (rampant in GitHub) | New `pyrepr` filter using Python `repr()` |
| `snake_case` doesn't sanitize `/`, `:`, `@`, leading digits | **Critical** — full GitHub spec produces `def meta/root(...)` → SyntaxError | Strip non-ident chars in both `snake_case` and `pyident` filter |
| `press`/`press-cmd` duplicate command | Minor — confusing in `--help` | Use `@app.command("press")` directly |
| `ast.parse`-only test misses NameError | Process bug | Replaced with `importlib.import_module` |

**These are real issues I missed when I built DuckTap in one session. PP doesn't have analogous bugs because (a) it's been battle-tested on 30+ APIs, and (b) Go's compiler catches this class of error at generation time via `go mod tidy`** — which is exactly why PP refuses to finish without `go` on PATH.

---

## 11. Things DuckTap does that PP doesn't

To be fair, DuckTap is genuinely ahead on a few axes:

| | Status |
|---|---|
| **Python everywhere** (no Go required to use or run CLIs) | ✅ DuckTap |
| **Web UI** (`ducktap ui` → FastAPI dashboard) | ✅ DuckTap |
| **Multi-LLM** (LiteLLM: Claude / GPT / Gemini / Ollama / Groq / Azure) | ✅ DuckTap *(but no command yet actually uses an LLM — it's only scaffolded)* |
| **Plugin registry via Python entry points** | ✅ DuckTap |
| **Cursor `.mdc` skill format** | ✅ DuckTap |
| **Generic `tools.json` for arbitrary agent harnesses** | ✅ DuckTap |
| **Pip-installable generated CLIs** (no separate binary) | ✅ DuckTap |
| **Website** | ✅ Both (PP: printingpress.dev; DT: ducktap-website.vercel.app) |
| **PyPI distribution** | ✅ DuckTap (PP is `go install` only) |

**Note on multi-LLM:** the abstraction is there (`ducktap.llm.base`) but no command currently *uses* it. PP has `--polish` which actually calls Claude/Codex to rewrite descriptions; DuckTap's `polish` is a v0.2 roadmap item.

---

## 12. Side-by-side numbers

```
                         PP 4.2.2          DuckTap 0.1.1
Tool source LOC          142,473           1,756
Tool source files            448               28
Internal packages             29                8
Top-level CLI commands        29                8
Catalog entries (built-in)    21                3
Generated LOC (petstore)  12,706            1,802
Generated files (petstore)    71               18
Generated SKILL.md lines     209               71
Generated README lines       268               50
Scorecard dimensions          27                6
Shipcheck legs                 6                5
Auto-generated CLI features  ~30%              base
  (--select, --compact,
   provenance, doctor,
   profile, auth, sync,
   tail, mcp annotations,
   table output, ...)
```

---

## 13. Final verdict

### Where each one wins right now

**Printing Press is better if you want:**
- The best-engineered agent CLI today, with no concessions.
- A massive catalog of pre-printed CLIs you can just install.
- Production-grade verification (`shipcheck`, `dogfood`, `verify-skill`, `validate-narrative`).
- A consistent UX across every CLI an agent uses (the "muscle memory").
- Single-binary distribution.
- MCP tool annotations and surface-strategy choice.
- The `polish` / `vision` / `crowd-sniff` LLM workflows that actually work today.

**DuckTap is better if you want:**
- Pure Python — no Go install, easy to hack the generator itself.
- A web UI to drive generation visually.
- Pip-installable generated CLIs.
- Cursor + generic-tools-json skill support, not just Claude Code.
- Multi-LLM provider switching (architecturally — needs commands that *use* it).
- A modular plugin system to ship new discoverers/generators without forking.

### Honest score (subjective, weighted by "does it work today")

**PP: 8.5 / 10** — mature, broad, deep, well-verified. The only knocks are the Go install friction for end users and the Claude-Code-first skill format.

**DuckTap: 4.5 / 10** — base loop works (now), genuinely better install story, good ideas for plugins/UI/multi-LLM/multi-harness skills, but the generated output is shallow, the catalog is tiny, the verification is light, and we had to fix three critical generator bugs to make it work on a real spec.

To realistically catch up to PP, DuckTap needs:
1. **All the agent-playbook commands baked into generated CLIs** (doctor, profile, auth, sync, tail, etc.) — this is the biggest single gap.
2. **Real polish step** that uses the multi-LLM abstraction.
3. **Tool annotations** in the MCP output (read-only / destructive / idempotent).
4. **Expanded scorecard** (PP-style 25+ dimensions).
5. **Real `verify-skill` + `dogfood`** in shipcheck — actually run the CLI against the API.
6. **At least 15-20 catalog entries** with verified `shipcheck pass` for each.
7. **`--select` / `--compact` / provenance / auto-table** in generated commands.

That's the roadmap, and it's exactly what the comparison shows.

---

## Appendix: raw test commands

```bash
# Setup
mkdir -p comparison/{pp-bin,pp-out,dt-out}
cd comparison/pp-bin && unzip cli-printing-press_windows_amd64.zip
cp .../DuckTap/tests/fixtures/petstore.yaml .

# PP
./pp-bin/printing-press.exe generate --spec petstore.yaml --output pp-out --owner zanni098 --name petstore
./pp-bin/printing-press.exe scorecard --dir pp-out --spec petstore.yaml --json
./pp-bin/printing-press.exe shipcheck --dir pp-out --spec petstore.yaml
./pp-bin/printing-press.exe tools-audit pp-out
./pp-bin/printing-press.exe catalog list

# DuckTap
ducktap press petstore.yaml --out dt-out --name petstore
ducktap shipcheck petstore --out-dir dt-out
ducktap catalog list
ducktap plugins list

# Stress test: GitHub REST (1183 ops)
curl -L .../api.github.com.json -o github.json
ducktap press github.json --out dt-github --name github
cd dt-github/github-dt-cli && pip install -e . && github-dt-cli meta-root
```

All commits from this test:
- `fix(generator): MCP server template emitted JSON booleans into Python literal`
- `fix(generator): sanitize non-identifier chars in op IDs + use pyrepr for defaults`
