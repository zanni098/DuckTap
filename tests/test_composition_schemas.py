"""Tests for oneOf / anyOf / allOf composition schemas in OpenAPI discovery (#51)."""

from pathlib import Path

from ducktap.discovery.openapi import OpenAPIDiscoverer
from ducktap.generator.python_cli import cli_params
from ducktap.verify.scorecard import score

FIXTURE_ALLOF = Path(__file__).parent / "fixtures" / "composition_allof.yaml"
FIXTURE_ONEOF = Path(__file__).parent / "fixtures" / "composition_oneof.yaml"


def test_allof_composition_discovery():
    """Verify that allOf merges subschema properties and required fields into typed params."""
    d = OpenAPIDiscoverer()
    assert d.can_handle(str(FIXTURE_ALLOF))
    spec = d.discover(str(FIXTURE_ALLOF))

    ops = {op.operation_id: op for op in spec.operations}
    assert "create_charge" in ops
    charge_op = ops["create_charge"]

    param_map = {p.name: p for p in charge_op.params}
    # Properties from both BaseCharge and inline schema should be present
    assert "amount" in param_map
    assert "currency" in param_map
    assert "idempotency_key" in param_map

    # Check typing and required status
    assert param_map["amount"].type == "integer"
    assert param_map["amount"].required is True
    assert param_map["currency"].type == "string"
    assert param_map["currency"].required is True
    assert param_map["idempotency_key"].type == "string"
    assert param_map["idempotency_key"].required is True

    # Check CLI flag generation
    flags = [p["flag"] for p in cli_params(charge_op)]
    assert "--amount" in flags
    assert "--currency" in flags
    assert "--idempotency-key" in flags


def test_nested_allof_refs_resolution():
    """Verify that nested allOf chains with multiple $ref levels resolve completely."""
    d = OpenAPIDiscoverer()
    spec = d.discover(str(FIXTURE_ALLOF))

    ops = {op.operation_id: op for op in spec.operations}
    assert "create_special_charge" in ops
    special_op = ops["create_special_charge"]

    param_map = {p.name: p for p in special_op.params}
    assert "amount" in param_map
    assert "currency" in param_map
    assert "customer_id" in param_map
    assert "surcharge" in param_map

    assert param_map["amount"].type == "integer"
    assert param_map["customer_id"].type == "string"
    assert param_map["customer_id"].required is True
    assert param_map["surcharge"].type == "number"
    assert param_map["surcharge"].required is False


def test_oneof_polymorphic_discovery():
    """Verify that oneOf with discriminator produces a working operation without crashing."""
    d = OpenAPIDiscoverer()
    assert d.can_handle(str(FIXTURE_ONEOF))
    spec = d.discover(str(FIXTURE_ONEOF))

    ops = {op.operation_id: op for op in spec.operations}
    assert "process_payment" in ops
    pay_op = ops["process_payment"]

    param_names = [p.name for p in pay_op.params]
    assert "method_type" in param_names
    assert "card_number" in param_names

    # Check CLI flag generation does not crash and produces flags
    cli_p = cli_params(pay_op)
    assert len(cli_p) >= 2


def test_scorecard_typed_params_with_composition(tmp_path):
    """Verify that scorecard typed_params accounts for merged composition properties."""
    d = OpenAPIDiscoverer()
    spec = d.discover(str(FIXTURE_ALLOF))

    card = score(spec, str(tmp_path))
    scores_by_dim = {s.dimension: s for s in card.scores}

    assert "typed_params" in scores_by_dim
    # All non-string / typed params are counted properly
    assert scores_by_dim["typed_params"].score > 0
