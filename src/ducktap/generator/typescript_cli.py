"""TypeScript CLI generator (oclif).

Produces a self-contained `<api>-dt-ts` TypeScript package using oclif as the
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


def _tsident(s: str) -> str:
    """Turn an arbitrary string into a safe TypeScript identifier."""
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


def _ts_type(p: Param) -> str:
    return {
        "string": "string", "integer": "number", "number": "number",
        "boolean": "boolean", "array": "string[]", "object": "Record<string, unknown>",
    }.get(p.type, "string")


def _path_params(op: Operation) -> list[Param]:
    return [p for p in op.params if p.location == "path"]


def _query_params(op: Operation) -> list[Param]:
    return [p for p in op.params if p.location == "query"]


def _body_params(op: Operation) -> list[Param]:
    return [p for p in op.params if p.location == "body"]


def _header_params(op: Operation) -> list[Param]:
    return [p for p in op.params if p.location == "header"]


class TypeScriptCLIGenerator:
    name = "typescript-cli"
    target = "typescript-cli"

    def generate(self, spec: APISpec, out_dir: str, **opts: Any) -> list[str]:
        env = _env()
        env.filters["flag"] = flag_name
        env.filters["cmd"] = cli_command_name
        env.filters["tstype"] = _ts_type
        env.filters["tsident"] = _tsident
        env.filters["json"] = lambda v: json.dumps(v)

        pkg_name = spec.name + "-dt-ts"
        root = Path(out_dir) / pkg_name
        src = root / "src"
        src.mkdir(parents=True, exist_ok=True)

        ctx = {
            "spec": spec,
            "pkg_name": pkg_name,
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
            ("ts_cli/package.json.j2", root / "package.json"),
            ("ts_cli/tsconfig.json.j2", root / "tsconfig.json"),
            ("ts_cli/bin/run.js.j2", root / "bin" / "run.js"),
            ("ts_cli/src/base.ts.j2", src / "base.ts"),
            ("ts_cli/src/index.ts.j2", src / "index.ts"),
            ("ts_cli/README.md.j2", root / "README.md"),
            ("ts_cli/.gitignore.j2", root / ".gitignore"),
        ]
        # One command file per operation (grouped by tag)
        for op in spec.operations:
            tag = (op.tags[0] if op.tags else "general")
            cmd_dir = src / "commands" / cli_command_name(tag)
            cmd_dir.mkdir(parents=True, exist_ok=True)
            dst = cmd_dir / (cli_command_name(op.operation_id) + ".ts")
            text = env.get_template("ts_cli/src/command.ts.j2").render(op=op, **ctx)
            dst.write_text(text, encoding="utf-8")
            written.append(str(dst))

        for tpl, dst in files:
            text = env.get_template(tpl).render(**ctx)
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(text, encoding="utf-8")
            written.append(str(dst))
        return written


plugins.register_generator(TypeScriptCLIGenerator())
