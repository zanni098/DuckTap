"""OpenAPI / Swagger discoverer.

Reads OpenAPI 2.0 (Swagger) and 3.x specs from a local file or URL and produces
a normalized DuckTap APISpec.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
import jsonref
import yaml

from ducktap.core import plugins
from ducktap.core.naming import operation_id_from_path, slugify, snake_case
from ducktap.core.spec import APISpec, AuthScheme, Operation, Param, Response


class OpenAPIDiscoverer:
    name = "openapi"

    def can_handle(self, source: str) -> bool:
        s = source.lower()
        if s.startswith(("http://", "https://")):
            return s.endswith((".json", ".yaml", ".yml")) or "openapi" in s or "swagger" in s
        p = Path(source)
        if not p.exists():
            return False
        if p.suffix.lower() not in {".json", ".yaml", ".yml"}:
            return False
        try:
            doc = _load_raw(source)
            return "openapi" in doc or "swagger" in doc
        except Exception:
            return False

    def discover(self, source: str, **opts: Any) -> APISpec:
        raw = _load_raw(source)
        # Resolve $ref references for easier handling
        try:
            doc = jsonref.replace_refs(raw, lazy_load=False)
        except Exception:
            doc = raw

        is_v3 = "openapi" in doc
        info = doc.get("info") or {}
        name_hint = opts.get("name") or info.get("title") or _name_from_source(source)
        name = slugify(name_hint)

        servers = []
        if is_v3:
            servers = [s.get("url", "") for s in (doc.get("servers") or []) if s.get("url")]
        else:
            host = doc.get("host", "")
            base_path = doc.get("basePath", "")
            schemes = doc.get("schemes") or ["https"]
            if host:
                servers = [f"{schemes[0]}://{host}{base_path}"]

        spec = APISpec(
            name=name,
            display_name=info.get("title") or name,
            description=info.get("description", "") or "",
            version=info.get("version", "0.1.0") or "0.1.0",
            base_url=servers[0] if servers else "",
            server_urls=servers,
            source={"discoverer": "openapi", "source": source, "openapi": is_v3},
        )

        # Auth schemes
        if is_v3:
            schemes = (doc.get("components") or {}).get("securitySchemes") or {}
        else:
            schemes = doc.get("securityDefinitions") or {}
        for sname, sdef in schemes.items():
            spec.auth_schemes.append(_parse_auth(sname, sdef, name))

        # Operations
        paths = doc.get("paths") or {}
        for path, methods in paths.items():
            if not isinstance(methods, dict):
                continue
            path_level_params = methods.get("parameters") or []
            for method, op in methods.items():
                if method.lower() not in {"get", "post", "put", "patch", "delete", "head", "options"}:
                    continue
                if not isinstance(op, dict):
                    continue
                spec.operations.append(
                    _parse_operation(method.upper(), path, op, path_level_params, is_v3)
                )

        return spec


def _load_raw(source: str) -> dict[str, Any]:
    if source.startswith(("http://", "https://")):
        r = httpx.get(source, follow_redirects=True, timeout=30.0)
        r.raise_for_status()
        text = r.text
    else:
        text = Path(source).read_text(encoding="utf-8")
    text_stripped = text.lstrip()
    if text_stripped.startswith("{"):
        return json.loads(text)
    return yaml.safe_load(text)


def _name_from_source(source: str) -> str:
    if source.startswith(("http://", "https://")):
        host = urlparse(source).hostname or "api"
        return host.split(".")[0]
    return Path(source).stem


def _parse_auth(name: str, sdef: dict[str, Any], project: str) -> AuthScheme:
    t = sdef.get("type", "apiKey")
    if t == "apiKey":
        return AuthScheme(
            name=name, type="apiKey",
            location=sdef.get("in", "header"),
            parameter_name=sdef.get("name", "X-API-Key"),
            env_var=f"{project.upper().replace('-', '_')}_API_KEY",
            description=sdef.get("description", ""),
        )
    if t == "http":
        scheme = sdef.get("scheme", "bearer")
        return AuthScheme(
            name=name, type="http", location="header",
            parameter_name="Authorization", scheme=scheme,
            env_var=f"{project.upper().replace('-', '_')}_TOKEN",
            description=sdef.get("description", ""),
        )
    if t in ("oauth2", "openIdConnect"):
        return AuthScheme(
            name=name, type=t, location="header",  # type: ignore[arg-type]
            parameter_name="Authorization", scheme="bearer",
            env_var=f"{project.upper().replace('-', '_')}_TOKEN",
            description=sdef.get("description", ""),
        )
    return AuthScheme(name=name, type="none", description=sdef.get("description", ""))


def _parse_operation(
    method: str,
    path: str,
    op: dict[str, Any],
    path_params: list[dict[str, Any]],
    is_v3: bool,
) -> Operation:
    op_id_raw = op.get("operationId") or operation_id_from_path(method, path)
    op_id = snake_case(op_id_raw)

    params: list[Param] = []
    seen: set[str] = set()
    for raw in list(path_params) + list(op.get("parameters") or []):
        if not isinstance(raw, dict):
            continue
        key = (raw.get("name"), raw.get("in"))
        if key in seen or not raw.get("name"):
            continue
        seen.add(key)
        params.append(_parse_param(raw, is_v3))

    if is_v3 and "requestBody" in op:
        rb = op["requestBody"] or {}
        content = (rb.get("content") or {})
        # prefer JSON
        media = content.get("application/json") or next(iter(content.values()), {})
        schema = (media or {}).get("schema") or {}
        # flatten top-level object properties into individual body params for ergonomics
        props = (schema.get("properties") or {}) if schema.get("type") == "object" else {}
        required_set = set(schema.get("required") or [])
        if props:
            for pname, pschema in props.items():
                if not isinstance(pschema, dict):
                    continue
                params.append(Param(
                    name=pname, location="body",
                    type=pschema.get("type", "string"),
                    required=pname in required_set,
                    description=pschema.get("description", ""),
                    enum=pschema.get("enum"),
                    schema=pschema,
                ))
        else:
            params.append(Param(
                name="body", location="body", type="object",
                required=bool(rb.get("required")),
                description=rb.get("description", ""),
                schema=schema,
            ))

    responses: list[Response] = []
    for status, rdef in (op.get("responses") or {}).items():
        if not isinstance(rdef, dict):
            continue
        if is_v3:
            content = (rdef.get("content") or {})
            media = content.get("application/json") or next(iter(content.values()), {})
            schema = (media or {}).get("schema")
            ct = next(iter(content.keys()), "application/json") if content else "application/json"
        else:
            schema = rdef.get("schema")
            ct = "application/json"
        responses.append(Response(
            status=str(status), description=rdef.get("description", ""),
            content_type=ct, schema=schema,
        ))

    security = op.get("security") or []
    auth = []
    for s in security:
        if isinstance(s, dict):
            auth.extend(s.keys())

    return Operation(
        operation_id=op_id, method=method, path=path,  # type: ignore[arg-type]
        summary=op.get("summary", "") or "",
        description=op.get("description", "") or "",
        tags=list(op.get("tags") or []),
        params=params, responses=responses,
        auth=auth, deprecated=bool(op.get("deprecated")),
    )


def _parse_param(raw: dict[str, Any], is_v3: bool) -> Param:
    schema = raw.get("schema") if is_v3 else raw
    schema = schema or {}
    return Param(
        name=raw["name"],
        location=raw.get("in", "query"),
        type=(schema.get("type") if isinstance(schema, dict) else None) or "string",
        required=bool(raw.get("required")),
        description=raw.get("description", "") or "",
        default=schema.get("default") if isinstance(schema, dict) else None,
        enum=schema.get("enum") if isinstance(schema, dict) else None,
        example=raw.get("example"),
        schema=schema if isinstance(schema, dict) else None,
    )


# Register
plugins.register_discoverer(OpenAPIDiscoverer())
