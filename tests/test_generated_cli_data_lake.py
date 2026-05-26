"""Tests for the generated CLI local data lake (--save, data query, data search)."""
from __future__ import annotations

import importlib
import json
import sys

import httpx
import pytest

from ducktap.core.pipeline import press

FIXTURE_TEXT = """
openapi: 3.0.0
info:
  title: Mini API
  version: 1.0.0
servers:
  - url: https://example.test/api
paths:
  /pets:
    get:
      operationId: listPets
      summary: List all pets
      responses:
        "200":
          description: ok
          content:
            application/json:
              schema:
                type: array
                items: {type: object}
"""


@pytest.fixture
def cli_module(tmp_path):
    spec_path = tmp_path / "mini.yaml"
    spec_path.write_text(FIXTURE_TEXT)
    out = tmp_path / "out"
    press(str(spec_path), str(out), name="mini")

    cli_root = str(out / "mini-dt-cli")
    sys.path.insert(0, cli_root)
    for k in list(sys.modules):
        if k.startswith("mini_dt_cli"):
            del sys.modules[k]
    try:
        cli_main = importlib.import_module("mini_dt_cli.main")
        cli_client = importlib.import_module("mini_dt_cli.client")
        yield cli_main, cli_client
    finally:
        sys.path.remove(cli_root)


def _install_mock(monkeypatch, cli_client, handler):
    transport = httpx.MockTransport(handler)
    real_init = cli_client.Client.__init__

    def patched_init(self, *args, **kwargs):
        real_init(self, *args, **kwargs)
        self._client.close()
        self._client = httpx.Client(transport=transport, follow_redirects=True)

    monkeypatch.setattr(cli_client.Client, "__init__", patched_init)


def test_save_persists_to_mirror(cli_module, monkeypatch, tmp_path):
    cli_main, cli_client = cli_module

    def handler(req):
        return httpx.Response(200, json=[{"id": 1, "name": "rex"}])

    _install_mock(monkeypatch, cli_client, handler)
    monkeypatch.setenv("DUCKTAP_HOME", str(tmp_path))

    from click.testing import CliRunner
    r = CliRunner().invoke(
        cli_main.cli, ["--no-cache", "--save", "pets", "list-pets"]
    )
    assert r.exit_code == 0, r.output

    # Query the mirror directly
    from mini_dt_cli.mirror import Mirror
    mirror = Mirror(path=str(tmp_path / "mini" / "mirror.sqlite"))
    rows = mirror.search("rex")
    assert len(rows) >= 1
    assert rows[0]["collection"] == "pets"


def test_data_query_runs_select(cli_module, monkeypatch, tmp_path):
    cli_main, cli_client = cli_module

    def handler(req):
        return httpx.Response(200, json=[{"id": 1, "name": "rex"}])

    _install_mock(monkeypatch, cli_client, handler)
    monkeypatch.setenv("DUCKTAP_HOME", str(tmp_path))

    from click.testing import CliRunner
    # First save something
    r = CliRunner().invoke(
        cli_main.cli, ["--no-cache", "--save", "pets", "list-pets"]
    )
    assert r.exit_code == 0, r.output

    # Then query it
    r = CliRunner().invoke(
        cli_main.cli, ["data", "query", "SELECT * FROM records WHERE collection = 'pets'"]
    )
    assert r.exit_code == 0, r.output
    result = json.loads(r.output)
    assert len(result) >= 1


def test_data_search_finds_text(cli_module, monkeypatch, tmp_path):
    cli_main, cli_client = cli_module

    def handler(req):
        return httpx.Response(200, json=[{"id": 1, "name": "rex"}])

    _install_mock(monkeypatch, cli_client, handler)
    monkeypatch.setenv("DUCKTAP_HOME", str(tmp_path))

    from click.testing import CliRunner
    CliRunner().invoke(
        cli_main.cli, ["--no-cache", "--save", "pets", "list-pets"]
    )

    r = CliRunner().invoke(
        cli_main.cli, ["data", "search", "rex"]
    )
    assert r.exit_code == 0, r.output
    result = json.loads(r.output)
    assert len(result) >= 1
    assert result[0]["body"]["name"] == "rex"
