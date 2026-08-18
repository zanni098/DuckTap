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


def test_openapi_webhooks_discovery():
    webhook_fixture = Path(__file__).parent / "fixtures" / "openapi_webhooks.yaml"
    d = OpenAPIDiscoverer()
    assert d.can_handle(str(webhook_fixture))
    spec = d.discover(str(webhook_fixture))
    
    # Regular operations
    assert len(spec.operations) == 1
    assert spec.operations[0].operation_id == "create_subscription"
    
    # Webhooks
    assert len(spec.webhooks) == 2
    webhook_ids = {wh.operation_id for wh in spec.webhooks}
    assert "on_new_event" in webhook_ids
    assert "post_order_canceled" in webhook_ids or "order_canceled" in webhook_ids
    
    # Webhook payload parameters and tags
    on_new_event = next(wh for wh in spec.webhooks if wh.operation_id == "on_new_event")
    assert on_new_event.method == "POST"
    assert on_new_event.path == "/new_event"
    assert on_new_event.tags == ["webhooks"]
    assert len(on_new_event.params) >= 2
    param_names = {p.name for p in on_new_event.params}
    assert "id" in param_names
    assert "event_type" in param_names
    assert on_new_event.responses[0].status == "200"

    # Verify normalize() preserves webhooks uniqueness
    spec.normalize()
    assert len(spec.webhooks) == 2

