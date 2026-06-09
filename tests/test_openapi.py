from pathlib import Path

from ducktap.discovery.openapi import OpenAPIDiscoverer

FIXTURE = Path(__file__).parent / "fixtures" / "petstore.yaml"


def test_petstore_discovery():
    d = OpenAPIDiscoverer()
    assert d.can_handle(str(FIXTURE))
    spec = d.discover(str(FIXTURE))
    assert spec.name == "swagger-petstore-openapi-3-0" or "petstore" in spec.name
    assert len(spec.operations) > 5
    # The petstore spec has these well-known operations
    ids = {op.operation_id for op in spec.operations}
    assert any("pet" in i for i in ids)
    # It has at least one auth scheme defined
    assert len(spec.auth_schemes) >= 1
    # Every operation has method + path
    for op in spec.operations:
        assert op.method
        assert op.path.startswith("/")


def test_formdata_param_location_coerced_to_query():
    """Swagger 2.0 `in: formData` (and unknown locations) must not crash parsing."""
    from ducktap.discovery.openapi import _coerce_location, _parse_param
    assert _coerce_location("formData") == "query"
    assert _coerce_location("weird") == "query"
    assert _coerce_location("path") == "path"
    p = _parse_param({"name": "file", "in": "formData"}, is_v3=False)
    assert p.location == "query" and p.name == "file"
