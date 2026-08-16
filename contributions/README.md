# Contributed model runs

This directory accepts externally executed, hash-bound model runs without requiring the
maintainer to pay for every model or hardware configuration.

Each contribution lives in one directory:

```text
contributions/<short-name>/
  contribution.json
  run.jsonl
```

The manifest must satisfy `schemas/run-contribution.schema.json`. The run file must satisfy
the existing run-record contract, cover every item exactly once, reproduce the frozen prompt
hashes, and use one immutable model/runtime/arm/seed/hardware identity.

Before opening a pull request, run:

```bash
python -m claimpromotebench.contributions \
  --manifest contributions/<short-name>/contribution.json
```

To validate every checked-in contribution:

```bash
python -m claimpromotebench.contributions --root contributions
```

A contribution is data, not an endorsement or an independent reproduction by itself. The
maintainer may reject results with unverifiable model revisions, mutable API aliases,
ambiguous licensing, secrets, personal data, incomplete prompts, or non-reproducible runtime
metadata.
