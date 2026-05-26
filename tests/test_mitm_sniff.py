"""Tests for mitm_sniff discoverer."""
from __future__ import annotations

import pytest

from ducktap.discovery.mitm_sniff import MitmSniffDiscoverer


def test_can_handle_mitm_url() -> None:
    d = MitmSniffDiscoverer()
    assert d.can_handle("mitm://proxy")
    assert not d.can_handle("https://example.com")
    assert not d.can_handle("foo.har")


def test_discover_raises_without_mitmproxy(monkeypatch) -> None:
    import subprocess
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **k: (_ for _ in ()).throw(FileNotFoundError("no mitmproxy")),
    )
    d = MitmSniffDiscoverer()
    with pytest.raises(RuntimeError, match="mitm-sniff requires mitmproxy"):
        d.discover("mitm://proxy")
