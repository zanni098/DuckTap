"""OpenAPI / Swagger discoverer.

Reads OpenAPI 2.0 (Swagger) and 3.x specs from a local file or URL and produces
a normalized DuckTap APISpec.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
import jsonref
import yaml

from ducktap.core import plugins
from ducktap.core.naming import operation_id_from_path, short_name, snake_case
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
        # Resolve $ref references for easier handling, then flatten the lazy
        # proxies into plain data with cycles cut (see `_materialize`).
        try:
            doc = _materialize(jsonref.replace_refs(raw, lazy_load=False))
        except Exception:
            doc = raw

        is_v3 = "openapi" in doc
        info = doc.get("info") or {}
        # If the user passes --name, take it as-is (already a slug). Otherwise
        # produce a short, agent-friendly slug from the spec title.
        if opts.get("name"):
            name = opts["name"]
        elif info.get("title"):
            name = short_name(info["title"], fallback=_name_from_source(source))
        else:
            name = short_name(_name_from_source(source))

        servers = []
        if is_v3:
            servers = [s.get("url", "") for s in (doc.get("servers") or []) if s.get("url")]
        else:
            host = doc.get("host", "")
            base_path = doc.get("basePath", "")
            schemes = doc.get("schemes") or ["https"]
            if host:
                servers = [f"{schemes[0]}://{host}{base_path}"]

        # Resolve relative server URLs (common for petstore-style specs that
        # ship "/api/v3") against the source URL, so the generated CLI has a
        # working base_url out of the box.
        if source.startswith(("http://", "https://")):
            servers = [urljoin(source, s) if not _is_absolute(s) else s for s in servers]

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

        # Webhooks (OpenAPI 3.1+)
        if is_v3:
            webhooks = doc.get("webhooks") or {}
            if isinstance(webhooks, dict):
                for name, methods in webhooks.items():
                    if not isinstance(methods, dict):
                        continue
                    webhook_path = name if name.startswith("/") else f"/{name}"
                    webhook_level_params = methods.get("parameters") or []
                    for method, op in methods.items():
                        if method.lower() not in {"get", "post", "put", "patch", "delete", "head", "options"}:
                            continue
                        if not isinstance(op, dict):
                            continue
                        parsed_webhook = _parse_operation(
                            method.upper(), webhook_path, op, webhook_level_params, is_v3
                        )
                        if not parsed_webhook.tags:
                            parsed_webhook.tags = ["webhooks"]
                        spec.webhooks.append(parsed_webhook)

        return spec


# A spec is fetched from a URL the user names, but that URL is not always
# trusted (catalog entries, redirects, the local dashboard). Cap the download
# so a hostile or broken endpoint cannot exhaust memory.
MAX_SPEC_BYTES = 64 * 1024 * 1024

# Depth at which a resolved schema is truncated. Recursive models ($ref back to
# an ancestor) are extremely common -- GitHub, Stripe and Notion all ship them
# -- and jsonref resolves them into a genuinely cyclic object graph.
_MAX_SCHEMA_DEPTH = 24
_TRUNCATED: dict[str, Any] = {"type": "object", "x-ducktap-truncated": "recursive $ref"}


def _materialize(node: Any, _depth: int = 0, _stack: tuple[int, ...] = ()) -> Any:
    """Turn a jsonref-resolved document into plain, acyclic, JSON-safe data.

    `jsonref.replace_refs` hands back lazy proxies, and a self-referencing
    schema becomes an infinite object graph: walking it (to build an MCP input
    schema, to dump the APISpec, to checksum it) raises RecursionError. Cutting
    the cycle here -- once, at the boundary -- keeps every downstream consumer
    simple.
    """
    if isinstance(node, dict):
        if _depth >= _MAX_SCHEMA_DEPTH or id(node) in _stack:
            return dict(_TRUNCATED)
        stack = (*_stack, id(node))
        return {str(k): _materialize(v, _depth + 1, stack) for k, v in node.items()}
    if isinstance(node, (list, tuple)):
        if _depth >= _MAX_SCHEMA_DEPTH or id(node) in _stack:
            return []
        stack = (*_stack, id(node))
        return [_materialize(v, _depth + 1, stack) for v in node]
    if isinstance(node, (str, int, float, bool)) or node is None:
        return node
    return str(node)


def _load_raw(source: str) -> dict[str, Any]:
    if source.startswith(("http://", "https://")):
        with httpx.stream("GET", source, follow_redirects=True, timeout=30.0) as r:
            r.raise_for_status()
            chunks: list[bytes] = []
            size = 0
            for chunk in r.iter_bytes():
                size += len(chunk)
                if size > MAX_SPEC_BYTES:
                    raise ValueError(
                        f"spec at {source} exceeds the {MAX_SPEC_BYTES} byte limit"
                    )
                chunks.append(chunk)
            text = b"".join(chunks).decode(r.encoding or "utf-8", errors="replace")
    else:
        text = Path(source).read_text(encoding="utf-8")
    text_stripped = text.lstrip()
    if text_stripped.startswith("{"):
        doc = json.loads(text)
    else:
        doc = yaml.safe_load(text)
    if not isinstance(doc, dict):
        raise ValueError(f"{source} is not an OpenAPI document (expected a mapping)")
    return doc


def _is_absolute(url: str) -> bool:
    return url.startswith(("http://", "https://"))


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


def _flatten_schema(
    schema: Any,
    _depth: int = 0,
    _stack: tuple[int, ...] = (),
) -> dict[str, Any]:
    """Resolve and flatten allOf, oneOf, and anyOf composition schemas.

    - allOf: recursively merges all subschemas into a single flat object schema,
      shallow-merging `properties` and unioning `required` fields.
    - oneOf / anyOf: picks the first non-empty object branch (preferring discriminator
      when present) to produce typed CLI parameters, avoiding crashes on polymorphic bodies.
    """
    if not isinstance(schema, dict):
        return {} if schema is None else schema

    if _depth >= _MAX_SCHEMA_DEPTH or id(schema) in _stack:
        return dict(schema)

    stack = (*_stack, id(schema))
    out: dict[str, Any] = dict(schema)

    # 1. Handle allOf composition
    if "allOf" in schema and isinstance(schema["allOf"], list):
        merged_props: dict[str, Any] = {}
        merged_required: set[str] = set()

        if isinstance(out.get("properties"), dict):
            merged_props.update(out["properties"])
        if isinstance(out.get("required"), (list, set, tuple)):
            merged_required.update(out["required"])

        for sub in schema["allOf"]:
            if not isinstance(sub, dict):
                continue
            flat_sub = _flatten_schema(sub, _depth + 1, stack)
            if isinstance(flat_sub.get("properties"), dict):
                merged_props.update(flat_sub["properties"])
            if isinstance(flat_sub.get("required"), (list, set, tuple)):
                merged_required.update(flat_sub["required"])
            if "type" not in out and flat_sub.get("type"):
                out["type"] = flat_sub["type"]
            if "description" not in out and flat_sub.get("description"):
                out["description"] = flat_sub["description"]

        if merged_props:
            out["type"] = "object"
            out["properties"] = merged_props
        if merged_required:
            out["required"] = sorted(merged_required)
        out.pop("allOf", None)

    # 2. Handle oneOf / anyOf composition
    for keyword in ("oneOf", "anyOf"):
        if keyword in out and isinstance(out[keyword], list):
            branches = [b for b in out[keyword] if isinstance(b, dict)]
            if branches:
                chosen_branch = branches[0]
                discriminator = out.get("discriminator")
                if isinstance(discriminator, dict) and "propertyName" in discriminator:
                    prop_name = discriminator["propertyName"]
                    for b in branches:
                        if prop_name in (b.get("properties") or {}) or prop_name in (b.get("required") or []):
                            chosen_branch = b
                            break

                flat_chosen = _flatten_schema(chosen_branch, _depth + 1, stack)
                for k, v in flat_chosen.items():
                    if k not in out or not out[k]:
                        out[k] = v
                if "properties" in flat_chosen and isinstance(flat_chosen["properties"], dict):
                    out.setdefault("properties", {})
                    if isinstance(out["properties"], dict):
                        out["properties"].update(flat_chosen["properties"])
                    if "type" not in out:
                        out["type"] = "object"
                if "required" in flat_chosen and isinstance(flat_chosen["required"], (list, tuple, set)):
                    out.setdefault("required", [])
                    out["required"] = sorted(set(out.get("required") or []).union(set(flat_chosen["required"])))

            out.pop(keyword, None)

    return out


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
    seen: set[tuple[Any, Any]] = set()
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
        media: dict[str, Any] = content.get("application/json") or next(iter(content.values()), {})
        raw_schema = (media or {}).get("schema") or {}
        schema = _flatten_schema(raw_schema) if isinstance(raw_schema, dict) else raw_schema
        # flatten top-level object properties into individual body params for ergonomics
        props = (schema.get("properties") or {}) if isinstance(schema, dict) and schema.get("type") == "object" else {}
        required_set = set(schema.get("required") or []) if isinstance(schema, dict) else set()
        if props:
            for pname, pschema in props.items():
                if not isinstance(pschema, dict):
                    continue
                flat_pschema = _flatten_schema(pschema) if isinstance(pschema, dict) else pschema
                params.append(Param(
                    name=pname, location="body",
                    type=flat_pschema.get("type", "string") if isinstance(flat_pschema, dict) else "string",
                    required=pname in required_set,
                    description=flat_pschema.get("description", "") if isinstance(flat_pschema, dict) else "",
                    enum=flat_pschema.get("enum") if isinstance(flat_pschema, dict) else None,
                    schema=flat_pschema if isinstance(flat_pschema, dict) else None,
                ))
        else:
            params.append(Param(
                name="body", location="body", type="object",
                required=bool(rb.get("required")),
                description=rb.get("description", ""),
                schema=schema if isinstance(schema, dict) else None,
            ))

    responses: list[Response] = []
    for status, rdef in (op.get("responses") or {}).items():
        if not isinstance(rdef, dict):
            continue
        if is_v3:
            content = (rdef.get("content") or {})
            rmedia: dict[str, Any] = content.get("application/json") or next(iter(content.values()), {})
            raw_schema = (rmedia or {}).get("schema")
            schema = _flatten_schema(raw_schema) if isinstance(raw_schema, dict) else raw_schema
            ct = next(iter(content.keys()), "application/json") if content else "application/json"
        else:
            raw_schema = rdef.get("schema")
            schema = _flatten_schema(raw_schema) if isinstance(raw_schema, dict) else raw_schema
            ct = "application/json"
        responses.append(Response(
            status=str(status), description=rdef.get("description", ""),
            content_type=ct, schema=schema,
        ))

    security = op.get("security") or []
    auth: list[str] = []
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
    schema = raw.get("schema") if is_v3 else (raw.get("schema") or raw)
    schema = schema or {}
    if isinstance(schema, dict):
        schema = _flatten_schema(schema)
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
