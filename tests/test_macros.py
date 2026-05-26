"""Tests for compound command macros."""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from ducktap.macros import Macro, MacroStep, _resolve, list_macros, run_macro


def test_resolve_simple_ref() -> None:
    ctx = {"step_0": {"id": 42, "name": "Ada"}}
    assert _resolve("{{ steps[0].id }}", ctx) == "42"
    assert _resolve("{{ steps[0].name }}", ctx) == "Ada"


def test_resolve_nested_ref() -> None:
    ctx = {"step_0": {"items": [{"id": 1}, {"id": 2}]}}
    assert _resolve("{{ steps[0].items[0].id }}", ctx) == "1"


def test_resolve_noop() -> None:
    assert _resolve("hello", {}) == "hello"
    assert _resolve(123, {}) == 123


def test_resolve_dict_and_list() -> None:
    ctx = {"step_0": {"x": 1}}
    assert _resolve({"a": "{{ steps[0].x }}"}, ctx) == {"a": "1"}
    assert _resolve(["{{ steps[0].x }}", 2], ctx) == ["1", 2]


def test_macro_from_file() -> None:
    yaml_text = """
name: pet-workflow
description: List then fetch one pet
steps:
  - operation: list-pets
    params: {}
    save_as: pets
  - operation: get-pet
    params:
      petId: "{{ steps[0].id }}"
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_text)
        path = f.name

    macro = Macro.from_file(path)
    assert macro.name == "pet-workflow"
    assert len(macro.steps) == 2
    assert macro.steps[1].params["petId"] == "{{ steps[0].id }}"


def test_run_macro_dry_invoke() -> None:
    macro = Macro(
        name="test",
        steps=[
            MacroStep(operation="op1", params={"x": 1}),
            MacroStep(operation="op2", params={"y": "{{ steps[0].result }}"}),
        ],
    )

    def invoke(op: str, **params) -> dict[str, Any]:
        return {"op": op, **params}

    results = run_macro(macro, invoke)
    assert len(results) == 2
    assert results[0]["op"] == "op1"
    # Step 1 references steps[0].result which doesn't exist, so resolves to ""
    assert results[1]["y"] == ""


def test_run_macro_with_save_as() -> None:
    macro = Macro(
        name="chain",
        steps=[
            MacroStep(operation="create", params={}, save_as="created"),
            MacroStep(operation="get", params={"id": "{{ steps[0].id }}"}),
        ],
    )

    responses = [
        {"id": "abc-123", "status": "ok"},
        {"id": "abc-123", "detail": "fetched"},
    ]

    def invoke(op: str, **params) -> dict[str, Any]:
        return responses.pop(0)

    results = run_macro(macro, invoke)
    assert results[1]["id"] == "abc-123"


def test_run_macro_select() -> None:
    macro = Macro(
        name="select-test",
        steps=[
            MacroStep(operation="list", params={}, select=["id", "name"]),
        ],
    )

    def invoke(op: str, **params) -> dict[str, Any]:
        return {"id": 1, "name": "Ada", "extra": "noise"}

    results = run_macro(macro, invoke)
    assert results[0] == {"id": 1, "name": "Ada"}


def test_list_macros() -> None:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "test.yaml"
        p.write_text("name: hello\nsteps:\n  - operation: list\n    params: {}\n")
        macros = list_macros(td)
        assert len(macros) == 1
        assert macros[0]["name"] == "hello"


def test_list_macros_empty_dir() -> None:
    with tempfile.TemporaryDirectory() as td:
        assert list_macros(td) == []
