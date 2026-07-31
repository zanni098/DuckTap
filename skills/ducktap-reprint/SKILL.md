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

1. Read the provenance manifest the previous press wrote: `ducktap info --out-dir ./out`
   (or `--json` for the raw `.ducktap.json`). It carries the original source, the spec
   checksum, the targets, the archetype and the DuckTap version that produced it.
2. Run `ducktap press <source> --name <name> --out ./out` with the same targets.
3. Run `ducktap scorecard` before and after; print the delta.
4. Compare `spec_checksum` before and after. Unchanged means the upstream spec did not
   move and any diff comes from DuckTap itself; changed means the API did.
5. Show `git diff` against the previous CLI if the output is under version control.
   Presses are deterministic, so an empty diff is the expected result of a no-op
   reprint — flag it if the diff is noisy.
