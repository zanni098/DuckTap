"""End-to-end: petstore spec -> generated CLI + MCP + skill -> shipcheck passes."""
import ast
from pathlib import Path

import pytest

from ducktap.core.pipeline import press
from ducktap.verify.scorecard import score
from ducktap.verify.shipcheck import shipcheck

FIXTURE = Path(__file__).parent / "fixtures" / "petstore.yaml"


@pytest.fixture
def out_dir(tmp_path):
    return tmp_path / "out"


def test_press_petstore_end_to_end(out_dir):
    result = press(str(FIXTURE), str(out_dir), name="petstore")
    assert result.spec.name == "petstore"
    assert len(result.spec.operations) > 5

    # Three target groups generated
    assert "python-cli" in result.artifacts
    assert "mcp-server" in result.artifacts
    assert "skill" in result.artifacts

    # All emitted .py files parse cleanly
    cli_dir = out_dir / "petstore-dt-cli"
    assert cli_dir.exists()
    py_files = list(cli_dir.rglob("*.py"))
    assert py_files, "expected generated python files"
    for py in py_files:
        try:
            ast.parse(py.read_text(encoding="utf-8"))
        except SyntaxError as e:
            pytest.fail(f"{py}: {e}")

    # MCP server present
    assert (out_dir / "petstore-dt-mcp" / "petstore_dt_mcp" / "server.py").exists()

    # Skill files present
    skill_dir = out_dir / "skills" / "ducktap-petstore"
    assert (skill_dir / "SKILL.md").exists()
    assert (skill_dir / "tools.json").exists()

    # Scorecard runs and is sane
    sc = score(result.spec, str(out_dir))
    assert 0 <= sc.overall <= 100
    assert sc.grade in {"A", "B", "C", "D", "F"}


def test_generated_packages_actually_import(out_dir):
    """Stronger test: import the generated packages as packages so relative
    imports resolve and bound-identifier errors (e.g. JSON `false` inside a
    Python literal) surface here, not only when a user runs the CLI."""
    import importlib
    import sys

    press(str(FIXTURE), str(out_dir), name="petstore")

    cli_root = str(out_dir / "petstore-dt-cli")
    mcp_root = str(out_dir / "petstore-dt-mcp")
    sys.path.insert(0, cli_root)
    sys.path.insert(0, mcp_root)
    # Drop any previously-imported petstore_* modules (from a sibling test)
    for k in list(sys.modules):
        if k.startswith(("petstore_dt_cli", "petstore_dt_mcp")):
            del sys.modules[k]
    try:
        for modname in (
            "petstore_dt_cli",
            "petstore_dt_cli.client",
            "petstore_dt_cli.mirror",
            "petstore_dt_cli.commands",
            "petstore_dt_cli.main",
            "petstore_dt_mcp",
            "petstore_dt_mcp.server",
        ):
            try:
                importlib.import_module(modname)
            except Exception as e:
                pytest.fail(f"{modname} failed to import: {e!r}")
    finally:
        sys.path.remove(cli_root)
        sys.path.remove(mcp_root)


def test_shipcheck_petstore(out_dir):
    press(str(FIXTURE), str(out_dir), name="petstore")
    results = shipcheck(str(out_dir), "petstore")
    by_name = {r.name: r for r in results}
    assert by_name["cli_dir_exists"].passed
    assert by_name["python_syntax"].passed, by_name["python_syntax"].detail
    assert by_name["pyproject"].passed
    assert by_name["readme"].passed
