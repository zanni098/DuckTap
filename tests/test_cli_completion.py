"""Unit tests for DuckTap CLI shell completion and top-level options."""
from unittest.mock import patch

from typer.testing import CliRunner

from ducktap import __version__
from ducktap.cli import app

runner = CliRunner()


def test_cli_version_flag():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert f"ducktap {__version__}" in result.output


def test_cli_help_flag_includes_completion():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "--install-completion" in result.output
    assert "--show-completion" in result.output


def test_cli_show_completion():
    with patch("shellingham.detect_shell", return_value=("bash", "/bin/bash")):
        result = runner.invoke(app, ["--show-completion"])
        assert result.exit_code == 0
        assert "_ducktap_completion" in result.output
