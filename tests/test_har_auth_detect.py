"""Tests for HAR discoverer auth-flow detection."""
from __future__ import annotations

import json
from pathlib import Path

from ducktap.discovery.har import HARDiscoverer


def _make_har(entries: list[dict]) -> str:
    return json.dumps({"log": {"entries": entries}})


def test_detects_bearer_from_request_header(tmp_path: Path) -> None:
    har = _make_har([
        {
            "request": {
                "url": "https://api.example.com/pets",
                "method": "GET",
                "headers": [
                    {"name": "Authorization", "value": "Bearer abc123"},
                    {"name": "Content-Type", "value": "application/json"},
                ],
            },
            "response": {
                "status": 200,
                "headers": [
                    {"name": "Content-Type", "value": "application/json"},
                ],
            },
        }
    ])
    p = tmp_path / "test.har"
    p.write_text(har)
    spec = HARDiscoverer().discover(str(p))
    assert len(spec.auth_schemes) == 1
    assert spec.auth_schemes[0].type == "http"
    assert spec.auth_schemes[0].scheme == "bearer"
    assert "TOKEN" in spec.auth_schemes[0].env_var


def test_detects_oauth_redirect(tmp_path: Path) -> None:
    har = _make_har([
        {
            "request": {
                "url": "https://api.example.com/protected",
                "method": "GET",
                "headers": [{"name": "Content-Type", "value": "application/json"}],
            },
            "response": {
                "status": 302,
                "headers": [
                    {"name": "Location", "value": "https://auth.example.com/oauth/authorize"},
                    {"name": "Content-Type", "value": "application/json"},
                ],
            },
        }
    ])
    p = tmp_path / "test.har"
    p.write_text(har)
    spec = HARDiscoverer().discover(str(p))
    assert any(s.type == "oauth2" for s in spec.auth_schemes)


def test_detects_api_key_header(tmp_path: Path) -> None:
    har = _make_har([
        {
            "request": {
                "url": "https://api.example.com/pets",
                "method": "GET",
                "headers": [
                    {"name": "X-API-Key", "value": "secret123"},
                    {"name": "Content-Type", "value": "application/json"},
                ],
            },
            "response": {
                "status": 200,
                "headers": [
                    {"name": "Content-Type", "value": "application/json"},
                ],
            },
        }
    ])
    p = tmp_path / "test.har"
    p.write_text(har)
    spec = HARDiscoverer().discover(str(p))
    assert any(s.type == "apiKey" and s.parameter_name == "X-API-Key" for s in spec.auth_schemes)
