"""Intermediate API spec representation.

This is DuckTap's normalized model that all discovery modules produce and all
generators consume. It is *deliberately* simpler than OpenAPI: it captures
only what an agent-native CLI needs.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

HTTPMethod = Literal["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]
ParamLocation = Literal["path", "query", "header", "body", "cookie"]
AuthType = Literal["apiKey", "http", "oauth2", "openIdConnect", "none"]


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
    type: AuthType = "apiKey"
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
    webhooks: list[Operation] = Field(default_factory=list)
    auth_schemes: list[AuthScheme] = Field(default_factory=list)
    source: dict[str, Any] = Field(default_factory=dict)  # provenance: discovery method + source
    extensions: dict[str, Any] = Field(default_factory=dict)  # vendor extensions
    # v0.7.x Creative Layer:
    archetype: str = "unknown"  # detected domain archetype (see core.archetype)
    insight: str = ""           # Non-Obvious Insight (NOI) for this API

    @field_validator("name")
    @classmethod
    def _slug_name(cls, v: str) -> str:
        """The name becomes directory names, package names and binary names.

        Anything that is not a slug is therefore a bug at best and a path
        traversal at worst (``--name ../../etc`` would otherwise write outside
        the requested output directory), so normalize it here -- the one place
        every discoverer funnels through -- rather than in each generator.
        """
        from ducktap.core.naming import slugify

        slug = slugify(v)
        if not slug:
            raise ValueError(f"name {v!r} does not contain any usable characters")
        return slug

    def normalize(self) -> APISpec:
        """Make the spec safe to hand to a generator. Mutates and returns self.

        Currently: guarantees operation ids are unique. Duplicate ids are legal
        in the wild (OpenAPI only *recommends* uniqueness, and synthesized ids
        can collide after snake-casing) but every generator maps one id to one
        symbol, so duplicates silently drop operations.
        """
        from ducktap.core.naming import uniquify

        for op, unique_id in zip(
            self.operations,
            uniquify([op.operation_id for op in self.operations]),
            strict=True,
        ):
            op.operation_id = unique_id

        if self.webhooks:
            for op, unique_id in zip(
                self.webhooks,
                uniquify([op.operation_id for op in self.webhooks]),
                strict=True,
            ):
                op.operation_id = unique_id
        return self

    def by_tag(self) -> dict[str, list[Operation]]:
        groups: dict[str, list[Operation]] = {}
        for op in self.operations:
            for t in op.tags or ["default"]:
                groups.setdefault(t, []).append(op)
        return groups
