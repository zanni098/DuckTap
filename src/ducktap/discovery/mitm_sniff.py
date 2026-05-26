"""mitmproxy-backed sniff discoverer.

Runs a local mitmproxy instance, captures traffic while the user browses (or an
automated script runs), then converts the resulting HAR into an APISpec.

No headless browser required — point any HTTP client or browser at the proxy
and DuckTap will do the rest.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from ducktap.core import plugins
from ducktap.core.spec import APISpec

MITM_ADDON = '''
from mitmproxy import http
import json, os

_HAR = {"log": {"version": "1.2", "creator": {"name": "ducktap-mitm", "version": "0.1"}, "entries": []}}
_OUT = os.environ.get("DUCKTAP_MITM_HAR", "/tmp/ducktap_mitm.har")

def response(flow: http.HTTPFlow) -> None:
    req = flow.request
    resp = flow.response
    entry = {
        "startedDateTime": "1970-01-01T00:00:00.000Z",
        "time": 0,
        "request": {
            "method": req.method,
            "url": req.url,
            "httpVersion": "HTTP/1.1",
            "headers": [{"name": k, "value": v} for k, v in req.headers.items()],
            "queryString": [{"name": k, "value": v} for k, v in req.query.items()],
            "postData": {"mimeType": req.headers.get("content-type", ""), "text": req.content.decode("utf-8", "replace")} if req.content else None,
        },
        "response": {
            "status": resp.status_code,
            "statusText": "",
            "httpVersion": "HTTP/1.1",
            "headers": [{"name": k, "value": v} for k, v in resp.headers.items()],
            "content": {"mimeType": resp.headers.get("content-type", ""), "text": resp.content.decode("utf-8", "replace")} if resp.content else None,
        },
    }
    _HAR["log"]["entries"].append(entry)
    with open(_OUT, "w") as f:
        json.dump(_HAR, f)
'''


class MitmSniffDiscoverer:
    name = "mitm-sniff"

    def can_handle(self, source: str) -> bool:
        return source == "mitm://proxy"

    def discover(self, source: str, **opts: Any) -> APISpec:
        try:
            subprocess.run([sys.executable, "-m", "mitmproxy", "--version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            raise RuntimeError(
                "mitm-sniff requires mitmproxy. Install with: pip install mitmproxy"
            ) from e

        proxy_port = int(opts.get("proxy_port", 8080))
        timeout = int(opts.get("timeout", 60))
        out_har = opts.get("har_path") or str(
            Path(tempfile.mkdtemp(prefix="ducktap-mitm-")) / "capture.har"
        )

        addon_path = Path(tempfile.mkdtemp(prefix="ducktap-mitm-addon-")) / "addon.py"
        addon_path.write_text(MITM_ADDON, encoding="utf-8")

        env = os.environ.copy()
        env["DUCKTAP_MITM_HAR"] = out_har

        proc = subprocess.Popen(
            [
                sys.executable, "-m", "mitmweb",
                "--listen-port", str(proxy_port),
                "--web-port", str(proxy_port + 1),
                "--scripts", str(addon_path),
                "--quiet",
            ],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        print(f"[mitm-sniff] Proxy running on port {proxy_port}. Configure your client/browser to use it.")
        print(f"[mitm-sniff] Web UI available at http://127.0.0.1:{proxy_port + 1}")
        print(f"[mitm-sniff] Waiting up to {timeout}s for traffic... (Ctrl-C to stop early)")

        try:
            time.sleep(timeout)
        except KeyboardInterrupt:
            print("\n[mitm-sniff] Stopping early...")

        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

        if not Path(out_har).exists():
            raise RuntimeError("No traffic captured. Did you route any requests through the proxy?")

        from ducktap.discovery.har import HARDiscoverer
        name = opts.get("name") or "mitm-api"
        spec = HARDiscoverer().discover(out_har, name=name)
        spec.source = {"discoverer": "mitm-sniff", "har": out_har}
        return spec


plugins.register_discoverer(MitmSniffDiscoverer())
