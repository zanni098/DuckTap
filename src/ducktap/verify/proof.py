"""Proof of behavior — mechanical checks that a generated CLI actually does
what the spec says, not just that it parses.

Four deterministic proofs run against the APISpec and the generated Python CLI
source:

* **Path Proof**  — every request path baked into the generated commands exists
  in the spec (catches hallucinated / stale endpoints).
* **Coverage Proof** — every spec operation is reachable as a generated command.
* **Auth Proof**  — the auth header in the generated client matches the spec's
  auth scheme type (Bearer for http/oauth2, the named header for apiKey).
* **Pipeline Proof** — every mirror table that is written is also read by at
  least one query/search path (no write-only dead tables).

`ducktap verify <name>` runs all four and emits a structured JSON report.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path

from ducktap.core.spec import APISpec


@dataclass
class Proof:
    name: str
    passed: bool
    detail: str = ""
    offenders: list[str] | None = None


@dataclass
class ProofReport:
    name: str
    passed: bool
    proofs: list[Proof]

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "passed": self.passed,
            "proofs": [asdict(p) for p in self.proofs],
        }


def _cli_pkg(out_dir: str, name: str) -> Path:
    return Path(out_dir) / f"{name}-dt-cli" / f"{name}_dt_cli".replace("-", "_")


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def path_proof(spec: APISpec, commands_src: str) -> Proof:
    """Every `path = "..."` literal in the generated commands is a real spec path."""
    spec_paths = {op.path for op in spec.operations}
    referenced = set(re.findall(r'path\s*=\s*"([^"]+)"', commands_src))
    # only consider path-template literals (start with "/")
    referenced = {p for p in referenced if p.startswith("/")}
    hallucinated = sorted(p for p in referenced if p not in spec_paths)
    return Proof(
        "path_proof", not hallucinated,
        f"{len(referenced)} command paths, {len(hallucinated)} not in spec"
        if referenced else "no command paths found",
        offenders=hallucinated or None,
    )


def coverage_proof(spec: APISpec, commands_src: str) -> Proof:
    """Every spec operation_id appears as a generated command handler."""
    missing = sorted(
        op.operation_id for op in spec.operations
        if op.operation_id not in commands_src
    )
    return Proof(
        "coverage_proof", not missing,
        f"{len(spec.operations) - len(missing)}/{len(spec.operations)} operations exposed",
        offenders=missing or None,
    )


def auth_proof(spec: APISpec, client_src: str) -> Proof:
    """The generated client's auth header matches the spec's auth scheme type."""
    if not spec.auth_schemes:
        return Proof("auth_proof", True, "no auth schemes to verify")
    problems: list[str] = []
    for s in spec.auth_schemes:
        if s.type in ("http", "oauth2", "openIdConnect"):
            if "Bearer" not in client_src and "Authorization" not in client_src:
                problems.append(f"{s.name}: expected Bearer/Authorization header")
        elif s.type == "apiKey":
            header = s.parameter_name or "X-API-Key"
            if header not in client_src:
                problems.append(f"{s.name}: expected header {header!r}")
    return Proof(
        "auth_proof", not problems,
        f"{len(spec.auth_schemes)} scheme(s) checked, {len(problems)} mismatch(es)",
        offenders=problems or None,
    )


def pipeline_proof(mirror_src: str) -> Proof:
    """Every table created in the mirror is also read by a SELECT somewhere."""
    created = set(re.findall(r"CREATE TABLE IF NOT EXISTS (\w+)", mirror_src))
    # FROM <table> or JOIN <table> or INTO <table> (writes counted separately)
    read = set(re.findall(r"(?:FROM|JOIN)\s+(\w+)", mirror_src))
    write_only = sorted(t for t in created if t not in read and not t.endswith("_fts"))
    return Proof(
        "pipeline_proof", not write_only,
        f"{len(created)} tables, {len(write_only)} write-only",
        offenders=write_only or None,
    )


def verify(spec: APISpec, out_dir: str, name: str) -> ProofReport:
    pkg = _cli_pkg(out_dir, name)
    commands_src = _read(pkg / "commands.py")
    client_src = _read(pkg / "client.py")
    mirror_src = _read(pkg / "mirror.py")
    proofs = [
        path_proof(spec, commands_src),
        coverage_proof(spec, commands_src),
        auth_proof(spec, client_src),
        pipeline_proof(mirror_src),
    ]
    return ProofReport(name=name, passed=all(p.passed for p in proofs), proofs=proofs)
