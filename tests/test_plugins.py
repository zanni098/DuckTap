from ducktap.core import plugins


def test_builtins_register():
    plugins.autoload_builtins()
    discs = plugins.get_discoverers()
    gens = plugins.get_generators()
    assert {"openapi", "har", "browser-sniff", "graphql"} <= set(discs)
    assert {
        "python-cli",
        "mcp-server",
        "skill",
        "typescript-cli",
        "go-cli",
        "rust-cli",
    } <= set(gens)
