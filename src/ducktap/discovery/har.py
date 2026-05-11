"""HAR (HTTP Archive) discoverer.

Reads a HAR file (recorded browser traffic) and infers an APISpec by clustering
similar requests.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, parse_qsl

from ducktap.core import plugins
from ducktap.core.naming import operation_id_from_path, slugify
from ducktap.core.spec import APISpec, Operation, Param, Response

_PATH_ID_RE = re.compile(r"^[0-9a-f-]{8,}$|^\d+$", re.IGNORECASE)


def _generalize_path(path: str) -> str:
    parts = []
    for seg in path.split("/"):
        if seg and _PATH_ID_RE.match(seg):
            parts.append("{id}")
        else:
            parts.append(seg)
    return "/".join(parts) or "/"


class HARDiscoverer:
    name = "har"

    def can_handle(self, source: str) -> bool:
        p = Path(source)
        if not p.exists() or p.suffix.lower() != ".har":
            return False
        try:
            doc = json.loads(p.read_text(encoding="utf-8"))
            return "log" in doc and "entries" in doc["log"]
        except Exception:
            return False

    def discover(self, source: str, **opts: Any) -> APISpec:
        doc = json.loads(Path(source).read_text(encoding="utf-8"))
        entries = doc.get("log", {}).get("entries", [])
        # Cluster by (method, generalized path, host)
        clusters: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
        for e in entries:
            req = e.get("request") or {}
            url = req.get("url") or ""
            if not url:
                continue
            u = urlparse(url)
            ct = ""
            for h in req.get("headers") or []:
                if h.get("name", "").lower() == "content-type":
                    ct = h.get("value", "")
                    break
            # filter non-API responses (heuristic): only keep json
            resp = e.get("response") or {}
            rct = ""
            for h in resp.get("headers") or []:
                if h.get("name", "").lower() == "content-type":
                    rct = h.get("value", "")
                    break
            if "json" not in (rct or "") and "json" not in (ct or ""):
                continue
            key = (req.get("method", "GET").upper(), _generalize_path(u.path), u.netloc)
            clusters[key].append(e)

        if not clusters:
            raise ValueError("No JSON API requests found in HAR")

        # Pick host with most calls as the base
        host_counts: dict[str, int] = defaultdict(int)
        for (_, _, host), es in clusters.items():
            host_counts[host] += len(es)
        host = max(host_counts, key=host_counts.get)
        scheme = "https"
        base = f"{scheme}://{host}"
        name = opts.get("name") or slugify(host.split(".")[0])

        spec = APISpec(
            name=slugify(name), display_name=name, base_url=base,
            server_urls=[base], source={"discoverer": "har", "source": source},
        )

        for (method, path, h), es in clusters.items():
            if h != host:
                continue
            sample = es[0]
            req = sample["request"]
            u = urlparse(req["url"])
            # query params
            params: list[Param] = []
            for q in req.get("queryString") or []:
                params.append(Param(name=q["name"], location="query", required=False))
            # path params
            for seg in path.split("/"):
                if seg.startswith("{") and seg.endswith("}"):
                    params.append(Param(name=seg[1:-1], location="path", required=True))
            # body
            body = (req.get("postData") or {}).get("text")
            if body:
                try:
                    parsed = json.loads(body)
                    if isinstance(parsed, dict):
                        for k in parsed:
                            params.append(Param(name=k, location="body"))
                except Exception:
                    pass

            op_id = operation_id_from_path(method, path)
            spec.operations.append(Operation(
                operation_id=op_id, method=method, path=path,  # type: ignore[arg-type]
                summary=f"{method} {path}",
                params=params,
                responses=[Response(status="200", description="OK")],
            ))

        return spec


plugins.register_discoverer(HARDiscoverer())
