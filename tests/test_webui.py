from fastapi.testclient import TestClient

from ducktap.webui.app import create_app

FIXTURE = "tests/fixtures/petstore.yaml"


def test_dashboard_home_is_rich_workbench():
    client = TestClient(create_app())
    r = client.get("/")
    assert r.status_code == 200
    html = r.text
    assert "DuckTap Workbench" in html
    assert "status-grid" in html
    assert "source-form" in html
    assert "target-python-cli" in html
    assert "target-typescript-cli" in html
    assert "target-go-cli" in html
    assert "target-rust-cli" in html
    assert "catalog-search" in html
    assert "scorecard-panel" in html
    assert "recent-runs" in html


def test_status_api_exposes_version_and_targets():
    client = TestClient(create_app())
    r = client.get("/api/status")
    assert r.status_code == 200
    data = r.json()
    assert data["version"]
    assert "python-cli" in data["targets"]
    assert "go-cli" in data["targets"]
    assert data["catalog_entries"] >= 1


def test_catalog_api_returns_entries():
    client = TestClient(create_app())
    r = client.get("/api/catalog")
    assert r.status_code == 200
    entries = r.json()
    assert any(e["name"] == "petstore" for e in entries)


def test_generate_respects_selected_targets(tmp_path, monkeypatch):
    monkeypatch.setenv("DUCKTAP_OUT", str(tmp_path / "out"))
    client = TestClient(create_app())
    r = client.post(
        "/generate",
        data={
            "source": FIXTURE,
            "custom_name": "petstore-web",
            "targets": ["python-cli", "skill"],
        },
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["spec"]["name"] == "petstore-web"
    assert set(data["artifacts"]) == {"python-cli", "skill"}
