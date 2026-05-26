"""Intermediate API spec representation.

This is DuckTap's normalized model that all discovery modules produce and all
generators consume. It is *deliberately* simpler than OpenAPI: it captures
only what an agent-native CLI needs.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

HTTPMethod = Literal["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]
ParamLocation = Literal["path", "query", "header", "body", "cookie"]


class Param(BaseModel):
    """A single parameter on an operation."""

    name: str
    location: ParamLocation
    type: str = "string"  # "string", "integer", "number", "boolean", "array", "object"
    required: bool = False
    description: str = ""
    default: Any | None = None
    enum: list[Any] | None = None
    example: Any | None = None
    # For nested body params we keep the raw JSON Schema fragment
    schema_: dict[str, Any] | None = Field(default=None, alias="schema")

    model_config = {"populate_by_name": True}


class Response(BaseModel):
    status: str = "200"
    description: str = ""
    content_type: str = "application/json"
    schema_: dict[str, Any] | None = Field(default=None, alias="schema")
    example: Any | None = None

    model_config = {"populate_by_name": True}


class Operation(BaseModel):
    """One callable endpoint, becomes one CLI subcommand and one MCP tool."""

    operation_id: str          # canonical id, snake_case (e.g. "list_pets")
    method: HTTPMethod
    path: str                  # e.g. "/pets/{petId}"
    summary: str = ""
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    params: list[Param] = Field(default_factory=list)
    responses: list[Response] = Field(default_factory=list)
    auth: list[str] = Field(default_factory=list)  # security scheme names
    deprecated: bool = False


class AuthScheme(BaseModel):
    name: str
    type: Literal["apiKey", "http", "oauth2", "openIdConnect", "none"] = "apiKey"
    location: Literal["header", "query", "cookie"] = "header"
    parameter_name: str = "Authorization"
    scheme: str = "bearer"  # for http auth: "basic", "bearer"
    env_var: str = ""        # suggested env var name for the credential
    description: str = ""


class APISpec(BaseModel):
    """Normalized API specification -- DuckTap's single intermediate format."""

    name: str                  # canonical slug, e.g. "petstore"
    display_name: str = ""
    description: str = ""
    version: str = "0.1.0"
    base_url: str = ""
    server_urls: list[str] = Field(default_factory=list)
    operations: list[Operation] = Field(default_factory=list)
    auth_schemes: list[AuthScheme] = Field(default_factory=list)
    source: dict[str, Any] = Field(default_factory=dict)  # provenance: discovery method + source
    extensions: dict[str, Any] = Field(default_factory=dict)  # vendor extensions

    def by_tag(self) -> dict[str, list[Operation]]:
        groups: dict[str, list[Operation]] = {}
        for op in self.operations:
            for t in op.tags or ["default"]:
                groups.setdefault(t, []).append(op)
        return groups
