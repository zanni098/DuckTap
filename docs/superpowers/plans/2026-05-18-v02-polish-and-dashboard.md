# DuckTap v0.2 Polish And Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the highest-impact gaps against Printing Press by improving DuckTap's generated CLI UX, test hygiene, generated docs, and local dashboard.

**Architecture:** Keep the core `APISpec` and plugin pipeline unchanged. Add agent-native behavior in the generated CLI templates, add deterministic checks in tests, and replace the minimal dashboard HTML with a richer local operations console backed by existing catalog and generate APIs.

**Tech Stack:** Python 3.12, Typer, Click-generated CLIs, Jinja2 templates, FastAPI HTML/JSON responses, pytest.

---

### Task 1: Release And Test Hygiene

**Files:**
- Modify: `src/ducktap/__init__.py`
- Modify: `tests/test_generated_cli_runtime.py`
- Create: `tests/test_version.py`

- [ ] Write a failing test that asserts `ducktap.__version__` equals the project version in `pyproject.toml`.
- [ ] Run `.\.venv\Scripts\python -m pytest tests\test_version.py -q` and verify it fails with `0.1.1 != 0.1.2`.
- [ ] Update `src/ducktap/__init__.py` to `__version__ = "0.1.2"`.
- [ ] Replace the removed Click `CliRunner(mix_stderr=False)` constructor usage with Click-version-neutral invocation handling.
- [ ] Run `.\.venv\Scripts\python -m pytest tests\test_version.py tests\test_generated_cli_runtime.py -q`.

### Task 2: Generated CLI Agent Controls

**Files:**
- Modify: `src/ducktap/generator/templates/cli/main.py.j2`
- Modify: `src/ducktap/generator/templates/cli/commands.py.j2`
- Modify: `src/ducktap/generator/templates/cli/client.py.j2`
- Modify: `tests/test_generated_cli_runtime.py`

- [ ] Write failing tests for `--select`, `--compact`, `--quiet`, `--dry-run`, and typed HTTP-ish exit status behavior.
- [ ] Run the focused generated runtime tests and verify the new tests fail because the flags do not exist.
- [ ] Add global Click options for the new controls and store them in `ctx.obj`.
- [ ] Add filtering helpers in generated `commands.py`: select comma-separated top-level fields, compact common high-gravity fields, quiet output suppression, and dry-run request previews.
- [ ] Map API errors to typed exit codes: `3` for 404, `4` for 401/403, `5` for other API errors, `7` for 429, `10` for local config errors.
- [ ] Run the focused generated runtime tests and verify they pass.

### Task 3: Generated Doctor And README Polish

**Files:**
- Modify: `src/ducktap/generator/templates/cli/commands.py.j2`
- Modify: `src/ducktap/generator/templates/cli/README.md.j2`
- Modify: `tests/test_e2e.py`

- [ ] Write failing checks that generated README auth vars and command bullets appear on separate lines, and that generated CLI exposes `doctor`.
- [ ] Add a generated `doctor` command that reports base URL validity, auth env var presence using redacted fingerprints, and cache location.
- [ ] Rewrite README sections with clean Markdown tables and agent usage examples.
- [ ] Run `.\.venv\Scripts\python -m pytest tests\test_e2e.py -q`.

### Task 4: Dashboard Upgrade

**Files:**
- Modify: `src/ducktap/webui/app.py`
- Create: `tests/test_webui.py`

- [ ] Write failing tests for richer dashboard HTML: status metrics, source form, catalog filtering controls, scorecard/result area, and API catalog endpoint.
- [ ] Replace the minimal page with a polished workbench layout: compact status rail, source press panel, catalog table, generated run result panel, and embedded JavaScript that uses `/api/catalog` plus `/generate`.
- [ ] Keep the UI functional without a build step or external assets.
- [ ] Run `.\.venv\Scripts\python -m pytest tests\test_webui.py -q`.

### Task 5: Verification

**Files:**
- No production files.

- [ ] Run `.\.venv\Scripts\python -m pytest -q`.
- [ ] Run `.\.venv\Scripts\ruff check src tests`.
- [ ] Run `.\.venv\Scripts\ducktap press tests\fixtures\petstore.yaml --out .\out-test --name petstore`.
- [ ] Run `.\.venv\Scripts\ducktap shipcheck petstore --out-dir .\out-test`.
- [ ] Run `.\.venv\Scripts\ducktap scorecard tests\fixtures\petstore.yaml --out-dir .\out-test --fail-under 80`.
