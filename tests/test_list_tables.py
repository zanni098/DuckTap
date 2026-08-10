"""Tests for `ducktap list-tables` subcommand."""
from pathlib import Path
from typer.testing import CliRunner
import pytest

from ducktap.cli import app

runner = CliRunner()


def test_list_tables_nonexistent_file(tmp_path: Path):
    db_path = tmp_path / "nonexistent.db"
    result = runner.invoke(app, ["list-tables", str(db_path)])
    assert result.exit_code == 1
    assert "does not exist" in result.output


def test_list_tables_success(tmp_path: Path):
    try:
        import duckdb
    except ImportError:
        pytest.skip("duckdb not installed")

    db_path = tmp_path / "test.db"
    conn = duckdb.connect(str(db_path))
    conn.execute("CREATE TABLE users (id INT, name VARCHAR);")
    conn.execute("CREATE TABLE orders (id INT, total FLOAT);")
    conn.execute("CREATE SCHEMA metrics;")
    conn.execute("CREATE TABLE metrics.events (id INT);")
    conn.close()

    result = runner.invoke(app, ["list-tables", str(db_path)])
    assert result.exit_code == 0
    assert "main.users" in result.output
    assert "main.orders" in result.output
    assert "metrics.events" in result.output


def test_list_tables_empty(tmp_path: Path):
    try:
        import duckdb
    except ImportError:
        pytest.skip("duckdb not installed")

    db_path = tmp_path / "empty.db"
    conn = duckdb.connect(str(db_path))
    conn.close()

    result = runner.invoke(app, ["list-tables", str(db_path)])
    assert result.exit_code == 0
    assert "No tables found" in result.output
