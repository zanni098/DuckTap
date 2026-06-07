"""HAR (HTTP Archive) discoverer.

Reads a HAR file (recorded browser traffic) and infers an APISpec by clustering
similar requests.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlparse

from ducktap.core import plugins
from ducktap.core.naming import operation_id_from_path, slugify
from ducktap.core.spec import (
    APISpec,
    AuthScheme,
    AuthType,
    HTTPMethod,
    Operation,
    Param,
    Response,
)

# Rate-limit header names (RFC 6585 + common vendor extensions)
_RATE_LIMIT_HEADERS = [
    "x-ratelimit-limit",
    "x-ratelimit-remaining",
    "x-ratelimit-reset",
    "x-rate-limit-limit",
    "x-rate-limit-remaining",
    "x-rate-limit-reset",
    "ratelimit-limit",
    "ratelimit-remaining",
    "ratelimit-reset",
    "retry-after",
]


def _detect_rate_limits(entries: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Scan HAR entries for rate-limit headers and infer policy + retry strategy."""
    limits: dict[str, Any] = {}
    retry_after: list[int] = []
    statuses: set[int] = set()
    for e in entries:
        resp = e.get("response") or {}
        st = resp.get("status", 0)
        if st in (429, 503):
            statuses.add(st)
        for h in resp.get("headers", []):
            name = h.get("name", "").lower()
            val = h.get("value", "")
            if name in _RATE_LIMIT_HEADERS:
                try:
                    limits[name] = int(val)
                except ValueError:
                    limits[name] = val
            if name == "retry-after":
                try:
                    retry_after.append(int(val))
                except ValueError:
                    pass
    if not limits and not statuses:
        return None
    result: dict[str, Any] = {
        "headers_found": list(limits.keys()),
        "statuses_seen": sorted(statuses),
    }
    if "ratelimit-limit" in limits or "x-ratelimit-limit" in limits:
        result["limit"] = limits.get("ratelimit-limit") or limits.get("x-ratelimit-limit")
    if retry_after:
        result["retry_after_seconds"] = retry_after[0]
        result["retry_strategy"] = "exponential backoff starting at 1s, max 60s"
    elif statuses:
        result["retry_strategy"] = "exponential backoff starting at 1s, max 60s"
    return result


_PATH_ID_RE = re.compile(r"^[0-9a-f-]{8,}$|^\d+$", re.IGNORECASE)


def _generalize_path(path: str) -> str:
    parts = []
    for seg in path.split("/"):
        if seg and _PATH_ID_RE.match(seg):
            parts.append("{id}")
        else:
            parts.append(seg)
    return "/".join(parts) or "/"



_AUTH_PATTERNS: list[tuple[re.Pattern[str], AuthType, str]] = [
    (re.compile(r'oauth|openid|sso|saml', re.I), 'oauth2', 'OAuth 2.0 / SSO redirect detected'),
    (re.compile(r'login|signin|sign-in|authenticate', re.I), 'apiKey', 'Login page detected -- likely session or API key auth'),
    (re.compile(r'api[_-]?key|x-api-key', re.I), 'apiKey', 'API key header pattern detected'),
    (re.compile(r'bearer|jwt|token', re.I), 'http', 'Bearer token pattern detected'),
]


def _detect_auth(entries: list[dict[str, Any]], host: str) -> list[AuthScheme]:
    """Scan HAR entries for auth flows and return inferred auth schemes."""
    schemes: list[AuthScheme] = []
    seen: set[str] = set()
    for e in entries:
        req = e.get('request') or {}
        resp = e.get('response') or {}
        url = req.get('url', '')
        # Check redirects to auth endpoints
        if resp.get('status', 0) in (301, 302, 307, 308):
            for h in resp.get('headers', []):
                if h.get('name', '').lower() == 'location':
                    loc = h.get('value', '')
                    for pat, atype, desc in _AUTH_PATTERNS:
                        if pat.search(loc) and atype not in seen:
                            seen.add(atype)
                            env = f"{slugify(host).upper().replace('-', '_')}_TOKEN"
                            if atype == 'apiKey':
                                env = f"{slugify(host).upper().replace('-', '_')}_API_KEY"
                            schemes.append(AuthScheme(
                                name=f"{atype}_auth", type=atype,
                                env_var=env, description=desc,
                            ))
        # Check request headers for auth patterns
        for h in req.get('headers', []):
            name = h.get('name', '').lower()
            val = h.get('value', '')
            if name == 'authorization' and 'bearer' in val.lower() and 'http' not in seen:
                seen.add('http')
                schemes.append(AuthScheme(
                    name='bearer_auth', type='http', scheme='bearer',
                    env_var=f"{slugify(host).upper().replace('-', '_')}_TOKEN",
                    description='Bearer token from Authorization header',
                ))
            if name == 'x-api-key' and 'apiKey' not in seen:
                seen.add('apiKey')
                schemes.append(AuthScheme(
                    name='api_key', type='apiKey', location='header',
                    parameter_name='X-API-Key',
                    env_var=f"{slugify(host).upper().replace('-', '_')}_API_KEY",
                    description='API key from X-API-Key header',
                ))
        # Check URL patterns for known auth providers
        for pat, atype, desc in _AUTH_PATTERNS:
            if pat.search(url) and atype not in seen:
                seen.add(atype)
                env = f"{slugify(host).upper().replace('-', '_')}_TOKEN"
                if atype == 'apiKey':
                    env = f"{slugify(host).upper().replace('-', '_')}_API_KEY"
                schemes.append(AuthScheme(
                    name=f"{atype}_auth", type=atype,
                    env_var=env, description=desc,
                ))
    return schemes

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
        host = max(host_counts, key=lambda h: host_counts[h])
        scheme = "https"
        base = f"{scheme}://{host}"
        name = opts.get("name") or slugify(host.split(".")[0])

        spec = APISpec(
            name=slugify(name), display_name=name, base_url=base,
            server_urls=[base], source={"discoverer": "har", "source": source},
        )
        spec.auth_schemes = _detect_auth(entries, host)
        rate_info = _detect_rate_limits(entries)
        if rate_info:
            spec.extensions["x-ducktap-rate-limits"] = rate_info

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
                operation_id=op_id, method=cast(HTTPMethod, method), path=path,
                summary=f"{method} {path}",
                params=params,
                responses=[Response(status="200", description="OK")],
            ))

        return spec


plugins.register_discoverer(HARDiscoverer())
