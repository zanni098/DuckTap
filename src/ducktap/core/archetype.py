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
from typing import NamedTuple

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

# A raw score is not enough on its own: a single ambiguous keyword repeated
# across one resource can clear _MIN_SCORE by itself. The Swagger Petstore, for
# example, scored 13 for "payments" -- 12 of which came from the word "order"
# in `/store/order`. To commit to an archetype we also require the evidence to
# be *spread out*: several different keywords must fire, and no single keyword
# may account for nearly all of the score.
#
# Calibrated against real specs (see tests/test_archetype_calibration.py):
#   stripe   payments           score=1610 distinct=19 concentration=0.20  -> keep
#   github   project_management score= 949 distinct=10 concentration=0.53  -> keep
#   petstore payments           score=  13 distinct= 2 concentration=0.92  -> reject
_MIN_DISTINCT_SIGNALS = 3
_MAX_SIGNAL_CONCENTRATION = 0.8

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


class Evidence(NamedTuple):
    """How strongly -- and how broadly -- one archetype matched a spec."""

    score: int
    """Weighted keyword score (resource hits count double)."""
    distinct: int
    """How many different keywords fired at least once."""
    top_points: int
    """Points contributed by the single highest-scoring keyword."""

    @property
    def concentration(self) -> float:
        """Share of the score owed to one keyword (1.0 = a single keyword)."""
        return self.top_points / self.score if self.score else 0.0

    def is_conclusive(self) -> bool:
        """True when the evidence is strong *and* spread across keywords."""
        return (
            self.score >= _MIN_SCORE
            and self.distinct >= _MIN_DISTINCT_SIGNALS
            and self.concentration <= _MAX_SIGNAL_CONCENTRATION
        )


def archetype_evidence(spec: APISpec) -> dict[str, Evidence]:
    """Per-archetype match evidence: score, keyword spread, and concentration."""
    resource_text = " ".join(
        [op.path for op in spec.operations]
        + [op.operation_id for op in spec.operations]
        + [t for op in spec.operations for t in op.tags]
    )
    field_text = " ".join(p.name for op in spec.operations for p in op.params)
    resource_tokens = _tokens(resource_text)
    field_tokens = _tokens(field_text)

    evidence: dict[str, Evidence] = {}
    for archetype in ARCHETYPES:
        score = distinct = top_points = 0
        for kw, tokens, weight in (
            *((k, resource_tokens, 2) for k in _RESOURCE_SIGNALS[archetype]),
            *((k, field_tokens, 1) for k in _FIELD_SIGNALS[archetype]),
        ):
            points = weight * _count(tokens, kw)
            if points:
                score += points
                distinct += 1
                top_points = max(top_points, points)
        evidence[archetype] = Evidence(score, distinct, top_points)
    return evidence


def archetype_scores(spec: APISpec) -> dict[str, int]:
    """Weighted match score per archetype (resource hits count double)."""
    return {a: e.score for a, e in archetype_evidence(spec).items()}


def detect_archetype(spec: APISpec) -> str:
    """Return the best-matching archetype, or ``"unknown"`` if none is clear.

    An archetype is only returned when its evidence is conclusive: a high
    enough score, drawn from several distinct keywords, and not dominated by
    any single one. Anything less stays ``"unknown"`` -- a generic CRUD API
    should not be described as a payment processor because it happens to have
    an ``/order`` endpoint.
    """
    evidence = archetype_evidence(spec)
    best = max(ARCHETYPES, key=lambda a: evidence[a].score)
    return best if evidence[best].is_conclusive() else "unknown"


# Natural-language / FTS text column for each archetype's primary resource.
ARCHETYPE_TEXT_COLUMN: dict[str, str] = {
    "project_management": "title",
    "communication": "content",
    "payments": "description",
    "infrastructure": "name",
    "content": "content",
}
