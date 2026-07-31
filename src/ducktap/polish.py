"""LLM-assisted polish and rename for APISpecs.

`ducktap polish`  – rewrite operation summaries / descriptions to be
agent-friendly (concise, action-oriented, no marketing fluff).

`ducktap rename`   – suggest better operation_ids for unwieldy or
auto-generated names so agents can guess them more easily.
"""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from ducktap.core.spec import APISpec, Operation
from ducktap.llm.base import chat

DEFAULT_POLISH_SYSTEM = (
    "You are a technical editor that rewrites API operation descriptions "
    "for AI agents. Keep descriptions under 120 chars, action-oriented, "
    "and free of marketing language. Return ONLY the rewritten text, "
    "no markdown, no quotes."
)

DEFAULT_RENAME_SYSTEM = (
    "You are a CLI designer. Given an API operation, suggest a short, "
    "memorable, snake_case operation_id that an AI agent could guess from "
    "the path and method. Avoid abbreviations. Return ONLY the new id, "
    "no explanation."
)


def _operation_prompt(op: Operation) -> str:
    return (
        f"Method: {op.method}\n"
        f"Path: {op.path}\n"
        f"Current summary: {op.summary}\n"
        f"Current description: {op.description}\n"
        f"Rewrite the summary (and description if it adds value)."
    )


def _rename_prompt(op: Operation) -> str:
    return (
        f"Method: {op.method}\n"
        f"Path: {op.path}\n"
        f"Current operationId: {op.operation_id}\n"
        f"Summary: {op.summary}\n"
        f"Suggest a better snake_case operation_id."
    )


def _load_spec(source: str) -> APISpec:
    if source.endswith(".json") and Path(source).exists():
        return APISpec.model_validate_json(Path(source).read_text(encoding="utf-8"))
    from ducktap.core.pipeline import discover
    return discover(source)


def polish(
    source: str,
    *,
    model: str | None = None,
    out_json: Path | None = None,
    descriptions_only: bool = False,
    concurrency: int = 8,
) -> APISpec:
    """Rewrite operation summaries / descriptions via LLM.

    One request per operation, issued in parallel: a 300-operation spec run
    serially is 300 sequential round trips. Any operation whose request fails
    (no litellm, no API key, rate limit, ...) simply keeps its original text --
    a partial polish is far more useful than an aborted one.
    """
    spec = _load_spec(source)

    def _polish_one(op: Operation) -> None:
        try:
            result = chat(_operation_prompt(op), system=DEFAULT_POLISH_SYSTEM, model=model)
        except Exception:  # noqa: BLE001 - provider errors vary wildly
            return
        # Split result into summary (first line) and description (rest)
        lines = [ln.strip() for ln in result.strip().splitlines() if ln.strip()]
        if lines:
            op.summary = lines[0][:120]
            if not descriptions_only and len(lines) > 1:
                op.description = " ".join(lines[1:])[:500]

    if spec.operations:
        with ThreadPoolExecutor(max_workers=max(1, concurrency)) as pool:
            list(pool.map(_polish_one, spec.operations))
    if out_json:
        out_json.write_text(
            json.dumps(spec.model_dump(by_alias=True), indent=2, default=str),
            encoding="utf-8",
        )
    return spec


def rename(
    source: str,
    *,
    model: str | None = None,
    out_json: Path | None = None,
    dry_run: bool = False,
) -> dict[str, str]:
    """Suggest better operation_ids via LLM.  Returns {old: new} mapping."""
    spec = _load_spec(source)
    mapping: dict[str, str] = {}
    # A model happily suggests `list_items` for two different operations; the
    # generators would then emit one command and drop the other.
    taken = {op.operation_id for op in spec.operations}
    for op in spec.operations:
        # Skip already-clean names (short, no numeric suffixes, readable)
        if len(op.operation_id) < 25 and "_" in op.operation_id and not op.operation_id.endswith("_0"):
            continue
        prompt = _rename_prompt(op)
        try:
            new_id = chat(prompt, system=DEFAULT_RENAME_SYSTEM, model=model).strip()
        except Exception:  # noqa: BLE001 - provider errors vary wildly
            continue
        # Sanity: must be valid snake_case and different from current
        new_id = new_id.replace(" ", "_").replace("-", "_").lower()
        new_id = "".join(c if c.isalnum() or c == "_" else "_" for c in new_id).strip("_")
        if new_id and new_id != op.operation_id and not new_id[0].isdigit() \
                and new_id not in taken:
            taken.discard(op.operation_id)
            taken.add(new_id)
            mapping[op.operation_id] = new_id
            if not dry_run:
                op.operation_id = new_id
    if out_json:
        out_json.write_text(
            json.dumps(spec.model_dump(by_alias=True), indent=2, default=str),
            encoding="utf-8",
        )
    return mapping
