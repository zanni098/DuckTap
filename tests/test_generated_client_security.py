"""Runtime tests for the generated HTTP client's credential handling."""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import httpx
import pytest

from ducktap.core.pipeline import press

SPEC = """
openapi: 3.0.0
info: {title: Secure API, version: "1.0.0"}
servers: [{url: "https://api.secure.test"}]
components:
  securitySchemes:
    apiKey:
      type: apiKey
      in: header
      name: X-API-Key
paths:
  /things:
    get:
      operationId: listThings
      responses: {"200": {description: ok}}
"""


@pytest.fixture
def client_module(tmp_path: Path, monkeypatch):
    spec_file = tmp_path / "secure.yaml"
    spec_file.write_text(SPEC, encoding="utf-8")
    out = tmp_path / "out"
    press(str(spec_file), str(out))
    root = out / "secure-dt-cli"
    monkeypatch.syspath_prepend(str(root))
    for mod in [m for m in sys.modules if m.startswith("secure_dt_cli")]:
        del sys.modules[mod]
    module = importlib.import_module("secure_dt_cli.client")
    yield module
    for mod in [m for m in sys.modules if m.startswith("secure_dt_cli")]:
        del sys.modules[mod]


def _client_with(module, handler):
    client = module.Client(base_url="https://api.secure.test")
    client._client = httpx.Client(
        transport=httpx.MockTransport(handler), follow_redirects=False
    )
    return client


def test_credentials_are_dropped_on_cross_origin_redirect(client_module):
    hops: list[tuple[str, dict[str, str]]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        hops.append((str(request.url), dict(request.headers)))
        if "evil" in str(request.url):
            return httpx.Response(200, json={"ok": True})
        return httpx.Response(302, headers={"location": "https://evil.test/steal"})

    _client_with(client_module, handler).request(
        "GET", "/things", headers={"X-API-Key": "SECRET", "Authorization": "Bearer S"}
    )
    assert len(hops) == 2
    leaked = hops[1][1]
    assert "x-api-key" not in leaked
    assert "authorization" not in leaked


def test_credentials_survive_a_same_origin_redirect(client_module):
    hops: list[dict[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        hops.append(dict(request.headers))
        if request.url.path == "/things":
            return httpx.Response(
                302, headers={"location": "https://api.secure.test/things/v2"}
            )
        return httpx.Response(200, json={"ok": True})

    _client_with(client_module, handler).request(
        "GET", "/things", headers={"X-API-Key": "SECRET"}
    )
    assert hops[-1]["x-api-key"] == "SECRET"


def test_redirect_loop_is_bounded(client_module):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "https://api.secure.test/loop"})

    with pytest.raises(client_module.APIError, match="too many redirects"):
        _client_with(client_module, handler).request("GET", "/things")
