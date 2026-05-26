"""Rust CLI generator (clap).

Produces a self-contained `<api>-dt-rs` Rust crate using clap as the
command framework. Builds to a single binary for easy distribution.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from ducktap import __version__ as ducktap_version
from ducktap.core import plugins
from ducktap.core.naming import cli_command_name, flag_name
from ducktap.core.spec import APISpec, Operation, Param

_TEMPLATES_DIR = Path(__file__).parent / "templates"


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


class RustCLIGenerator:
    name = "rust-cli"
    target = "rust-cli"

    def generate(self, spec: APISpec, out_dir: str, **opts: Any) -> list[str]:
        env = _env()
        env.filters["flag"] = flag_name
        env.filters["cmd"] = cli_command_name
        env.filters["rusttype"] = _rust_type
        import re as _re
        _ident_re = _re.compile(r"[^A-Za-z0-9_]+")

        def _rustident(s: str) -> str:
            out = _ident_re.sub("_", str(s))
            if out and out[0].isdigit():
                out = "_" + out
            return out or "_"
        env.filters["rustident"] = _rustident

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
