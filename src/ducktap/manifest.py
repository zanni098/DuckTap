"""Provenance manifest (`.ducktap.json`).

Every ``ducktap press`` run writes a small manifest next to the generated
artifacts capturing *how* the CLI was produced: the source, a checksum of the
normalized spec, the detected archetype, the NOI, the DuckTap version, a
timestamp, and the scorecard grade. ``ducktap info`` reads it back.

This is the deterministic record that makes a generation reproducible and
reviewable -- the same input yields the same manifest (modulo timestamp).
"""
from __future__ import annotations

import datetime
import hashlib
import json
from pathlib import Path
from typing import Any

from ducktap import __version__
from ducktap.core.spec import APISpec

MANIFEST_NAME = ".ducktap.json"
SCHEMA_VERSION = 1


def spec_checksum(spec: APISpec) -> str:
    """Stable sha256 over the normalized spec (excludes volatile manifest bits)."""
    payload = spec.model_dump(by_alias=True, exclude={"insight"})
    blob = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return "sha256:" + hashlib.sha256(blob).hexdigest()


def build_manifest(
    spec: APISpec,
    *,
    targets: list[str] | None = None,
    scorecard_grade: str | None = None,
    scorecard_overall: int | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "name": spec.name,
        "display_name": spec.display_name or spec.name,
        "archetype": spec.archetype,
        "insight": spec.insight,
        "ducktap_version": __version__,
        "generated_at": datetime.datetime.now(datetime.UTC).isoformat(),
        "source": spec.source,
        "spec_checksum": spec_checksum(spec),
        "operation_count": len(spec.operations),
        "auth_env_vars": [s.env_var for s in spec.auth_schemes if s.env_var],
        "targets": targets or [],
        "scorecard": {"overall": scorecard_overall, "grade": scorecard_grade},
    }


def write_manifest(out_dir: str, manifest: dict[str, Any]) -> Path:
    path = Path(out_dir) / MANIFEST_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")
    return path


def read_manifest(out_dir: str) -> dict[str, Any] | None:
    path = Path(out_dir) / MANIFEST_NAME
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
