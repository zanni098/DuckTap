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


def test_agent_flag_enables_compact_json(cli_module, monkeypatch):
    cli_main, cli_client = cli_module

    def handler(req):
        return httpx.Response(200, json=[{
            "id": 1, "name": "rex", "status": "available", "internal": "noise",
        }])

    _install_mock(monkeypatch, cli_client, handler)

    from click.testing import CliRunner
    r = CliRunner().invoke(cli_main.cli, ["--no-cache", "--agent", "list-pets"])
    assert r.exit_code == 0, r.output
    # --agent implies --compact, which drops the "internal" field.
    out = json.loads(r.output)
    assert out == [{"id": 1, "name": "rex", "status": "available"}]


def test_format_csv_emits_csv(cli_module, monkeypatch):
    cli_main, cli_client = cli_module

    def handler(req):
        return httpx.Response(200, json=[
            {"id": 1, "name": "rex"},
            {"id": 2, "name": "spot"},
        ])

    _install_mock(monkeypatch, cli_client, handler)

    from click.testing import CliRunner
    r = CliRunner().invoke(cli_main.cli, ["--no-cache", "--format", "csv", "list-pets"])
    assert r.exit_code == 0, r.output
    lines = r.output.strip().splitlines()
    assert lines[0] == "id,name"
    assert "1,rex" in lines
    assert "2,spot" in lines


def test_format_jsonl_emits_one_object_per_line(cli_module, monkeypatch):
    cli_main, cli_client = cli_module

    def handler(req):
        return httpx.Response(200, json=[
            {"id": 1, "name": "rex"},
            {"id": 2, "name": "spot"},
        ])

    _install_mock(monkeypatch, cli_client, handler)

    from click.testing import CliRunner
    r = CliRunner().invoke(cli_main.cli, ["--no-cache", "--format", "jsonl", "list-pets"])
    assert r.exit_code == 0, r.output
    lines = r.output.strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["id"] == 1
    assert json.loads(lines[1])["id"] == 2


def test_agent_context_returns_structured_metadata(cli_module):
    cli_main, _ = cli_module
    from click.testing import CliRunner
    r = CliRunner().invoke(cli_main.cli, ["agent-context"])
    assert r.exit_code == 0, r.output
    data = json.loads(r.output)
    assert data["cli"] == "mini-dt-cli"
    assert isinstance(data["operations"], list)
    assert len(data["operations"]) >= 3
    assert "global_flags" in data
    assert "exit_codes" in data
    assert "groups" in data


def test_which_searches_operations_by_keyword(cli_module):
    cli_main, _ = cli_module
    from click.testing import CliRunner
    r = CliRunner().invoke(cli_main.cli, ["which", "pet"])
    assert r.exit_code == 0, r.output
    matches = json.loads(r.output)
    assert len(matches) >= 1
    assert all("command" in m for m in matches)


def test_which_unknown_keyword_exits_3(cli_module):
    cli_main, _ = cli_module
    from click.testing import CliRunner
    r = CliRunner().invoke(cli_main.cli, ["which", "zzzz-no-such-thing"])
    assert r.exit_code == 3
    assert json.loads(r.output) == []


def test_profile_save_and_apply(cli_module, tmp_path, monkeypatch):
    cli_main, cli_client = cli_module

    # Redirect HOME so we don't touch the developer's real profiles.
    monkeypatch.setenv("HOME", str(tmp_path))

    from click.testing import CliRunner
    runner = CliRunner()

    # Save a profile with --compact and --format jsonl.
    r = runner.invoke(
        cli_main.cli,
        ["profile", "save", "agent", "--format", "jsonl", "--compact"],
    )
    assert r.exit_code == 0, r.output

    # Apply it: should emit JSONL + compact.
    def handler(req):
        return httpx.Response(200, json=[
            {"id": 1, "name": "rex", "status": "available", "internal": "noise"},
        ])

    _install_mock(monkeypatch, cli_client, handler)
    r = runner.invoke(
        cli_main.cli,
        ["--no-cache", "--profile", "agent", "list-pets"],
    )
    assert r.exit_code == 0, r.output
    # JSONL: each item on its own line.
    parsed = [json.loads(line) for line in r.output.strip().splitlines()]
    assert parsed == [{"id": 1, "name": "rex", "status": "available"}]


def test_dry_run_payload_includes_grouped_command_context(cli_module, monkeypatch):
    """Smoke-check: dry-run still works after the tag-grouped tree refactor
    for operations without tags (mini fixture has no tags -> stays flat)."""
    cli_main, cli_client = cli_module

    def handler(req):
        raise AssertionError("must not be called")

    _install_mock(monkeypatch, cli_client, handler)

    from click.testing import CliRunner
    r = CliRunner().invoke(
        cli_main.cli, ["--no-cache", "--dry-run", "get-pet", "--pet-id", "1"],
    )
    assert r.exit_code == 0, r.output
    out = json.loads(r.output)
    assert out["method"] == "GET"
    assert out["path"] == "/pets/1"


def test_doctor_reports_tag_groups(cli_module):
    cli_main, _ = cli_module
    from click.testing import CliRunner
    r = CliRunner().invoke(cli_main.cli, ["doctor"])
    assert r.exit_code == 0, r.output
    data = json.loads(r.output)
    assert data["operations"] >= 3
    # mini fixture has no tags, so operations live under "general".
    assert "general" in data["groups"]


def test_agent_dry_run_keeps_full_request_payload(cli_module, monkeypatch):
    """Regression: --agent (which implies --compact) must NOT strip fields
    off the dry-run payload — those are request metadata, not response data."""
    cli_main, cli_client = cli_module

    def handler(req):
        raise AssertionError("dry-run must not call the API")

    _install_mock(monkeypatch, cli_client, handler)

    from click.testing import CliRunner
    r = CliRunner().invoke(
        cli_main.cli,
        ["--no-cache", "--agent", "--dry-run", "get-pet", "--pet-id", "1"],
    )
    assert r.exit_code == 0, r.output
    out = json.loads(r.output)
    assert set(out.keys()) == {"method", "path", "url", "query", "headers", "body"}
    assert out["method"] == "GET"
    assert out["path"] == "/pets/1"


# ---------------------------------------------------------------------------
# auth-doctor: pressed from a separate spec that has security schemes so we
# can exercise both the env-var validation and the live-probe code paths.
# ---------------------------------------------------------------------------

AUTH_FIXTURE_TEXT = """
openapi: 3.0.0
info:
  title: Auth Mini
  version: 1.0.0
servers:
  - url: https://auth.example.test/api
components:
  securitySchemes:
    apiKey:
      type: apiKey
      in: header
      name: X-API-Key
      description: Get one at https://auth.example.test/settings/keys
security:
  - apiKey: []
paths:
  /ping:
    get:
      operationId: ping
      summary: Probe endpoint
      responses:
        "200":
          description: ok
          content:
            application/json:
              schema: {type: object}
"""


@pytest.fixture
def auth_cli_module(tmp_path):
    spec_path = tmp_path / "auth_mini.yaml"
    spec_path.write_text(AUTH_FIXTURE_TEXT)
    out = tmp_path / "out"
    press(str(spec_path), str(out), name="authmini")

    cli_root = str(out / "authmini-dt-cli")
    sys.path.insert(0, cli_root)
    for k in list(sys.modules):
        if k.startswith("authmini_dt_cli"):
            del sys.modules[k]
    try:
        cli_main = importlib.import_module("authmini_dt_cli.main")
        cli_client = importlib.import_module("authmini_dt_cli.client")
        yield cli_main, cli_client
    finally:
        sys.path.remove(cli_root)


def test_auth_doctor_reports_unset_env_var_exits_10(auth_cli_module, monkeypatch):
    cli_main, _ = auth_cli_module
    monkeypatch.delenv("AUTHMINI_API_KEY", raising=False)

    from click.testing import CliRunner
    r = CliRunner().invoke(cli_main.cli, ["auth-doctor"])
    assert r.exit_code == 10, r.output
    data = json.loads(r.output)
    assert data["summary"]["all_set"] is False
    assert data["summary"]["unset"] == 1
    scheme = data["schemes"][0]
    assert scheme["env_var"] == "AUTHMINI_API_KEY"
    assert scheme["set"] is False
    # Hint should point at the description we set on the security scheme.
    assert "settings/keys" in scheme["hint"]
    assert data["probe"] is None


def test_auth_doctor_probe_classifies_auth_failure(auth_cli_module, monkeypatch):
    cli_main, cli_client = auth_cli_module
    monkeypatch.setenv("AUTHMINI_API_KEY", "wrong-key")

    sent_header = {}

    def handler(req):
        sent_header["x_api_key"] = req.headers.get("X-API-Key")
        return httpx.Response(401, json={"error": "bad key"})

    _install_mock(monkeypatch, cli_client, handler)

    from click.testing import CliRunner
    r = CliRunner().invoke(cli_main.cli, ["--no-cache", "auth-doctor", "--probe"])
    assert r.exit_code == 4, r.output
    data = json.loads(r.output)
    assert data["summary"]["all_set"] is True
    assert data["probe"]["classification"] == "auth_failed"
    assert data["probe"]["http_status"] == 401
    # Client must have forwarded the env-var as the configured header.
    assert sent_header["x_api_key"] == "wrong-key"


def test_auth_doctor_probe_succeeds_with_valid_key(auth_cli_module, monkeypatch):
    cli_main, cli_client = auth_cli_module
    monkeypatch.setenv("AUTHMINI_API_KEY", "right-key")

    def handler(req):
        assert req.headers.get("X-API-Key") == "right-key"
        return httpx.Response(200, json={"ok": True})

    _install_mock(monkeypatch, cli_client, handler)

    from click.testing import CliRunner
    r = CliRunner().invoke(cli_main.cli, ["--no-cache", "auth-doctor", "--probe"])
    assert r.exit_code == 0, r.output
    data = json.loads(r.output)
    assert data["probe"]["classification"] == "auth_works"
    assert data["probe"]["http_status"] == 200


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
