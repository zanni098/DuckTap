"""Compound command macros — declarative recipes that chain API operations.

A macro is a YAML file describing a sequence of API calls where the output
of one step can be piped into the input of the next via Jinja2-style
expressions.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

_STEP_REF_RE = re.compile(r"\{\{\s*steps\[(\d+)\]\.(.+?)\s*\}\}")


@dataclass
class MacroStep:
    """One step in a macro recipe."""
    operation: str           # e.g. "list-pets"
    params: dict[str, Any] = field(default_factory=dict)
    save_as: str = ""        # name to save result under for later steps
    select: list[str] = field(default_factory=list)


@dataclass
class Macro:
    """A compound macro recipe."""
    name: str
    description: str = ""
    steps: list[MacroStep] = field(default_factory=list)

    @classmethod
    def from_file(cls, path: str) -> Macro:
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        steps = [
            MacroStep(
                operation=s["operation"],
                params=s.get("params", {}),
                save_as=s.get("save_as", ""),
                select=s.get("select", []),
            )
            for s in data.get("steps", [])
        ]
        return cls(
            name=data.get("name", Path(path).stem),
            description=data.get("description", ""),
            steps=steps,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "steps": [
                {
                    "operation": s.operation,
                    "params": s.params,
                    "save_as": s.save_as,
                    "select": s.select,
                }
                for s in self.steps
            ],
        }


def _resolve(value: Any, context: dict[str, Any]) -> Any:
    """Replace {{ steps[n].field }} references in strings/lists/dicts."""
    if isinstance(value, str):

        def replacer(m: re.Match[str]) -> str:
            idx = int(m.group(1))
            field = m.group(2)
            step_result = context.get(f"step_{idx}")
            if step_result is None:
                raise ValueError(f"Step {idx} not yet executed")
            # Support dotted path like steps[0].id or steps[0].items[0].name
            parts = field.replace("[", ".").replace("]", "").split(".")
            obj = step_result
            for part in parts:
                if obj is None:
                    return ""
                if isinstance(obj, dict):
                    obj = obj.get(part)
                elif isinstance(obj, list):
                    try:
                        obj = obj[int(part)]
                    except (ValueError, IndexError):
                        return ""
                else:
                    return ""
            return str(obj) if obj is not None else ""

        return _STEP_REF_RE.sub(replacer, value)
    if isinstance(value, list):
        return [_resolve(v, context) for v in value]
    if isinstance(value, dict):
        return {k: _resolve(v, context) for k, v in value.items()}
    return value


def run_macro(macro: Macro, invoke: Any) -> list[Any]:
    """Execute a macro against a CLI invoke callable.

    `invoke` should be a callable that takes (operation_id, **params)
    and returns the parsed response data.
    """
    context: dict[str, Any] = {}
    results: list[Any] = []
    for i, step in enumerate(macro.steps):
        params = _resolve(step.params, context)
        result = invoke(step.operation, **params)
        if step.select:
            if isinstance(result, list):
                result = [{k: item.get(k) for k in step.select} for item in result]
            elif isinstance(result, dict):
                result = {k: result.get(k) for k in step.select}
        if step.save_as:
            context[step.save_as] = result
        context[f"step_{i}"] = result
        results.append(result)
    return results


def list_macros(macro_dir: str) -> list[dict[str, Any]]:
    """Discover all .yaml macro files in a directory."""
    p = Path(macro_dir)
    if not p.exists():
        return []
    return [Macro.from_file(str(f)).to_dict() for f in p.glob("*.yaml")]
