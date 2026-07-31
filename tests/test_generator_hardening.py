"""Regression tests for generator inputs that used to produce broken output.

Each case here is a real spec shape that made DuckTap emit code that would not
parse, would not install, or would build the wrong HTTP request.
"""
from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path

import pytest

from ducktap.core.naming import (
    pep440_version,
    safe_identifier,
    semver_version,
    uniquify,
)
from ducktap.core.pipeline import press
from ducktap.core.spec import APISpec, Operation, Param

# operationId `class` is a Python keyword; `updateWidget` and `update_widget`
# collapse to the same snake_case id; `id` appears in both the path and body.
TRICKY_SPEC = """
openapi: 3.0.0
info:
  title: Tricky API
  version: "2024-01-15"
servers:
  - url: https://api.tricky.test/v1
paths:
  /widgets/{id}:
    put:
      operationId: updateWidget
      tags: [widgets]
      parameters:
        - name: id
          in: path
          required: true
          schema: {type: string}
      requestBody:
        content:
          application/json:
            schema:
              type: object
              required: [id]
              properties:
                id: {type: string}
                name: {type: string}
  /widgets:
    get:
      operationId: update_widget
      tags: [widgets]
    post:
      operationId: "class"
      tags: [widgets]
"""

RECURSIVE_SPEC = """
openapi: 3.0.0
info: {title: Recursive API, version: "1.0.0"}
servers: [{url: "https://r.test"}]
paths:
  /tree:
    post:
      operationId: makeTree
      requestBody:
        content:
          application/json:
            schema: {$ref: '#/components/schemas/Node'}
components:
  schemas:
    Node:
      type: object
      properties:
        name: {type: string}
        children:
          type: array
          items: {$ref: '#/components/schemas/Node'}
"""


@pytest.fixture
def tricky_out(tmp_path: Path) -> Path:
    spec_file = tmp_path / "tricky.yaml"
    spec_file.write_text(TRICKY_SPEC, encoding="utf-8")
    out = tmp_path / "out"
    press(str(spec_file), str(out))
    return out


def _commands_src(out: Path, name: str = "tricky") -> str:
    pkg = name.replace("-", "_") + "_dt_cli"
    return (out / f"{name}-dt-cli" / pkg / "commands.py").read_text(encoding="utf-8")


# --- naming primitives ----------------------------------------------------

def test_safe_identifier_escapes_keywords():
    assert safe_identifier("class") == "class_"
    assert safe_identifier("import") == "import_"
    assert safe_identifier("list_pets") == "list_pets"
    assert safe_identifier("2fast") == "_2fast"
    assert safe_identifier("type", lang="go") == "type_"
    assert safe_identifier("fn", lang="rust") == "fn_"


def test_uniquify_disambiguates_in_order():
    assert uniquify(["a", "b", "a", "a"]) == ["a", "b", "a_2", "a_3"]
    assert uniquify([]) == []


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("2022-11-15", "2022.11.15"), ("v1", "1"), ("1.0.0", "1.0.0"), ("", "0.1.0")],
)
def test_pep440_version(raw, expected):
    assert pep440_version(raw) == expected


def test_semver_always_has_three_parts():
    assert semver_version("2022-11-15") == "2022.11.15"
    assert semver_version("v1") == "1.0.0"
    assert semver_version("nonsense") == "0.1.0"


# --- spec normalization ---------------------------------------------------

def test_spec_name_is_slugified_so_it_cannot_escape_the_output_dir():
    assert APISpec(name="../../etc/passwd").name == "etc-passwd"
    assert APISpec(name="My Cool API").name == "my-cool-api"
    with pytest.raises(ValueError):
        APISpec(name="../..")


def test_normalize_makes_operation_ids_unique():
    spec = APISpec(
        name="dup",
        operations=[
            Operation(operation_id="list_pets", method="GET", path="/a"),
            Operation(operation_id="list_pets", method="GET", path="/b"),
        ],
    )
    spec.normalize()
    assert [op.operation_id for op in spec.operations] == ["list_pets", "list_pets_2"]


# --- generated output -----------------------------------------------------

def test_keyword_operation_id_still_parses(tricky_out: Path):
    """`operationId: class` used to emit `def class(...)` -- a SyntaxError."""
    ast.parse(_commands_src(tricky_out))


def test_duplicate_operation_ids_produce_two_distinct_commands(tricky_out: Path):
    src = _commands_src(tricky_out)
    assert '"update-widget",' in src
    assert '"update-widget-2",' in src


def test_colliding_param_names_get_separate_destinations(tricky_out: Path):
    """A path `id` and a body `id` must not share one Click destination."""
    src = _commands_src(tricky_out)
    assert '"--body-id",\n        "body_id",' in src
    # The wire name stays `id` -- only the local variable is renamed.
    assert 'body["id"] = _coerce(kwargs["body_id"])' in src


def test_generated_package_version_is_installable(tricky_out: Path):
    pyproject = (tricky_out / "tricky-dt-cli" / "pyproject.toml").read_text()
    assert 'version = "2024.01.15"' in pyproject


def test_recursive_schema_does_not_blow_the_stack(tmp_path: Path):
    """A $ref cycle used to raise RecursionError during MCP tool generation."""
    spec_file = tmp_path / "rec.yaml"
    spec_file.write_text(RECURSIVE_SPEC, encoding="utf-8")
    out = tmp_path / "out"
    result = press(str(spec_file), str(out))
    assert len(result.spec.operations) == 1
    # The APISpec must stay JSON-serializable for the manifest / research output.
    json.dumps(result.spec.model_dump(by_alias=True), default=str)
    server = (out / "recursive-dt-mcp" / "recursive_dt_mcp" / "server.py").read_text()
    ast.parse(server)


def test_path_parameters_are_percent_encoded(tricky_out: Path):
    assert "_quote_path(kwargs.get" in _commands_src(tricky_out)


def test_no_cache_is_honoured_even_when_saving(tricky_out: Path):
    """`use_cache` used to be hardcoded to `method == GET`."""
    src = _commands_src(tricky_out)
    assert 'use_cache=_use_cache(ctx, "GET")' in src
    assert 'use_cache=("GET" == "GET")' not in src


def test_generated_cli_help_runs(tricky_out: Path):
    root = tricky_out / "tricky-dt-cli"
    proc = subprocess.run(
        [sys.executable, "-m", "tricky_dt_cli", "--help"],
        cwd=str(root), capture_output=True, text=True, timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    assert "--watch" in proc.stdout


def test_watch_flag_is_actually_wired_up(tricky_out: Path, monkeypatch):
    """`--watch` was parsed and stored, but nothing ever read it."""
    monkeypatch.syspath_prepend(str(tricky_out / "tricky-dt-cli"))
    for mod in [m for m in sys.modules if m.startswith("tricky_dt_cli")]:
        del sys.modules[mod]
    commands = __import__("tricky_dt_cli.commands", fromlist=["commands"])

    class _Ctx:
        def __init__(self, watch): self.obj = {"watch": watch}

    assert list(commands._watch_ticks(_Ctx(0))) == [0]
    ticks = commands._watch_ticks(_Ctx(1))
    assert next(ticks) == 0  # a positive interval keeps yielding
    for mod in [m for m in sys.modules if m.startswith("tricky_dt_cli")]:
        del sys.modules[mod]


def test_cli_params_helper_keeps_wire_names():
    from ducktap.generator.python_cli import cli_params

    op = Operation(
        operation_id="x", method="PUT", path="/w/{id}",
        params=[
            Param(name="id", location="path", required=True),
            Param(name="id", location="body"),
        ],
    )
    resolved = cli_params(op)
    assert [c["flag"] for c in resolved] == ["--id", "--body-id"]
    assert [c["dest"] for c in resolved] == ["id", "body_id"]
    assert [c["param"].name for c in resolved] == ["id", "id"]
