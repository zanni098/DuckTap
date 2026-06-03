// Real output captured from: ducktap press tests/fixtures/petstore.yaml --name petstore
// (DuckTap 0.6.0). Numbers are from an actual run, not illustrative.
window.SESSION = [
  { t: 'comment', s: '# Turn an OpenAPI spec into an MCP server -- deterministically' },
  { t: 'cmd',     s: 'ducktap press petstore.yaml --name petstore' },
  { t: 'good',    s: 'Pressed petstore (19 operations) -> out' },
  { t: 'out',     s: '  python-cli: 11 files' },
  { t: 'out',     s: '  mcp-server:  5 files' },
  { t: 'out',     s: '  skill:       3 files' },
  { t: 'out',     s: '' },
  { t: 'head',    s: 'Scorecard: 87/100 (B)' },
  { t: 'out',     s: '  - coverage:      95    19 operations exposed' },
  { t: 'out',     s: '  - documentation: 100   19/19 operations have docs' },
  { t: 'out',     s: '  - auth:          100   2 auth schemes' },
  { t: 'out',     s: '  - typed_params:  54    29/53 params typed' },
  { t: 'out',     s: '  - naming:        100   19/19 unique operation ids' },
  { t: 'out',     s: '' },
  { t: 'comment', s: '# No LLM. No API key. Same spec -> same output, every time.' },
  { t: 'comment', s: '# Drop out/petstore-dt-mcp into Claude Desktop -- your agent can call it.' },
];
