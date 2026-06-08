"""Typed per-resource SQLite tables in the generated Python CLI.

Presses an archetype-shaped spec, imports the generated `mirror` module, and
exercises the typed upsert/search/since methods + FTS5 + the sync cursor.
"""
from __future__ import annotations

import importlib.util

from ducktap.core.spec import APISpec, Operation, Param
from ducktap.generator.python_cli import PythonCLIGenerator


def _load_module(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _pm_spec() -> APISpec:
    return APISpec(
        name="linear",
        display_name="Linear",
        archetype="project_management",
        operations=[
            Operation(
                operation_id="list_issues", method="GET", path="/issues",
                params=[Param(name="assignee", location="query")],
            )
        ],
    )


def test_typed_domain_table_upsert_search_since(tmp_path, monkeypatch):
    monkeypatch.setenv("DUCKTAP_HOME", str(tmp_path / "home"))
    out = tmp_path / "out"
    PythonCLIGenerator().generate(_pm_spec(), str(out))

    mirror_py = out / "linear-dt-cli" / "linear_dt_cli" / "mirror.py"
    assert mirror_py.exists()
    # The typed "issues" table (project_management archetype) must be emitted.
    src = mirror_py.read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS issues" in src
    assert "issues_fts" in src  # FTS5 over the text column

    mod = _load_module(str(mirror_py), "linear_mirror")
    m = mod.Mirror(path=str(tmp_path / "m.sqlite"))

    n = m.upsert_domain([
        {"id": "1", "title": "Login is broken", "status": "open",
         "priority": "high", "updated_at": "2026-06-01"},
        {"id": "2", "title": "Dark mode flicker", "status": "closed",
         "priority": "low", "updated_at": "2026-06-05"},
    ])
    assert n == 2

    # FTS5 search over the "title" text column.
    hits = m.search_domain("login")
    assert any(h["id"] == "1" for h in hits)

    # Incremental --since filter on the timestamp column (updated_at).
    recent = m.domain_since("2026-06-03")
    assert [r["id"] for r in recent] == ["2"]

    # Re-upsert replaces (no duplicate rows / FTS drift).
    m.upsert_domain([{"id": "1", "title": "Login fixed", "status": "closed",
                      "updated_at": "2026-06-07"}])
    assert not m.search_domain("broken")          # old text gone from FTS
    assert any(h["id"] == "1" for h in m.search_domain("fixed"))

    # Sync cursor persistence.
    assert m.get_cursor() is None
    m.set_cursor("2026-06-07")
    assert m.get_cursor() == "2026-06-07"
    m.close()


def test_unknown_archetype_emits_no_typed_table(tmp_path):
    spec = APISpec(
        name="weird", display_name="Weird", archetype="unknown",
        operations=[Operation(operation_id="ping", method="GET", path="/ping")],
    )
    out = tmp_path / "out"
    PythonCLIGenerator().generate(spec, str(out))
    src = (out / "weird-dt-cli" / "weird_dt_cli" / "mirror.py").read_text(encoding="utf-8")
    # No archetype -> no typed domain table / methods, but cursor helpers remain.
    assert "upsert_domain" not in src
    assert "def get_cursor" in src
