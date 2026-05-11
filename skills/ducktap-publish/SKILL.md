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
/ducktap-publish petstore --org <github-user-or-org>
```

Steps:

1. `cd out/<name>-dt-cli` and `git init && git add -A && git commit -m "initial: <name> via DuckTap"`.
2. `gh repo create <org>/<name>-dt-cli --public --source=. --push` (requires `gh`).
3. If `--pypi` was passed, run `python -m build && twine upload dist/*` (must have `TWINE_PASSWORD` set).
4. Open the new repo URL.
