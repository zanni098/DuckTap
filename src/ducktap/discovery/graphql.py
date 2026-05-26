"""GraphQL introspection discoverer.

Turns a GraphQL endpoint into DuckTap's APISpec by introspecting Query fields.
Each query field becomes a POST operation against the GraphQL endpoint with
arguments exposed as body parameters.
"""
from __future__ import annotations

from typing import Any

import httpx

from ducktap.core import plugins
from ducktap.core.naming import slugify, snake_case
from ducktap.core.spec import APISpec, Operation, Param, Response

_INTROSPECT = """
{
  __schema {
    queryType {
      fields {
        name
        description
        args {
          name
          description
          type { kind name ofType { kind name ofType { kind name } } }
        }
      }
    }
  }
}
"""


def _unwrap_type(type_node: dict[str, Any] | None) -> tuple[str, bool]:
    required = False
    node = type_node or {}
    while node.get("kind") in {"NON_NULL", "LIST"} and node.get("ofType"):
        required = required or node.get("kind") == "NON_NULL"
        node = node["ofType"] or {}
    gql_name = node.get("name") or "String"
    return {
        "Int": "integer",
        "Float": "number",
        "Boolean": "boolean",
        "ID": "string",
        "String": "string",
    }.get(gql_name, "string"), required


class GraphQLDiscoverer:
    name = "graphql"

    def can_handle(self, source: str) -> bool:
        return source.startswith(("http://", "https://")) and "graphql" in source.lower()

    def discover(self, source: str, **opts: Any) -> APISpec:
        response = httpx.post(source, json={"query": _INTROSPECT}, timeout=30.0)
        if response.status_code >= 400:
            response.raise_for_status()
        schema = response.json().get("data", {}).get("__schema", {})
        fields = ((schema.get("queryType") or {}).get("fields") or [])
        name = opts.get("name") or slugify(source.split("/")[2].split(".")[0])
        spec = APISpec(
            name=name,
            display_name=name,
            base_url=source,
            server_urls=[source],
            source={"discoverer": "graphql", "source": source},
        )
        for field in fields:
            params: list[Param] = []
            for arg in field.get("args") or []:
                ptype, required = _unwrap_type(arg.get("type"))
                params.append(Param(
                    name=arg["name"],
                    location="body",
                    type=ptype,
                    required=required,
                    description=arg.get("description", "") or "",
                ))
            spec.operations.append(Operation(
                operation_id=snake_case(field["name"]),
                method="POST",
                path="",
                summary=field.get("description", "") or field["name"],
                tags=["graphql"],
                params=params,
                responses=[Response(status="200")],
            ))
        return spec


plugins.register_discoverer(GraphQLDiscoverer())
