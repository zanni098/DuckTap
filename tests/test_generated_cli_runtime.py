"""End-to-end runtime test: actually invoke the generated CLI commands against
an in-process httpx mock transport and verify they produce correct requests
and parse responses correctly.

This is the strongest signal that the generator produces a *working* CLI, not
just one that imports cleanly.
"""
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
      parameters:
        - name: limit
          in: query
          schema: {type: integer}
      responses:
        "200":
          description: ok
          content:
            application/json:
              schema:
                type: array
                items: {type: object}
    post:
      operationId: addPet
      summary: Create a pet
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [name]
              properties:
                name: {type: string}
                tag: {type: string}
      responses:
        "201":
          description: created
          content:
            application/json:
              schema: {type: object}
  /pets/{petId}:
    get:
      operationId: getPet
      summary: Fetch one pet
      parameters:
        - name: petId
          in: path
          required: true
          schema: {type: integer}
      responses:
        "200":
          description: ok
          content:
            application/json:
              schema: {type: object}
"""


@pytest.fixture
def cli_module(tmp_path):
    """Press the fixture, then import the generated petstore CLI package."""
    spec_path = tmp_path / "mini.yaml"
    spec_path.write_text(FIXTURE_TEXT)
    out = tmp_path / "out"
    press(str(spec_path), str(out), name="mini")

    cli_root = str(out / "mini-dt-cli")
    sys.path.insert(0, cli_root)
    # Clear any prior imports in case another test pressed a different "mini"
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
    """Replace the Client._client with a httpx.Client backed by MockTransport."""
    transport = httpx.MockTransport(handler)
    real_init = cli_client.Client.__init__

    def patched_init(self, *args, **kwargs):
        real_init(self, *args, **kwargs)
        self._client.close()
        self._client = httpx.Client(transport=transport, follow_redirects=True)

    monkeypatch.setattr(cli_client.Client, "__init__", patched_init)


def test_get_with_query_param(cli_module, monkeypatch):
    cli_main, cli_client = cli_module
    seen = {}

    def handler(req):
        seen["url"] = str(req.url)
        seen["method"] = req.method
        seen["accept"] = req.headers.get("Accept")
        return httpx.Response(200, json=[{"id": 1, "name": "rex"}])

    _install_mock(monkeypatch, cli_client, handler)

    from click.testing import CliRunner
    r = CliRunner().invoke(cli_main.cli, ["--no-cache", "list-pets", "--limit", "5"])
    assert r.exit_code == 0, r.output
    assert seen["method"] == "GET"
    assert "limit=5" in seen["url"]
    assert seen["url"].startswith("https://example.test/api/pets")
    assert seen["accept"] == "application/json"
    out = json.loads(r.output)
    assert out[0]["name"] == "rex"


def test_path_param_substitution(cli_module, monkeypatch):
    cli_main, cli_client = cli_module
    seen = {}

    def handler(req):
        seen["path"] = req.url.path
        return httpx.Response(200, json={"id": 42, "name": "spot"})

    _install_mock(monkeypatch, cli_client, handler)

    from click.testing import CliRunner
    r = CliRunner().invoke(cli_main.cli, ["--no-cache", "get-pet", "--pet-id", "42"])
    assert r.exit_code == 0, r.output
    assert seen["path"].endswith("/pets/42")
    assert "{petId}" not in seen["path"]


def test_post_body(cli_module, monkeypatch):
    cli_main, cli_client = cli_module
    seen = {}

    def handler(req):
        seen["method"] = req.method
        seen["body"] = json.loads(req.content.decode() or "{}")
        return httpx.Response(201, json={"id": 1, "name": "rex"})

    _install_mock(monkeypatch, cli_client, handler)

    from click.testing import CliRunner
    r = CliRunner().invoke(
        cli_main.cli, ["add-pet", "--name", "rex", "--tag", "good-boy"]
    )
    assert r.exit_code == 0, r.output
    assert seen["method"] == "POST"
    assert seen["body"] == {"name": "rex", "tag": "good-boy"}


def test_4xx_emits_error_to_stderr(cli_module, monkeypatch):
    cli_main, cli_client = cli_module

    def handler(req):
        return httpx.Response(404, json={"detail": "no such pet"})

    _install_mock(monkeypatch, cli_client, handler)

    from click.testing import CliRunner
    r = CliRunner().invoke(
        cli_main.cli, ["--no-cache", "get-pet", "--pet-id", "999"]
    )
    assert r.exit_code == 3
    err = json.loads(r.stderr)
    assert err["status"] == 404
    assert err["body"] == {"detail": "no such pet"}


def test_select_filters_top_level_fields(cli_module, monkeypatch):
    cli_main, cli_client = cli_module

    def handler(req):
        return httpx.Response(200, json=[{
            "id": 1,
            "name": "rex",
            "status": "available",
            "internal": "noise",
        }])

    _install_mock(monkeypatch, cli_client, handler)

    from click.testing import CliRunner
    r = CliRunner().invoke(
        cli_main.cli, ["--no-cache", "--select", "id,name", "list-pets"]
    )
    assert r.exit_code == 0, r.output
    assert json.loads(r.output) == [{"id": 1, "name": "rex"}]


def test_compact_keeps_high_gravity_fields(cli_module, monkeypatch):
    cli_main, cli_client = cli_module

    def handler(req):
        return httpx.Response(200, json=[{
            "id": 1,
            "name": "rex",
            "status": "available",
            "internal": "noise",
        }])

    _install_mock(monkeypatch, cli_client, handler)

    from click.testing import CliRunner
    r = CliRunner().invoke(cli_main.cli, ["--no-cache", "--compact", "list-pets"])
    assert r.exit_code == 0, r.output
    assert json.loads(r.output) == [{"id": 1, "name": "rex", "status": "available"}]


def test_quiet_suppresses_success_output(cli_module, monkeypatch):
    cli_main, cli_client = cli_module

    def handler(req):
        return httpx.Response(200, json={"id": 1, "name": "rex"})

    _install_mock(monkeypatch, cli_client, handler)

    from click.testing import CliRunner
    r = CliRunner().invoke(cli_main.cli, ["--no-cache", "--quiet", "get-pet", "--pet-id", "1"])
    assert r.exit_code == 0, r.output
    assert r.output == ""


def test_dry_run_prints_request_without_calling_api(cli_module, monkeypatch):
    cli_main, cli_client = cli_module

    def handler(req):
        raise AssertionError("dry-run must not call the API")

    _install_mock(monkeypatch, cli_client, handler)

    from click.testing import CliRunner
    r = CliRunner().invoke(
        cli_main.cli, ["--no-cache", "--dry-run", "get-pet", "--pet-id", "42"]
    )
    assert r.exit_code == 0, r.output
    out = json.loads(r.output)
    assert out["method"] == "GET"
    assert out["path"] == "/pets/42"
    assert out["url"].endswith("/pets/42")


def test_api_errors_use_typed_exit_codes(cli_module, monkeypatch):
    cli_main, cli_client = cli_module

    def handler(req):
        return httpx.Response(429, json={"detail": "slow down"})

    _install_mock(monkeypatch, cli_client, handler)

    from click.testing import CliRunner
    r = CliRunner().invoke(cli_main.cli, ["--no-cache", "get-pet", "--pet-id", "1"])
    assert r.exit_code == 7
    err = json.loads(r.stderr)
    assert err["status"] == 429


def test_relative_server_url_resolves_against_http_source(tmp_path, monkeypatch):
    """If we discover from a URL whose spec has a relative `servers` URL,
    the generated client must end up with an absolute base_url."""
    from ducktap.discovery.openapi import OpenAPIDiscoverer

    yaml_text = """
openapi: 3.0.0
info: {title: Petsy, version: '1'}
servers:
  - url: /api/v3
paths: {}
"""
    # Simulate a remote source by monkey-patching the loader.
    import ducktap.discovery.openapi as mod
    monkeypatch.setattr(
        mod, "_load_raw",
        lambda src: __import__("yaml").safe_load(yaml_text)
    )
    spec = OpenAPIDiscoverer().discover("https://petstore3.swagger.io/api/v3/openapi.yaml")
    assert spec.base_url == "https://petstore3.swagger.io/api/v3"
