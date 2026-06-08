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
    manifest: dict[str, Any] = field(default_factory=dict)


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
    archetype: str | None = None,
    insight: str | None = None,
    use_llm: bool = True,
    **opts: Any,
) -> PressResult:
    """One-shot: discover then generate all default targets.

    Phase 0 (Creative Layer): detect the domain archetype and generate a
    Non-Obvious Insight before generation, then write a `.ducktap.json`
    provenance manifest alongside the artifacts.
    """
    plugins.autoload_builtins()
    spec = discover(source, hint=hint, name=name, **opts)

    # Phase 0: archetype + NOI
    from ducktap.core.archetype import detect_archetype
    from ducktap.insight import generate_noi
    spec.archetype = archetype or detect_archetype(spec)
    spec.insight = generate_noi(spec, override=insight, use_llm=use_llm)

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

    # Provenance manifest (best-effort; never fail the press over it).
    manifest: dict[str, Any] = {}
    try:
        from ducktap.manifest import build_manifest, write_manifest
        from ducktap.verify.scorecard import score
        sc = score(spec, out_dir)
        manifest = build_manifest(
            spec, targets=list(targets),
            scorecard_grade=sc.grade, scorecard_overall=sc.overall,
        )
        write_manifest(out_dir, manifest)
    except Exception as e:  # noqa: BLE001
        plugins.emit("manifest.error", error=e)

    return PressResult(spec=spec, out_dir=out_dir, artifacts=artifacts, manifest=manifest)
