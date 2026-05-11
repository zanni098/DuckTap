# Changelog

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
