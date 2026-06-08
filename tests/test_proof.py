"""Proof of behavior tests."""
from __future__ import annotations

from pathlib import Path

from ducktap.core.pipeline import discover, press
from ducktap.core.spec import APISpec, AuthScheme, Operation
from ducktap.verify.proof import (
    auth_proof,
    coverage_proof,
    path_proof,
    pipeline_proof,
    verify,
)

FIXTURE = Path(__file__).parent / "fixtures" / "petstore.yaml"


def test_all_proofs_pass_on_generated_cli(tmp_path):
    out = tmp_path / "out"
    press(str(FIXTURE), str(out), name="petstore", targets=["python-cli"], use_llm=False)
    spec = discover(str(FIXTURE), name="petstore")
    report = verify(spec, str(out), "petstore")
    assert report.passed, report.to_dict()
    assert {p.name for p in report.proofs} == {
        "path_proof", "coverage_proof", "auth_proof", "pipeline_proof"
    }


def test_path_proof_flags_hallucinated_path():
    spec = APISpec(name="x", operations=[Operation(operation_id="a", method="GET", path="/real")])
    good = path_proof(spec, 'path = "/real"')
    assert good.passed
    bad = path_proof(spec, 'path = "/real"\npath = "/made-up"')
    assert not bad.passed
    assert bad.offenders == ["/made-up"]


def test_coverage_proof_flags_dropped_operation():
    spec = APISpec(name="x", operations=[
        Operation(operation_id="list_pets", method="GET", path="/pets"),
        Operation(operation_id="get_pet", method="GET", path="/pets/{id}"),
    ])
    r = coverage_proof(spec, "def list_pets(): ...")  # get_pet missing
    assert not r.passed
    assert r.offenders == ["get_pet"]


def test_auth_proof_matches_scheme_type():
    spec = APISpec(name="x", auth_schemes=[AuthScheme(name="k", type="apiKey", parameter_name="X-API-Key")])
    assert auth_proof(spec, 'headers["X-API-Key"] = key').passed
    assert not auth_proof(spec, "no header here").passed

    bearer = APISpec(name="y", auth_schemes=[AuthScheme(name="o", type="oauth2")])
    assert auth_proof(bearer, 'req.headers["Authorization"] = f"Bearer {tok}"').passed


def test_pipeline_proof_flags_write_only_table():
    src = (
        "CREATE TABLE IF NOT EXISTS used (id)\n"
        "CREATE TABLE IF NOT EXISTS orphan (id)\n"
        "SELECT * FROM used\n"
    )
    r = pipeline_proof(src)
    assert not r.passed
    assert r.offenders == ["orphan"]
