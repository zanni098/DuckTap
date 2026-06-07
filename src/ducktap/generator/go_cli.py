"""Go CLI generator (cobra).

Produces a self-contained `<api>-dt-go` Go module using cobra as the
command framework.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from ducktap import __version__ as ducktap_version
from ducktap.core import plugins
from ducktap.core.naming import cli_command_name, flag_name
from ducktap.core.spec import APISpec, Operation, Param

_TEMPLATES_DIR = Path(__file__).parent / "templates"
_IDENT_RE = re.compile(r"[^A-Za-z0-9_]+")


def _goident(s: str) -> str:
    """Turn an arbitrary string into a safe Go identifier."""
    out = _IDENT_RE.sub("", str(s))
    if out and out[0].isdigit():
        out = "_" + out
    return out or "_"


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )


def _go_type(p: Param) -> str:
    return {
        "string": "string", "integer": "int", "number": "float64",
        "boolean": "bool", "array": "[]string", "object": "map[string]interface{}",
    }.get(p.type, "string")


def _path_params(op: Operation) -> list[Param]:
    return [p for p in op.params if p.location == "path"]


def _query_params(op: Operation) -> list[Param]:
    return [p for p in op.params if p.location == "query"]


def _body_params(op: Operation) -> list[Param]:
    return [p for p in op.params if p.location == "body"]


def _header_params(op: Operation) -> list[Param]:
    return [p for p in op.params if p.location == "header"]


class GoCLIGenerator:
    name = "go-cli"
    target = "go-cli"

    def generate(self, spec: APISpec, out_dir: str, **opts: Any) -> list[str]:
        env = _env()
        env.filters["flag"] = flag_name
        env.filters["cmd"] = cli_command_name
        env.filters["gotype"] = _go_type
        env.filters["goident"] = _goident
        # A Go interpreted string literal: JSON encoding escapes quotes,
        # backslashes, and newlines compatibly.
        env.filters["gostr"] = lambda v: json.dumps(str(v))

        pkg_name = spec.name + "-dt-go"
        mod_name = "github.com/example/" + pkg_name
        root = Path(out_dir) / pkg_name
        cmd = root / "cmd"
        internal = root / "internal"
        cmd.mkdir(parents=True, exist_ok=True)
        internal.mkdir(parents=True, exist_ok=True)

        ctx = {
            "spec": spec,
            "pkg_name": pkg_name,
            "mod_name": mod_name,
            "cli_bin": pkg_name,
            "operations": spec.operations,
            "ducktap_version": ducktap_version,
            "path_params": _path_params,
            "query_params": _query_params,
            "body_params": _body_params,
            "header_params": _header_params,
        }
        written: list[str] = []

        files = [
            ("go_cli/go.mod.j2", root / "go.mod"),
            ("go_cli/main.go.j2", root / "main.go"),
            ("go_cli/cmd/root.go.j2", cmd / "root.go"),
            ("go_cli/cmd/agent_context.go.j2", cmd / "agent_context.go"),
            ("go_cli/internal/client.go.j2", internal / "client.go"),
            ("go_cli/README.md.j2", root / "README.md"),
            ("go_cli/.gitignore.j2", root / ".gitignore"),
        ]
        # One command file per operation, all in a single flat `cmd` package
        # that registers each subcommand on the shared rootCmd via init().
        for op in spec.operations:
            dst = cmd / (cli_command_name(op.operation_id) + ".go")
            text = env.get_template("go_cli/cmd/command.go.j2").render(op=op, **ctx)
            dst.write_text(text, encoding="utf-8")
            written.append(str(dst))

        for tpl, dst in files:
            text = env.get_template(tpl).render(**ctx)
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(text, encoding="utf-8")
            written.append(str(dst))
        return written


plugins.register_generator(GoCLIGenerator())
