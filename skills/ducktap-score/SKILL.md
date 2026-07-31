---
name: ducktap-score
description: Run the DuckTap scorecard against a generated CLI and explain the breakdown.
version: 0.1.0
allowed-tools:
  - Bash
  - Read
---

# /ducktap-score

```bash
/ducktap-score petstore
```

Runs `ducktap scorecard out/petstore.spec.json --out-dir ./out` and explains each
dimension (coverage, documentation, auth, typed_params, artifacts, naming,
domain_correctness). Suggest 1-3 concrete fixes for the lowest-scoring dimensions.

Pass `--fail-under <n>` to make the command exit non-zero below a threshold, which is
how it is used in CI.

For a stronger signal than the scorecard, run `ducktap verify <name> --source <spec>`:
it mechanically checks the generated CLI against the spec (no hallucinated paths, every
operation reachable, auth header matches, no write-only mirror tables).
