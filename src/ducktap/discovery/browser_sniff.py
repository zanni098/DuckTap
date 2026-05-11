"""Browser-sniff discoverer.

Drives a headless browser (Playwright) to a URL, optionally executes a script
to interact with the page, records all network traffic to a HAR, then delegates
to the HAR discoverer.

This module imports Playwright lazily — DuckTap remains usable without the
`[sniff]` extra installed.
"""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from ducktap.core import plugins
from ducktap.core.naming import slugify
from ducktap.core.spec import APISpec


class BrowserSniffDiscoverer:
    name = "browser-sniff"

    def can_handle(self, source: str) -> bool:
        return source.startswith(("http://", "https://")) and not source.endswith(
            (".json", ".yaml", ".yml", ".har")
        )

    def discover(self, source: str, **opts: Any) -> APISpec:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as e:
            raise RuntimeError(
                "browser-sniff requires the [sniff] extra. "
                "Install with: pip install 'ducktap[sniff]' && playwright install chromium"
            ) from e

        wait_ms = int(opts.get("wait_ms", 8000))
        actions = opts.get("actions") or []   # list of {action, selector, ...}
        out_har = opts.get("har_path") or str(
            Path(tempfile.mkdtemp(prefix="ducktap-sniff-")) / "capture.har"
        )

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=opts.get("headless", True))
            context = browser.new_context(record_har_path=out_har, record_har_content="embed")
            page = context.new_page()
            page.goto(source, wait_until="networkidle", timeout=60000)
            for act in actions:
                kind = act.get("action")
                if kind == "click":
                    page.click(act["selector"])
                elif kind == "fill":
                    page.fill(act["selector"], act["value"])
                elif kind == "wait":
                    page.wait_for_timeout(int(act.get("ms", 1000)))
                elif kind == "scroll":
                    page.mouse.wheel(0, int(act.get("dy", 2000)))
            page.wait_for_timeout(wait_ms)
            context.close()
            browser.close()

        from ducktap.discovery.har import HARDiscoverer
        name = opts.get("name") or slugify((urlparse(source).hostname or "site").split(".")[0])
        spec = HARDiscoverer().discover(out_har, name=name)
        spec.source = {"discoverer": "browser-sniff", "source": source, "har": out_har}
        return spec


plugins.register_discoverer(BrowserSniffDiscoverer())
