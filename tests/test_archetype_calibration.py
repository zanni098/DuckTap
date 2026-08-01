"""Calibration tests for archetype detection (regression cover for #38).

Archetype detection is a keyword heuristic, and a keyword heuristic will
confidently mislabel a spec whenever one ambiguous word repeats. These tests
pin the calibration that stops that: an archetype is only committed to when the
evidence is strong *and* spread across several distinct keywords.

The reference numbers in ``archetype.py`` were measured against live Stripe and
GitHub specs. Those are too large and too networked for CI, so the shapes they
represent are reproduced here with synthetic specs plus the offline Petstore
fixture.
"""
from __future__ import annotations

from pathlib import Path

from ducktap.core.archetype import (
    _MAX_SIGNAL_CONCENTRATION,
    _MIN_DISTINCT_SIGNALS,
    Evidence,
    archetype_evidence,
    detect_archetype,
)
from ducktap.core.pipeline import discover
from ducktap.core.spec import APISpec, Operation, Param
from ducktap.insight import deterministic_noi

FIXTURE = Path(__file__).parent / "fixtures" / "petstore.yaml"


def _op(op_id, path, method="GET", params=None):
    return Operation(
        operation_id=op_id, method=method, path=path,
        params=[Param(name=n, location="query") for n in (params or [])],
    )


def _spec(name, ops):
    return APISpec(name=name, display_name=name, operations=ops)


# --------------------------------------------------------------------------- #
# The #38 regression: Petstore must not be called a payment processor
# --------------------------------------------------------------------------- #

def test_petstore_is_not_classified_as_payments():
    """The bug in #38: `/store/order` alone made Petstore a "payments" API."""
    spec = discover(str(FIXTURE), name="petstore")
    assert detect_archetype(spec) == "unknown"


def test_petstore_payments_evidence_is_concentrated_in_one_keyword():
    """Documents *why* Petstore was misread: ~all of its score is one word."""
    spec = discover(str(FIXTURE), name="petstore")
    payments = archetype_evidence(spec)["payments"]

    # Strong enough on raw score alone -- which is exactly why score is not
    # a sufficient test.
    assert payments.score >= 13
    # ...but drawn from almost nothing: "order", plus a single "quantity".
    assert payments.distinct < _MIN_DISTINCT_SIGNALS
    assert payments.concentration > _MAX_SIGNAL_CONCENTRATION


def test_petstore_noi_makes_no_domain_claim():
    """The user-visible symptom: no "revenue observatory" prose for a pet store."""
    spec = discover(str(FIXTURE), name="petstore")
    spec.archetype = detect_archetype(spec)
    noi = deterministic_noi(spec)

    for forbidden in ("payment processor", "revenue observatory", "charge"):
        assert forbidden not in noi.lower()


# --------------------------------------------------------------------------- #
# Broad evidence still classifies (no false negatives)
# --------------------------------------------------------------------------- #

def test_broad_payments_evidence_still_detected():
    """Stripe's shape: many different payment keywords, none dominant."""
    spec = _spec("stripe", [
        _op("list_charges", "/charges", params=["amount", "currency"]),
        _op("create_invoice", "/invoices", "POST", params=["customer"]),
        _op("list_refunds", "/refunds"),
        _op("get_payout", "/payouts/{id}"),
        _op("list_disputes", "/disputes", params=["fee"]),
        _op("get_balance", "/balance"),
    ])
    evidence = archetype_evidence(spec)["payments"]

    assert evidence.distinct >= _MIN_DISTINCT_SIGNALS
    assert evidence.concentration <= _MAX_SIGNAL_CONCENTRATION
    assert detect_archetype(spec) == "payments"


def test_repeating_one_keyword_never_reaches_a_verdict():
    """A single word repeated any number of times stays inconclusive."""
    spec = _spec("orders", [
        _op(f"get_order_{i}", f"/orders/{i}") for i in range(40)
    ])
    evidence = archetype_evidence(spec)["payments"]

    assert evidence.score > 50  # trivially clears the old score-only gate
    assert evidence.distinct == 1
    assert detect_archetype(spec) == "unknown"


# --------------------------------------------------------------------------- #
# Evidence arithmetic
# --------------------------------------------------------------------------- #

def test_evidence_concentration_is_zero_for_an_empty_match():
    assert Evidence(score=0, distinct=0, top_points=0).concentration == 0.0


def test_evidence_requires_all_three_conditions():
    # Strong, broad, well spread -> conclusive.
    assert Evidence(score=20, distinct=5, top_points=6).is_conclusive()
    # Too weak overall.
    assert not Evidence(score=2, distinct=5, top_points=1).is_conclusive()
    # Strong but too few distinct keywords.
    assert not Evidence(score=20, distinct=2, top_points=6).is_conclusive()
    # Strong and broad, but one keyword dominates.
    assert not Evidence(score=20, distinct=5, top_points=19).is_conclusive()
