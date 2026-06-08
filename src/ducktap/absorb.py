"""Ecosystem absorb gate.

Before (or after) generating, ``ducktap absorb <api>`` catalogs the features an
agent-grade CLI for this API is expected to have into an **absorb manifest**.

The baseline is the proven agent-CLI playbook (local mirror, compound commands,
agent-native flags, typed exit codes, ...) -- the features the best community
CLIs and MCP servers converge on. Each is classified ``must_match`` (table
stakes) or ``transcend`` (nice-to-have). When a LiteLLM model is configured and
``crowd_sniff`` returns sources, the manifest is enriched with API-specific
features and novel suggestions; otherwise the deterministic baseline is used so
the gate still runs in CI.

``absorb_check`` verifies a generated CLI against the ``must_match`` features by
scanning its source, so the gate is mechanical, not aspirational.
"""
from __future__ import annotations

import datetime
import re
from pathlib import Path
from typing import Any

_PLAYBOOK = "agent-cli-playbook"
_PLAYBOOK_URL = "https://github.com/steipete/gogcli"

# Baseline features + a regex that, if found anywhere in the generated CLI
# source, counts as "matched". priority: must_match | transcend.
_BASELINE: list[dict[str, Any]] = [
    {"feature": "agent-context self-introspection", "priority": "must_match",
     "evidence": r"agent-context"},
    {"feature": "typed exit codes", "priority": "must_match",
     "evidence": r"exit_code|EXIT_CODES|sys\.exit\(3\)|exit=3"},
    {"feature": "dry-run flag", "priority": "must_match",
     "evidence": r"dry[-_]run"},
    {"feature": "JSON-first / --agent output", "priority": "must_match",
     "evidence": r"--agent|\bjson\b"},
    {"feature": "auth from environment variables", "priority": "must_match",
     "evidence": r"environ|getenv|os\.environ|env="},
    {"feature": "local SQLite mirror", "priority": "transcend",
     "evidence": r"sqlite3|mirror"},
    {"feature": "compound query commands", "priority": "transcend",
     "evidence": r"\bstale\b|\bhealth\b|bottleneck"},
    {"feature": "auth-doctor", "priority": "transcend",
     "evidence": r"auth-doctor|auth_doctor"},
    {"feature": "saved profiles", "priority": "transcend",
     "evidence": r"profile"},
]


def build_absorb_manifest(
    api_name: str,
    *,
    model: str | None = None,
    use_llm: bool = True,
) -> dict[str, Any]:
    """Catalog expected features for ``api_name``.

    Always includes the deterministic baseline; enriches with crowd-sniffed,
    LLM-summarized sources when available.
    """
    features = [
        {
            "feature": f["feature"],
            "priority": f["priority"],
            "source_tool": _PLAYBOOK,
            "source_url": _PLAYBOOK_URL,
        }
        for f in _BASELINE
    ]
    sources: list[dict[str, str]] = []
    novel: list[str] = []

    if use_llm:
        try:
            from ducktap.crowd_sniff import crowd_sniff
            res = crowd_sniff(api_name, model=model)
            sources = res.get("sources", [])
            if res.get("summary"):
                novel.append(res["summary"].strip()[:500])
        except Exception:
            pass

    return {
        "api": api_name,
        "generated_at": datetime.datetime.now(datetime.UTC).isoformat(),
        "features": features,
        "novel_suggestions": novel,
        "sources": sources,
    }


def _gather_source_text(out_dir: str, name: str) -> str:
    """Concatenate generated CLI source for the given API for scanning."""
    root = Path(out_dir)
    chunks: list[str] = []
    for sub in (f"{name}-dt-cli", f"{name}-dt-go", f"{name}-dt-rs", f"{name}-dt-ts"):
        d = root / sub
        if not d.exists():
            continue
        for f in d.rglob("*"):
            if f.is_file() and f.suffix in {".py", ".go", ".rs", ".ts"}:
                try:
                    chunks.append(f.read_text(encoding="utf-8", errors="ignore"))
                except OSError:
                    continue
    return "\n".join(chunks)


def absorb_check(out_dir: str, name: str, manifest: dict[str, Any]) -> dict[str, Any]:
    """Check a generated CLI against the manifest's ``must_match`` features.

    Returns ``{matched, missing, passed}`` where ``passed`` is True iff every
    ``must_match`` feature has evidence in the generated source.
    """
    text = _gather_source_text(out_dir, name)
    evidence = {f["feature"]: f["evidence"] for f in _BASELINE}
    matched: list[str] = []
    missing: list[str] = []
    for feat in manifest.get("features", []):
        if feat.get("priority") != "must_match":
            continue
        pat = evidence.get(feat["feature"])
        if pat and re.search(pat, text, re.IGNORECASE):
            matched.append(feat["feature"])
        else:
            missing.append(feat["feature"])
    return {"matched": matched, "missing": missing, "passed": not missing}
