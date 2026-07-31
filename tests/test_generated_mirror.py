"""Tests for the generated local data lake (mirror.py)."""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

from ducktap.core.pipeline import press

SPEC = """
openapi: 3.0.0
info: {title: Lake API, version: "1.0.0"}
servers: [{url: "https://api.lake.test"}]
paths:
  /items:
    get:
      operationId: listItems
      tags: [items]
      responses: {"200": {description: ok}}
"""


@pytest.fixture
def mirror_cls(tmp_path: Path, monkeypatch):
    spec_file = tmp_path / "lake.yaml"
    spec_file.write_text(SPEC, encoding="utf-8")
    out = tmp_path / "out"
    press(str(spec_file), str(out))
    monkeypatch.syspath_prepend(str(out / "lake-dt-cli"))
    for mod in [m for m in sys.modules if m.startswith("lake_dt_cli")]:
        del sys.modules[mod]
    module = importlib.import_module("lake_dt_cli.mirror")
    yield module.Mirror
    for mod in [m for m in sys.modules if m.startswith("lake_dt_cli")]:
        del sys.modules[mod]


@pytest.fixture
def mirror(mirror_cls, tmp_path: Path):
    m = mirror_cls(path=str(tmp_path / "mirror.sqlite"))
    m.save_record("things", "GET", "/items", "https://api.lake.test/items",
                  [{"id": 1, "name": "alpha"}, {"id": 2, "name": "beta"}])
    yield m
    m.close()


def test_query_returns_rows(mirror):
    rows = mirror.query("SELECT collection, method FROM records")
    assert len(rows) == 2
    assert rows[0]["collection"] == "things"


def test_query_accepts_bind_parameters(mirror):
    """`stale` and `bottleneck` interpolate their arguments -- as parameters."""
    rows = mirror.query(
        "SELECT method, path, COUNT(*) as calls FROM records "
        "GROUP BY method, path ORDER BY calls DESC LIMIT ?",
        (1,),
    )
    assert rows == [{"method": "GET", "path": "/items", "calls": 2}]


def test_query_allows_common_table_expressions(mirror):
    rows = mirror.query("WITH t AS (SELECT * FROM records) SELECT COUNT(*) AS n FROM t")
    assert rows[0]["n"] == 2


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM records",
        "DROP TABLE records",
        "UPDATE records SET body = 'x'",
        "INSERT INTO records(collection, method, path, url, body, saved_at) "
        "VALUES ('x','GET','/','u','{}',1)",
    ],
)
def test_query_refuses_to_write(mirror, sql):
    with pytest.raises(ValueError):
        mirror.query(sql)
    assert len(mirror.query("SELECT id FROM records")) == 2


def test_write_disguised_as_a_cte_is_stopped_by_the_engine(mirror):
    """A prefix check alone would wave this through."""
    with pytest.raises(ValueError):
        mirror.query("WITH x AS (SELECT 1) DELETE FROM records")
    assert len(mirror.query("SELECT id FROM records")) == 2


def test_records_table_is_indexed(mirror):
    plan = mirror.query(
        "SELECT * FROM sqlite_master WHERE type = 'index' AND tbl_name = 'records'"
    )
    names = {row["name"] for row in plan}
    assert {"records_saved_at", "records_collection", "records_endpoint"} <= names


def test_full_text_search_finds_saved_bodies(mirror):
    hits = mirror.search("alpha")
    assert len(hits) == 1
    assert hits[0]["body"]["name"] == "alpha"
