# Anonymous reviewer bundle

## Purpose

The anonymous bundle is the paper's double-blind source-and-score replay artifact. It combines the
controlled benchmark, source-traceable revisions, and privacy-filtered model-service records needed
to recompute every reported endpoint. It does not reproduce hosted inference: model calls are never
issued during bundle construction or review replay.

The top-level `MANIFEST.json` derives its file count and SHA-256 map from the generated tree.
Documentation therefore carries no fixed file total.

## Included evidence

- the public 20-pair benchmark, policies, schemas, executable fixtures, and Lean package;
- exact Gatekeeper, Trivy, Cosign, and Agent Governance Toolkit revisions with upstream tests,
  licenses, finite cases, minimum-suite certificates, and offline validators;
- the frozen 465-repository discovery registry and agentgateway fixed-commit source-test receipt;
- the 24-item Gatekeeper study plan, 144-cell frozen schedule, all six sanitized repetition files,
  content-free failure taxonomy, aggregate, and privacy receipts;
- the r6 reviewer release and coverage addendum;
- the 90-pair balanced public challenge;
- the authored SLSA migration study and three pinned local replications;
- 1,320 content-free endpoint-audit records that reconstruct raw-strict, registered-parser, and
  full-contract action metrics across ten route stacks;
- the finite policy-difference enumerator, suite reducer, transition and mutation certificates, and
  minimum-suite derivations.

## Privacy boundary

Paper-facing records retain item and pair identities, gold and extracted actions, terminal classes,
endpoint validity, and correctness fields. Every scheduled failure remains in the end-to-end
denominator. The bundle omits raw response text, free-form transport errors, complete invalid
objects, provider request and response identifiers, account identifiers, credentials, hidden
reasoning, author provenance, private commit identity, and Git history.

The r6 metadata overlay corrects stale construction labels while preserving the byte-frozen source
manifest. The endpoint derivative records raw-strict and registered-parser actions plus parser
provenance before response-content redaction. The bundle includes the exact raw-strict parser and
the historical route-parser source needed to inspect that distinction. No audited response contains
a duplicate key. Frozen SLSA plans retain inert hashes for excluded exploratory runners; those
scripts and their results contribute no manuscript metric.

## Reviewer command

Use Python 3.11 or newer.

```bash
python -m pip install --require-hashes -r requirements-review.lock
python -m pip install --no-deps -e .
python scripts/run_review_checks.py
```

The default command validates source bindings, pair contracts, benchmark invariants, empirical
aggregates, endpoint provenance, privacy receipts, selected tests, and Lean fixtures.
`--python-only` runs the Python portion when Lean is unavailable. The command performs deterministic
source and score replay; it does not reissue hosted calls.

## Interpretation

A successful replay establishes internal consistency among released source bytes, datasets,
sanitized route records, validators, and manuscript statistics. The central model IDs share one
provider/API and adapter configuration; provider-side serving internals remain opaque. The
challenge was author-created and commit-frozen before calls according to retained workflow
receipts. Authored SLSA labels encode the paper's policy mapping, the deterministic executor defines
the policy ceiling, and Naive Bayes supplies a deliberately weak sanity control.
