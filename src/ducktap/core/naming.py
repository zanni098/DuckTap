"""Naming and canonicalization.

Mirrors Printing Press's naming rules: convert API verbosity into short,
agent-friendly, deterministic identifiers.
"""
from __future__ import annotations

import re
import unicodedata

_SLUG_RE = re.compile(r"[^a-z0-9]+")
_SNAKE_RE_1 = re.compile(r"(.)([A-Z][a-z]+)")
_SNAKE_RE_2 = re.compile(r"([a-z0-9])([A-Z])")


def slugify(text: str) -> str:
    """Lowercase, ascii, hyphenated — for project & binary names."""
    norm = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return _SLUG_RE.sub("-", norm.lower()).strip("-")


def snake_case(text: str) -> str:
    """API-style operation ids: `listPets` -> `list_pets`, `Foo-Bar` -> `foo_bar`."""
    s = text.replace("-", "_").replace(" ", "_")
    s = _SNAKE_RE_1.sub(r"\1_\2", s)
    s = _SNAKE_RE_2.sub(r"\1_\2", s)
    return s.lower().strip("_")


def kebab_case(text: str) -> str:
    return snake_case(text).replace("_", "-")


def cli_command_name(operation_id: str) -> str:
    """Operation id -> CLI subcommand (kebab-case, short)."""
    return kebab_case(operation_id)


def flag_name(param_name: str) -> str:
    """Parameter name -> long flag (--kebab-case)."""
    return "--" + kebab_case(param_name)


def env_var_name(project: str, suffix: str = "API_KEY") -> str:
    """Suggested env var, e.g. `DUCKTAP_PETSTORE_API_KEY`."""
    return f"{project.upper().replace('-', '_')}_{suffix}"


def operation_id_from_path(method: str, path: str) -> str:
    """Synthesize a stable operation id when the spec omits one.

    GET /pets/{petId}/photos -> get_pets_pet_id_photos
    """
    parts = []
    for seg in path.strip("/").split("/"):
        if not seg:
            continue
        if seg.startswith("{") and seg.endswith("}"):
            parts.append(seg[1:-1])
        else:
            parts.append(seg)
    return snake_case(f"{method.lower()}_{'_'.join(parts)}") or method.lower()
