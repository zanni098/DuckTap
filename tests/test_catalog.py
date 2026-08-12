from typer.testing import CliRunner

from ducktap.catalog import get_entry, list_entries
from ducktap.cli import app


def test_catalog_loads():
    entries = list_entries()
    names = [e.name for e in entries]
    assert "petstore" in names
    assert "github" in names


def test_get_entry():
    e = get_entry("petstore")
    assert e is not None
    assert e.spec_url
    assert e.source() == e.spec_url


def test_known_unpressable_graphql_entries_are_unsupported():
    for name in ("linear", "shopify"):
        e = get_entry(name)
        assert e is not None
        assert e.tier == "unsupported"
        assert e.notes


def test_catalog_print_refuses_unsupported_entry(monkeypatch):
    def fail_if_pressed(*args, **kwargs):
        raise AssertionError("press must not be called")

    monkeypatch.setattr("ducktap.cli.press", fail_if_pressed)
    result = CliRunner().invoke(app, ["catalog", "print", "linear"])

    assert result.exit_code == 2
    assert "marked unsupported" in result.output
    assert "Traceback" not in result.output
