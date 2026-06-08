"""Domain archetype detection.

Classifies an :class:`~ducktap.core.spec.APISpec` into one of five archetypes
based on resource names (paths / tags / operation ids) and field names
(parameters). The detected archetype drives Non-Obvious Insight generation
(``ducktap insight``) and the typed per-resource SQLite tables emitted into
generated CLIs.

Detection is deterministic -- no LLM, no network -- so it runs in CI and
produces the same archetype for the same spec every time.
"""
from __future__ import annotations

import re
from collections import Counter

from ducktap.core.spec import APISpec

ARCHETYPES = (
    "project_management",
    "communication",
    "payments",
    "infrastructure",
    "content",
)

# Minimum weighted score before we commit to an archetype (else "unknown").
_MIN_SCORE = 4

# Resource keywords, matched against path segments / tags / operation ids.
_RESOURCE_SIGNALS: dict[str, list[str]] = {
    "project_management": [
        "issue", "task", "ticket", "project", "epic", "sprint", "board",
        "milestone", "backlog", "story", "workflow",
    ],
    "communication": [
        "message", "channel", "thread", "conversation", "chat", "dm",
        "comment", "inbox", "reply", "mention",
    ],
    "payments": [
        "charge", "payment", "invoice", "transaction", "refund", "payout",
        "subscription", "balance", "order", "checkout", "dispute",
    ],
    "infrastructure": [
        "server", "deploy", "instance", "cluster", "node", "container",
        "droplet", "volume", "network", "deployment", "region",
    ],
    "content": [
        "document", "page", "block", "article", "asset", "media",
        "folder", "note", "wiki", "file", "post",
    ],
}

# Field keywords, matched against parameter names.
_FIELD_SIGNALS: dict[str, list[str]] = {
    "project_management": [
        "assignee", "priority", "status", "state", "label", "due",
        "estimate", "reporter",
    ],
    "communication": [
        "author", "timestamp", "thread", "body", "recipient", "sender",
        "unread", "subject",
    ],
    "payments": [
        "amount", "currency", "customer", "card", "total", "price",
        "quantity", "fee",
    ],
    "infrastructure": [
        "region", "hostname", "ip", "size", "image", "zone", "memory", "cpu",
    ],
    "content": [
        "content", "body", "title", "version", "slug", "parent",
        "published", "draft",
    ],
}


def _tokens(text: str) -> Counter[str]:
    return Counter(t for t in re.split(r"[^a-z]+", text.lower()) if t)


def _count(tokens: Counter[str], keyword: str) -> int:
    """Count a keyword and its naive plural ("issue" + "issues")."""
    return tokens.get(keyword, 0) + tokens.get(keyword + "s", 0)


def archetype_scores(spec: APISpec) -> dict[str, int]:
    """Weighted match score per archetype (resource hits count double)."""
    resource_text = " ".join(
        [op.path for op in spec.operations]
        + [op.operation_id for op in spec.operations]
        + [t for op in spec.operations for t in op.tags]
    )
    field_text = " ".join(p.name for op in spec.operations for p in op.params)
    resource_tokens = _tokens(resource_text)
    field_tokens = _tokens(field_text)

    scores: dict[str, int] = {a: 0 for a in ARCHETYPES}
    for archetype in ARCHETYPES:
        for kw in _RESOURCE_SIGNALS[archetype]:
            scores[archetype] += 2 * _count(resource_tokens, kw)
        for kw in _FIELD_SIGNALS[archetype]:
            scores[archetype] += 1 * _count(field_tokens, kw)
    return scores


def detect_archetype(spec: APISpec) -> str:
    """Return the best-matching archetype, or ``"unknown"`` if none is clear."""
    scores = archetype_scores(spec)
    best = max(ARCHETYPES, key=lambda a: scores[a])
    return best if scores[best] >= _MIN_SCORE else "unknown"


# Natural-language / FTS text column for each archetype's primary resource.
ARCHETYPE_TEXT_COLUMN: dict[str, str] = {
    "project_management": "title",
    "communication": "content",
    "payments": "description",
    "infrastructure": "name",
    "content": "content",
}
