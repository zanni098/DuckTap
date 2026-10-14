"""Lockfile generation for the Python CLI (issue #82).

The generated Python CLI ships two dependency files:

* ``requirements.txt`` -- direct deps, unpinned.
* ``requirements.lock`` -- the full closure, every package pinned.

The lock must be deterministic (no network) and installable, and ``--no-lock``
must suppress it without touching ``requirements.txt``.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from ducktap.core.pipeline import press
from ducktap.generator.lockfile import (
    DIRECT_DEPS,
    KNOWN_PINS,
    render_requirements_lock,
    render_requirements_txt,
)

FIXTURE = Path(__file__).parent / "fixtures" / "petstore.yaml"

_PIN_RE = re.compile(r"^[A-Za-z0-9_.\-]+==[^\s;]+(\s*;.*)?$")


@pytest.fixture
def out_dir(tmp_path):
    return tmp_path / "out"


def test_requirements_txt_lists_direct_deps():
    text = render_requirements_txt()
    for dep in DIRECT_DEPS:
        assert dep in text
    # Unpinned: no "==" constraint in the direct list.
    assert "==" not in text.replace("pip install -r requirements.lock", "")


def test_requirements_lock_pins_every_line():
    lines = [
        ln for ln in render_requirements_lock().splitlines()
        if ln.strip() and not ln.startswith("#")
    ]
    assert lines, "lock should not be empty"
    for line in lines:
        assert _PIN_RE.match(line), f"not a pinned requirement: {line!r}"
        assert "==" in line


def test_lock_covers_direct_and_transitive_deps():
    lock = render_requirements_lock()
    # Direct deps must appear (normalized names).
    for name in ("click", "httpx", "rich"):
        assert re.search(rf"^{name}==", lock, re.MULTILINE), name
    # And a couple of transitive dependencies the closure pulls in.
    for name in ("httpcore", "anyio", "certifi"):
        assert re.search(rf"^{name}==", lock, re.MULTILINE), name


def test_lock_has_no_duplicate_packages():
    names = [
        ln.split("==", 1)[0] for ln in KNOWN_PINS
    ]
    assert len(names) == len(set(names)), "duplicate pins in the lock"


def test_lock_is_deterministic():
    assert render_requirements_lock() == render_requirements_lock()
    assert render_requirements_txt() == render_requirements_txt()


def test_press_writes_requirements_txt_and_lock(out_dir):
    press(str(FIXTURE), str(out_dir), name="petstore")
    root = out_dir / "petstore-dt-cli"
    assert (root / "requirements.txt").exists()
    lock = root / "requirements.lock"
    assert lock.exists()
    assert "click==" in lock.read_text(encoding="utf-8")


def test_no_lock_skips_lock_but_keeps_requirements_txt(out_dir):
    press(str(FIXTURE), str(out_dir), name="petstore", no_lock=True)
    root = out_dir / "petstore-dt-cli"
    assert (root / "requirements.txt").exists()
    assert not (root / "requirements.lock").exists()


def test_lock_files_are_recorded_as_artifacts(out_dir):
    result = press(str(FIXTURE), str(out_dir), name="petstore", targets=["python-cli"])
    files = result.artifacts["python-cli"]
    assert any(f.endswith("requirements.txt") for f in files)
    assert any(f.endswith("requirements.lock") for f in files)


def test_lock_online_falls_back_when_pip_tools_absent(monkeypatch, out_dir):
    """Without pip-compile the bundled pins are used, not a crash."""
    monkeypatch.setattr("shutil.which", lambda _: None)
    press(str(FIXTURE), str(out_dir), name="petstore", lock_online=True)
    lock = (out_dir / "petstore-dt-cli" / "requirements.lock").read_text(encoding="utf-8")
    assert re.search(r"^click==", lock, re.MULTILINE)
