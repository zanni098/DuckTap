from fastapi.testclient import TestClient

from ducktap.webui.app import create_app


def test_dashboard_home_is_rich_workbench():
    client = TestClient(create_app())
    r = client.get("/")
    assert r.status_code == 200
    html = r.text
    assert "DuckTap Workbench" in html
    assert "status-grid" in html
    assert "source-form" in html
    assert "catalog-search" in html
    assert "scorecard-panel" in html
    assert "recent-runs" in html


def test_catalog_api_returns_entries():
    client = TestClient(create_app())
    r = client.get("/api/catalog")
    assert r.status_code == 200
    entries = r.json()
    assert any(e["name"] == "petstore" for e in entries)
