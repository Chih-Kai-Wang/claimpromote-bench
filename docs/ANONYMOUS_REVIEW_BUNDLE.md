# Anonymous reviewer bundle

## Purpose

The anonymous bundle is the paper's double-blind replay artifact. It combines the controlled
benchmark, source-traceable revisions, and privacy-filtered model-service records needed to
recompute every reported endpoint. Model inference is never invoked during bundle construction or
review replay.

The top-level `MANIFEST.json` derives its file count and SHA-256 map from the generated tree.
Documentation therefore carries no fixed file total.

## Included evidence

- the public 20-pair benchmark, policies, schemas, executable fixtures, and Lean package;
- exact Gatekeeper, Trivy, and Cosign revisions with upstream tests, licenses, finite cases,
  minimum-suite certificates, and offline validators;
- the 24-item Gatekeeper study plan, 144-cell frozen schedule, all six sanitized repetition files,
  content-free failure taxonomy, aggregate, and privacy receipts;
- the r6 reviewer release and coverage addendum;
- the 90-pair balanced public challenge;
- the authored SLSA migration study and three pinned local replications;
- 1,320 content-free dual-endpoint item records that reconstruct strict-action and contract-action
  metrics across ten route stacks;
- the policy-difference compiler, transition and mutation certificates, and minimum-suite
  derivations; and
- the frozen naturalistic-candidate registry and its zero-case pre-inference decision.

## Privacy boundary

Paper-facing records retain item and pair identities, gold and extracted actions, terminal classes,
endpoint validity, and correctness fields. Every scheduled failure remains in the end-to-end
denominator. The bundle omits raw response text, free-form transport errors, complete invalid
objects, provider request and response identifiers, account identifiers, credentials, hidden
reasoning, author provenance, private commit identity, and Git history.

The r6 metadata overlay corrects stale construction labels while preserving the byte-frozen source
manifest. The dual-endpoint derivative records the exact extracted action and extraction class
before response-content redaction, allowing metric replay within the release boundary.

## Reviewer command

```bash
python -m pip install --require-hashes -r requirements-review.lock
python -m pip install --no-deps -e .
python scripts/run_review_checks.py
```

The default command validates source bindings, pair contracts, benchmark invariants, empirical
aggregates, privacy receipts, selected tests, and Lean fixtures. `--python-only` runs the Python
portion when Lean is unavailable.

## Interpretation

A successful replay establishes internal consistency among released source bytes, datasets,
sanitized route records, validators, and manuscript statistics. Hosted route values describe the
complete time-stamped service stack. The public challenge measures frozen robustness. Authored
SLSA labels encode the paper's policy mapping, the deterministic executor defines the policy
ceiling, and Naive Bayes supplies a deliberately weak sanity control.
