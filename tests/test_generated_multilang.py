"""Multi-language generator tests.

Two tiers:

1. ``test_all_generators_render`` always runs. It presses every built-in
   generator and asserts each produces files. This is a cheap regression guard
   that the Go/Rust/TS generators stay *reachable* (registered in
   ``autoload_builtins``) and that their templates render without error.

2. The per-language ``*_builds`` tests actually compile the generated project
   with the real toolchain. They are heavy (they download dependencies) so they
   only run when ``DUCKTAP_COMPILE_TESTS=1`` is set *and* the toolchain is
   present. CI sets the env var in a dedicated job; local runs skip them.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from ducktap.core.pipeline import press

FIXTURE = Path(__file__).parent / "fixtures" / "petstore.yaml"

_RUN_COMPILE = os.environ.get("DUCKTAP_COMPILE_TESTS") == "1"
_compile_only = pytest.mark.skipif(
    not _RUN_COMPILE,
    reason="set DUCKTAP_COMPILE_TESTS=1 to run language compile tests",
)


def _press(tmp_path: Path, target: str) -> Path:
    out = tmp_path / "out"
    press(str(FIXTURE), str(out), name="petstore", targets=[target])
    return out


def _run(cmd: list[str], cwd: Path, env: dict | None = None, timeout: int = 600):
    return subprocess.run(
        cmd, cwd=str(cwd), capture_output=True, text=True,
        timeout=timeout, env=env,
    )


def test_all_generators_render(tmp_path):
    """Every built-in generator is registered and renders to non-empty files."""
    out = tmp_path / "out"
    targets = ["python-cli", "mcp-server", "skill", "go-cli", "rust-cli", "typescript-cli"]
    result = press(str(FIXTURE), str(out), name="petstore", targets=targets)
    for t in targets:
        files = result.artifacts.get(t)
        assert files, f"{t} produced no files"
        for f in files:
            assert Path(f).exists() and Path(f).stat().st_size > 0, f"empty: {f}"


@_compile_only
@pytest.mark.skipif(not shutil.which("go"), reason="go toolchain not installed")
def test_go_cli_builds(tmp_path):
    root = _press(tmp_path, "go-cli") / "petstore-dt-go"
    env = {**os.environ, "GOFLAGS": "-mod=mod", "GOTOOLCHAIN": "local"}
    tidy = _run(["go", "mod", "tidy"], root, env=env)
    assert tidy.returncode == 0, tidy.stderr
    build = _run(["go", "build", "./..."], root, env=env)
    assert build.returncode == 0, build.stderr


@_compile_only
@pytest.mark.skipif(not shutil.which("cargo"), reason="cargo toolchain not installed")
def test_rust_cli_builds(tmp_path):
    root = _press(tmp_path, "rust-cli") / "petstore-dt-rs"
    build = _run(["cargo", "build"], root)
    assert build.returncode == 0, build.stderr
    # Treat warnings as a polish regression: the templates should be clean.
    assert "warning:" not in build.stderr, build.stderr


@_compile_only
@pytest.mark.skipif(not shutil.which("npm"), reason="node/npm toolchain not installed")
def test_typescript_cli_builds(tmp_path):
    root = _press(tmp_path, "typescript-cli") / "petstore-dt-ts"
    install = _run(
        ["npm", "install", "--no-audit", "--no-fund", "--loglevel=error"], root
    )
    assert install.returncode == 0, install.stderr
    build = _run(["npx", "tsc", "--noEmit"], root)
    assert build.returncode == 0, build.stdout + build.stderr
