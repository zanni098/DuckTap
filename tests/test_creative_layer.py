"""Tests for the v0.7.x Creative Layer: archetype, NOI, manifest, absorb."""
from __future__ import annotations

import json
from pathlib import Path

from ducktap.absorb import absorb_check, build_absorb_manifest
from ducktap.core.archetype import ARCHETYPES, detect_archetype
from ducktap.core.pipeline import press
from ducktap.core.spec import APISpec, Operation, Param
from ducktap.insight import deterministic_noi, generate_noi
from ducktap.manifest import build_manifest, read_manifest, spec_checksum

FIXTURE = Path(__file__).parent / "fixtures" / "petstore.yaml"


def _op(op_id, path, method="GET", params=None):
    return Operation(
        operation_id=op_id, method=method, path=path,
        params=[Param(name=n, location="query") for n in (params or [])],
    )


def _spec(name, ops):
    return APISpec(name=name, display_name=name, operations=ops)


# --------------------------------------------------------------------------- #
# Archetype detection
# --------------------------------------------------------------------------- #

def test_detect_project_management():
    spec = _spec("linear", [
        _op("list_issues", "/issues", params=["assignee", "priority", "status"]),
        _op("get_issue", "/issues/{id}"),
        _op("list_sprints", "/sprints"),
        _op("create_ticket", "/tickets", "POST", params=["label"]),
    ])
    assert detect_archetype(spec) == "project_management"


def test_detect_payments():
    spec = _spec("stripe", [
        _op("list_charges", "/charges", params=["amount", "currency", "customer"]),
        _op("create_invoice", "/invoices", "POST"),
        _op("list_refunds", "/refunds"),
        _op("get_payout", "/payouts/{id}"),
    ])
    assert detect_archetype(spec) == "payments"


def test_detect_communication():
    spec = _spec("slack", [
        _op("list_messages", "/messages", params=["author", "thread", "body"]),
        _op("list_channels", "/channels"),
        _op("post_message", "/messages", "POST"),
    ])
    assert detect_archetype(spec) == "communication"


def test_detect_unknown_for_sparse_spec():
    spec = _spec("weird", [_op("ping", "/ping"), _op("pong", "/pong")])
    assert detect_archetype(spec) == "unknown"


def test_petstore_detects_a_valid_archetype():
    from ducktap.core.pipeline import discover
    spec = discover(str(FIXTURE), name="petstore")
    assert detect_archetype(spec) in (*ARCHETYPES, "unknown")


# --------------------------------------------------------------------------- #
# Non-Obvious Insight
# --------------------------------------------------------------------------- #

def test_deterministic_noi_uses_archetype_template():
    spec = _spec("Stripe", [_op("list_charges", "/charges", params=["amount"])])
    spec.archetype = "payments"
    noi = deterministic_noi(spec)
    assert "Stripe" in noi
    assert "revenue observatory" in noi


def test_generate_noi_respects_override():
    spec = _spec("x", [_op("a", "/a")])
    assert generate_noi(spec, override="My custom insight.", use_llm=False) == "My custom insight."


def test_generate_noi_is_deterministic_without_llm():
    spec = _spec("Acme", [_op("list_documents", "/documents", params=["content", "title"])])
    spec.archetype = "content"
    a = generate_noi(spec, use_llm=False)
    b = generate_noi(spec, use_llm=False)
    assert a == b and "Acme" in a


# --------------------------------------------------------------------------- #
# Provenance manifest
# --------------------------------------------------------------------------- #

def test_manifest_checksum_is_stable_and_excludes_insight():
    spec = _spec("petstore", [_op("a", "/a")])
    c1 = spec_checksum(spec)
    spec.insight = "anything at all"   # excluded from checksum
    assert spec_checksum(spec) == c1


def test_build_manifest_has_core_fields():
    spec = _spec("petstore", [_op("a", "/a")])
    spec.archetype = "content"
    spec.insight = "noi"
    m = build_manifest(spec, targets=["python-cli"], scorecard_grade="B", scorecard_overall=85)
    assert m["name"] == "petstore"
    assert m["archetype"] == "content"
    assert m["insight"] == "noi"
    assert m["targets"] == ["python-cli"]
    assert m["scorecard"] == {"overall": 85, "grade": "B"}
    assert m["spec_checksum"].startswith("sha256:")


# --------------------------------------------------------------------------- #
# Press integration: manifest written, archetype + NOI set
# --------------------------------------------------------------------------- #

def test_press_writes_manifest_and_sets_creative_fields(tmp_path):
    out = tmp_path / "out"
    result = press(str(FIXTURE), str(out), name="petstore",
                   targets=["python-cli"], use_llm=False)
    assert result.spec.archetype in (*ARCHETYPES, "unknown")
    assert result.spec.insight  # non-empty NOI
    manifest = read_manifest(str(out))
    assert manifest is not None
    assert manifest["name"] == "petstore"
    assert manifest["insight"] == result.spec.insight
    assert manifest["archetype"] == result.spec.archetype
    assert manifest["operation_count"] == len(result.spec.operations)


def test_press_insight_override(tmp_path):
    out = tmp_path / "out"
    result = press(str(FIXTURE), str(out), name="petstore",
                   targets=["python-cli"], insight="Forced NOI.", use_llm=False)
    assert result.spec.insight == "Forced NOI."
    assert read_manifest(str(out))["insight"] == "Forced NOI."


# --------------------------------------------------------------------------- #
# Absorb gate
# --------------------------------------------------------------------------- #

def test_absorb_manifest_has_must_match_baseline():
    m = build_absorb_manifest("stripe", use_llm=False)
    must = [f for f in m["features"] if f["priority"] == "must_match"]
    assert len(must) >= 4
    assert all("source_tool" in f for f in m["features"])


def test_absorb_check_passes_on_generated_python_cli(tmp_path):
    out = tmp_path / "out"
    press(str(FIXTURE), str(out), name="petstore", targets=["python-cli"], use_llm=False)
    manifest = build_absorb_manifest("petstore", use_llm=False)
    result = absorb_check(str(out), "petstore", manifest)
    assert result["passed"], f"missing must_match features: {result['missing']}"


def test_absorb_check_fails_on_empty_dir(tmp_path):
    manifest = build_absorb_manifest("petstore", use_llm=False)
    result = absorb_check(str(tmp_path), "petstore", manifest)
    assert not result["passed"]
    assert manifest  # sanity


def test_absorb_manifest_serializes(tmp_path):
    m = build_absorb_manifest("petstore", use_llm=False)
    p = tmp_path / "absorb.json"
    p.write_text(json.dumps(m, indent=2))
    assert json.loads(p.read_text())["api"] == "petstore"
