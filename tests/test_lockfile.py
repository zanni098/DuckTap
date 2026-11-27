"""Lockfile generation for the Python CLI (issue #82).

The generated Python CLI ships two dependency files:

* ``requirements.txt`` -- direct deps, unpinned.
* ``requirements.lock`` -- the full closure, every package pinned.

The lock must be deterministic (no network) and installable, and ``--no-lock``
must suppress it without touching ``requirements.txt``.
"""
from __future__ import annotations

import re
import subprocess
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
    """Without pip-compile the bundled pins are used, but not silently."""
    monkeypatch.setattr("shutil.which", lambda _: None)
    with pytest.warns(RuntimeWarning, match="falling back to the bundled pins"):
        press(str(FIXTURE), str(out_dir), name="petstore", lock_online=True)
    lock = (out_dir / "petstore-dt-cli" / "requirements.lock").read_text(encoding="utf-8")
    assert re.search(r"^click==", lock, re.MULTILINE)


def test_requirements_txt_without_lock_does_not_recommend_it():
    text = render_requirements_txt(with_lock=False)
    assert "requirements.lock" not in text
    for dep in DIRECT_DEPS:
        assert dep in text


def test_no_lock_readme_does_not_recommend_a_missing_lock(out_dir):
    press(str(FIXTURE), str(out_dir), name="petstore", no_lock=True)
    root = out_dir / "petstore-dt-cli"
    assert "requirements.lock" not in (root / "README.md").read_text(encoding="utf-8")
    assert "requirements.lock" not in (root / "requirements.txt").read_text(encoding="utf-8")
    assert "pip install ." in (root / "README.md").read_text(encoding="utf-8")


def test_locked_readme_documents_the_pinned_install(out_dir):
    press(str(FIXTURE), str(out_dir), name="petstore")
    readme = (out_dir / "petstore-dt-cli" / "README.md").read_text(encoding="utf-8")
    assert "pip install -c requirements.lock ." in readme


def test_online_lock_preserves_python_3_10_conditional_pin(monkeypatch, out_dir):
    """A 3.11 resolver cannot see 3.10-only deps; the lock must still cover them."""
    def fake_compile(cmd, **kwargs):
        dst = Path(cmd[cmd.index("--output-file") + 1])
        # Simulate pip-compile on Python 3.11: no exceptiongroup pin.
        dst.write_text("anyio==4.16.0\nclick==8.5.1\n", encoding="utf-8")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr("shutil.which", lambda _: "pip-compile")
    monkeypatch.setattr("ducktap.generator.lockfile.subprocess.run", fake_compile)
    press(str(FIXTURE), str(out_dir), name="petstore", lock_online=True)
    lock = (out_dir / "petstore-dt-cli" / "requirements.lock").read_text(encoding="utf-8")
    assert lock.count("exceptiongroup==") == 1
    assert 'exceptiongroup==1.3.2 ; python_version < "3.11"' in lock


def test_bundled_pins_are_not_stale_vulnerable_versions():
    """Regression guard for the 2024 pin set that shipped known advisories."""
    lock = render_requirements_lock()
    for stale in ("anyio==4.8.0", "certifi==2024.8.30", "h11==0.14.0",
                  "idna==3.10", "pygments==2.18.0"):
        assert stale not in lock
