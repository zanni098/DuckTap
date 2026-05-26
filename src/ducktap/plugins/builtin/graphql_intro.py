"""First-class GraphQL discoverer.

Introspects a GraphQL endpoint and normalizes Query, Mutation, and
Subscription fields into DuckTap APISpec operations.  Also attempts to
fetch persisted-query hashes if the server exposes them.
"""
from __future__ import annotations

from typing import Any

import httpx

from ducktap.core import plugins
from ducktap.core.naming import slugify, snake_case
from ducktap.core.spec import APISpec, Operation, Param, Response

_INTROSPECT = """
query IntrospectionQuery {
  __schema {
    queryType { name fields { name description args { name description type { name kind ofType { name kind ofType { name kind } } } } } }
    mutationType { name fields { name description args { name description type { name kind ofType { name kind ofType { name kind } } } } } }
    subscriptionType { name fields { name description args { name description type { name kind ofType { name kind ofType { name kind } } } } } }
  }
}
"""


def _unwrap_type(type_node: dict[str, Any] | None) -> tuple[str, bool]:
    """Return (ducktap_type, required)."""
    required = False
    node = type_node or {}
    while node.get("kind") in {"NON_NULL", "LIST"} and node.get("ofType"):
        required = required or node.get("kind") == "NON_NULL"
        node = node["ofType"] or {}
    gql_name = node.get("name") or "String"
    return {
        "Int": "integer", "Float": "number", "Boolean": "boolean",
        "ID": "string", "String": "string",
    }.get(gql_name, "string"), required


def _fields_to_operations(
    fields: list[dict[str, Any]], method: str, base_url: str
) -> list[Operation]:
    ops: list[Operation] = []
    for field in fields:
        params: list[Param] = []
        for arg in field.get("args") or []:
            ptype, required = _unwrap_type(arg.get("type"))
            params.append(Param(
                name=arg["name"], location="body", type=ptype,
                required=required,
                description=arg.get("description", "") or "",
            ))
        ops.append(Operation(
            operation_id=snake_case(field["name"]),
            method="POST", path="",
            summary=field.get("description", "") or field["name"],
            tags=[method.lower()],
            params=params,
            responses=[Response(status="200")],
        ))
    return ops


def _fetch_persisted_queries(endpoint: str) -> list[dict[str, str]]:
    """Best-effort: some GraphQL servers expose persisted queries at
    a well-known path or via Apollo-style automatic persisted queries.
    We just note the attempt; real APQ exchange requires server-specific
    protocol support.
    """
    # Placeholder for future APQ negotiation.
    return []


class GraphQLDiscoverer:
    name = "graphql"

    def can_handle(self, source: str) -> bool:
        return (
            source.startswith(("http://", "https://"))
            and "graphql" in source.lower()
        )

    def discover(self, source: str, **opts: Any) -> APISpec:
        r = httpx.post(
            source, json={"query": _INTROSPECT}, timeout=30.0
        )
        if r.status_code >= 400:
            r.raise_for_status()
        schema = r.json().get("data", {}).get("__schema", {})
        name = opts.get("name") or slugify(
            source.split("/")[2].split(".")[0]
        )
        spec = APISpec(
            name=name, display_name=name, base_url=source,
            server_urls=[source],
            source={"discoverer": "graphql", "source": source},
        )
        for type_name, tag in (("queryType", "query"), ("mutationType", "mutation"), ("subscriptionType", "subscription")):
            type_data = schema.get(type_name) or {}
            fields = type_data.get("fields") or []
            spec.operations.extend(_fields_to_operations(fields, tag, source))
        # Best-effort persisted-query hint
        _fetch_persisted_queries(source)
        return spec


plugins.register_discoverer(GraphQLDiscoverer())
