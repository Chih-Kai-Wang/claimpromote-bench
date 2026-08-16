# Contributing model runs

ClaimPromoteBench accepts externally executed model runs so model and hardware diversity can
accumulate without requiring one maintainer to purchase every API or GPU configuration.
Contributed results are accepted only as immutable, reproducible data packages.

## What a contribution contains

Create one directory:

```text
contributions/<descriptive-name>/
  contribution.json
  run.jsonl
```

`run.jsonl` must follow `schemas/run-record.schema.json`. It must contain every frozen item
exactly once and use one model artifact, runtime, arm, seed, quantization, and hardware
identity throughout the file.

Start `contribution.json` as a draft containing only the human-supplied fields:

```json
{
  "schema_version": "1.0.0",
  "contributor": {
    "github_login": "your-login",
    "display_name": "Your Name",
    "attestation": true
  },
  "dataset_gold_file": "data/alpha/gold.jsonl",
  "run_file": "run.jsonl",
  "license": "MIT",
  "consent": {
    "redistribution": true,
    "public_attribution": true,
    "contains_secrets": false,
    "contains_personal_data": false,
    "terms_accepted": true
  },
  "reproduction": {
    "command": ["llama-cli", "...exact arguments..."],
    "runtime": "llama.cpp plus exact commit and build details",
    "source_revision": "immutable model revision",
    "network_access": false,
    "notes": "Anything needed to reproduce the run."
  }
}
```

Do not manually invent hashes or copy an identity from another run. Derive them from the
actual file:

```bash
python -m claimpromotebench.contributions \
  --prepare contributions/<descriptive-name>/contribution.json \
  --write
```

Preparation validates the complete run first, then inserts:

- the frozen dataset-manifest SHA-256;
- the run-file SHA-256;
- the immutable model/runtime/arm/seed/hardware identity read from the run records;
- a stable contribution ID bound to the contributor, dataset, run bytes, identity, and
  license.

Validate the finished package:

```bash
python -m claimpromotebench.contributions \
  --manifest contributions/<descriptive-name>/contribution.json
```

Run the full repository gate before submitting:

```bash
python -m claimpromotebench.contributions --root contributions
python -m pytest
ruff check .
ruff format --check .
mypy
```

## Required provenance

A contribution must identify a frozen model artifact or weight file with its SHA-256. Mutable
API aliases such as `latest` are not sufficient. Record the exact runtime commit,
quantization, seed, hardware, prompt hashes, output token count, latency, and verifier-call
count. If the run used network access, state that explicitly and document which requests were
necessary.

The submitted reproduction command is stored as data and is never executed by the validator.
The validator does not run contributor commands or load contributor code.

## Automatic rejection

Validation fails closed when any of the following occurs:

- the run file or dataset manifest changed after preparation;
- a prompt hash differs from the frozen renderer;
- an item is missing, duplicated, or unknown;
- one file mixes multiple run identities;
- the manifest identity disagrees with the run records;
- the contribution ID is copied or stale;
- a path escapes its allowed directory;
- a duplicate contribution or duplicate validated run already exists;
- redistribution, attribution, privacy, secret, or licensing attestations are missing.

## Interpretation and credit

A passing package proves contract compliance and byte-level binding. It does not prove that
the contributor independently reproduced the full research claim, that the model is free of
contamination, or that the hardware report is externally audited.

Accepted contributors are attributed by GitHub login in the manifest and repository history.
Results remain separated by model artifact, runtime, seed, hardware, and intervention arm;
they are never silently pooled across incompatible identities.
