"""Top-level pipeline: input -> APISpec -> generated artifacts."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ducktap.core import plugins
from ducktap.core.spec import APISpec


@dataclass
class PressResult:
    spec: APISpec
    out_dir: str
    artifacts: dict[str, list[str]] = field(default_factory=dict)


def discover(source: str, *, hint: str | None = None, **opts: Any) -> APISpec:
    """Run discovery. If `hint` is given (e.g. "openapi"), force that discoverer."""
    plugins.autoload_builtins()
    discs = plugins.get_discoverers()
    if hint:
        if hint not in discs:
            raise ValueError(f"unknown discoverer: {hint}. Have: {list(discs)}")
        return discs[hint].discover(source, **opts)
    # priority order
    for name in ("openapi", "graphql", "har", "browser-sniff"):
        d = discs.get(name)
        if d and d.can_handle(source):
            plugins.emit("discovery.start", name=name, source=source)
            spec = d.discover(source, **opts)
            plugins.emit("discovery.done", name=name, spec=spec)
            return spec
    raise ValueError(f"no discoverer can handle: {source}")


def press(
    source: str, out_dir: str, *,
    hint: str | None = None,
    targets: list[str] | None = None,
    name: str | None = None,
    **opts: Any,
) -> PressResult:
    """One-shot: discover then generate all default targets."""
    plugins.autoload_builtins()
    spec = discover(source, hint=hint, name=name, **opts)
    targets = targets or ["python-cli", "mcp-server", "skill"]
    gens = plugins.get_generators()
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    artifacts: dict[str, list[str]] = {}
    for t in targets:
        if t not in gens:
            raise ValueError(f"unknown target: {t}. Have: {list(gens)}")
        plugins.emit("generate.start", target=t, spec=spec)
        files = gens[t].generate(spec, out_dir, **opts)
        plugins.emit("generate.done", target=t, files=files)
        artifacts[t] = files
    return PressResult(spec=spec, out_dir=out_dir, artifacts=artifacts)
