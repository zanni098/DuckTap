---
name: ducktap-publish
description: Push a generated DuckTap CLI to GitHub and (optionally) PyPI.
version: 0.1.0
allowed-tools:
  - Bash
  - Read
  - Write
---

# /ducktap-publish

```bash
/ducktap-publish petstore
```

Steps:

1. Run `ducktap publish <name> --out-dir ./out --dry-run` first and show the user the
   plan. The command runs shipcheck, initialises git, creates the GitHub repo via `gh`,
   builds, and uploads to PyPI — each step reported as OK/FAIL.
2. When the user confirms, run it for real: `ducktap publish <name> --out-dir ./out`.
   - `--no-pypi` for GitHub only, `--no-github` for PyPI only, `--private` for a
     private repo.
   - PyPI upload needs `twine` installed and credentials in the environment
     (`TWINE_USERNAME` / `TWINE_PASSWORD`, or a `~/.pypirc`). Never write a token
     into the repo.
3. If a step fails, report its `stderr` verbatim rather than retrying blindly — a
   failed shipcheck means the generated CLI is not shippable yet.
4. Open the new repo URL.
