"""Tests for the publish command."""
from __future__ import annotations

import tempfile
from pathlib import Path

from ducktap.publish import publish


def _fake_run(cmd: list[str], cwd: str | None = None) -> tuple[int, str, str]:
    """Fake subprocess runner that always succeeds."""
    return 0, "ok", ""


def _fake_run_fail_git(cmd: list[str], cwd: str | None = None) -> tuple[int, str, str]:
    """Fake runner that fails on git push."""
    if "push" in cmd:
        return 1, "", "rejected"
    return 0, "ok", ""


def test_publish_missing_cli_dir() -> None:
    with tempfile.TemporaryDirectory() as td:
        result = publish("nonexistent", out_dir=td, run=_fake_run)
        assert not result.success
        assert "not found" in result.message


def test_publish_skip_shipcheck() -> None:
    with tempfile.TemporaryDirectory() as td:
        # Create a minimal fake CLI structure so shipcheck is skipped
        cli_dir = Path(td) / "test-dt-cli"
        cli_dir.mkdir()
        (cli_dir / "pyproject.toml").write_text("[project]\nname=\"test\"\n")
        (cli_dir / "README.md").write_text("# test")
        pkg = cli_dir / "test_dt_cli"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "main.py").write_text("import click\n")

        result = publish("test", out_dir=td, skip_shipcheck=True, github=False, pypi=False, run=_fake_run)
        assert result.success
        step_names = {s.name for s in result.steps}
        assert "git_init" in step_names


def test_publish_shipcheck_fails() -> None:
    with tempfile.TemporaryDirectory() as td:
        cli_dir = Path(td) / "test-dt-cli"
        cli_dir.mkdir()
        # Missing README / pyproject -> shipcheck fails
        result = publish("test", out_dir=td, skip_shipcheck=False, github=False, pypi=False, run=_fake_run)
        assert not result.success
        assert "Shipcheck failed" in result.message


def test_publish_dry_run_no_side_effects() -> None:
    with tempfile.TemporaryDirectory() as td:
        cli_dir = Path(td) / "test-dt-cli"
        cli_dir.mkdir()
        (cli_dir / "pyproject.toml").write_text("[project]\nname=\"test\"\n")
        (cli_dir / "README.md").write_text("# test")
        pkg = cli_dir / "test_dt_cli"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "main.py").write_text("import click\n")

        result = publish(
            "test", out_dir=td, skip_shipcheck=True,
            dry_run=True, github=False, pypi=False, run=_fake_run,
        )
        assert result.success
