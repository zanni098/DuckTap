"""Non-Obvious Insight (NOI) generation.

A NOI is a one-sentence reframing of an API from "obvious CRUD surface" to
"what the data is *really* a signal about", in the shape:

    "{API} isn't just {obvious}. It's {non-obvious}. Every {data point} is a
     signal about {hidden truth}."

Generation is deterministic by default -- it is driven by the detected domain
archetype, so it runs in CI and needs no API key. If a LiteLLM model is
configured (and reachable) the deterministic NOI is offered to the model as a
seed and its sharper rewrite is used instead; any failure falls back to the
deterministic version.
"""
from __future__ import annotations

from ducktap.core.archetype import detect_archetype
from ducktap.core.spec import APISpec

# Deterministic NOI templates keyed by archetype. {name} is the display name.
_TEMPLATES: dict[str, str] = {
    "project_management": (
        "{name} isn't just an issue tracker. It's a team-behavior observatory. "
        "Every status change is a signal about cycle time, bottlenecks, and who is blocked."
    ),
    "communication": (
        "{name} isn't just a messaging API. It's a record of how a team thinks together. "
        "Every message is a signal about response latency, sentiment, and unanswered threads."
    ),
    "payments": (
        "{name} isn't just a payment processor. It's a revenue observatory. "
        "Every charge is a signal about customer lifetime value, churn risk, and dispute exposure."
    ),
    "infrastructure": (
        "{name} isn't just a control plane. It's a fleet health monitor. "
        "Every resource is a signal about cost drift, region imbalance, and stale deployments."
    ),
    "content": (
        "{name} isn't just a content store. It's a knowledge graph. "
        "Every document is a signal about freshness, ownership, and what nobody maintains anymore."
    ),
    "unknown": (
        "{name} isn't just a set of endpoints. It's a queryable view of a live system. "
        "Every record is a signal about state, freshness, and change over time."
    ),
}

_SYSTEM = (
    "You write a single Non-Obvious Insight (NOI) about an API for AI agents. "
    "Format: '<API> isn't just <obvious thing>. It's <non-obvious thing>. "
    "Every <data point> is a signal about <hidden truth>.' "
    "Be specific to the API. Return ONLY the sentence, no markdown, no quotes."
)


def deterministic_noi(spec: APISpec) -> str:
    """Archetype-driven NOI with no LLM and no network."""
    archetype = spec.archetype if spec.archetype != "unknown" else detect_archetype(spec)
    name = spec.display_name or spec.name
    return _TEMPLATES.get(archetype, _TEMPLATES["unknown"]).format(name=name)


def generate_noi(
    spec: APISpec,
    *,
    override: str | None = None,
    model: str | None = None,
    use_llm: bool = True,
) -> str:
    """Return a NOI for ``spec``.

    Priority: explicit ``override`` > LLM rewrite (if configured) > deterministic.
    """
    if override:
        return override.strip()

    base = deterministic_noi(spec)
    if not use_llm:
        return base

    try:
        from ducktap.llm.base import chat
        top = ", ".join(op.operation_id for op in spec.operations[:8]) or "(none)"
        prompt = (
            f"API: {spec.display_name or spec.name}\n"
            f"Detected archetype: {spec.archetype}\n"
            f"Sample operations: {top}\n"
            f"Seed NOI (improve on this, keep the format): {base}"
        )
        result = chat(prompt, system=_SYSTEM, model=model).strip()
    except Exception:
        return base
    # Guard against an empty or obviously-broken response.
    return result if len(result) > 20 else base
