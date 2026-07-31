"""Naming and canonicalization.

Mirrors Printing Press's naming rules: convert API verbosity into short,
agent-friendly, deterministic identifiers.
"""
from __future__ import annotations

import keyword
import re
import unicodedata
from collections.abc import Iterable

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


def safe_identifier(text: str, *, lang: str = "python") -> str:
    """Identifier that is legal *and* not a reserved word in the target language.

    `snake_case` alone is not enough: an API is free to name an operation
    ``class``, ``import`` or ``type``, and emitting ``def class(...)`` produces
    a generated CLI that will not even parse. Reserved words get a trailing
    underscore, which is the same escape hatch the languages themselves use.
    """
    ident = _NON_IDENT_RE.sub("_", str(text))
    if ident and ident[0].isdigit():
        ident = "_" + ident
    if not ident:
        return "_"
    if lang == "python":
        reserved = keyword.iskeyword(ident) or keyword.issoftkeyword(ident)
    else:
        reserved = ident in _RESERVED_WORDS.get(lang, frozenset())
    return ident + "_" if reserved else ident


# Reserved words for the non-Python generators. Python uses the `keyword`
# module so it stays correct across interpreter versions.
_RESERVED_WORDS: dict[str, frozenset[str]] = {
    "go": frozenset({
        "break", "case", "chan", "const", "continue", "default", "defer", "else",
        "fallthrough", "for", "func", "go", "goto", "if", "import", "interface",
        "map", "package", "range", "return", "select", "struct", "switch", "type", "var",
    }),
    "rust": frozenset({
        "as", "async", "await", "break", "const", "continue", "crate", "dyn", "else",
        "enum", "extern", "false", "fn", "for", "if", "impl", "in", "let", "loop",
        "match", "mod", "move", "mut", "pub", "ref", "return", "self", "static",
        "struct", "super", "trait", "true", "type", "unsafe", "use", "where", "while",
    }),
    "typescript": frozenset({
        "break", "case", "catch", "class", "const", "continue", "debugger", "default",
        "delete", "do", "else", "enum", "export", "extends", "false", "finally", "for",
        "function", "if", "import", "in", "instanceof", "new", "null", "return", "super",
        "switch", "this", "throw", "true", "try", "typeof", "var", "void", "while",
        "with", "let", "static", "yield", "await",
    }),
}


def uniquify(names: Iterable[str]) -> list[str]:
    """Disambiguate a sequence of names in order, appending ``_2``, ``_3``, ...

    Generators turn each name into a symbol (a Click command, a Go function, a
    file on disk). Two identical names mean the second silently overwrites the
    first, so the API surface shrinks without any error being raised.
    """
    seen: dict[str, int] = {}
    out: list[str] = []
    for name in names:
        if name not in seen:
            seen[name] = 1
            out.append(name)
            continue
        while True:
            seen[name] += 1
            candidate = f"{name}_{seen[name]}"
            if candidate not in seen:
                seen[candidate] = 1
                out.append(candidate)
                break
    return out


_PEP440_RE = re.compile(
    r"^\s*v?(\d+(?:\.\d+)*)"                    # release segment
    r"((?:[-_.]?(?:a|b|c|rc|alpha|beta|pre|preview|post|rev|r|dev)[-_.]?\d*)*)"
    r"(?:\+[a-z0-9]+(?:[-_.][a-z0-9]+)*)?\s*$",
    re.IGNORECASE,
)


def pep440_version(text: str, fallback: str = "0.1.0") -> str:
    """Coerce an OpenAPI ``info.version`` into something pip will accept.

    Real specs put all sorts of things here -- Stripe ships ``2022-11-15``,
    others ship ``v1`` or ``1.0-beta``. A non-PEP 440 version makes the
    *generated* package impossible to build or install, so normalize instead of
    passing it straight through.
    """
    raw = str(text or "").strip()
    if not raw:
        return fallback
    if _PEP440_RE.match(raw):
        return raw.lstrip("vV").strip()
    # Date-like versions (2022-11-15) map cleanly onto a release segment.
    digits = re.findall(r"\d+", raw)
    if digits:
        return ".".join(digits[:3])
    return fallback


def semver_version(text: str, fallback: str = "0.1.0") -> str:
    """Coerce a free-form version into ``major.minor.patch``.

    npm and cargo both reject anything else outright, so a generated
    package.json / Cargo.toml carrying a raw ``info.version`` may not build.
    """
    parts = re.findall(r"\d+", pep440_version(text, fallback))
    if not parts:
        return fallback
    parts = (parts + ["0", "0"])[:3]
    return ".".join(parts)


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
