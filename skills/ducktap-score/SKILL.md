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

Runs `ducktap scorecard out/petstore.spec.json --out-dir ./out` and explains each dimension (coverage, documentation, auth, typed_params, artifacts, naming). Suggest 1-3 concrete fixes for the lowest-scoring dimensions.
