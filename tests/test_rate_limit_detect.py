"""Tests for rate-limit detection in HAR discoverer."""
from __future__ import annotations

import json
import tempfile

from ducktap.discovery.har import _detect_rate_limits


def _make_entry(status: int = 200, headers: list[dict[str, str]] | None = None) -> dict:
    return {
        "request": {"url": "https://api.example.com/v1/items", "method": "GET", "headers": []},
        "response": {"status": status, "headers": headers or []},
    }


def test_no_rate_limits() -> None:
    entries = [_make_entry()]
    assert _detect_rate_limits(entries) is None


def test_detects_429_status() -> None:
    entries = [_make_entry(status=429)]
    result = _detect_rate_limits(entries)
    assert result is not None
    assert result["statuses_seen"] == [429]
    assert "exponential backoff" in result["retry_strategy"]


def test_detects_retry_after() -> None:
    entries = [
        _make_entry(status=429, headers=[{"name": "Retry-After", "value": "10"}]),
    ]
    result = _detect_rate_limits(entries)
    assert result is not None
    assert result["retry_after_seconds"] == 10
    assert result["headers_found"] == ["retry-after"]


def test_detects_rate_limit_headers() -> None:
    entries = [
        _make_entry(headers=[{"name": "X-RateLimit-Limit", "value": "100"}]),
        _make_entry(headers=[{"name": "X-RateLimit-Remaining", "value": "42"}]),
    ]
    result = _detect_rate_limits(entries)
    assert result is not None
    assert "x-ratelimit-limit" in result["headers_found"]
    assert result["limit"] == 100


def test_integration_in_har_discoverer() -> None:
    from ducktap.discovery.har import HARDiscoverer

    entries = [
        {
            "request": {
                "url": "https://api.example.com/v1/items",
                "method": "GET",
                "headers": [{"name": "Content-Type", "value": "application/json"}],
                "queryString": [],
            },
            "response": {
                "status": 200,
                "headers": [
                    {"name": "Content-Type", "value": "application/json"},
                    {"name": "X-RateLimit-Limit", "value": "500"},
                ],
            },
        }
    ]
    har = {"log": {"version": "1.2", "creator": {"name": "test", "version": "1"}, "entries": entries}}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".har", delete=False) as f:
        f.write(json.dumps(har))
        path = f.name

    spec = HARDiscoverer().discover(path, name="testapi")
    assert "x-ducktap-rate-limits" in spec.extensions
    assert spec.extensions["x-ducktap-rate-limits"]["limit"] == 500
