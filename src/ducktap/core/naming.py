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


# Words that are noise in API titles ("Swagger Petstore - OpenAPI 3.0" -> "petstore").
_NAME_NOISE = frozenset({
    "api", "apis", "rest", "restful", "openapi", "swagger", "service",
    "services", "spec", "specs", "v1", "v2", "v3", "v4", "v5",
    "1", "2", "3", "4", "5",
    "0", "00", "30", "20", "10",
    "the", "a", "an", "of", "for", "to", "and", "or",
})


def short_name(title: str, fallback: str = "api") -> str:
    """Best-effort short, agent-friendly slug from a verbose API title.

    The full title is slugified, split on hyphens, and obvious noise
    ("OpenAPI", "v3", "REST", version numbers, ...) is dropped. Up to three
    meaningful tokens are kept.

    >>> short_name("Swagger Petstore - OpenAPI 3.0")
    'petstore'
    >>> short_name("GitHub v3 REST API")
    'github'
    >>> short_name("Stripe API")
    'stripe'
    """
    full = slugify(title)
    if not full:
        return fallback
    parts = [p for p in full.split("-") if p and p not in _NAME_NOISE]
    if not parts:
        # Every token was noise; keep the whole slug rather than returning ""
        return full
    return "-".join(parts[:3])


_NON_IDENT_RE = re.compile(r"[^A-Za-z0-9_]+")


def snake_case(text: str) -> str:
    """API-style operation ids: `listPets` -> `list_pets`, `Foo-Bar` -> `foo_bar`.

    All non-identifier characters (slashes, dots, colons, at-signs, etc.) are
    collapsed to underscores so the result is a legal Python identifier.
    Leading digits are prefixed with `_`.
    """
    s = _SNAKE_RE_1.sub(r"\1_\2", text)
    s = _SNAKE_RE_2.sub(r"\1_\2", s)
    s = _NON_IDENT_RE.sub("_", s)
    s = re.sub(r"__+", "_", s).lower().strip("_")
    if s and s[0].isdigit():
        s = "_" + s
    return s


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
