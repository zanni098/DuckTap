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
    # discover() decides whether mitmproxy is installed by calling
    # shutil.which("mitmweb"), not subprocess.run, so patch the lookup the
    # code actually performs. Forcing it to return None makes the test
    # exercise the missing-mitmproxy guard deterministically, regardless of
    # whether mitmweb happens to be installed on the machine running the test.
    from ducktap.discovery import mitm_sniff

    def no_mitmweb(name: str) -> None:
        return None

    monkeypatch.setattr(mitm_sniff.shutil, "which", no_mitmweb)
    d = MitmSniffDiscoverer()
    with pytest.raises(RuntimeError, match="mitm-sniff requires mitmproxy"):
        d.discover("mitm://proxy")
