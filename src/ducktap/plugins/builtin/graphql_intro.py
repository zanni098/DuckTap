"""Sample plugin: discover a GraphQL endpoint via introspection.

Demonstrates the DuckTap plugin shape. Activate with:

    pyproject.toml:
        [project.entry-points."ducktap.plugins"]
        graphql = "ducktap.plugins.builtin.graphql_intro"

This minimal implementation runs an introspection query and turns each Query
field into one Operation. POST /graphql with the appropriate selection set.
"""
from __future__ import annotations

from typing import Any

import httpx

from ducktap.core import plugins
from ducktap.core.naming import slugify, snake_case
from ducktap.core.spec import APISpec, Operation, Param, Response

_INTROSPECT = """
{ __schema { queryType { name fields { name description args { name description type { name kind ofType { name kind } } } } } } }
"""


class GraphQLDiscoverer:
    name = "graphql"

    def can_handle(self, source: str) -> bool:
        return source.startswith(("http://", "https://")) and "graphql" in source.lower()

    def discover(self, source: str, **opts: Any) -> APISpec:
        r = httpx.post(source, json={"query": _INTROSPECT}, timeout=30.0)
        r.raise_for_status()
        data = r.json().get("data", {}).get("__schema", {})
        query_type = data.get("queryType") or {}
        fields = query_type.get("fields") or []
        name = opts.get("name") or slugify(source.split("/")[2].split(".")[0])
        spec = APISpec(name=name, display_name=name, base_url=source,
                       server_urls=[source],
                       source={"discoverer": "graphql", "source": source})
        for f in fields:
            params = [
                Param(name=a["name"], location="body",
                      type=(a.get("type") or {}).get("name") or "string",
                      description=a.get("description", "") or "")
                for a in (f.get("args") or [])
            ]
            spec.operations.append(Operation(
                operation_id=snake_case(f["name"]), method="POST", path="",
                summary=f.get("description", "") or f["name"],
                params=params, responses=[Response(status="200")],
            ))
        return spec


plugins.register_discoverer(GraphQLDiscoverer())
