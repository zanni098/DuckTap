"""MCP server generator.

Produces a `<api>-dt-mcp` Python package implementing an MCP server (stdio
transport) that exposes every API operation as an MCP tool. Reuses the
generated CLI's HTTP client at runtime.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from ducktap.core import plugins
from ducktap.core.naming import cli_command_name, flag_name
from ducktap.core.spec import APISpec, Operation, Param

_TEMPLATES_DIR = Path(__file__).parent / "templates"


def _plainify(obj: Any) -> Any:
    """Recursively convert jsonref proxies / weird subclasses into plain
    dict/list/scalar so json.dumps works."""
    if isinstance(obj, dict):
        return {str(k): _plainify(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_plainify(v) for v in obj]
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    return str(obj)


def _operation_input_schema(op: Operation) -> dict[str, Any]:
    """Build a JSON Schema for an MCP tool's input."""
    props: dict[str, Any] = {}
    required: list[str] = []
    for p in op.params:
        sch_raw = p.schema_ or {"type": p.type or "string"}
        sch = _plainify(sch_raw) if isinstance(sch_raw, dict) else {"type": p.type or "string"}
        if p.description and not sch.get("description"):
            sch["description"] = p.description
        if p.enum:
            sch["enum"] = list(p.enum)
        props[p.name] = sch
        if p.required:
            required.append(p.name)
    schema: dict[str, Any] = {
        "type": "object",
        "properties": props,
        "additionalProperties": False,
    }
    if required:
        schema["required"] = required
    return schema


class MCPServerGenerator:
    name = "mcp-server"
    target = "mcp-server"

    def generate(self, spec: APISpec, out_dir: str, **opts: Any) -> list[str]:
        env = Environment(
            loader=FileSystemLoader(str(_TEMPLATES_DIR)),
            undefined=StrictUndefined,
            keep_trailing_newline=True,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        env.filters["flag"] = flag_name
        env.filters["cmd"] = cli_command_name
        env.filters["pyident"] = lambda s: s.replace("-", "_").replace(".", "_")

        pkg_name = (spec.name + "_dt_mcp").replace("-", "_")
        bin_name = f"{spec.name}-dt-mcp"
        cli_pkg = (spec.name + "_dt_cli").replace("-", "_")
        cli_bin = f"{spec.name}-dt-cli"

        # Pre-compute tool definitions
        tools = []
        for op in spec.operations:
            tools.append({
                "name": cli_command_name(op.operation_id),
                "description": op.summary or op.description or f"{op.method} {op.path}",
                "input_schema": _operation_input_schema(op),
                "op": op,
            })

        root = Path(out_dir) / bin_name
        pkg = root / pkg_name
        pkg.mkdir(parents=True, exist_ok=True)

        ctx = {
            "spec": spec, "pkg_name": pkg_name, "bin_name": bin_name,
            "cli_pkg": cli_pkg, "cli_bin": cli_bin, "tools": tools,
        }
        written: list[str] = []
        for tpl, dst in [
            ("mcp/__init__.py.j2", pkg / "__init__.py"),
            ("mcp/__main__.py.j2", pkg / "__main__.py"),
            ("mcp/server.py.j2", pkg / "server.py"),
            ("mcp/pyproject.toml.j2", root / "pyproject.toml"),
            ("mcp/README.md.j2", root / "README.md"),
        ]:
            text = env.get_template(tpl).render(**ctx)
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(text, encoding="utf-8")
            written.append(str(dst))
        return written


plugins.register_generator(MCPServerGenerator())
