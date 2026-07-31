"""Python CLI generator.

Produces a self-contained `<api>-dt-cli` Python package using Click as the
command framework. The generated CLI:

* Reads auth from environment variables (suggested names from the spec).
* Hits the live API via httpx with sensible defaults (timeouts, retries, JSON).
* Mirrors responses into a local SQLite cache (`~/.ducktap/<api>/mirror.sqlite`)
  for fast compound queries.
* Supports `--json` (raw output) and `--pretty` (rich table) globally.
* Each subcommand corresponds to one Operation.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from ducktap import __version__ as ducktap_version
from ducktap.core import plugins
from ducktap.core.naming import (
    cli_command_name,
    flag_name,
    pep440_version,
    safe_identifier,
)
from ducktap.core.spec import APISpec, Operation, Param

_TEMPLATES_DIR = Path(__file__).parent / "templates"

# Typed per-resource tables per archetype: (table, [(col, type)], text_col, ts_col).
# Drives the domain-specific SQLite tables + FTS5 in the generated mirror.
_ARCHETYPE_TABLES: dict[str, tuple[str, list[tuple[str, str]], str, str]] = {
    "project_management": (
        "issues",
        [("id", "TEXT PRIMARY KEY"), ("title", "TEXT"), ("status", "TEXT"),
         ("assignee", "TEXT"), ("priority", "TEXT"), ("created_at", "TEXT"),
         ("updated_at", "TEXT"), ("body", "TEXT")],
        "title", "updated_at",
    ),
    "communication": (
        "messages",
        [("id", "TEXT PRIMARY KEY"), ("channel_id", "TEXT"), ("author_id", "TEXT"),
         ("content", "TEXT"), ("timestamp", "TEXT"), ("thread_id", "TEXT")],
        "content", "timestamp",
    ),
    "payments": (
        "charges",
        [("id", "TEXT PRIMARY KEY"), ("amount", "REAL"), ("currency", "TEXT"),
         ("status", "TEXT"), ("customer_id", "TEXT"), ("created_at", "TEXT"),
         ("description", "TEXT")],
        "description", "created_at",
    ),
    "infrastructure": (
        "resources",
        [("id", "TEXT PRIMARY KEY"), ("name", "TEXT"), ("type", "TEXT"),
         ("status", "TEXT"), ("region", "TEXT"), ("created_at", "TEXT"),
         ("metadata", "TEXT")],
        "name", "created_at",
    ),
    "content": (
        "documents",
        [("id", "TEXT PRIMARY KEY"), ("title", "TEXT"), ("content", "TEXT"),
         ("author_id", "TEXT"), ("updated_at", "TEXT"), ("parent_id", "TEXT")],
        "content", "updated_at",
    ),
}


def _archetype_table_ctx(archetype: str) -> dict[str, Any]:
    """Template context describing the archetype's typed table (or empty)."""
    entry = _ARCHETYPE_TABLES.get(archetype)
    if not entry:
        return {"archetype_table": None}
    table, cols, text_col, ts_col = entry
    return {
        "archetype_table": table,
        "archetype_cols": [{"name": n, "type": t} for n, t in cols],
        "archetype_col_names": [n for n, _ in cols],
        "archetype_text_col": text_col,
        "archetype_ts_col": ts_col,
    }


def cli_params(op: Operation) -> list[dict[str, Any]]:
    """Assign each parameter a unique CLI flag *and* a unique Python argument.

    Both have to be unique, and they are separate namespaces: two parameters
    called ``id`` (one in the path, one in the body) are perfectly legal in
    OpenAPI, but a single ``--id``/``id`` pair means Click hands the command
    one value where it needs two -- the request is then built with the wrong
    one, silently. Collisions are disambiguated by parameter location, which
    keeps the common case (`--id`) untouched.
    """
    out: list[dict[str, Any]] = []
    seen_flags: set[str] = set()
    seen_dests: set[str] = set()
    for p in op.params:
        flag = flag_name(p.name)
        if flag in seen_flags:
            flag = flag_name(f"{p.location}-{p.name}")
        n = 1
        while flag in seen_flags:
            n += 1
            flag = f"{flag_name(f'{p.location}-{p.name}')}-{n}"
        seen_flags.add(flag)

        dest = safe_identifier(p.name)
        if dest in seen_dests:
            dest = safe_identifier(f"{p.location}_{p.name}")
        n = 1
        while dest in seen_dests:
            n += 1
            dest = safe_identifier(f"{p.location}_{p.name}_{n}")
        seen_dests.add(dest)

        out.append({"param": p, "flag": flag, "dest": dest})
    return out


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )


def _python_type(p: Param) -> str:
    return {
        "string": "str", "integer": "int", "number": "float",
        "boolean": "bool", "array": "str", "object": "str",
    }.get(p.type, "str")


def _click_type(p: Param) -> str:
    base = {
        "string": "str", "integer": "int", "number": "float", "boolean": "bool",
    }.get(p.type, "str")
    if p.enum:
        choices = ", ".join(repr(str(x)) for x in p.enum)
        return f"click.Choice([{choices}])"
    return base


def _path_params(op: Operation) -> list[Param]:
    return [p for p in op.params if p.location == "path"]


def _query_params(op: Operation) -> list[Param]:
    return [p for p in op.params if p.location == "query"]


def _body_params(op: Operation) -> list[Param]:
    return [p for p in op.params if p.location == "body"]


def _header_params(op: Operation) -> list[Param]:
    return [p for p in op.params if p.location == "header"]


class PythonCLIGenerator:
    name = "python-cli"
    target = "python-cli"

    def generate(self, spec: APISpec, out_dir: str, **opts: Any) -> list[str]:
        env = _env()
        env.filters["flag"] = flag_name
        env.filters["cmd"] = cli_command_name
        env.filters["pytype"] = _python_type
        env.filters["clicktype"] = _click_type
        env.filters["pyident"] = safe_identifier
        env.filters["cli_params"] = cli_params
        # repr() yields a valid Python literal for scalars (True/False/None/...)
        env.filters["pyrepr"] = lambda v: repr(v)

        pkg_name = (spec.name + "_dt_cli").replace("-", "_")
        cli_bin = f"{spec.name}-dt-cli"
        root = Path(out_dir) / cli_bin
        pkg = root / pkg_name
        pkg.mkdir(parents=True, exist_ok=True)
        (root / "tests").mkdir(exist_ok=True)

        ctx = {
            "spec": spec,
            "pkg_name": pkg_name,
            "cli_bin": cli_bin,
            "operations": spec.operations,
            "ducktap_version": ducktap_version,
            "package_version": pep440_version(spec.version),
            "path_params": _path_params,
            "query_params": _query_params,
            "body_params": _body_params,
            "header_params": _header_params,
            **_archetype_table_ctx(spec.archetype),
        }
        written: list[str] = []

        files = [
            ("cli/__init__.py.j2", pkg / "__init__.py"),
            ("cli/__main__.py.j2", pkg / "__main__.py"),
            ("cli/main.py.j2", pkg / "main.py"),
            ("cli/client.py.j2", pkg / "client.py"),
            ("cli/mirror.py.j2", pkg / "mirror.py"),
            ("cli/commands.py.j2", pkg / "commands.py"),
            ("cli/pyproject.toml.j2", root / "pyproject.toml"),
            ("cli/README.md.j2", root / "README.md"),
            ("cli/.gitignore.j2", root / ".gitignore"),
            ("cli/test_smoke.py.j2", root / "tests" / "test_smoke.py"),
            ("cli/.github/workflows/test_and_release.yml.j2", root / ".github" / "workflows" / "test_and_release.yml"),
        ]
        for tpl, dst in files:
            text = env.get_template(tpl).render(**ctx)
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(text, encoding="utf-8")
            written.append(str(dst))
        return written


plugins.register_generator(PythonCLIGenerator())
