"""Rust CLI generator (clap).

Produces a self-contained `<api>-dt-rs` Rust crate using clap as the
command framework. Builds to a single binary for easy distribution.
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


def _rustident(s: str) -> str:
    """Turn an arbitrary string into a safe Rust identifier."""
    out = _IDENT_RE.sub("_", str(s))
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


def _rust_type(p: Param) -> str:
    return {
        "string": "String", "integer": "i64", "number": "f64",
        "boolean": "bool", "array": "Vec<String>", "object": "serde_json::Value",
    }.get(p.type, "String")


def _path_params(op: Operation) -> list[Param]:
    return [p for p in op.params if p.location == "path"]


def _query_params(op: Operation) -> list[Param]:
    return [p for p in op.params if p.location == "query"]


def _body_params(op: Operation) -> list[Param]:
    return [p for p in op.params if p.location == "body"]


def _header_params(op: Operation) -> list[Param]:
    return [p for p in op.params if p.location == "header"]


# Priority for resolving duplicate parameter names: a name used in the path
# wins over the same name appearing in the query/header/body, so the generated
# Args struct never declares the same field twice.
_LOC_PRIORITY = {"path": 0, "query": 1, "header": 2, "body": 3}


def _dedup_params(op: Operation) -> list[Param]:
    """Return op.params with duplicate names removed (first-wins by location)."""
    seen: set[str] = set()
    out: list[Param] = []
    for p in sorted(op.params, key=lambda p: _LOC_PRIORITY.get(p.location, 9)):
        if p.name in seen:
            continue
        seen.add(p.name)
        out.append(p)
    return out


class RustCLIGenerator:
    name = "rust-cli"
    target = "rust-cli"

    def generate(self, spec: APISpec, out_dir: str, **opts: Any) -> list[str]:
        env = _env()
        env.filters["flag"] = flag_name
        env.filters["cmd"] = cli_command_name
        env.filters["rusttype"] = _rust_type
        env.filters["rustident"] = _rustident
        # A Rust string literal: JSON escaping is compatible for our purposes.
        env.filters["json"] = lambda v: json.dumps(v if isinstance(v, str) else str(v))

        pkg_name = spec.name.replace("-", "_") + "_dt_rs"
        root = Path(out_dir) / (spec.name + "-dt-rs")
        src = root / "src"
        src.mkdir(parents=True, exist_ok=True)

        ctx = {
            "spec": spec,
            "pkg_name": pkg_name,
            "cli_bin": spec.name + "-dt-rs",
            "operations": spec.operations,
            "ducktap_version": ducktap_version,
            "path_params": _path_params,
            "query_params": _query_params,
            "body_params": _body_params,
            "header_params": _header_params,
            "dedup": _dedup_params,
        }
        written: list[str] = []

        files = [
            ("rust_cli/Cargo.toml.j2", root / "Cargo.toml"),
            ("rust_cli/src/main.rs.j2", src / "main.rs"),
            ("rust_cli/src/client.rs.j2", src / "client.rs"),
            ("rust_cli/src/commands.rs.j2", src / "commands.rs"),
            ("rust_cli/README.md.j2", root / "README.md"),
            ("rust_cli/.gitignore.j2", root / ".gitignore"),
        ]
        for tpl, dst in files:
            text = env.get_template(tpl).render(**ctx)
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(text, encoding="utf-8")
            written.append(str(dst))
        return written


plugins.register_generator(RustCLIGenerator())
