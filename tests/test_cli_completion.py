"""Unit tests for DuckTap CLI shell completion and top-level options."""
import re
from unittest.mock import patch

from typer.testing import CliRunner

from ducktap import __version__
from ducktap.cli import app

runner = CliRunner()

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


def test_cli_version_flag():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert f"ducktap {__version__}" in result.output


def test_cli_help_flag_includes_completion():
    result = runner.invoke(app, ["--help"], env={"COLUMNS": "120"})
    assert result.exit_code == 0
    plain = _strip_ansi(result.output)
    assert "--install-completion" in plain
    assert "--show-completion" in plain


def test_cli_show_completion():
    with patch("shellingham.detect_shell", return_value=("bash", "/bin/bash")):
        result = runner.invoke(app, ["--show-completion"])
        assert result.exit_code == 0
        assert "_ducktap_completion" in result.output
