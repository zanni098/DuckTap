# Changelog

## 0.6.0 — 2026-05-26

Quality push toward and beyond Printing Press parity.

### Added

- First-class GraphQL introspection discovery via `--from graphql`.
- Default multi-target generation: Python CLI, MCP server, agent skill,
  TypeScript scaffold, Go scaffold, and Rust scaffold.
- Generated Python CLIs now support `--save NAME`, `data query`, and
  `data search` for a local SQLite response lake.
- `ducktap publish <name>` dry-run packaging: zips generated artifacts,
  writes a release manifest, and embeds scorecard/shipcheck results.
- Scorecard now includes `agent_native` and `local_data` dimensions.
- Dashboard status API and richer GUI target selector for all six targets.

### Changed

- `ducktap press` defaults to every built-in target. Use `--targets` to
  generate a narrower set.
- The generated APISpec manifest is saved to `<out>/<name>.apispec.json`
  so publish and verification commands can reuse normalized discovery output.
- README, roadmap, and comparison docs now describe the v0.6 surface.

## 0.2.2 — 2026-05-19

- Generated CLIs gained `auth-doctor` with env-var validation, actionable
  hints, optional live probe, and typed exit codes.
- Metadata commands such as `--dry-run`, `agent-context`, `doctor`, and
  profile management preserve complete payloads under `--agent`.

## 0.2.1 — 2026-05-18

- Generated CLIs gained tag-grouped command trees, `--agent`, multi-format
  output, `agent-context`, `which`, saved profiles, `--rate-limit`, and
  `--timeout`.
- Catalog expanded from 3 to 17 entries.
- Dashboard and generated README polish shipped.

## 0.2.0 — 2026-05-18

- Agent-native CLI controls: `--select`, `--compact`, `--quiet`, and
  `--dry-run`.
- Typed exit codes and a generated `doctor` command.
- Local FastAPI dashboard upgraded into a workbench with catalog filtering,
  result display, and `/api/catalog`.

## 0.1.2 — 2026-05-12

Quality pass. Generated CLIs are now actually usable end-to-end against
real APIs.

### Fixed

- **Spec naming**: titles like "Swagger Petstore - OpenAPI 3.0" now slugify
  to `petstore` instead of `swagger-petstore-openapi-3-0`, which cascades
  into project dir, binary name, and env-var prefix
  (`PETSTORE_TOKEN` instead of `SWAGGER_PETSTORE_OPENAPI_3_0_TOKEN`).
- **Relative server URLs**: when a spec ships `servers: [{url: /api/v3}]`
  and is fetched over HTTP, the discoverer now resolves it against the
  source URL, so the generated client gets a working absolute base_url.
- Generated client sends `Accept: application/json` and `User-Agent`.
- Generated client raises a clear `APIError` (instead of silently
  failing) when no `base_url` is configured.
- Flag collisions (e.g. `id` in path and body of the same operation)
  no longer crash Click at decorator time; the body-side flag is
  auto-renamed to `--body-<name>`.

### Changed

- Dropped redundant `--json/--no-json` flag (`--pretty` already toggles).
- Added `--debug` / `<NAME>_DEBUG` env var: logs requests to stderr
  with `Authorization`/`api_key`/`X-API-Key` redacted.
- Body decode boilerplate extracted into a `_coerce()` helper.
- `ducktap scorecard --fail-under N` exits 2 for CI gating.

### Tests

- New `tests/test_generated_cli_runtime.py`: presses a tiny spec, runs
  the generated CLI through `httpx.MockTransport`, and verifies query
  params, path substitution, POST bodies, 4xx-to-stderr, and absolute
  base_url resolution all work end-to-end.

## 0.1.1 — 2026-05-11

- First release published via PyPI Trusted Publishing (OIDC).
- Catalog loader now recurses one level into category subdirs, so the
  community catalog at `zanni098/ducktap-library` works without flattening.
- Lint fixes (E701/E702); CI ignores B008 for Typer's option default idiom.
- README: dashboard screenshot, demo block, PyPI + Release badges,
  community-library quick-start.

## 0.1.0 — 2026-05-11

Initial release. The lean loop end-to-end:

- OpenAPI / HAR / browser-sniff discoverers
- Python CLI + MCP server + skill generators
- Multi-LLM (LiteLLM)
- Plugin registry (entry points)
- Scorecard + shipcheck
- FastAPI dashboard
- Catalog (petstore, github, stripe)
