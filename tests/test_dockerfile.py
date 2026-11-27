"""Dockerfile generator (issue #83).

`press --docker` writes a multi-stage Dockerfile into every generated language
CLI. These tests assert the structural properties the issue calls for:
registration, multi-stage builds, correct entrypoints, a Python Dockerfile that
tracks the lockfile, and the alpine/slim base switch.

The heavy `docker build` checks are gated behind ``DUCKTAP_DOCKER_TESTS=1`` and
a Docker daemon, mirroring ``DUCKTAP_COMPILE_TESTS`` in the multi-language
suite; they never run in the default test job.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from ducktap.core.pipeline import press
from ducktap.core.plugins import autoload_builtins, get_generators

FIXTURE = Path(__file__).parent / "fixtures" / "petstore.yaml"

_ALL_LANGS = ["python-cli", "go-cli", "rust-cli", "typescript-cli"]

_RUN_DOCKER = os.environ.get("DUCKTAP_DOCKER_TESTS") == "1"
_docker_only = pytest.mark.skipif(
    not (_RUN_DOCKER and shutil.which("docker")),
    reason="set DUCKTAP_DOCKER_TESTS=1 with Docker running to build images",
)


@pytest.fixture
def out_dir(tmp_path):
    return tmp_path / "out"


def _stages(dockerfile: str) -> list[str]:
    return [ln for ln in dockerfile.splitlines() if ln.startswith("FROM ")]


def test_dockerfile_generator_is_registered():
    autoload_builtins()
    assert "dockerfile" in get_generators()


def test_default_press_has_no_dockerfile(out_dir):
    press(str(FIXTURE), str(out_dir), name="petstore")
    assert not (out_dir / "petstore-dt-cli" / "Dockerfile").exists()


def test_docker_flag_adds_dockerfile_for_present_clis(out_dir):
    result = press(
        str(FIXTURE), str(out_dir), name="petstore",
        targets=["python-cli"], docker=True,
    )
    assert "dockerfile" in result.artifacts
    assert (out_dir / "petstore-dt-cli" / "Dockerfile").exists()
    # No Go/Rust/TS project was generated, so no Dockerfile for them.
    assert not (out_dir / "petstore-dt-go" / "Dockerfile").exists()


def test_dockerfile_for_all_four_languages(out_dir):
    result = press(
        str(FIXTURE), str(out_dir), name="petstore",
        targets=_ALL_LANGS, docker=True,
    )
    assert len(result.artifacts["dockerfile"]) == 4
    dirs = {
        "python-cli": "petstore-dt-cli",
        "go-cli": "petstore-dt-go",
        "rust-cli": "petstore-dt-rs",
        "typescript-cli": "petstore-dt-ts",
    }
    for lang, rel in dirs.items():
        assert (out_dir / rel / "Dockerfile").exists(), lang


def test_every_dockerfile_is_multi_stage(out_dir):
    press(str(FIXTURE), str(out_dir), name="petstore", targets=_ALL_LANGS, docker=True)
    for rel in (
        "petstore-dt-cli", "petstore-dt-go", "petstore-dt-rs", "petstore-dt-ts",
    ):
        text = (out_dir / rel / "Dockerfile").read_text(encoding="utf-8")
        stages = _stages(text)
        assert len(stages) >= 2, f"{rel} is not multi-stage: {stages}"
        # A named runtime stage and a copy from the build stage.
        assert "AS build" in text
        assert "AS runtime" in text
        assert "COPY --from=build" in text


def test_python_dockerfile_uses_lock_and_entrypoint(out_dir):
    press(str(FIXTURE), str(out_dir), name="petstore", targets=["python-cli"], docker=True)
    text = (out_dir / "petstore-dt-cli" / "Dockerfile").read_text(encoding="utf-8")
    assert "requirements.lock" in text
    assert 'ENTRYPOINT ["petstore-dt-cli"]' in text


def test_python_dockerfile_tracks_no_lock(out_dir):
    press(
        str(FIXTURE), str(out_dir), name="petstore",
        targets=["python-cli"], no_lock=True, docker=True,
    )
    text = (out_dir / "petstore-dt-cli" / "Dockerfile").read_text(encoding="utf-8")
    assert "requirements.lock" not in text
    # Still pins via requirements.txt so the build is reproducible-ish.
    assert "requirements.txt" in text


def test_no_lock_regeneration_drops_stale_lock(out_dir):
    """Regenerating in place with --no-lock must not leave an old lock behind."""
    press(str(FIXTURE), str(out_dir), name="petstore")
    root = out_dir / "petstore-dt-cli"
    assert (root / "requirements.lock").exists()

    press(
        str(FIXTURE), str(out_dir), name="petstore",
        targets=["python-cli"], no_lock=True, docker=True,
    )
    assert not (root / "requirements.lock").exists()
    text = (root / "Dockerfile").read_text(encoding="utf-8")
    assert "requirements.lock" not in text
    assert "requirements.txt" in text


def test_dockerfile_ignores_stale_lock_when_no_lock(out_dir):
    """The dockerfile generator itself must honor --no-lock."""
    press(str(FIXTURE), str(out_dir), name="petstore")
    root = out_dir / "petstore-dt-cli"
    assert (root / "requirements.lock").exists()

    press(str(FIXTURE), str(out_dir), name="petstore", targets=["dockerfile"], no_lock=True)
    text = (root / "Dockerfile").read_text(encoding="utf-8")
    assert "requirements.lock" not in text
    assert "requirements.txt" in text


def test_dockerfile_alpine_is_default(out_dir):
    press(str(FIXTURE), str(out_dir), name="petstore", targets=["python-cli"], docker=True)
    text = (out_dir / "petstore-dt-cli" / "Dockerfile").read_text(encoding="utf-8")
    assert "python:3.12-alpine" in text


def test_docker_base_slim_switches_base_image(out_dir):
    press(
        str(FIXTURE), str(out_dir), name="petstore",
        targets=["python-cli"], docker=True, docker_base="slim",
    )
    text = (out_dir / "petstore-dt-cli" / "Dockerfile").read_text(encoding="utf-8")
    assert "python:3.12-slim" in text
    assert "alpine" not in text


def test_unknown_docker_base_is_rejected(out_dir):
    with pytest.raises(ValueError, match="docker base"):
        press(
            str(FIXTURE), str(out_dir), name="petstore",
            targets=["python-cli"], docker=True, docker_base="windows",
        )


def test_rust_dockerfile_uses_crate_binary(out_dir):
    press(str(FIXTURE), str(out_dir), name="petstore", targets=["rust-cli"], docker=True)
    text = (out_dir / "petstore-dt-rs" / "Dockerfile").read_text(encoding="utf-8")
    # The Rust binary is the crate name (underscored), not the directory name.
    assert "petstore_dt_rs" in text
    assert "target/release/petstore_dt_rs" in text


def test_rust_dockerfile_uses_edition_2024_capable_toolchain(out_dir):
    """Rust 1.82 cannot parse current crates.io manifests (edition2024)."""
    press(str(FIXTURE), str(out_dir), name="petstore", targets=["rust-cli"], docker=True)
    text = (out_dir / "petstore-dt-rs" / "Dockerfile").read_text(encoding="utf-8")
    assert "FROM rust:1.91-alpine AS build" in text


def test_dockerfile_target_is_always_last(out_dir):
    """An explicit `dockerfile` first in targets must not emit empty output."""
    press(
        str(FIXTURE), str(out_dir), name="petstore",
        targets=["dockerfile", "python-cli"], docker=True,
    )
    assert (out_dir / "petstore-dt-cli" / "Dockerfile").exists()


# --- opt-in real builds ---------------------------------------------------

@_docker_only
def test_generated_python_image_builds_and_runs(tmp_path):
    out = tmp_path / "out"
    press(str(FIXTURE), str(out), name="petstore", targets=["python-cli"], docker=True)
    root = out / "petstore-dt-cli"
    tag = "ducktap-petstore-cli:test"
    build = subprocess.run(
        ["docker", "build", "-t", tag, "."],
        cwd=str(root), capture_output=True, text=True, timeout=1800,
    )
    assert build.returncode == 0, build.stderr[-2000:]
    run = subprocess.run(
        ["docker", "run", "--rm", tag, "--help"],
        capture_output=True, text=True, timeout=120,
    )
    assert run.returncode == 0, run.stderr


@_docker_only
def test_generated_go_image_is_small(tmp_path):
    """A statically linked Go CLI must fit in the <50MB budget from the issue."""
    out = tmp_path / "out"
    press(str(FIXTURE), str(out), name="petstore", targets=["go-cli"], docker=True)
    root = out / "petstore-dt-go"
    tag = "ducktap-petstore-go:test"
    build = subprocess.run(
        ["docker", "build", "-t", tag, "."],
        cwd=str(root), capture_output=True, text=True, timeout=1800,
    )
    assert build.returncode == 0, build.stderr[-2000:]
    size = subprocess.run(
        ["docker", "image", "inspect", tag, "--format", "{{.Size}}"],
        capture_output=True, text=True, timeout=60,
    )
    assert size.returncode == 0, size.stderr
    assert int(size.stdout.strip()) < 50 * 1024 * 1024


@_docker_only
def test_generated_rust_image_builds_and_runs(tmp_path):
    out = tmp_path / "out"
    press(str(FIXTURE), str(out), name="petstore", targets=["rust-cli"], docker=True)
    root = out / "petstore-dt-rs"
    tag = "ducktap-petstore-rs:test"
    build = subprocess.run(
        ["docker", "build", "-t", tag, "."],
        cwd=str(root), capture_output=True, text=True, timeout=1800,
    )
    assert build.returncode == 0, build.stderr[-2000:]
    run = subprocess.run(
        ["docker", "run", "--rm", tag, "--help"],
        capture_output=True, text=True, timeout=120,
    )
    assert run.returncode == 0, run.stderr
    size = subprocess.run(
        ["docker", "image", "inspect", tag, "--format", "{{.Size}}"],
        capture_output=True, text=True, timeout=60,
    )
    assert int(size.stdout.strip()) < 50 * 1024 * 1024


@_docker_only
def test_generated_typescript_image_builds_and_runs(tmp_path):
    out = tmp_path / "out"
    press(
        str(FIXTURE), str(out), name="petstore",
        targets=["typescript-cli"], docker=True,
    )
    root = out / "petstore-dt-ts"
    tag = "ducktap-petstore-ts:test"
    build = subprocess.run(
        ["docker", "build", "-t", tag, "."],
        cwd=str(root), capture_output=True, text=True, timeout=1800,
    )
    assert build.returncode == 0, build.stderr[-2000:]
    run = subprocess.run(
        ["docker", "run", "--rm", tag, "--help"],
        capture_output=True, text=True, timeout=120,
    )
    assert run.returncode == 0, run.stderr
    # Issue #83 sets one <50MB budget for simple CLIs; no language exception.
    size = subprocess.run(
        ["docker", "image", "inspect", tag, "--format", "{{.Size}}"],
        capture_output=True, text=True, timeout=60,
    )
    assert int(size.stdout.strip()) < 50 * 1024 * 1024
