---
name: ducktap-reprint
description: Re-press an existing DuckTap CLI under the latest factory version. Pulls the original spec, rebuilds artifacts, diffs the scorecard.
version: 0.1.0
allowed-tools:
  - Bash
  - Read
  - Write
---

# /ducktap-reprint

Reprint a previously generated CLI:

```bash
/ducktap-reprint petstore
```

Steps:

1. Locate the prior run in `./out/<name>-dt-cli/` and parse provenance from its `README.md` (`Provenance: <discoverer> from <source>`).
2. Run `ducktap press <source> --name <name> --out ./out`.
3. Run `ducktap scorecard` before and after; print the delta.
4. Show `git diff` against the previous CLI if the output is under version control.
