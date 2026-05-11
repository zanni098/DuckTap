"""Shipcheck: structural/runtime sanity checks before publishing a CLI."""
from __future__ import annotations

import ast
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str = ""


def shipcheck(out_dir: str, cli_name: str) -> list[CheckResult]:
    results: list[CheckResult] = []
    root = Path(out_dir) / f"{cli_name}-dt-cli"

    # 1. Directory exists
    results.append(CheckResult(
        "cli_dir_exists", root.exists(),
        f"expected {root}"
    ))
    if not root.exists():
        return results

    # 2. All generated .py files parse
    bad = []
    for py in root.rglob("*.py"):
        try:
            ast.parse(py.read_text(encoding="utf-8"))
        except SyntaxError as e:
            bad.append(f"{py}:{e.lineno}: {e.msg}")
    results.append(CheckResult(
        "python_syntax", not bad,
        "OK" if not bad else f"{len(bad)} files with syntax errors: {bad[:3]}"
    ))

    # 3. pyproject.toml present
    pp = root / "pyproject.toml"
    results.append(CheckResult("pyproject", pp.exists(), str(pp)))

    # 4. README present
    rd = root / "README.md"
    results.append(CheckResult("readme", rd.exists(), str(rd)))

    # 5. --help works (best effort, requires editable install)
    try:
        pkg = (cli_name + "_dt_cli").replace("-", "_")
        proc = subprocess.run(
            [sys.executable, "-m", pkg, "--help"],
            cwd=str(root), capture_output=True, text=True, timeout=15,
        )
        ok = proc.returncode == 0 and "--help" in proc.stdout
        results.append(CheckResult(
            "help_runs", ok,
            proc.stdout[:200] if ok else (proc.stderr[:200] or "no output"),
        ))
    except Exception as e:  # noqa: BLE001
        results.append(CheckResult("help_runs", False, f"could not invoke: {e}"))

    return results
