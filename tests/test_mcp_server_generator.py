"""Dedicated tests for the MCP server generator."""
from __future__ import annotations

import ast
import importlib
import json
import sys
from pathlib import Path

from ducktap.core.pipeline import press
from ducktap.core.spec import APISpec, Operation, Param
from ducktap.generator.mcp_server import MCPServerGenerator, _operation_input_schema

MINI_SPEC = """
openapi: 3.0.0
info: {title: Mini API, version: "1.2.3"}
servers: [{url: "https://example.test/api"}]
paths:
  /pets/{petId}:
    get:
      operationId: getPet
      summary: Fetch one pet
      parameters:
        - name: petId
          in: path
          required: true
          description: Pet identifier
          schema: {type: integer}
        - name: include_history
          in: query
          schema: {type: boolean}
      responses:
        "200": {description: ok}
  /pets:
    post:
      operationId: addPet
      summary: Create a pet
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [name]
              properties:
                name: {type: string}
                tag: {type: string}
      responses:
        "201": {description: created}
"""


AUTH_SPEC = """
openapi: 3.0.0
info: {title: Auth API, version: "1.0.0"}
servers: [{url: "https://auth.example.test"}]
components:
  securitySchemes:
    apiKey:
      type: apiKey
      in: header
      name: X-API-Key
    oauth:
      type: oauth2
      flows:
        clientCredentials:
          tokenUrl: https://auth.example.test/token
          scopes: {}
security:
  - apiKey: []
  - oauth: []
paths:
  /me:
    get:
      operationId: getMe
      summary: Fetch current user
      responses:
        "200": {description: ok}
"""


DUPLICATE_SPEC = """
openapi: 3.0.0
info: {title: Names API, version: "1.0.0"}
servers: [{url: "https://names.example.test"}]
paths:
  /one:
    get:
      operationId: syncUser
      responses:
        "200": {description: ok}
  /two:
    get:
      operationId: sync_user
      responses:
        "200": {description: ok}
  /three:
    get:
      operationId: class
      responses:
        "200": {description: ok}
"""


EMPTY_SPEC = """
openapi: 3.0.0
info: {title: Empty API, version: "1.0.0"}
servers: [{url: "https://empty.example.test"}]
paths: {}
"""


def _press_text(tmp_path: Path, text: str, *, name: str, targets: list[str]) -> Path:
    spec_file = tmp_path / f"{name}.yaml"
    spec_file.write_text(text, encoding="utf-8")
    out = tmp_path / "out"
    press(str(spec_file), str(out), name=name, targets=targets)
    return out


def _mcp_server_source(out: Path, name: str) -> str:
    pkg = name.replace("-", "_") + "_dt_mcp"
    return (out / f"{name}-dt-mcp" / pkg / "server.py").read_text(encoding="utf-8")


def test_basic_generation_writes_valid_mcp_package(tmp_path: Path) -> None:
    out = _press_text(tmp_path, MINI_SPEC, name="mini", targets=["mcp-server"])

    server = out / "mini-dt-mcp" / "mini_dt_mcp" / "server.py"
    assert server.exists()
    ast.parse(server.read_text(encoding="utf-8"))
    assert (out / "mini-dt-mcp" / "pyproject.toml").exists()
    assert (out / "mini-dt-mcp" / "README.md").exists()


def test_generated_tools_expose_names_descriptions_and_input_schemas(tmp_path: Path) -> None:
    out = _press_text(tmp_path, MINI_SPEC, name="mini", targets=["python-cli", "mcp-server"])
    monkey_path = [str(out / "mini-dt-cli"), str(out / "mini-dt-mcp")]
    for root in reversed(monkey_path):
        sys.path.insert(0, root)
    for module in list(sys.modules):
        if module.startswith("mini_dt_"):
            del sys.modules[module]
    try:
        server = importlib.import_module("mini_dt_mcp.server")
        tools = {tool.name: tool for tool in server.TOOLS}
    finally:
        for root in monkey_path:
            sys.path.remove(root)

    assert set(tools) == {"get-pet", "add-pet"}
    assert tools["get-pet"].description == "Fetch one pet"
    schema = tools["get-pet"].input_schema
    assert schema["type"] == "object"
    assert schema["properties"]["petId"]["type"] == "integer"
    assert schema["properties"]["petId"]["description"] == "Pet identifier"
    assert schema["properties"]["include_history"]["type"] == "boolean"
    assert schema["required"] == ["petId"]
    assert schema["additionalProperties"] is False


def test_operation_input_schema_preserves_required_and_enum_metadata() -> None:
    op = Operation(
        operation_id="search",
        method="GET",
        path="/search",
        params=[
            Param(name="q", location="query", required=True, description="Search text"),
            Param(
                name="status",
                location="query",
                schema={"type": "string"},
                enum=["open", "closed"],
            ),
        ],
    )

    schema = _operation_input_schema(op)

    assert schema["required"] == ["q"]
    assert schema["properties"]["q"]["description"] == "Search text"
    assert schema["properties"]["status"] == {
        "type": "string",
        "enum": ["open", "closed"],
    }


def test_operation_input_schema_preserves_body_object_schema() -> None:
    op = Operation(
        operation_id="create_pet",
        method="POST",
        path="/pets",
        params=[
            Param(
                name="payload",
                location="body",
                required=True,
                schema={
                    "type": "object",
                    "required": ["name"],
                    "properties": {"name": {"type": "string"}},
                },
            ),
        ],
    )

    schema = _operation_input_schema(op)

    assert schema["required"] == ["payload"]
    assert schema["properties"]["payload"]["properties"]["name"]["type"] == "string"


def test_recursive_schema_is_bounded_and_json_serializable() -> None:
    recursive: dict[str, object] = {"type": "object"}
    recursive["properties"] = {"child": recursive}
    op = Operation(
        operation_id="create_tree",
        method="POST",
        path="/tree",
        params=[Param(name="payload", location="body", schema=recursive)],
    )

    schema = _operation_input_schema(op)

    json.dumps(schema)
    assert schema["properties"]["payload"]["type"] == "object"


def test_duplicate_and_keyword_operation_names_render_as_tools(tmp_path: Path) -> None:
    out = _press_text(tmp_path, DUPLICATE_SPEC, name="names", targets=["mcp-server"])
    server = _mcp_server_source(out, "names")

    assert '"name": "sync-user"' in server
    assert '"name": "sync-user-2"' in server
    assert '"name": "class"' in server


def test_auth_schemes_flow_through_the_mcp_package(tmp_path: Path) -> None:
    out = _press_text(tmp_path, AUTH_SPEC, name="auth-demo", targets=["python-cli", "mcp-server"])

    readme = (out / "auth-demo-dt-mcp" / "README.md").read_text(encoding="utf-8")
    pyproject = (out / "auth-demo-dt-mcp" / "pyproject.toml").read_text(encoding="utf-8")
    client = (out / "auth-demo-dt-cli" / "auth_demo_dt_cli" / "client.py").read_text(
        encoding="utf-8"
    )

    assert '"AUTH_DEMO_API_KEY": "${AUTH_DEMO_API_KEY}"' in readme
    assert '"AUTH_DEMO_TOKEN": "${AUTH_DEMO_TOKEN}"' in readme
    assert '"auth-demo-dt-cli"' in pyproject
    assert 'h["X-API-Key"] = v' in client
    assert 'h["Authorization"] = "Bearer " + v' in client


def test_empty_openapi_spec_generates_empty_valid_tool_list(tmp_path: Path) -> None:
    out = _press_text(tmp_path, EMPTY_SPEC, name="empty", targets=["mcp-server"])

    server = _mcp_server_source(out, "empty")
    readme = (out / "empty-dt-mcp" / "README.md").read_text(encoding="utf-8")

    ast.parse(server)
    assert "_TOOL_DEFS = [" in server
    assert "## Tools exposed (0)" in readme


def test_generator_can_render_empty_in_memory_spec(tmp_path: Path) -> None:
    out = tmp_path / "manual"

    files = MCPServerGenerator().generate(APISpec(name="manual"), str(out))

    assert len(files) == 5
    assert (out / "manual-dt-mcp" / "manual_dt_mcp" / "server.py").exists()
