"""Plugin registry.

DuckTap is extensible: discovery sources, code generators, output formats, and
LLM providers are all plugins. Plugins register either by importing this module
and calling `register_*`, or via Python entry points in the `ducktap.plugins`
group.
"""
from __future__ import annotations

from collections.abc import Callable
from importlib.metadata import entry_points
from typing import Any, Protocol

from ducktap.core.spec import APISpec


class Discoverer(Protocol):
    """A plugin that converts some input into an APISpec."""

    name: str

    def can_handle(self, source: str) -> bool: ...
    def discover(self, source: str, **opts: Any) -> APISpec: ...


class Generator(Protocol):
    """A plugin that consumes an APISpec and writes files to an output dir."""

    name: str
    target: str   # e.g. "python-cli", "mcp-server", "claude-skill"

    def generate(self, spec: APISpec, out_dir: str, **opts: Any) -> list[str]: ...


_discoverers: dict[str, Discoverer] = {}
_generators: dict[str, Generator] = {}
_hooks: dict[str, list[Callable[..., Any]]] = {}


def register_discoverer(d: Discoverer) -> Discoverer:
    _discoverers[d.name] = d
    return d


def register_generator(g: Generator) -> Generator:
    _generators[g.name] = g
    return g


def register_hook(event: str, fn: Callable[..., Any]) -> None:
    _hooks.setdefault(event, []).append(fn)


def get_discoverers() -> dict[str, Discoverer]:
    _load_entry_points()
    return dict(_discoverers)


def get_generators() -> dict[str, Generator]:
    _load_entry_points()
    return dict(_generators)


def emit(event: str, *args: Any, **kwargs: Any) -> None:
    for fn in _hooks.get(event, []):
        try:
            fn(*args, **kwargs)
        except Exception as e:  # noqa: BLE001
            # Plugin failures must not crash the pipeline.
            import logging
            logging.getLogger("ducktap.plugins").warning("hook %s failed: %s", event, e)


_loaded = False


def _load_entry_points() -> None:
    global _loaded
    if _loaded:
        return
    _loaded = True
    try:
        eps = entry_points(group="ducktap.plugins")
    except Exception:
        return
    for ep in eps:
        try:
            ep.load()  # plugin module registers on import
        except Exception as e:  # noqa: BLE001
            import logging
            logging.getLogger("ducktap.plugins").warning("failed to load %s: %s", ep.name, e)


def autoload_builtins() -> None:
    """Import built-in plugins so they register themselves."""
    # Discoverers
    from ducktap.discovery import browser_sniff as _b  # noqa: F401
    from ducktap.discovery import har as _h  # noqa: F401
    from ducktap.discovery import openapi as _o  # noqa: F401

    # Generators
    from ducktap.generator import go_cli as _go  # noqa: F401
    from ducktap.generator import mcp_server as _mcp  # noqa: F401
    from ducktap.generator import python_cli as _pc  # noqa: F401
    from ducktap.generator import rust_cli as _rs  # noqa: F401
    from ducktap.generator import skill as _s  # noqa: F401
    from ducktap.generator import typescript_cli as _ts  # noqa: F401
