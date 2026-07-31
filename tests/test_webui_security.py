"""The dashboard listens on localhost, which any page in the user's browser can
reach, and it renders values that came out of a spec DuckTap just fetched."""
from __future__ import annotations

import re
from pathlib import Path

from fastapi.testclient import TestClient

from ducktap.webui import app as webui


def _client() -> TestClient:
    return TestClient(webui.create_app())


def _token(client: TestClient) -> str:
    html = client.get("/").text
    match = re.search(r"csrf_token',\s*\"([^\"]+)\"", html)
    assert match, "CSRF token not rendered into the page"
    return match.group(1)


def test_generate_rejects_requests_without_a_csrf_token():
    client = _client()
    r = client.post("/generate", data={"source": "https://evil.test/openapi.yaml"})
    assert r.status_code == 403


def test_generate_rejects_a_wrong_csrf_token():
    client = _client()
    r = client.post(
        "/generate",
        data={"source": "https://evil.test/openapi.yaml", "csrf_token": "nope"},
    )
    assert r.status_code == 403


def test_generate_rejects_cross_site_form_posts():
    client = _client()
    r = client.post(
        "/generate",
        data={"source": "https://evil.test/openapi.yaml", "csrf_token": _token(client)},
        headers={"Sec-Fetch-Site": "cross-site"},
    )
    assert r.status_code == 403


def test_generate_accepts_a_same_origin_request_with_the_token(tmp_path, monkeypatch):
    monkeypatch.setenv("DUCKTAP_OUT", str(tmp_path / "out"))
    fixture = Path(__file__).parent / "fixtures" / "petstore.yaml"
    client = _client()
    r = client.post(
        "/generate",
        data={
            "source": str(fixture),
            "csrf_token": _token(client),
            "target": ["skill"],
        },
        headers={"Sec-Fetch-Site": "same-origin"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["name"] == "petstore"


def test_catalog_values_are_escaped_into_the_page(monkeypatch, tmp_path):
    """A recipe (or a DUCKTAP_CATALOG directory) must not be able to inject
    markup into the dashboard."""
    (tmp_path / "evil.yaml").write_text(
        'name: evil\n'
        'display_name: "<script>alert(1)</script>"\n'
        'category: "<img src=x onerror=alert(1)>"\n'
        'spec_url: "https://example.test/openapi.yaml"\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("DUCKTAP_CATALOG", str(tmp_path))
    html = _client().get("/").text
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "<img src=x onerror=alert(1)>" not in html
