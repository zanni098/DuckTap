# Changelog

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
